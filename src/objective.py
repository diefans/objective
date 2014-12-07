"""``objective`` helps you to ensure and transform certain input values in a flexible way.

There are other means that try to cover that issue:

    - colander
    - formencode

All seem to fail or don't provide me with satisfactory results.
So I invented the wheel a little bit rounder - at least for me.


The plan is to declarativly build a structure which has to be instanciated for examination.



"""


class Item(object):

    """Declares an item of a mapping to be instantiated."""

    def __init__(self, node_class=None, name=None, *args, **kwargs):
        """Prepares node class instantiation.

        :param node_class: the type of the node
        :param name: the explicit name of the node
        :param args: additional arguments for the node instantiation
        :param kwargs: additional keyword arguments for the node instantiation

        """
        # the instance of the node this item has created
        # this will later be created and returned by the descriptor
        self.node = None

        self.node_class = node_class
        self.name = name

        self.node_args = args
        self.node_kwargs = kwargs

    def __get__(self, obj, cls=None):
        """Resolve the ``Node`` instance or return the ``Item`` instance."""

        if obj is None:
            # return the Item if accessed over class
            return self

        if self.node is None:
            self.node = self.create_node()

        return self.node

    def __call__(self, node_class):
        """Decorate a class, which will be setup for instantiation of the node."""

        self.node_class = node_class

        return self

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.name} = {0.node}>"\
            .format(self)

    def attach_name(self, name):
        """Attach a name to an item.

        Called by NodeMeta to attach a name to an item.

        If the item.name is already set the parent name will be ignored.
        So we are able to map certain external names, which might be reserved words
        to varying internal ones.

        :returns: a tuple of name, self

        """
        if not self.name:
            self.name = name

        return self.name, self

    def create_node(self):
        """Create a ``Node`` instance.

        All args and kwargs are forwarded to the node.

        :returns: a ``Node`` instance
        """

        if self.node_class is not None:
            node = self.node_class(*self.node_args, **self.node_kwargs)

            node._item = self

            return node

        raise ValueError("You have to create an ``Item`` by calling ``__init__`` with ``node_class`` argument"
                         " or by decorating a ``Node`` class.")


class NodeMeta(type):

    """Performs ``Node`` instantiation by lookup ``Item`` instances."""

    base = None

    def __new__(mcs, name, bases, dct):
        """Collect all ``Item`` instances and add them to the new class."""

        # collect all items
        items = {}

        # if we don't have a base yet, we ignore possible items
        if mcs.base:
            # inherite from bases
            for base in bases:
                if issubclass(base, mcs.base):
                    items.update(base._children)

        # take own items last
        # override name with explicit item.name
        items.update(item.attach_name(name)
                     for name, item in dct.iteritems()
                     if isinstance(item, Item))

        # add items to the new class
        dct['_children'] = items

        cls = type.__new__(mcs, name, bases, dct)

        # just register our base class so we know it for items collection
        if mcs.base is None:
            mcs.base = cls

        return cls


class Node(object):

    """A node of a tree like structure, which serves as a blueprint for value examination."""

    __metaclass__ = NodeMeta

    # stores all children items, collected by __new__
    _children = {}

    # the item this node is created by
    _item = None

    @property
    def _name(self):
        return self._item and self._item.name or None

    def __getitem__(self, name):
        """Returns a previously collected ``Item``, which will be a ``Node`` by descriptor magic."""

        if name in self._children:
            return self._children[name].__get__(self, self.__class__)

        raise KeyError("`{}` not in {}".format(name, self))

    def __repr__(self):
        """Represent a Node."""

        return "<{n.__class__.__name__}: {items}>"\
            .format(
                n=self, items=', '.join(sorted(self._children))
            )

    def __iter__(self):
        """Iterates over all items and returns appropriate nodes."""
        return iter(self.iteritems())

    def iteritems(self):
        for name in self._children:
            yield name, getattr(self, name)

    def itervalues(self):
        for name in self._children:
            yield getattr(self, name)

    def iterkeys(self):
        for name in self._children:
            yield name


# validator specific section
class Undefined(object):

    """Describes a value, which was not defined. So this is different from ``None``."""

    def __repr__(self):
        return "<{0.__class__.__name__}>".format(self)


class UndefinedValue(Exception):

    """Raised when a value is not defined."""


class Invalid(Exception):

    """Raised when a validator failed."""

    def __init__(self, node, msg=None, value=Undefined(), *args, **kwargs):
        super(Invalid, self).__init__(*args)

        self.node = node
        self.value = value
        self.msg = msg or "Invalid value for `{name}`: {0.value}"\
            .format(self, name=node._name)

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.node_name} = {0.value}>"\
            .format(self)

    @property
    def node_name(self):
        return self.node._name or self.node.__class__.__name__


class InvalidChildren(Invalid):

    """Contains a list of previously raised Invalids."""

    def __init__(self, node, children, *args, **kwargs):
        super(InvalidChildren, self).__init__(node, *args, **kwargs)

        self.children = children

    def __iter__(self):
        """Traverse through children an yield name, child."""

        for child in self.children:
            yield child.node._name, child


class InvalidType(Invalid):

    """Raised when a type is not as expected."""


class MissingValue(Invalid, UndefinedValue):

    """Raised when a value is not defined but seems to be mandatory."""


class IgnoreValue(UndefinedValue):

    """Raised when the undefined value shall be ignored."""


class Validator(object):

    def __call__(self, value, environment=None):
        """Perform value validation.

        Should raise ``Invalid`` if something seems wrong.
        """

        return value


# field specific section
class Missing(object):

    """Defines an action to be peformed when the value is missing."""

    def __init__(self, node, environment=None):
        self.node = node
        self.environment = environment or {}

    def __call__(self, value):
        """Just raise a ``MissingValue`` exception."""

        raise MissingValue(self.node,
                           value=value,
                           msg="Value for {0} is missing!".format(self.node._name))


class Ignore(Missing):

    def __call__(self, value):
        """We raise an ``IgnoreValue`` exception."""

        raise IgnoreValue("Ignore `{}`.".format(self.node._name))


class Field(Node):

    """A ``Field`` describes the value of a ``Node``.

    It can serialize and deserialize a value.

    An optional validator sanitizes the value before deserializing it.
    """

    validator = None

    def __init__(self, validator=None, **kwargs):
        """Optionally Assigns the validator.

        :param validator: the validator to be used
        :param missing: action to be performed when the value is ``Undefined`` and therefor missing
        """

        if callable(validator):
            self.validator = validator

        self.missing = kwargs.get('missing', Missing)

    def serialize(self, value):
        """Serialze a value into a transportable and interchangeable format."""
        # TODO

        return value

    def deserialize(self, value, environment=None):
        """Deserialize a value into a special application specific format or type.

        ``value`` can be ``Missing``, ``None`` or something else.

        :param value: the value to be deserialized
        :param environment: additional environment
        """

        if isinstance(value, Undefined):
            if isinstance(self.missing, type) and issubclass(self.missing, Missing):
                missing = self.missing(self, environment)

                # invoke missing callback
                value = missing(value)

            else:
                # we just assign any value
                value = self.missing

        if callable(self.validator):
            validated = self.validator(value, environment or {})

            return validated

        # we just return the value as is
        return value


class Mapping(Field):

    """A ``Mapping`` resembles a dict like structure."""

    def deserialize(self, value, environment=None):

        # first invoke super validation
        validated = super(Mapping, self).deserialize(
            value, environment=environment
        )

        # traverse items and match against validated struct
        mapping = self.traverse_children(validated, environment)

        return mapping

    def traverse_children(self, value, environment):
        """Traverse over all defined items and return a dictionary.

        :param value: a ``dict`` wich contains mapped values
        """

        mapping = {}

        invalids = []

        for name, item in self.iteritems():
            # deserialize each item
            try:
                mapping[name] = item.deserialize(
                    value.get(name, Undefined()), environment=environment
                )

            except IgnoreValue:
                # just ignore this value
                pass

            except Invalid as ex:
                # append this to the list of invalids, so we can return a complete overview of errors
                invalids.append(ex)

        if invalids:
            # on invalids this item is also ``Invalid``
            raise InvalidChildren(self, invalids)

        return mapping


# this is the test section
import pytest


class TestValidator(object):

    def test_validate(self):
        v = Validator()

        assert v('foo') == 'foo'


class TestFields(object):

    def test_schema(self):
        class S(Node):
            foo = Item(Field)

        assert isinstance(S.foo, Item)

        s = S()

        assert isinstance(s.foo, Node)
        assert isinstance(s.foo, Field)

    def test_mapping(self):

        class M(Mapping):
            foo = Item(Field)
            bar = Item(Field)
            bam = Item(Field, missing=Ignore)
            fom = Item(Field, missing='default')

        m = M()

        result = m.deserialize({
            'foo': 'foo',
            'bar': 'bar',
            'baz': 'baz'    # this should be ignored
        })

        assert result == {
            'foo': 'foo',
            'bar': 'bar',
            'fom': 'default'
        }

    def test_mapping_missing(self):

        class M(Mapping):
            foo = Item(Field, missing='1')
            bar = Item(Field)

            @Item()
            class bam(Mapping):

                foo = Item(Field)
                fom = Item(Field, missing='default')

        m = M(name='m')

        with pytest.raises(Invalid) as ex:
            m.deserialize({'bam': {}})

        assert isinstance(ex.value, InvalidChildren)
        assert ex.value.children[0].node == m.bam
        assert ex.value.children[0].children[0].node == m.bam.foo
        assert ex.value.children[1].node == m.bar


class TestNode(object):

    def test_schema(self):

        class Schema(Node):

            foo = Item(Node)
            _bar = Item(Node, name='bar')

            @Item(name='sub')
            class _sub(Node):
                fom = Item(Node)

        s = Schema()

        assert isinstance(s, Node)
        assert isinstance(s.foo, Node)
        assert isinstance(s._bar, Node)
        assert isinstance(s._sub, Node)
        assert isinstance(s._sub.fom, Node)
        assert isinstance(Schema.foo, Item)

    def test_name(self):
        class S(Node):

            foo = Item(Node)
            bar = Item(Node, name='BAR')

        s = S()

        assert s.foo._name == 'foo'
        assert s.bar._name == 'BAR'

    def test_iter(self):
        class S(Node):
            foo = Item(Node)
            bar = Item(Node)

        s = S()

        items = list(s)

        assert ('foo', s.foo) in items
        assert ('bar', s.bar) in items

    def test_inheritance(self):

        class S1(Node):
            foo = Item(Node)

        class S2(S1):
            bar = Item(Node)

        class S3(Node):
            bam = Item(Node)

        class S4(S2, S3):
            bar = Item(Node)

        assert 'foo' in S4._children
        assert 'bar' in S4._children

    def test_getitem(self):

        class S1(Node):
            foo = Item(Node)

            @Item(name='bam')
            class bar(Node):
                baz = Item(Node)
                bim = Item(Node)

        s = S1()

        assert isinstance(s['foo'], Node)
        assert isinstance(s['bam'], Node)
        assert isinstance(s['bam']['baz'], Node)

        # test id
        assert id(s['foo']) == id(s['foo'])

        with pytest.raises(KeyError) as ex:
            s['bam']['missing']

        assert ex.value.message == '`missing` not in <bar: baz, bim>'
