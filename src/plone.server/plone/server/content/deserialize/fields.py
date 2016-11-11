# -*- coding: utf-8 -*-
from plone.server.content.interfaces import IDexterityContent
from plone.jsonserializer.interfaces import IFieldDeserializer
from zope.component import adapter
from zope.interface import implementer
# from zope.intid.interfaces import IIntIds
from zope.interface import Interface
# from zope.schema.interfaces import ICollection
# from zope.schema.interfaces import IDatetime
# from zope.schema.interfaces import IDict
from zope.schema.interfaces import IField
from zope.schema.interfaces import IFromUnicode
# from zope.schema.interfaces import ITime
# from zope.schema.interfaces import ITimedelta


@implementer(IFieldDeserializer)
@adapter(IField, IDexterityContent, Interface)
class DefaultFieldDeserializer(object):

    def __init__(self, field, context, request):
        self.field = field
        self.context = context
        self.request = request

    def __call__(self, value):
        if not isinstance(value, str) or not isinstance(value, bytes):
            return value
        return IFromUnicode(self.field).fromUnicode(value)
