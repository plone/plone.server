# -*- coding: utf-8 -*-
from zope.security.management import getSecurityPolicy
from plone.server.content import utils
from plone.server.content.factory import Factory
from plone.server.content.interfaces import IFTI
from plone.server.content.interfaces import IFTIModificationDescription
from plone.server.content.schema import SchemaInvalidatedEvent
from zope.component import getAllUtilitiesRegisteredFor
from zope.component import getGlobalSiteManager
from zope.component import queryUtility
from zope.component.interfaces import IFactory
from zope.event import notify
from zope.i18nmessageid import Message
from zope.interface import implementer
from zope.lifecycleevent import modified
from zope.security.interfaces import IPermission
import logging


@implementer(IFTIModificationDescription)
class FTIModificationDescription(object):

    def __init__(self, attribute, oldValue):
        self.attribute = attribute
        self.oldValue = oldValue


@implementer(IFTI)
class FTI(object):
    """A FTI
    """

    add_permission = 'plone.AddContent'
    behaviors = []
    klass = 'plone.server.content.content.Item'
    schema = ''
    restriction = ''
    factory = ''
    allowed_types = None

    def __init__(self, id, *args, **kwargs):
        self.id = id

        if 'schema' in kwargs:
            self.schema = kwargs['schema']

        if 'klass' in kwargs:
            self.klass = kwargs['klass']

        if 'allowed_types' in kwargs:
            self.allowed_types = kwargs['allowed_types']

        # Default factory name to be the FTI name
        if not self.factory:
            self.factory = self.id

        klass = utils.resolveDottedName(self.klass)
        if klass is not None:
            self.content_meta_type = getattr(klass, 'meta_type', None)

        if 'behaviors' in kwargs:
            self.behaviors = kwargs['behaviors']
        if 'add_permission' in kwargs:
            self.add_permission = kwargs['add_permission']

    def getId(self):
        return self.id

    def Title(self):
        if self.title and self.i18n_domain:
            try:
                return Message(self.title.decode('utf8'), self.i18n_domain)
            except UnicodeDecodeError:
                return Message(self.title.decode('latin-1'), self.i18n_domain)
        else:
            return self.title or self.getId()

    def Metatype(self):
        if self.content_meta_type:
            return self.content_meta_type
        # BBB - this didn't use to be set
        klass = utils.resolveDottedName(self.klass)
        if klass is not None:
            self.content_meta_type = getattr(klass, 'meta_type', None)
        return self.content_meta_type

    def lookupSchema(self):
        schema = None

        # If a specific schema is given, use it
        if self.schema:
            try:
                schema = utils.resolveDottedName(self.schema)
            except ImportError:
                logging.warning(
                    'Schema {0:s} set for type {1:s} cannot be resolved'
                    .format(self.schema, self.getId())
                )
                # fall through to return a fake class with no
                # fields so that end user code doesn't break

        if schema:
            return schema

    def allowType(self, portal_type):
        if self.allowed_types is None:
            return True
        elif portal_type in self.allowed_types:
            return True
        else:
            return False

    #
    # Base class overrides
    #

    # Make sure we get an event when the FTI is modified

    def _updateProperty(self, id, value):
        """Allow property to be updated, and fire a modified event. We do this
        on a per-property basis and invalidate selectively based on the id of
        the property that was changed.
        """

        oldValue = getattr(self, id, None)
        super(FTI, self)._updateProperty(id, value)
        new_value = getattr(self, id, None)

        if oldValue != new_value:
            modified(self, FTIModificationDescription(id, oldValue))

            # Update meta_type from klass
            if id == 'klass':
                klass = utils.resolveDottedName(new_value)
                if klass is not None:
                    self.content_meta_type = getattr(klass, 'meta_type', None)

    # Allow us to specify a particular add permission rather than rely on ones
    # stored in meta types that we don't have anyway

    def isConstructionAllowed(self, container, request=None):
        if not self.add_permission:
            return False

        permission = queryUtility(IPermission, name=self.add_permission)
        if permission is None:
            return False

        if request:
            return request.security.checkPermission(permission.id, container)
        else:
            return bool(
                getSecurityPolicy()().checkPermission(  # noqa
                    permission.title, container)
            )

    #
    # Helper methods
    #

    def possiblePermissionIds(self):
        """Get a vocabulary of Zope 3 permission ids
        """
        permission_names = set()
        for permission in getAllUtilitiesRegisteredFor(IPermission):
            permission_names.add(permission.id)
        return sorted(permission_names)


# Event handlers
def register(fti):
    """Helper method to:

         - register an FTI as a local utility
         - register a local factory utility
         - register an add view
    """

    site_manager = getGlobalSiteManager()

    portal_type = fti.getId()

    fti_utility = queryUtility(IFTI, name=portal_type)
    if fti_utility is None:
        site_manager.registerUtility(
            fti,
            IFTI,
            portal_type,
            info='plone.server.content.dynamic'
        )

    factory_utility = queryUtility(IFactory, name=fti.factory)
    if factory_utility is None:
        site_manager.registerUtility(
            Factory(portal_type),
            IFactory,
            fti.factory,
            info='plone.server.content.dynamic'
        )


def unregister(fti, old_name=None):
    """Helper method to:

        - unregister the FTI local utility
        - unregister any local factory utility associated with the FTI
        - unregister any local add view associated with the FTI
    """
    site_manager = getGlobalSiteManager()

    portal_type = old_name or fti.getId()

    notify(SchemaInvalidatedEvent(portal_type))

    site_manager.unregisterUtility(provided=IFTI, name=portal_type)
    unregister_factory(fti.factory, site_manager)


def unregister_factory(factory_name, site_manager):
    """Helper method to unregister factories when unused by any type."""
    utilities = list(site_manager.registeredUtilities())
    # Do nothing if an FTI is still using it
    if factory_name in [
        f.component.factory for f in utilities
        if (f.provided, f.info) == (IFTI, 'plone.server.content.dynamic')
    ]:
        return

    # If a factory with a matching name exists, remove it
    if [f for f in utilities
        if (f.provided, f.name, f.info) ==
            (IFactory, factory_name, 'plone.server.content.dynamic')]:
        site_manager.unregisterUtility(provided=IFactory, name=factory_name)


def ftiAdded(object, event):
    """When the FTI is created, install local components
    """

    if not IFTI.providedBy(event.object):
        return

    register(event.object)


def ftiRemoved(object, event):
    """When the FTI is removed, uninstall local coponents
    """

    if not IFTI.providedBy(event.object):
        return

    unregister(event.object)


