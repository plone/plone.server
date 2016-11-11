# -*- coding: utf-8 -*-
"""Main routing traversal class."""
from aiohttp.abc import AbstractMatchInfo
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from plone.server.registry.interfaces import IRegistry
from plone.server import _
from plone.server import DICT_METHODS
from plone.server.api.dexterity import DefaultOPTIONS
from plone.server.api.layer import IDefaultLayer
from plone.server.auth.participation import AnonymousParticipation
from plone.server.browser import ErrorResponse
from plone.server.browser import Response
from plone.server.browser import UnauthorizedResponse
from plone.server.contentnegotiation import content_type_negotiation
from plone.server.contentnegotiation import language_negotiation
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDataBase
from plone.server.interfaces import IOPTIONS
from plone.server.interfaces import IRendered
from plone.server.interfaces import IRequest
from plone.server.interfaces import ITranslated
from plone.server.interfaces import ITraversableView
from plone.server.config import ACTIVE_LAYERS_KEY
from plone.server.config import CORS_KEY
from plone.server.transactions import locked
from plone.server.transactions import sync
from plone.server.utils import apply_cors
from plone.server.utils import import_class
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import queryMultiAdapter
from zope.component.interfaces import ISite
from zope.interface import alsoProvides
from zope.security.checker import getCheckerForInstancesOf
from zope.security.interfaces import IInteraction
from zope.security.interfaces import IParticipation
from zope.security.interfaces import IPermission
from zope.security.interfaces import Unauthorized
from zope.security.proxy import ProxyFactory

import aiohttp
import logging
import traceback
import json


logger = logging.getLogger(__name__)

SHARED_CONNECTION = False
WRITING_VERBS = ['POST', 'PUT', 'PATCH', 'DELETE']
SUBREQUEST_METHODS = ['get', 'delete', 'head', 'options', 'patch', 'put']


async def do_traverse(request, parent, path):
    """Traverse for the code API."""
    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    if ISite.providedBy(parent) and \
       path[0] != request._db_id:
        raise HTTPUnauthorized('Tried to access a site outsite the request')

    if IApplication.providedBy(parent) and \
       path[0] != request._site_id:
        raise HTTPUnauthorized('Tried to access a site outsite the request')

    try:
        if path[0].startswith('_'):
            raise HTTPUnauthorized()
        context = parent[path[0]]
    except TypeError:
        return parent, path
    except KeyError:
        return parent, path

    context._v_parent = parent

    return await traverse(request, context, path[1:])


async def subrequest(orig_request, path, relative_to_site=True,
                     headers={}, body=None, params=None, method='GET'):
    """Subrequest, initial implementation doing a real request
    """
    session = aiohttp.ClientSession()
    method = method.lower()
    if method not in SUBREQUEST_METHODS:
        raise AttributeError('No valid method ' + method)
    caller = getattr(session, method)

    for head in orig_request.headers:
        if head not in headers:
            headers[head] = orig_request.headers[head]

    params = {
        'headers': headers,
        'params': params
    }
    if method in ['put', 'patch']:
        params['data'] = body

    return caller(path, **params)


async def traverse(request, parent, path):
    """Do not use outside the main router function."""
    if IApplication.providedBy(parent):
        participation = parent.root_participation(request)
        if participation:
            logger.info('Root Participation added')
            request.security.add(participation)

    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc
    dbo = None
    if IDataBase.providedBy(parent):
        # Look on the PersistentMapping from the DB
        dbo = parent
        parent = parent.conn.root()

    try:
        if path[0].startswith('_'):
            raise HTTPUnauthorized()
        context = parent[path[0]]
    except TypeError:
        return parent, path
    except KeyError:
        return parent, path

    if dbo is not None:
        context._v_parent = dbo
    else:
        context._v_parent = parent

    if IDataBase.providedBy(context):
        if SHARED_CONNECTION:
            request.conn = context.conn
        else:
            request.conn = context.open()
        request._db_id = context.id

    if ISite.providedBy(context):
        request._site_id = context.id
        request.site = context
        request.site_components = context.getSiteManager()
        request.site_settings = request.site_components.getUtility(IRegistry)
        participation = IParticipation(request)
        # Lets extract the user from the request
        await participation()
        if participation.principal is not None:
            request.security.add(participation)
        layers = request.site_settings.get(ACTIVE_LAYERS_KEY, [])
        for layer in layers:
            alsoProvides(request, import_class(layer))

    return await traverse(request, context, path[1:])


class MatchInfo(AbstractMatchInfo):
    """Function that returns from traversal request on aiohttp."""

    def __init__(self, resource, request, view, rendered):
        """Value that comes from the traversing."""
        self.request = request
        self.resource = resource
        self.view = view
        self.rendered = rendered
        self._apps = []
        self._frozen = False

    async def handler(self, request):
        """Main handler function for aiohttp."""
        if request.method in WRITING_VERBS:
            txn = request.conn.transaction_manager.begin(request)
            try:
                async with locked(self.resource):
                    view_result = await self.view()
                    if isinstance(view_result, ErrorResponse):
                        await sync(request)(txn.abort)
                    elif isinstance(view_result, UnauthorizedResponse):
                        await sync(request)(txn.abort)
                    else:
                        await sync(request)(txn.commit)
            except Unauthorized:
                await sync(request)(txn.abort)
                view_result = UnauthorizedResponse(
                    _('Not authorized to render operation'))
            except Exception as e:
                logger.error(
                    "Exception on writing execution",
                    exc_info=e)
                await sync(request)(txn.abort)
                view_result = ErrorResponse(
                    'ServiceError',
                    _('Error on execution of operation')
                )
        else:
            try:
                view_result = await self.view()
            except Unauthorized:
                view_result = UnauthorizedResponse(
                    _('Not authorized to render view'))
            except Exception as e:
                logger.error(
                    "Exception on view execution",
                    exc_info=e)
                view_result = ErrorResponse(
                    'ViewError',
                    _('Error on execution of view'))

        # Make sure its a Response object to send to renderer
        if not isinstance(view_result, Response):
            view_result = Response(view_result)

        # Apply cors if its needed
        view_result.headers.update(await apply_cors(request))

        # If we want to close the connection after the request
        if SHARED_CONNECTION is False and hasattr(request, 'conn'):
            request.conn.close()

        return await self.rendered(view_result)

    def get_info(self):
        return {
            'request': self.request,
            'resource': self.resource,
            'view': self.view,
            'rendered': self.rendered
        }

    @property
    def apps(self):
        return tuple(self._apps)

    def add_app(self, app):
        if self._frozen:
            raise RuntimeError("Cannot change apps stack after .freeze() call")
        self._apps.insert(0, app)

    def freeze(self):
        self._frozen = True

    async def expect_handler(self, request):
        return None

    async def http_exception(self):
        return None


class TraversalRouter(AbstractRouter):
    """Custom router for plone.server."""

    _root = None

    def __init__(self, root=None):
        """On traversing aiohttp sets the root object."""
        self.set_root(root)

    def set_root(self, root):
        """Warpper to set the root object."""
        self._root = root

    async def resolve(self, request):
        """Main function to resolve a request."""
        alsoProvides(request, IRequest)
        alsoProvides(request, IDefaultLayer)

        request.site_components = getGlobalSiteManager()
        request.security = IInteraction(request)

        try:
            resource, tail = await self.traverse(request)
        except Exception as _exc:
            request.resource = request.tail = None
            request.exc = _exc
            # XXX should only should traceback if in some sort of dev mode?
            raise HTTPBadRequest(text=json.dumps({
                'success': False,
                'exception_message': str(_exc),
                'exception_type': getattr(type(_exc), '__name__', str(type(_exc))),
                'traceback': traceback.format_exc()
            }))

        request.resource = resource
        request.tail = tail

        if request.resource is None:
            raise HTTPBadRequest(text='Resource not found')

        traverse_to = None
        if tail and len(tail) == 1:
            view_name = tail[0]
        elif tail is None or len(tail) == 0:
            view_name = ''
        else:
            view_name = tail[0]
            traverse_to = tail[1:]

        method = DICT_METHODS[request.method]

        language = language_negotiation(request)
        language_object = language(request)

        translator = queryMultiAdapter(
            (language_object, resource, request),
            ITranslated)
        if translator is not None:
            resource = translator.translate()

        # Add anonymous participation
        if len(request.security.participations) == 0:
            logger.info("Anonymous User")
            request.security.add(AnonymousParticipation(request))

        permission = getUtility(IPermission, name='plone.AccessContent')

        allowed = request.security.checkPermission(permission.id, resource)

        if not allowed:
            # Check if its a CORS call:
            if IOPTIONS != method or \
                    (hasattr(request, 'site_settings') and
                     not request.site_settings.get(CORS_KEY, False)):
                logger.warn("No access content {content} with {auths}".format(
                    content=resource,
                    auths=str([x.principal.id
                               for x in request.security.participations])))
                raise HTTPUnauthorized()

        # Site registry lookup
        try:
            view = request.site_components.queryMultiAdapter(
                (resource, request), method, name=view_name)
        except AttributeError:
            view = None

        # Global registry lookup
        if view is None:
            view = queryMultiAdapter(
                (resource, request), method, name=view_name)

        # Traverse view if its needed
        if traverse_to is not None and view is not None:
            if not ITraversableView.providedBy(view):
                raise HTTPNotFound()
            else:
                try:
                    view = view.publishTraverse(traverse_to)
                except Exception as e:
                    logger.error(
                        "Exception on view execution",
                        exc_info=e)
                    raise HTTPNotFound()

        if view is None and method == IOPTIONS:
            if (not hasattr(request, 'site_settings') or
                    request.site_settings.get(CORS_KEY, False)):
                # Its a CORS call, we could not find any OPTION definition
                # Lets create a default preflight view
                # We check for site_settings in case the call is to some url before site
                view = DefaultOPTIONS(resource, request)

        checker = getCheckerForInstancesOf(view.__class__)
        if checker is not None:
            view = ProxyFactory(view, checker)
        # We want to check for the content negotiation

        renderer = content_type_negotiation(request, resource, view)
        renderer_object = renderer(request)

        rendered = queryMultiAdapter(
            (renderer_object, view, request), IRendered)

        if rendered is not None:
            return MatchInfo(resource, request, view, rendered)
        else:
            raise HTTPNotFound()

    async def traverse(self, request):
        """Wrapper that looks for the path based on aiohttp API."""
        path = tuple(p for p in request.path.split('/') if p)
        root = self._root
        return await traverse(request, root, path)
