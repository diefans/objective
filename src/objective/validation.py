import functools

from . import exc


def validate(meth):
    """Decorate a deserialize function with a validator."""

    @functools.wraps(meth)
    def wrapper(self, value, environment=None, validate=True):      # pylint: disable=W0621
        # get deserialize value
        value = meth(self, value, environment)

        # we disable validation on demand
        # this is useful when calling the super class deserialize method
        validator = getattr(self, '_validator', None)
        if validate and callable(validator):   # pylint: disable=W0212
            try:
                value = validator(self, value, environment)     # pylint: disable=W0212

            except exc.InvalidValue:
                # just reraise
                raise

            except exc.Invalid:
                # we convert a bare Invalid into InvalidValue
                raise exc.InvalidValue(self, value=value)

        return value

    return wrapper


class Validator(object):

    """A validator make assertions upon the deserialized value.

    You can use a validator to convert the value into something else.
    """

    def __call__(self, node, value, environment=None):
        """Perform value validation.

        Should raise ``Invalid`` if something seems wrong.
        """

        return value


class OneOf(Validator):
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, node, value, environment=None):
        if value in self.choices:
            return value

        raise exc.Invalid()


class NoneOf(Validator):
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, node, value, environment=None):
        if value in self.choices:
            raise exc.Invalid()

        return value
