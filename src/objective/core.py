from collections import OrderedDict

from . import validation, exc, values


class Missing(object):

    """Defines an action to be peformed when the value is missing."""

    def __init__(self, node, environment=None):
        self.node = node
        self.environment = environment

    def __call__(self, value):
        """Just raise a ``MissingValue`` exception."""

        raise exc.MissingValue(
            self.node,
            value=value,
            msg="Value for `{0}` is missing!".format(self.node._name)           # pylint: disable=W0212
        )


class Ignore(Missing):

    def __call__(self, value):
        """We raise an ``IgnoreValue`` exception."""

        raise exc.IgnoreValue("Ignore `{}`.".format(self.node._name))               # pylint: disable=W0212


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

            node._item = self       # pylint: disable=W0212

            return node

        raise ValueError("You have to create an ``Item`` by calling ``__init__`` with ``node_class`` argument"
                         " or by decorating a ``Node`` class.")


class NodeMeta(type):

    """Performs ``Node`` instantiation by looking up ``Item`` instances."""

    base = None

    def __new__(mcs, name, bases, dct):
        """Collect all ``Item`` instances and add them to the new class."""

        # collect all items
        items = OrderedDict()

        # if we don't have a base yet, we ignore possible items
        if mcs.base:
            # inherite from bases
            for base in bases:
                if issubclass(base, mcs.base):
                    items.update(base._children)        # pylint: disable=W0212

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

    def __iter__(cls):
        return cls._children.iteritems()


class Node(object):

    """A node of a tree like structure, which serves as a blueprint for value examination."""

    __metaclass__ = NodeMeta

    # stores all child items, collected by __new__
    _children = {}

    # the item this node was created by
    _item = None

    @property
    def _name(self):
        return self._item and self._item.name or None

    def __contains__(self, name):
        return name in self._children

    def __getitem__(self, name):
        """Returns a previously collected ``Item``, which will be a ``Node`` by descriptor magic."""

        if name in self._children:
            return self._children[name].__get__(self, self.__class__)

        raise KeyError("`{}` not in {}".format(name, self))

    def __iter__(self):
        """Iterates over all items and returns appropriate nodes."""

        for name in self._children:
            yield name, getattr(self, name)

    def __repr__(self):
        """Represent a Node."""

        return "<{n.__class__.__name__}:{n._name} [{items}]>"\
            .format(
                n=self, items=', '.join(sorted(self._children))
            )

    def get(self, name, default=None):
        if name in self:
            return self[name]

        return default


class Field(Node):

    """A ``Field`` describes the value of a ``Node``.

    It can serialize and deserialize a value.

    An optional validator sanitizes the value after deserializing it.
    """

    # create a validator in the Field
    # _validator = None

    def __init__(self, validator=None, **kwargs):
        """Optionally Assigns the validator.

        :param validator: the validator to be used
        :param missing: action to be performed when the value is ``Undefined`` and therefor missing
        """

        if callable(validator):
            setattr(self, "_validator", validator)

        # this is intentionally in kwargs, so we can also apply ``None`` for missing
        self._missing = kwargs.get('missing', Missing)

        # missing=Ignore shortcut: optional=True
        if 'missing' not in kwargs and kwargs.get('optional', False):
            self._missing = Ignore

    def resolve_value(self, value, environment=None):
        """Resolve the value.

        Either apply missing or leave the value as is.

        :param value: the value either from deserialize or serialize
        :param environment: an optional environment
        """

        # here we care about Undefined values
        if isinstance(value, values.Undefined):
            if isinstance(self._missing, type) and issubclass(self._missing, Missing):
                # instantiate the missing thing
                missing = self._missing(self, environment)

                # invoke missing callback
                # the default is to raise a MissingValue() exception
                value = missing(value)

            elif callable(self._missing):
                value = self._missing()

            else:
                # we just assign any value
                value = self._missing

        return value

    def serialize(self, value, environment=None):
        """Serialze a value into a transportable and interchangeable format.

        The default assumption is that the value is JSON e.g. string or number.
        Some encoders also support datetime by default.

        Serialization should not be validated, since the developer app would be
        bounced, since the mistake comes from there - use unittests for this!

        """
        value = self.resolve_value(value, environment)

        return value

    @validation.validate
    def deserialize(self, value, environment=None):
        """Deserialize a value into a special application specific format or type.

        ``value`` can be ``Missing``, ``None`` or something else.

        :param value: the value to be deserialized
        :param environment: additional environment
        """
        value = self.resolve_value(value, environment)

        return value
