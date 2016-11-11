===============
Registry events
===============

The registry fires certain events. These are:

``plone.registry.interfaces.IRecordAddedEvent``
    when a record has been added to the registry.

``plone.registry.interfaces.IRecordRemovedEvent``
    when a record has been removed from the registry.

``plone.registry.interfaces.IRecordModifiedEvent``,
    when a record's value is modified.

To test these events, we will create, modify and remove a few records::

    >>> from zope.component.eventtesting import clearEvents
    >>> clearEvents()
    >>> from plone.registry import Registry, Record, field
    >>> registry = Registry()

Adding a new record to the registry should fire ``IRecordAddedEvents``::

    >>> registry.records['plone.registry.tests.age'] = \
    ...     Record(field.Int(title=u"Age", min=0, default=18))

    >>> registry.records['plone.registry.tests.cms'] = \
    ...     Record(field.TextLine(title=u"Preferred CMS"), value=u"Plone")

When creating records from an interface, one event is fired for each field in the interface::

    >>> from plone.registry.tests import IMailSettings
    >>> registry.registerInterface(IMailSettings)

Deleting a record should fire an ``IRecordRemovedEvent``::

    >>> del registry.records['plone.registry.tests.cms']

Changing a record should fire an ``IRecordModifiedEvent``::

    >>> registry['plone.registry.tests.age'] = 25
    >>> registry.records['plone.registry.tests.age'].value = 24

Let's take a look at the events that were just fired::

    >>> from plone.registry.interfaces import IRecordEvent
    >>> from zope.component.eventtesting import getEvents
    >>> getEvents(IRecordEvent)
    [<RecordAddedEvent for plone.registry.tests.age>,
     <RecordAddedEvent for plone.registry.tests.cms>,
     <RecordAddedEvent for plone.registry.tests.IMailSettings.sender>,
     <RecordAddedEvent for plone.registry.tests.IMailSettings.smtp_host>,
     <RecordRemovedEvent for plone.registry.tests.cms>,
     <RecordModifiedEvent for plone.registry.tests.age>,
     <RecordModifiedEvent for plone.registry.tests.age>]

For the modified events, we can also check the value before and after the change::

    >>> from plone.registry.interfaces import IRecordModifiedEvent
    >>> [(repr(e), e.oldValue, e.newValue,) for e in getEvents(IRecordModifiedEvent)]
    [('<RecordModifiedEvent for plone.registry.tests.age>', 18, 25),
     ('<RecordModifiedEvent for plone.registry.tests.age>', 25, 24)]

IObjectEvent-style redispatchers
================================

There is a special event handler.
It takes care of re-dispatching registry events based on the schema interface prescribed by the record.

Let's re-set the event testing framework and register the re-dispatching event subscriber.
Normally, this would happen automatically by including this package's ZCML.

::

    >>> clearEvents()
    >>> from zope.component import provideHandler
    >>> from plone.registry.events import redispatchInterfaceAwareRecordEvents
    >>> provideHandler(redispatchInterfaceAwareRecordEvents)

We'll then register a schema interface::

    >>> from plone.registry.tests import IMailSettings
    >>> registry.registerInterface(IMailSettings)

We could now register an event handler to print any record event occurring on an ``IMailSettings`` record.
More specialised event handlers for e.g. ``IRecordModifiedEvent`` or ``IRecordRemovedEvent`` are of course also possible.
Note that it is not possible to re-dispatch ``IRecordAddedEvents``, so these are never caught.

    >>> from zope.component import adapter
    >>> @adapter(IMailSettings, IRecordEvent)
    ... def print_mail_settings_events(proxy, event):
    ...     print("Got %s for %s" % (event, proxy))
    >>> provideHandler(print_mail_settings_events)

Let's now modify one of the records for this interface.
The event handler should react immediately::

    >>> registry['plone.registry.tests.IMailSettings.sender'] = u"Some sender"
    Got <RecordModifiedEvent for plone.registry.tests.IMailSettings.sender> for <RecordsProxy for plone.registry.tests.IMailSettings>

Let's also modify a non-interface-aware record, for comparison's sake.
Here, there is nothing printed::

    >>> registry['plone.registry.tests.age'] = 3

We can try a record-removed event as well::

    >>> del registry.records['plone.registry.tests.IMailSettings.sender']
    Got <RecordRemovedEvent for plone.registry.tests.IMailSettings.sender> for <RecordsProxy for plone.registry.tests.IMailSettings>

The basic events that have been dispatched are::

    >>> getEvents(IRecordEvent)
    [<RecordAddedEvent for plone.registry.tests.IMailSettings.sender>,
     <RecordAddedEvent for plone.registry.tests.IMailSettings.smtp_host>,
     <RecordModifiedEvent for plone.registry.tests.IMailSettings.sender>,
     <RecordModifiedEvent for plone.registry.tests.age>,
     <RecordRemovedEvent for plone.registry.tests.IMailSettings.sender>]

