# -*- coding: utf-8 -*-
from plone.behavior.interfaces import IBehaviorAssignable
from plone.server.content.interfaces import IDexterityContent
from plone.server.content.schema import SCHEMA_CACHE
from zope.component import adapter
from zope.interface import implementer


@implementer(IBehaviorAssignable)
@adapter(IDexterityContent)
class DexterityBehaviorAssignable(object):
    """Support plone.behavior behaviors stored in the FTI
    """

    def __init__(self, context):
        self.context = context

    def supports(self, behavior_interface):
        for behavior in self.enumerateBehaviors():
            if behavior_interface in behavior.interface._implied:
                return True
        return False

    def enumerateBehaviors(self):
        for behavior in SCHEMA_CACHE.behavior_registrations(
            self.context.portal_type
        ):
            yield behavior