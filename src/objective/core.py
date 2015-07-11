from collections import OrderedDict

import six

from . import exc, values


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
            msg="Value for `{0}` is missing!".format(self.node.__name__)
        )


class Ignore(Missing):

    """:py:class:`Ignore` will make the deserialization simply ignore the
    missing value."""

    def __call__(self, value):
        """We raise an ``IgnoreValue`` exception."""

        raise exc.IgnoreValue("Ignore `{}`.".format(self.node.__name__))


class Item(object):

    """Declares an item of a mapping to be instantiated."""

    __nodes__ = []

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
        self._node_class = None

        if node_class is not None:
            self.node_class = node_class

        self.name = name

        self.node_args = args
        self.node_kwargs = kwargs

    @property
    def node_class(self):
        return self._node_class

    @node_class.setter
    def node_class(self, cls):
        # register node class also in Item index, so we know the order
        self.__nodes__.append(cls)
        self._node_class = cls

    def __get__(self, obj, cls=None):
        """Resolve the ``Node`` instance or return the ``Item`` instance."""

        if obj is None:
            # return the node class if accessed over class
            return self.node_class

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

        Called by :py:class:`NodeMeta` to attach a name to an item.

        If the item.name is already set the parent name will be ignored.
        So we are able to map certain external names, which might be reserved words
        to varying internal ones.

        """

        if not self.name:
            self.name = name

    def create_node(self):
        """Create a :py:class:`Node` instance.

        All args and kwargs are forwarded to the node.

        :returns: a :py:class:`Node` instance
        """

        if self.node_class is not None:
            node = self.node_class(*self.node_args, **self.node_kwargs)

            node.__item__ = self

            return node

        raise ValueError("You have to create an ``Item`` by calling ``__init__`` with ``node_class`` argument"
                         " or by decorating a ``Node`` class.")


class NodeMeta(type):

    """Performs ``Node`` instantiation by looking up ``Item`` instances."""

    __node_base__ = None

    def __new__(mcs, name, bases, dct):
        """Collect all ``Item`` instances and add them to the new class."""

        cls = type.__new__(mcs, name, bases, dct)

        # just register our base class so we know it for items collection
        if mcs.__node_base__ is None:
            mcs.__node_base__ = cls

        return cls

    def __init__(cls, name, bases, dct):
        super(NodeMeta, cls).__init__(name, bases, dct)

        # a simple name mapping
        cls.__names__ = OrderedDict()

        # if we don't have a base yet, we ignore possible items
        if cls.__node_base__:
            # inherite from bases
            for base in bases:
                if issubclass(base, cls.__node_base__):
                    cls.__names__.update(base.__names__)

        # take own items last
        for name, item in six.iteritems(dct):
            if isinstance(item, Item):
                # set name if not already set by Item call
                item.attach_name(name)
                cls.__names__[item.name or name] = name

    def __contains__(cls, name):
        return name in cls.__names__

    def __getitem__(cls, name):
        if name in cls:
            return getattr(cls, cls.__names__[name])

        raise KeyError("`{}` not in {}".format(name, cls))

    def __iter__(cls):
        for name in cls.__names__:
            yield name, cls[name]


class Node(six.with_metaclass(NodeMeta)):

    """A node of a tree like structure, which serves as a blueprint for value examination."""

    # the item this node was created by
    __item__ = None

    def __init__(self):
        # prepare children
        self.__children__ = list(self)

    @property
    def __name__(self):
        return self.__item__ and self.__item__.name or None

    def __contains__(self, name):
        return name in self.__names__

    def __getitem__(self, name):
        """Returns a previously collected ``Item``, which will be a ``Node`` by descriptor magic."""

        if name in self:
            return getattr(self, self.__names__[name])

        raise KeyError("`{}` not in {}".format(name, self))

    def __iter__(self):
        """Iterates over all items and returns appropriate nodes."""

        for name in self.__names__:
            yield name, self[name]

    def __repr__(self):
        """Represent a Node."""

        return "<{n.__class__.__name__}:{n.__name__} [{items}]>"\
            .format(
                n=self, items=', '.join(sorted(name for name, _ in self))
            )


class Field(Node):

    """A ``Field`` describes the value of a ``Node``.

    It can serialize and deserialize a value. An optional validator sanitizes
    the value after deserializing it.

    """

    # create a validator in the Field
    _validator = None

    def __init__(self, validator=None, **kwargs):
        """Optionally Assigns the validator.

        :param validator: the validator to be used
        :param missing: action to be performed when the value is ``Undefined`` and therefor missing

        """
        super(Field, self).__init__()

        if validator is not None:
            setattr(self, "_validator", validator)

        # this is intentionally in kwargs, so we can also apply ``None`` for missing
        self._missing = kwargs.get('missing', Missing)

        # missing=Ignore shortcut: optional=True
        if 'missing' not in kwargs and kwargs.get('optional', False):
            self._missing = Ignore

    def _resolve_value(self, value, environment=None):
        """Resolve the value.

        Either apply missing or leave the value as is.

        :param value: the value either from deserialize or serialize
        :param environment: an optional environment
        """

        # here we care about Undefined values
        if value == values.Undefined:
            if isinstance(self._missing, type) and issubclass(self._missing, Missing):
                # instantiate the missing thing
                missing = self._missing(self, environment)

                # invoke missing callback
                # the default is to raise a MissingValue() exception
                value = missing(value)

            elif hasattr(self._missing, "__call__"):
                value = self._missing()

            else:
                # we just assign any value
                value = self._missing

        return value

    def _serialize(self, value, environment=None):                # pylint: disable=R0201
        """Serialization worker."""

        return value

    def serialize(self, value, environment=None):
        """Serialze a value into a transportable and interchangeable format.

        The default assumption is that the value is JSON e.g. string or number.
        Some encoders also support datetime by default.

        Serialization should not be validated, since the developer app would be
        bounced, since the mistake comes from there - use unittests for this!

        """
        value = self._resolve_value(value, environment)

        value = self._serialize(value, environment)

        return value

    def _deserialize(self, value, environment=None):              # pylint: disable=R0201
        """Derserialization worker method."""

        return value

    def deserialize(self, value, environment=None):
        """Deserialize a value into a special application specific format or type.

        ``value`` can be ``Missing``, ``None`` or something else.

        :param value: the value to be deserialized
        :param environment: additional environment
        """

        value = self._resolve_value(value, environment)

        try:
            value = self._deserialize(value, environment)

            if self._validator is not None:
                value = self._validator(self, value, environment)     # pylint: disable=E1102

        except exc.InvalidValue as ex:
            # just reraise
            raise

        except (exc.Invalid, ValueError, TypeError):
            # we convert a bare Invalid into InvalidValue
            raise exc.InvalidValue(self, value=value)

        return value
