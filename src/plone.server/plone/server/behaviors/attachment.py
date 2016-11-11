from plone.server.content.interfaces import IContent
from plone.server.content.interfaces import IFormFieldProvider
from plone.server.behaviors.properties import ContextProperty
from plone.server.file import BasicFileField
from plone.server.content import model
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.interface import provider


@provider(IFormFieldProvider)
class IAttachment(model.Schema):
    file = BasicFileField(
        title=u'File',
        required=False
    )


@adapter(IContent)
class Attachment(ZDCAnnotatableAdapter):

    file = ContextProperty(u'file', None)

    def __init__(self, context):
        self.context = context
        super(Attachment, self).__init__(context)
