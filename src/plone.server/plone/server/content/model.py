# -*- coding: utf-8 -*-
from plone.server.content.interfaces import IModel
from plone.server.content.interfaces import ISchema
from plone.server.content.interfaces import IFieldset
from plone.server.content.interfaces import ISchemaPlugin
from plone.server.content.interfaces import DEFAULT_ORDER
from zope.component import getAdapters
from zope.interface import implementer
from zope.interface import Interface
from zope.interface.interface import InterfaceClass

import logging

logger = logging.getLogger(__name__)


@implementer(IFieldset)
class Fieldset(object):

    def __init__(
        self,
        __name__,
        label=None,
        description=None,
        fields=None,
        order=DEFAULT_ORDER
    ):
        self.__name__ = __name__
        self.label = label or __name__
        self.description = description
        self.order = order

        if fields:
            self.fields = fields
        else:
            self.fields = []

    def __repr__(self):
        return "<Fieldset '{0}' order {1:d} of {2}>".format(
            self.__name__,
            self.order,
            ', '.join(self.fields)
        )



@implementer(IModel)
class Model(object):

    def __init__(self, schemata=None):
        if schemata is None:
            schemata = {}
        self.schemata = schemata

    # Default schema

    @property
    def schema(self):
        return self.schemata.get(u"", None)


@implementer(ISchema)
class SchemaClass(InterfaceClass):

    def __init__(self, name, bases=(), attrs=None, __doc__=None,
                 __module__=None):
        InterfaceClass.__init__(self, name, bases, attrs, __doc__, __module__)
        self._SchemaClass_finalize()

    def _SchemaClass_finalize(self):
        adapters = [(getattr(adapter, 'order', 0), name, adapter)
                    for name, adapter in getAdapters((self,), ISchemaPlugin)]
        adapters.sort()
        for order, name, adapter in adapters:
            adapter()

Schema = SchemaClass(
    'Schema',
    (Interface,),
    __module__='plone.supermodel.model'
)
