from zope.component import adapter
from zope.component import queryUtility

from zope.lifecycleevent.interfaces import IObjectCreatedEvent
from zope.lifecycleevent.interfaces import IObjectCopiedEvent

from plone.server.uuid.interfaces import IUUIDGenerator
from plone.server.uuid.interfaces import IAttributeUUID

from plone.server.uuid.interfaces import ATTRIBUTE_NAME


@adapter(IAttributeUUID, IObjectCreatedEvent)
def addAttributeUUID(obj, event):

    if not IObjectCopiedEvent.providedBy(event):
        if getattr(obj, ATTRIBUTE_NAME, None):
            return  # defensive: keep existing UUID on non-copy create

    generator = queryUtility(IUUIDGenerator)
    if generator is None:
        return

    uuid = generator()
    if not uuid:
        return

    setattr(obj, ATTRIBUTE_NAME, uuid)