# -*- coding: utf-8 -*-
from plone.server.content.interfaces import IFactory
from plone.server.content.interfaces import IFTI
from plone.server.content.utils import resolveDottedName
from zope.component import getUtility
from zope.component.factory import Factory as ZopeFactory
from zope.interface import implementer
from zope.interface.declarations import Implements


@implementer(IFactory)
class Factory(ZopeFactory):
    """A factory for Dexterity content.
    """

    def __init__(self, portal_type):
        self.portal_type = portal_type

    def __call__(self, *args, **kw):
        fti = getUtility(IFTI, name=self.portal_type)

        klass = resolveDottedName(fti.klass)
        if klass is None or not callable(klass):
            raise ValueError(
                'Content class {0:s} set for type {1:s} is not valid'
                .format(fti.klass, self.portal_type)
            )

        try:
            obj = klass(*args, **kw)
        except TypeError as e:
            raise ValueError(
                'Error whilst constructing content for {0:s}'
                'using class {1:s}: {2:s}'
                .format(self.portal_type, fti.klass, str(e))
            )

        # Set portal_type if not set, but avoid creating an instance variable
        # if possible
        if getattr(obj, 'portal_type', '') != self.portal_type:
            obj.portal_type = self.portal_type

        return obj

    def getInterfaces(self):
        fti = getUtility(IFTI, name=self.portal_type)
        spec = Implements(fti.lookupSchema())
        spec.__name__ = self.portal_type
        return spec

    def __repr__(self):
        return '<{0:s} for {1:s}>'.format(self.__class__.__name__,
                                          self.portal_type)
