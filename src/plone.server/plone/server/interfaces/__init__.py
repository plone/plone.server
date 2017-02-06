# -*- coding: utf-8 -*-
from .catalog import ICatalogDataAdapter  # noqa
from .catalog import ICatalogUtility  # noqa
from .catalog import ISecurityInfo  # noqa
from .configuration import IDatabaseConfigurationFactory  # noqa
from .content import IApplication  # noqa
from .content import IContainer  # noqa
from .content import IContentNegotiation  # noqa
from .content import IDatabase  # noqa
from .content import IItem  # noqa
from .content import IRegistry  # noqa
from .content import IResource  # noqa
from .content import IResourceFactory  # noqa
from .content import ISite  # noqa
from .content import IStaticDirectory  # noqa
from .content import IStaticFile  # noqa
from .events import IFileFinishUploaded  # noqa
from .events import INewUserAdded  # noqa
from .events import IObjectFinallyCreatedEvent  # noqa
from .events import IObjectFinallyDeletedEvent  # noqa
from .events import IObjectFinallyModifiedEvent  # noqa
from .events import IObjectFinallyVisitedEvent  # noqa
from .events import IObjectPermissionsModifiedEvent  # noqa
from .events import IObjectPermissionsViewEvent  # noqa
from .exceptions import ISerializableException  # noqa
from .files import ICloudFileField  # noqa
from .files import IFile  # noqa
from .files import IFileField  # noqa
from .files import IFileManager  # noqa
from .files import IStorage  # noqa
from .files import NotStorable  # noqa
from .json import IBeforeJSONAssignedEvent  # noqa
from .json import IFactorySerializeToJson  # noqa
from .json import IJSONField  # noqa
from .json import IJSONToValue  # noqa
from .json import IResourceDeserializeFromJson  # noqa
from .json import IResourceFieldDeserializer  # noqa
from .json import IResourceFieldSerializer  # noqa
from .json import IResourceSerializeToJson  # noqa
from .json import IResourceSerializeToJsonSummary  # noqa
from .json import ISchemaFieldSerializeToJson  # noqa
from .json import ISchemaSerializeToJson  # noqa
from .json import IValueToJson  # noqa
from .layer import IDefaultLayer  # noqa
from .renderers import IRendererFormatHtml  # noqa
from .renderers import IRendererFormatJson  # noqa
from .renderers import IRendererFormatRaw  # noqa
from .renderers import IRenderFormats  # noqa
from .security import IRole  # noqa
from .security import IPrincipalRoleMap  # noqa
from .security import IPrincipalRoleManager  # noqa
from .security import IRolePermissionMap  # noqa
from .security import IRolePermissionManager  # noqa
from .security import IPrincipalPermissionMap  # noqa
from .security import IPrincipalPermissionManager  # noqa
from .security import Allow  # noqa
from .security import Deny  # noqa
from .security import Unset  # noqa
from .security import AllowSingle  # noqa
from .security import IGroups  # noqa
from .text import IRichText  # noqa
from .text import IRichTextValue  # noqa
from .types import IConstrainTypes  # noqa
from .views import ICONNECT  # noqa
from .views import IDELETE  # noqa
from .views import IDownloadView  # noqa
from .views import IGET  # noqa
from .views import IHEAD  # noqa
from .views import IOPTIONS  # noqa
from .views import IPATCH  # noqa
from .views import IPOST  # noqa
from .views import IPUT  # noqa
from .views import ITraversableView  # noqa
from .views import IView  # noqa
from zope.i18nmessageid.message import MessageFactory
from zope.interface import Interface


_ = MessageFactory('plone.server')

DEFAULT_ADD_PERMISSION = 'plone.AddContent'
DEFAULT_READ_PERMISSION = 'plone.ViewContent'
DEFAULT_WRITE_PERMISSION = 'plone.ManageContent'
MIGRATION_DATA_REGISTRY_KEY = '_migrations_info'

SHARED_CONNECTION = False
WRITING_VERBS = ['POST', 'PUT', 'PATCH', 'DELETE']
SUBREQUEST_METHODS = ['get', 'delete', 'head', 'options', 'patch', 'put']


class IFormFieldProvider(Interface):
    """Marker interface for schemata that provide form fields.
    """


class IRequest(Interface):
    pass


class IResponse(Interface):

    def __init__(context, request):
        pass


class IFrameFormats(Interface):
    pass


class IFrameFormatsJson(IFrameFormats):
    pass


class ILanguage(Interface):
    pass


# Target interfaces on resolving

class IRendered(Interface):
    pass


class ITranslated(Interface):
    pass


# Get Absolute URL


class IAbsoluteURL(Interface):
    pass


# Addon interface

class IAddOn(Interface):

    def install(cls, site, request):
        pass

    def uninstall(cls, site, request):
        pass


class TransformError(Exception):
    """Exception raised if a value could not be transformed. This is normally
    caused by another exception. Inspect self.cause to find that.
    """

    def __init__(self, message, cause=None):
        self.message = message
        self.cause = cause

    def __str__(self):
        return self.message


class ITransformer(Interface):
    """A simple abstraction for invoking a transformation from one MIME
    type to another.
    This is not intended as a general transformations framework, but rather
    as a way to abstract away a dependency on the underlying transformation
    engine.
    This interface will be implemented by an adapter onto the context where
    the value is stored.
    """

    def __init__(object):
        """Set the value object."""

    def __call__():
        """Transform the IRichTextValue 'value' to the given MIME type.
        Return a unicode string. Raises TransformError if something went
        wrong.
        """
