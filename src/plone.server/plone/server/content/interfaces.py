# -*- coding: utf-8 -*-
from zope.component.interfaces import IFactory
from zope.component.interfaces import IObjectEvent
from zope.interface import Attribute
from zope.interface import Interface
from zope.lifecycleevent.interfaces import IModificationDescription
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
import zope.schema
from zope.interface.interfaces import IInterface

INDEX_KEY = 'plone.server.catalog.index'
CATALOG_KEY = 'plone.server.catalog.catalog'
FIELDSETS_KEY = 'plone.server.content.fieldsets'
READ_PERMISSIONS_KEY = 'plone.server.content.security.read-permissions'
WRITE_PERMISSIONS_KEY = 'plone.server.content.security.write-permissions'
DEFAULT_ORDER = 9999


class IContainerModifiedEvent(IObjectModifiedEvent):
    """The container has been modified.

    This event is specific to "containerness" modifications, which means
    addition, removal or reordering of sub-objects.
    """


class ITypeInformation(Interface):
    pass


class IContentType(Interface):
    """This interface represents a content type.

    If an **interface** provides this interface type, then all objects
    providing the **interface** are considered content objects.
    """


class IConstrainTypes(Interface):
    """
    Interface for folderish content types supporting restricting addable types
    on a per-instance basis.
    """

    def getConstrainTypesMode():
        """
        Find out if add-restrictions are enabled. Returns 0 if they are
        disabled (the type's default FTI-set allowable types is in effect),
        1 if they are enabled (only a selected subset if allowed types will be
        available), and -1 if the allowed types should be acquired from the
        parent. Note that in this case, if the parent portal type is not the
        same as the portal type of this object, fall back on the default (same
        as 0)
        """

    def getLocallyAllowedTypes():
        """
        Get the list of FTI ids for the types which should be allowed to be
        added in this container.
        """

    def getImmediatelyAddableTypes():
        """
        Return a subset of the FTI ids from getLocallyAllowedTypes() which
        should be made most easily available.
        """

    def getDefaultAddableTypes():
        """
        Return a list of FTIs which correspond to the list of FTIs available
        when the constraint mode = 0 (that is, the types addable without any
        setLocallyAllowedTypes trickery involved)
        """

    def allowedContentTypes():
        """
        Return the list of currently permitted FTIs.
        """


class IDexterityFTI(ITypeInformation):
    """The Factory Type Information for Dexterity content objects
    """

    def lookupSchema():
        """Return an InterfaceClass that represents the schema of this type.
        Raises a ValueError if it cannot be found.

        If a schema interface is specified, return this. Otherwise, look up
        the model from either the TTW model source string or a specified
        model XML file, and build a schema from the unnamed schema
        specified in this model.
        """

    def lookupModel():
        """Return the IModel specified in either the model_source or
        model_file (the former takes precedence). See plone.supermodel for
        more information about this type.

        If neither a model_source or a model_file is given, but a schema is
        given, return a faux model that contains just this schema.

        Note that model.schema is not necessarily going to be the same as
        the schema returned by lookupSchema().
        """

    add_permission = zope.schema.DottedName(
        title='Add permission',
        description='Zope 3 permission name for the permission required to '
                    'construct this content',
    )

    behaviors = zope.schema.List(
        title='Behaviors',
        description='A list of behaviors that are enabled for this type. '
                    'See plone.behavior for more details.',
        value_type=zope.schema.DottedName(title='Behavior name')
    )

    schema = zope.schema.DottedName(
        title='Schema interface',
        description='Dotted name to an interface describing the type. '
                    'This is not required if there is a model file or a '
                    'model source string containing an unnamed schema.'
    )


class IDexterityFTIModificationDescription(IModificationDescription):
    """Descriptor passed with an IObjectModifiedEvent for a Dexterity FTI.
    """

    attribute = zope.schema.ASCII(
        title='Name of the attribute that was modified'
    )
    oldValue = Attribute('Old value')


class IDexterityFactory(IFactory):
    """A factory that can create Dexterity objects.

    This factory will create an object by looking up the klass property of
    the FTI with the given portal type. It will also set the portal_type
    on the instance and mark the instance as providing the schema interface
    if it does not do so already.
    """

    portal_type = zope.schema.TextLine(
        title='Portal type name',
        description='The portal type this is an FTI for'
    )


# Schema
class IDexteritySchema(Interface):
    """Base class for Dexterity schemata
    """


# Schema cache
class ISchemaInvalidatedEvent(Interface):
    """Event fired when the schema cache should be invalidated.

    If the portal_type is not given, all schemata will be cleared from the
    cache.
    """

    portal_type = zope.schema.TextLine(title='FTI name', required=False)


# Content
class IDexterityContent(Interface):
    """Marker interface for dexterity-managed content objects
    """


class IDexterityItem(IDexterityContent):
    """Marker interface applied to dexterity-managed non-folderish objects
    """


class IDexterityContainer(IDexterityContent):
    """Marker interface applied to dexterity-managed folderish objects
    """


class IDexterityBigContainer(IDexterityContainer):
    """Marker interface applied to dexterity-managed large folderish objects
    """


class ISchema(IInterface):
    """Describes a schema as generated by this library
    """



class IFieldset(Interface):
    """Describes a grouping of fields in the schema
    """

    __name__ = zope.schema.TextLine(title=u"Fieldset name")

    label = zope.schema.TextLine(title=u"Label")

    description = zope.schema.TextLine(
        title=u"Long description",
        required=False
    )

    order = zope.schema.Int(
        title=u"Order",
        required=False,
        default=DEFAULT_ORDER,
    )

    fields = zope.schema.List(
        title=u"Field names",
        value_type=zope.schema.TextLine(title=u"Field name")
    )


class IModel(Interface):
    """Describes a model as generated by this library
    """

    schema = zope.schema.InterfaceField(
        title=u"Default schema",
        readonly=True
    )

    schemata = zope.schema.Dict(
        title=u"Schemata",
        key_type=zope.schema.TextLine(
            title=u"Schema name",
            description=u"Default schema is under the key u''."
        ),
        value_type=zope.schema.Object(
            title=u"Schema interface",
            schema=ISchema
        )
    )


class ISchemaPlugin(Interface):
    """A named adapter that provides additional functionality during schema
    construction.
    Execution is deferred until the full supermodel environment is available.
    """

    order = zope.schema.Int(title=u"Order", required=False,
                            description=u"Sort key for plugin execution order")

    def __call__():
        """Execute plugin
        """


class IFieldNameExtractor(Interface):
    """Adapter to determine the canonical name of a field
    """

    def __call__():
        """Return the name of the adapted field
        """


class IToUnicode(Interface):
    """Reciprocal to IToUnicode. Adapting a field to this interface allows
    a string representation to be extracted.
    """

    def toUnicode(value):
        """Convert the field value to a unicode string.
        """


class IFormFieldProvider(Interface):
    """Marker interface for schemata that provide form fields.
    """