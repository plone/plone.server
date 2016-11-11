# -*- encoding: utf-8 -*-
from datetime import datetime
from dateutil.tz import tzlocal
from dateutil.tz import tzutc
from plone.server.content.interfaces import IDexterityContent
from plone.server.content.interfaces import IFormFieldProvider
from plone.server.behaviors.properties import ContextProperty
from plone.server.content import model
from plone.server.content.directives.base import catalog
from plone.server.content.directives.base import index
from zope.component import adapter
from zope.dublincore.annotatableadapter import ZDCAnnotatableAdapter
from zope.dublincore.interfaces import IWriteZopeDublinCore
from zope.interface import provider

_zone = tzlocal()
_utc = tzutc()

# never expires
CEILING_DATE = datetime(*datetime.max.timetuple()[:-2], tzutc())
# always effective
FLOOR_DATE = datetime(*datetime.min.timetuple()[:-2], tzutc())


@provider(IFormFieldProvider)
class IDublinCore(model.Schema, IWriteZopeDublinCore):
    catalog(creators='text')
    catalog(subject='text')
    catalog(contributors='text')
    index(contributors='non_analyzed')
    index(creators='non_analyzed')
    index(subject='non_analyzed')


@adapter(IDexterityContent)
class DublinCore(ZDCAnnotatableAdapter):

    creators = ContextProperty(u'creators', ())
    contributors = ContextProperty(u'contributors', ())
    created = ContextProperty(u'creation_date', None)
    modified = ContextProperty(u'modification_date', None)

    def __init__(self, context):
        self.context = context
        super(DublinCore, self).__init__(context)
        self.expires = CEILING_DATE
        self.effective = FLOOR_DATE
