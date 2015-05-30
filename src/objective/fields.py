from datetime import datetime
from dateutil.parser import parse as dateutil_parse
import pytz

from collections import OrderedDict
from . import core, exc, values


class CollectionMixin(object):
    items = core.Item(core.Field)

    def __new__(cls, items=None, **kwargs):
        inst = core.Field.__new__(cls, items=items, **kwargs)

        # inject items only for the instance if it is defined
        if items is not None:
            inst.__dict__['items'] = items.__get__(inst, cls)
        return inst


class Set(core.Field, CollectionMixin):

    def _deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value."""

        items = self.items

        # traverse items and match against validated struct
        collection = {items.deserialize(subvalue, environment) for subvalue in value}

        return collection


class List(core.Field, CollectionMixin):

    def _deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value."""

        items = self.items

        # traverse items and match against validated struct
        collection = [items.deserialize(subvalue, environment) for subvalue in value]

        return collection


class Mapping(core.Field):

    """A ``Mapping`` resembles a :py:obj:`dict` like structure."""

    _type = dict

    def _serialize(self, value, environment=None):

        mapping = self._type()

        invalids = []

        for name, item in self.__children__:

            # deserialize each item
            try:
                mapping[name] = item.serialize(
                    value.get(name, values.Undefined), environment
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

    def _deserialize(self, value, environment=None):
        """A collection traverses over something to deserialize its value.

        :param value: a ``dict`` wich contains mapped values
        """

        # traverse items and match against validated struct
        mapping = self._type()

        invalids = []

        for name, item in self.__children__:

            # deserialize each item
            try:
                mapping[name] = item.deserialize(
                    value.get(name, values.Undefined), environment
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


class OrderedMapping(Mapping):

    """A :py:class:OrderedDict result."""

    _type = OrderedDict


class Number(core.Field):

    """Represents a numeric value ``float`` or ``int``."""

    types = (int, float)

    def _deserialize(self, value, environment=None):
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

    def _deserialize(self, value, environment=None):
        # ensure we have a unicode afterwards

        try:
            value = unicode(value, self.encoding)

        except TypeError:
            # may be we have an integer or another number
            value = unicode(value)

        return value

    def serialize(self, value, environment=None):
        return value.encode(self.encoding)


def totimestamp(dt, epoch=datetime(1970, 1, 1, tzinfo=pytz.utc)):
    td = dt - epoch
    # return td.total_seconds()
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 1e6


class UtcDateTime(core.Field):

    """Represents a datetime string in UTC."""

    def _deserialize(self, value, environment=None):
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
        return str(value)
