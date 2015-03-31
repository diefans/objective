"""``objective`` helps you to ensure and transform certain input values in a flexible way.

There are other means that try to cover that issue:

    - colander
    - formencode

All seem to fail or don't provide me with satisfactory results.
So I invented the wheel a little bit rounder - at least for me.


The plan is to declarativly build a structure which has to be instanciated for examination.

Basic assumption is that serialization format is a JSON like representation of data.

"""
import functools

from datetime import datetime
from dateutil.parser import parse as dateutil_parse
import pytz


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
        items = {}

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

    def __getitem__(self, name):
        """Returns a previously collected ``Item``, which will be a ``Node`` by descriptor magic."""

        if name in self._children:
            return self._children[name].__get__(self, self.__class__)

        raise KeyError("`{}` not in {}".format(name, self))

    def __contains__(self, name):
        return name in self._children

    def get(self, name, default=None):
        if name in self:
            return self[name]

        return default

    def __iter__(self):
        """Iterates over all items and returns appropriate nodes."""

        for name in self._children:
            yield name, getattr(self, name)

    def iteritems(self):
        return iter(self)

    def itervalues(self):
        for name in self._children:
            yield getattr(self, name)

    def iterkeys(self):
        for name in self._children:
            yield name

    def __repr__(self):
        """Represent a Node."""

        return "<{n.__class__.__name__}: {items}>"\
            .format(
                n=self, items=', '.join(sorted(self._children))
            )


# validator specific section
class Undefined(object):        # pylint: disable=R0903

    """Describes a value, which was not defined. So this is different from ``None``."""

    def __repr__(self):
        return "<{0.__class__.__name__}>".format(self)


class UndefinedValue(Exception):

    """Raised when a value is not defined."""


class Invalid(Exception):

    """Raised when a validator failed."""

    def __init__(self, node, msg=None, value=Undefined(), *args, **kwargs):
        super(Invalid, self).__init__(node, msg, value, *args)

        self.node = node
        self.value = value
        self.message = msg or "Invalid value for `{name}`: {0.value}"\
            .format(self, name=self.node_name)

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.node_name} = {0.value}>"\
            .format(self)

    @property
    def node_name(self):
        """Return the name of this node or its class name."""

        return self.node._name or self.node.__class__.__name__              # pylint: disable=W0212


class InvalidChildren(Invalid):

    """Contains a list of previously raised Invalids."""

    def __init__(self, node, children, *args, **kwargs):
        super(InvalidChildren, self).__init__(node, *args, **kwargs)

        self.children = children

    def __iter__(self):
        """Traverse through children an yield name, child."""

        for invalid in self.children:
            yield [invalid], invalid

            if isinstance(invalid, InvalidChildren):
                for path, child in invalid:
                    yield [invalid] + list(path), child

    def error_dict(self):
        return {
            tuple(x.node_name for x in path): invalid.message
            for path, invalid in self
        }


class InvalidValue(Invalid):

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
        self.environment = environment

    def __call__(self, value):
        """Just raise a ``MissingValue`` exception."""

        raise MissingValue(
            self.node,
            value=value,
            msg="Value for `{0}` is missing!".format(self.node._name)           # pylint: disable=W0212
        )


class Ignore(Missing):

    def __call__(self, value):
        """We raise an ``IgnoreValue`` exception."""

        raise IgnoreValue("Ignore `{}`.".format(self.node._name))               # pylint: disable=W0212


def validate(meth):
    """Decorate a deserialize function with a validator."""

    @functools.wraps(meth)
    def wrapper(self, value, environment=None):
        # get validated value from supers
        value = meth(self, value, environment)

        # validate after we resolved the value
        # TODO find out if we need to validate also the missing value

        if callable(self._validator):   # pylint: disable=W0212
            value = self._validator(value, environment)     # pylint: disable=W0212

        return value

    return wrapper


class Field(Node):

    """A ``Field`` describes the value of a ``Node``.

    It can serialize and deserialize a value.

    An optional validator sanitizes the value after deserializing it.
    """

    _validator = None

    def __init__(self, validator=None, **kwargs):
        """Optionally Assigns the validator.

        :param validator: the validator to be used
        :param missing: action to be performed when the value is ``Undefined`` and therefor missing
        """

        if callable(validator):
            self._validator = validator

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
        if isinstance(value, Undefined):
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

    @validate
    def deserialize(self, value, environment=None):
        """Deserialize a value into a special application specific format or type.

        ``value`` can be ``Missing``, ``None`` or something else.

        :param value: the value to be deserialized
        :param environment: additional environment
        """
        value = self.resolve_value(value, environment)

        return value


# fields section

class ListMixin(object):
    items = Item(Field)

    def __new__(cls, items=None, **kwargs):
        inst = Field.__new__(cls, items=items, **kwargs)

        # inject items only for the instance if it is defined
        if items is not None:
            inst.__dict__['items'] = items.__get__(inst, cls)
        return inst

    def traverse_children(self, value, environment=None):
        # items must be defined
        items = getattr(self, 'items')

        for item in value:
            yield items.deserialize(item, environment)


class Set(Field, ListMixin):

    @validate
    def deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value."""

        # first invoke super validation
        validated = super(Set, self).deserialize(value, environment)

        # traverse items and match against validated struct
        collection = {item for item in self.traverse_children(validated, environment)}

        return collection


class List(Field, ListMixin):

    @validate
    def deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value."""

        # first invoke super validation
        validated = super(List, self).deserialize(value, environment)

        # traverse items and match against validated struct
        collection = [item for item in self.traverse_children(validated, environment)]

        return collection


class Mapping(Field):

    """A ``Mapping`` resembles a dict like structure."""

    def traverse_children(self, value, environment=None):
        """Traverse over all defined items and return a dictionary."""

        for name, item in self:
            yield name, item

    def serialize(self, value, environment=None):

        serialized = super(Mapping, self).serialize(value, environment)

        mapping = {}

        invalids = []

        for name, item in self.traverse_children(serialized, environment):

            # deserialize each item
            try:
                mapping[name] = item.serialize(
                    serialized.get(name, Undefined()), environment
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

    @validate
    def deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value.

        :param value: a ``dict`` wich contains mapped values
        """

        # first invoke super validation
        validated = super(Mapping, self).deserialize(value, environment)

        # traverse items and match against validated struct
        mapping = {}

        invalids = []

        for name, item in self.traverse_children(validated, environment):

            # deserialize each item
            try:
                mapping[name] = item.deserialize(
                    validated.get(name, Undefined()), environment
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


class Number(Field):

    """Represents a numeric value ``float`` or ``int``."""

    types = (int, float)

    def deserialize(self, value, environment=None):
        value = super(Number, self).deserialize(value, environment)

        for _type in self.types:
            try:
                casted = _type(value)
                return casted

            except ValueError:      # pylint: disable=W0704
                pass

        raise InvalidValue(self, "Invalid value `{value}` for `{types}`"
                           .format(value=value, types=self.types), value)


class Float(Number):

    """Represents a ``float`` value."""

    types = (float,)


class Int(Number):

    """Represents an ``int`` value."""

    types = (int,)


class Unicode(Field):

    """Represents a text string."""

    encoding = "utf-8"

    def deserialize(self, value, environment=None):
        value = super(Unicode, self).deserialize(value, environment)

        # ensure we have a unicode afterwards
        if isinstance(value, unicode):
            pass

        elif isinstance(value, str):
            value = unicode(value, self.encoding)

        else:
            value = unicode(value)

        return value

    def serialize(self, value, environment=None):
        value = super(Unicode, self).serialize(value, environment)
        return value.encode(self.encoding)


def totimestamp(dt, epoch=datetime(1970, 1, 1, tzinfo=pytz.utc)):
    td = dt - epoch
    # return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 1e6


class UtcDateTime(Field):

    """Represents a datetime string in UTC."""

    def deserialize(self, value, environment=None):
        value = super(UtcDateTime, self).deserialize(value, environment)

        # test for a timestamp
        if isinstance(value, basestring):
            # try utc datetime string
            return dateutil_parse(value)

        elif isinstance(value, (int, float)):
            dt = datetime.utcfromtimestamp(value)
            return pytz.utc.localize(dt)

        elif isinstance(value, datetime):
            return value

        raise InvalidValue(self, "Invalid DateTime", value)

    def serialize(self, value, environment=None):
        value = super(UtcDateTime, self).serialize(value, environment)
        return str(value)
