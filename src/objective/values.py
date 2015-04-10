class Undefined(object):        # pylint: disable=R0903

    """Describes a value, which was not defined. So this is different from ``None``."""

    def __repr__(self):
        return "<{0.__class__.__name__}>".format(self)


class Bunch(dict):

    """A dict whose items are also accessible as attributes."""

    def __init__(self, *args, **kwargs):
        self.__dict__ = self

        super(Bunch, self).__init__(*args, **kwargs)
