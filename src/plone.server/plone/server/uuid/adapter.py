from zope import interface
from zope import component

from plone.server.uuid import interfaces


@interface.implementer(interfaces.IUUID)
@component.adapter(interfaces.IAttributeUUID)
def attributeUUID(context):
    return getattr(context, interfaces.ATTRIBUTE_NAME, None)


@interface.implementer(interfaces.IMutableUUID)
@component.adapter(interfaces.IAttributeUUID)
class MutableAttributeUUID(object):

    def __init__(self, context):
        self.context = context

    def get(self):
        return getattr(self.context, interfaces.ATTRIBUTE_NAME, None)

    def set(self, uuid):
        uuid = str(uuid)
        setattr(self.context, interfaces.ATTRIBUTE_NAME, uuid)