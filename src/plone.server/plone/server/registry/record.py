# -*- coding: utf-8 -*-
from persistent import Persistent
from plone.server.registry.events import RecordModifiedEvent
from plone.server.registry.interfaces import IInterfaceAwareRecord
from plone.server.registry.interfaces import IPersistentField
from plone.server.registry.interfaces import IRecord
from zope.dottedname.resolve import resolve
from zope.event import notify
from zope.interface import implementer
from zope.interface import alsoProvides

_marker = object()


@implementer(IRecord)
class Record(Persistent):
    """A record that is stored in the registry.

    If __parent__ is set, consider this a "bound" record. In this case, the
    field and value are read from and written to the parent registry.

    BBB: The current storage implementation does not actually store Record
    objects directly. However, we keep the Persistent base class so that old
    values may be loaded during automated migration.
    """

    __name__ = u""
    __parent__ = None

    def __init__(self, field, value=_marker, _validate=True):

        if _validate and not IPersistentField.providedBy(field):
            raise ValueError("Field is not persistent")

        if value is _marker:
            value = field.default
        else:
            if _validate:
                if value != field.missing_value:
                    bound_field = field.bind(self)
                    bound_field.validate(value)

        # Bypass event notification and setting on the parent
        self._field = field
        self._value = value

        if field.interfaceName:
            alsoProvides(self, IInterfaceAwareRecord)

    # The 'field' property

    def _get_field(self):
        if self.__parent__ is not None:
            return self.__parent__.records._getField(self.__name__)
        return self._field

    def _set_field(self, value):
        if self.__parent__ is not None:
            self.__parent__.records._setField(self.__name__, value)
        self._field = value

    _field = None
    field = property(_get_field, _set_field)

    # The 'value' property

    def _get_value(self):
        if self.__parent__ is not None:
            return self.__parent__.records._values[self.__name__]
        return self._value

    def _set_value(self, value):

        field = self.field

        if field is None:
            raise ValueError("The record's field must be set before its value")

        field = field.bind(self)
        if value != field.missing_value:
            field.validate(value)

        oldValue = self._value
        self._value = value

        if self.__parent__ is not None:
            self.__parent__.records._values[self.__name__] = value

        notify(RecordModifiedEvent(self, oldValue, value))

    _value = None
    value = property(_get_value, _set_value)

    # Interface name, field name and interface instance

    @property
    def interfaceName(self):
        return self.field.interfaceName

    @property
    def fieldName(self):
        return self.field.fieldName

    @property
    def interface(self):
        try:
            return resolve(self.interfaceName)
        except ImportError:
            return None

    # Print representation

    def __repr__(self):
        return "<Record %s>" % self.__name__
