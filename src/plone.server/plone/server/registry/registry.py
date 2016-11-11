# -*- coding: utf-8 -*-
from BTrees.OOBTree import OOBTree
from persistent import Persistent
from plone.server.registry.events import RecordAddedEvent
from plone.server.registry.events import RecordRemovedEvent
from plone.server.registry.fieldref import FieldRef
from plone.server.registry.interfaces import IFieldRef
from plone.server.registry.interfaces import InvalidRegistryKey
from plone.server.registry.interfaces import IPersistentField
from plone.server.registry.interfaces import IRecord
from plone.server.registry.interfaces import IRegistry
from plone.server.registry.record import Record
from plone.server.registry.recordsproxy import RecordsProxy
from plone.server.registry.recordsproxy import RecordsProxyCollection
from zope.component import queryAdapter
from zope.event import notify
from zope.interface import implementer
from zope.schema import getFieldNames
from zope.schema import getFieldsInOrder
import re
import warnings

import sys
if sys.version_info >= (3,):
    basestring = str


@implementer(IRegistry)
class Registry(Persistent):
    """The persistent registry
    """

    def __init__(self):
        self._records = _Records(self)

    # Basic value access API

    def __getitem__(self, name):
        # Fetch straight from records._values to avoid loading the field
        # as a separate persistent object
        return self.records._values[name]

    def get(self, name, default=None):
        # Fetch straight from records._values to avoid loading the field
        # as a separate persistent object
        return self.records._values.get(name, default)

    def __setitem__(self, name, value):
        # make sure we get the Record class' validation
        self.records[name].value = value

    def __contains__(self, name):
        return name in self.records._values

    # Records - make this a property so that it's readonly

    @property
    def records(self):
        # XXX: On-the-fly migration
        if isinstance(self._records, Records):
            self._migrateRecords()
        return self._records

    # Schema interface API

    def forInterface(self, interface, check=True, omit=(), prefix=None,
                     factory=None):
        if prefix is None:
            prefix = interface.__identifier__

        if not prefix.endswith("."):
            prefix += '.'

        if check:
            for name in getFieldNames(interface):
                if name not in omit and prefix + name not in self:
                    raise KeyError(
                        "Interface `{0}` defines a field `{1}`, for which "
                        "there is no record.".format(
                            interface.__identifier__,
                            name
                        )
                    )

        if factory is None:
            factory = RecordsProxy

        return factory(self, interface, omitted=omit, prefix=prefix)

    def registerInterface(self, interface, omit=(), prefix=None):
        if prefix is None:
            prefix = interface.__identifier__

        if not prefix.endswith("."):
            prefix += '.'

        for name, field in getFieldsInOrder(interface):
            if name in omit or field.readonly:
                continue
            record_name = prefix + name
            persistent_field = queryAdapter(field, IPersistentField)
            if persistent_field is None:
                raise TypeError(
                    "There is no persistent field equivalent for the field "
                    "`{0}` of type `{1}`.".format(
                        name,
                        field.__class__.__name__
                    )
                )

            persistent_field.interfaceName = interface.__identifier__
            persistent_field.fieldName = name

            value = persistent_field.default

            # Attempt to retain the exisiting value
            if record_name in self.records:
                existing_record = self.records[record_name]
                value = existing_record.value
                bound_field = persistent_field.bind(existing_record)
                try:
                    bound_field.validate(value)
                except:
                    value = persistent_field.default

            self.records[record_name] = Record(
                persistent_field,
                value,
                _validate=False
            )

    def collectionOfInterface(self, interface, check=True, omit=(),
                              prefix=None, factory=None):
        return RecordsProxyCollection(
            self,
            interface,
            check,
            omit,
            prefix,
            factory
        )

    # BBB

    def _migrateRecords(self):
        """BBB: Migrate from the old Records structure to the new. This is
        done the first time the "old" structure is accessed.
        """
        records = _Records(self)

        oldData = getattr(self._records, 'data', None)
        if oldData is not None:
            for name, oldRecord in oldData.iteritems():
                oldRecord._p_activate()
                if (
                    'field' in oldRecord.__dict__
                    and 'value' in oldRecord.__dict__
                ):
                    records._fields[name] = oldRecord.__dict__['field']
                    records._values[name] = oldRecord.__dict__['value']

        self._records = records


class _Records(object):
    """The records stored in the registry. This implements dict-like access
    to records, where as the Registry object implements dict-like read-only
    access to values.
    """
    __parent__ = None

    # Similar to zope.schema._field._isdotted, but allows up to one '/'
    _validkey = re.compile(
        r"([a-zA-Z][a-zA-Z0-9_-]*)"
        r"([.][a-zA-Z][a-zA-Z0-9_-]*)*"
        r"([/][a-zA-Z][a-zA-Z0-9_-]*)?"
        r"([.][a-zA-Z][a-zA-Z0-9_-]*)*"
        # use the whole line
        r"$").match

    def __init__(self, parent):
        self.__parent__ = parent

        self._fields = OOBTree()
        self._values = OOBTree()

    def __setitem__(self, name, record):
        if not self._validkey(name):
            raise InvalidRegistryKey(record)
        if not IRecord.providedBy(record):
            raise ValueError("Value must be a record")

        self._setField(name, record.field)
        self._values[name] = record.value

        record.__name__ = name
        record.__parent__ = self.__parent__

        notify(RecordAddedEvent(record))

    def __delitem__(self, name):
        record = self[name]

        # unbind the record so that it won't attempt to look up values from
        # the registry anymore
        record.__parent__ = None

        del self._fields[name]
        del self._values[name]

        notify(RecordRemovedEvent(record))

    def __getitem__(self, name):

        field = self._getField(name)
        value = self._values[name]

        record = Record(field, value, _validate=False)
        record.__name__ = name
        record.__parent__ = self.__parent__

        return record

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def __nonzero__(self):
        return self._values.__nonzero__()

    def __len__(self):
        return self._values.__len__()

    def __iter__(self):
        return self._values.__iter__()

    def has_key(self, name):
        return self._values.__contains__(name)

    def __contains__(self, name):
        return self._values.__contains__(name)

    def keys(self, min=None, max=None):
        return self._values.keys(min, max)

    def maxKey(self, key=None):
        return self._values.maxKey(key)

    def minKey(self, key=None):
        return self._values.minKey(key)

    def values(self, min=None, max=None):
        return [self[name] for name in self.keys(min, max)]

    def items(self, min=None, max=None):
        return [(name, self[name],) for name in self.keys(min, max)]

    def setdefault(self, key, value):
        if key not in self:
            self[key] = value
        return self[key]

    def clear(self):
        self._fields.clear()
        self._values.clear()

    # Helper methods

    def _getField(self, name):
        field = self._fields[name]

        # Handle field reference pointers
        if isinstance(field, basestring):
            recordName = field
            while isinstance(field, basestring):
                recordName = field
                field = self._fields[recordName]
            field = FieldRef(recordName, field)

        return field

    def _setField(self, name, field):
        if not IPersistentField.providedBy(field):
            raise ValueError("The record's field must be an IPersistentField.")
        if IFieldRef.providedBy(field):
            if field.recordName not in self._fields:
                raise ValueError(
                    "Field reference points to non-existent record"
                )
            self._fields[name] = field.recordName  # a pointer, of sorts
        else:
            field.__name__ = 'value'
            self._fields[name] = field


class Records(_Records, Persistent):
    """BBB: This used to be the class for the _records attribute of the
    registry. Having this be a Persistent object was always a bad idea. We
    keep it here so that we can migrate to the new structure, but it should
    no longer be used.
    """

    def __init__(self, parent):
        warnings.warn(
            "The Records persistent class is deprecated and should not be "
            "used.",
            DeprecationWarning
        )
        super(Records, self).__init__(parent)
