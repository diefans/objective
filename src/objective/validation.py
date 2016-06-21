import six

import validate_email

from . import exc


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


class Email(Validator):

    """Validate an email.

    if ``pyDNS`` is installed you can check mx and verify the existance of that
    email.

    """

    def __init__(self, verify=False, check_mx=False):
        self.check_mx = check_mx
        self.verify = verify

    def __call__(self, node, value, environment=None):
        if isinstance(value, six.string_types):
            if validate_email.validate_email(
                    value,
                    check_mx=self.check_mx,
                    verify=self.verify
            ):
                return value

        raise exc.Invalid()


class ValueMap(Validator):

    """Map certain values to other values."""

    def __init__(self, map_values, **kwargs):
        self.map_values = map_values

        if 'default' in kwargs:
            self.default = kwargs.get('default')

    def __call__(self, node, value, environment=None):
        if callable(self.map_values):
            value = self.map_values(value)

        else:
            # assume dict
            try:
                value = self.map_values[value]
            except KeyError:
                if 'default' not in self.__dict__:
                    raise exc.Invalid()

                value = self.default

        return value


class Chain(Validator):

    """Chains a set of validators."""

    def __init__(self, *validators):
        self.validators = validators

    def __call__(self, node, value, environment=None):
        for validator in self.validators:
            value = validator(node, value, environment=environment)

        return value


class FieldValue(Validator):

    """Deserialize the value by field."""

    def __init__(self, field):
        self.field_class = field

    def __call__(self, node, value, environment=None):
        field = self.field_class(environment=environment)

        value = field.deserialize(value)

        return value
