# -*- coding: utf-8 -*-
from plone.server.registry.interfaces import IInterfaceAwareRecord
from plone.server.registry.interfaces import IRecordAddedEvent
from plone.server.registry.interfaces import IRecordEvent
from plone.server.registry.interfaces import IRecordModifiedEvent
from plone.server.registry.interfaces import IRecordRemovedEvent
from plone.server.registry.recordsproxy import RecordsProxy
from zope.component import adapter
from zope.component import subscribers
from zope.interface import implementer


@implementer(IRecordEvent)
class RecordEvent(object):

    def __init__(self, record):
        self.record = record

    def __repr__(self):
        return "<%s for %s>" % (self.__class__.__name__, self.record.__name__)


@implementer(IRecordAddedEvent)
class RecordAddedEvent(RecordEvent):
    """record added"""


@implementer(IRecordRemovedEvent)
class RecordRemovedEvent(RecordEvent):
    """record removed"""


@implementer(IRecordModifiedEvent)
class RecordModifiedEvent(RecordEvent):

    def __init__(self, record, oldValue, newValue):
        super(RecordModifiedEvent, self).__init__(record)
        self.oldValue = oldValue
        self.newValue = newValue


@adapter(IRecordEvent)
def redispatchInterfaceAwareRecordEvents(event):
    """When an interface-aware record received a record event,
    redispatch the event in a simlar manner to the IObjectEvent redispatcher.

    Note that this means one IRecordModifiedEvent will be fired for each
    change to a record.
    """

    record = event.record

    if not IInterfaceAwareRecord.providedBy(record):
        return

    schema = record.interface
    if schema is None:
        return

    proxy = RecordsProxy(record.__parent__, schema)

    adapters = subscribers((proxy, event), None)
    for ad in adapters:
        pass  # getting them does the work
