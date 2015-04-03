from . import values


class UndefinedValue(Exception):

    """Raised when a value is not defined."""


class Invalid(Exception):

    """Raised when a validator failed."""


class InvalidValue(Invalid):

    """Raised when a type is not as expected."""

    def __init__(self, node, msg=None, **kwargs):
        super(InvalidValue, self).__init__()

        self.node = node
        self.value = kwargs.pop("value", values.Undefined())
        self.message = msg or "Invalid value for `{name}`: {0.value}"\
            .format(self, name=self.node_name)

    def __repr__(self):
        return "<{0.__class__.__name__}: {0.node_name} = {0.value}>"\
            .format(self)

    @property
    def node_name(self):
        """Return the name of this node or its class name."""

        return self.node._name or self.node.__class__.__name__              # pylint: disable=W0212


class InvalidChildren(InvalidValue):

    """Contains a list of previously raised Invalids."""

    def __init__(self, node, children, **kwargs):
        super(InvalidChildren, self).__init__(node, **kwargs)

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


class MissingValue(InvalidValue, UndefinedValue):

    """Raised when a value is not defined but seems to be mandatory."""


class IgnoreValue(UndefinedValue):

    """Raised when the undefined value shall be ignored."""
