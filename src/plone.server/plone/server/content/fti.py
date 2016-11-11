# -*- coding: utf-8 -*-
from persistent import Persistent
from zope.security.management import getSecurityPolicy
from plone.server.content import utils
from plone.server.content.factory import DexterityFactory
from plone.server.content.interfaces import IDexterityFTI
from plone.server.content.interfaces import IDexterityFTIModificationDescription
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
import os.path
import plone.server.content.schema


@implementer(IDexterityFTIModificationDescription)
class DexterityFTIModificationDescription(object):

    def __init__(self, attribute, oldValue):
        self.attribute = attribute
        self.oldValue = oldValue


@implementer(IDexterityFTI)
class DexterityFTI(Persistent):
    """A Dexterity FTI
    """

    _properties = (
        {
            'id': 'add_permission',
            'type': 'selection',
            'select_variable': 'possiblePermissionIds',
            'mode': 'w',
            'label': 'Add permission',
            'description': 'Permission needed to be able to add content of '
                           'this type',
        },
        {
            'id': 'klass',
            'type': 'string',
            'mode': 'w',
            'label': 'Content type class',
            'description': 'Dotted name to the class that contains the '
                           'content type'
        },
        {
            'id': 'behaviors',
            'type': 'lines',
            'mode': 'w',
            'label': 'Behaviors',
            'description': 'Names of enabled behaviors type'
        },
        {
            'id': 'schema',
            'type': 'string',
            'mode': 'w',
            'label': 'Schema',
            'description': 'Dotted name to the interface describing content '
                           'type\'s schema.  This does not need to be given '
                           'if model_source or model_file are given, and '
                           'either contains an unnamed (default) schema.'
        },
        {
            'id': 'model_source',
            'type': 'text',
            'mode': 'w',
            'label': 'Model source',
            'description': 'XML source for the type\'s model. Note that this '
                           'takes precedence over any model file.'
        },
        {
            'id': 'model_file',
            'type': 'string',
            'mode': 'w',
            'label': 'Model file',
            'description': 'Path to file containing the schema model. '
                           'This can be relative to a package, e.g. '
                           '"my.package:myschema.xml".'
        },
        {
            'id': 'schema_policy',
            'type': 'string',
            'mode': 'w',
            'label': 'Content type schema policy',
            'description': 'Name of the schema policy.'
        },

    )

    # default_aliases = {
    #     '(Default)': '(dynamic view)',
    #     'view': '(selected layout)',
    #     'edit': '@@edit',
    #     'sharing': '@@sharing',
    # }

    default_actions = [
        {
            'id': 'view',
            'title': 'View',
            'action': 'string:${object_url}',
            'permissions': ('View',)
        },
        {
            'id': 'edit',
            'title': 'Edit',
            'action': 'string:${object_url}/edit',
            'permissions': ('Modify portal content',)
        },
    ]

    # immediate_view = 'view'
    # default_view = 'view'
    # view_methods = ('view',)
    add_permission = 'plone.AddContent'
    behaviors = []
    klass = 'plone.server.content.content.Item'
    model_source = '''\
<model xmlns='http://namespaces.plone.org/supermodel/schema'>
    <schema />
</model>
'''
    model_file = ''
    schema = ''
    schema_policy = 'dexterity'
    factory = ''

    def __init__(self, id, *args, **kwargs):
        self.id = id

        if 'schema' in kwargs:
            self.schema = kwargs['schema']

        if 'klass' in kwargs:
            self.klass = kwargs['klass']

        # if 'aliases' not in kwargs:
        #     self.setMethodAliases(self.default_aliases)

        # if 'actions' not in kwargs:
        #     for action in self.default_actions:
        #         self.addAction(id=action['id'],
        #                        name=action['title'],
        #                        action=action['action'],
        #                        condition=action.get('condition'),
        #                        permission=action.get('permissions', ()),
        #                        category=action.get('category', 'object'),
        #                        visible=action.get('visible', True))

        # Default factory name to be the FTI name
        if not self.factory:
            self.factory = self.id

        # In CMF (2.2+, but we've backported it) the property add_view_expr is
        # used to construct an action in the 'folder/add' category. The
        # portal_types tool loops over all FTIs and lets them provide such
        # actions.
        #
        # By convention, the expression is string:${folder_url}/++add++my.type
        #
        # The ++add++ traverser will find the FTI with name my.type, and then
        # looks up an adapter for (context, request, fti) with a name equal
        # to fti.factory, falling back on an unnamed adapter. The result is
        # assumed to be an add view.
        #
        # Dexterity provides a default (unnamed) adapter for any IFolderish
        # context, request and IDexterityFTI that can construct an add view
        # for any Dexterity schema.

        # if not self.add_view_expr:
        #     add_view_expr = kwargs.get(
        #         'add_view_expr',
        #         'string:${folder_url}/++add++{0:s}'.format(self.getId())
        #     )
        #     self._setPropValue('add_view_expr', add_view_expr)

        # Set the content_meta_type from the klass

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

    def Description(self):
        if self.description and self.i18n_domain:
            try:
                return Message(
                    self.description.decode('utf8'),
                    self.i18n_domain
                )
            except UnicodeDecodeError:
                return Message(
                    self.description.decode('latin-1'),
                    self.i18n_domain
                )
        else:
            return self.description

    def Metatype(self):
        if self.content_meta_type:
            return self.content_meta_type
        # BBB - this didn't use to be set
        klass = utils.resolveDottedName(self.klass)
        if klass is not None:
            self.content_meta_type = getattr(klass, 'meta_type', None)
        return self.content_meta_type

    @property
    def hasDynamicSchema(self):
        return not(self.schema)

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
        super(DexterityFTI, self)._updateProperty(id, value)
        new_value = getattr(self, id, None)

        if oldValue != new_value:
            modified(self, DexterityFTIModificationDescription(id, oldValue))

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

    def _absModelFile(self):
        colons = self.model_file.count(':')
        model_file = self.model_file

        # We have a package and not an absolute Windows path
        if colons == 1 and self.model_file[1:3] != ':\\':
            package, filename = self.model_file.split(':')
            mod = utils.resolveDottedName(package)
            # let / work as path separator on all platforms
            filename = filename.replace('/', os.path.sep)
            model_file = os.path.join(os.path.split(mod.__file__)[0], filename)
        else:
            if not os.path.isabs(model_file):
                raise ValueError(
                    'Model file name {0:s} is not an absolute path and does '
                    'not contain a package name in {1:s}'
                    .format(model_file, self.getId())
                )

        if not os.path.isfile(model_file):
            raise ValueError(
                'Model file {0:s} in {1:s} cannot be found'
                .format(model_file, self.getId())
            )

        return model_file


def _fixProperties(class_, ignored=['product', 'content_meta_type']):
    """Remove properties with the given ids, and ensure that later properties
    override earlier ones with the same id
    """
    properties = []
    processed = set()

    for item in reversed(class_._properties):
        item = item.copy()

        if item['id'] in processed:
            continue

        # Ignore some fields
        if item['id'] in ignored:
            continue

        properties.append(item)
        processed.add('id')

    class_._properties = tuple(reversed(properties))
_fixProperties(DexterityFTI)


# Event handlers
def register(fti):
    """Helper method to:

         - register an FTI as a local utility
         - register a local factory utility
         - register an add view
    """

    site_manager = getGlobalSiteManager()

    portal_type = fti.getId()

    fti_utility = queryUtility(IDexterityFTI, name=portal_type)
    if fti_utility is None:
        site_manager.registerUtility(
            fti,
            IDexterityFTI,
            portal_type,
            info='plone.dexterity.dynamic'
        )

    factory_utility = queryUtility(IFactory, name=fti.factory)
    if factory_utility is None:
        site_manager.registerUtility(
            DexterityFactory(portal_type),
            IFactory,
            fti.factory,
            info='plone.dexterity.dynamic'
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

    site_manager.unregisterUtility(provided=IDexterityFTI, name=portal_type)
    unregister_factory(fti.factory, site_manager)


def unregister_factory(factory_name, site_manager):
    """Helper method to unregister factories when unused by any dexterity
    type
    """
    utilities = list(site_manager.registeredUtilities())
    # Do nothing if an FTI is still using it
    if factory_name in [
        f.component.factory for f in utilities
        if (f.provided, f.info) == (IDexterityFTI, 'plone.dexterity.dynamic')
    ]:
        return

    # If a factory with a matching name exists, remove it
    if [f for f in utilities
        if (f.provided, f.name, f.info) ==
            (IFactory, factory_name, 'plone.dexterity.dynamic')]:
        site_manager.unregisterUtility(provided=IFactory, name=factory_name)


def ftiAdded(object, event):
    """When the FTI is created, install local components
    """

    if not IDexterityFTI.providedBy(event.object):
        return

    register(event.object)


def ftiRemoved(object, event):
    """When the FTI is removed, uninstall local coponents
    """

    if not IDexterityFTI.providedBy(event.object):
        return

    unregister(event.object)


