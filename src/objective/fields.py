from datetime import datetime
from dateutil.parser import parse as dateutil_parse
import pytz

from . import core, exc, validation, values


class ListMixin(object):
    items = core.Item(core.Field)

    def __new__(cls, items=None, **kwargs):
        inst = core.Field.__new__(cls, items=items, **kwargs)

        # inject items only for the instance if it is defined
        if items is not None:
            inst.__dict__['items'] = items.__get__(inst, cls)
        return inst

    def _traverse(self, value, environment=None):
        # items must be defined
        items = getattr(self, 'items')

        for item in value:
            yield items.deserialize(item, environment)


class Set(core.Field, ListMixin):

    @validation.validate
    def deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value."""

        # first invoke super validation
        validated = super(Set, self).deserialize(value, environment)

        # traverse items and match against validated struct
        collection = {item for item in self._traverse(validated, environment)}

        return collection


class List(core.Field, ListMixin):

    @validation.validate
    def deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value."""

        # first invoke super validation
        validated = super(List, self).deserialize(value, environment, validate=False)

        # traverse items and match against validated struct
        collection = [item for item in self._traverse(validated, environment)]

        return collection


class Mapping(core.Field):

    """A ``Mapping`` resembles a :py:obj:`dict` like structure."""

    _type = dict

    def _traverse(self, value, environment=None):
        """Traverse over all defined items and return a dictionary."""

        # self is a good iterator
        return self

    def serialize(self, value, environment=None):

        serialized = super(Mapping, self).serialize(value, environment)

        mapping = self._type()

        invalids = []

        for name, item in self._traverse(serialized, environment):

            # deserialize each item
            try:
                mapping[name] = item.serialize(
                    serialized.get(name, values.Undefined()), environment
                )

            except exc.IgnoreValue:
                # just ignore this value
                pass

            except exc.Invalid as ex:
                # append this to the list of invalids, so we can return a complete overview of errors
                invalids.append(ex)

        if invalids:
            # on invalids this item is also ``Invalid``
            raise exc.InvalidChildren(self, invalids)

        return mapping

    @validation.validate
    def deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value.

        :param value: a ``dict`` wich contains mapped values
        """

        # first invoke super validation
        validated = super(Mapping, self).deserialize(value, environment, validate=False)

        # traverse items and match against validated struct
        mapping = self._type()

        invalids = []

        for name, item in self._traverse(validated, environment):

            # deserialize each item
            try:
                mapping[name] = item.deserialize(
                    validated.get(name, values.Undefined()), environment
                )

            except exc.IgnoreValue:
                # just ignore this value
                pass

            except exc.Invalid as ex:
                # append this to the list of invalids, so we can return a complete overview of errors
                invalids.append(ex)

        if invalids:
            # on invalids this item is also ``Invalid``
            raise exc.InvalidChildren(self, invalids)

        return mapping


class BunchMapping(Mapping):

    """Will de/serialize into a :py:class:`.values.Bunch`."""

    _type = values.Bunch


class Number(core.Field):

    """Represents a numeric value ``float`` or ``int``."""

    types = (int, float)

    @validation.validate
    def deserialize(self, value, environment=None):
        value = super(Number, self).deserialize(value, environment, validate=False)

        for _type in self.types:
            try:
                casted = _type(value)
                return casted

            except ValueError:      # pylint: disable=W0704
                pass

        raise exc.InvalidValue(
            self,
            msg="Invalid value `{value}` for `{types}`".format(
                value=value, types=self.types
            ),
            value=value
        )


class Float(Number):

    """Represents a ``float`` value."""

    types = (float,)


class Int(Number):

    """Represents an ``int`` value."""

    types = (int,)


class Unicode(core.Field):

    """Represents a text string."""

    encoding = "utf-8"

    @validation.validate
    def deserialize(self, value, environment=None):
        value = super(Unicode, self).deserialize(value, environment, validate=False)

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


class UtcDateTime(core.Field):

    """Represents a datetime string in UTC."""

    @validation.validate
    def deserialize(self, value, environment=None):
        value = super(UtcDateTime, self).deserialize(value, environment, validate=False)

        # test for a timestamp
        if isinstance(value, basestring):
            # try utc datetime string
            return dateutil_parse(value)

        elif isinstance(value, (int, float)):
            dt = datetime.utcfromtimestamp(value)
            return pytz.utc.localize(dt)

        elif isinstance(value, datetime):
            return value

        raise exc.InvalidValue(self, "Invalid DateTime", value)

    def serialize(self, value, environment=None):
        value = super(UtcDateTime, self).serialize(value, environment)
        return str(value)
