# -*- coding: utf-8 -*-
"""Main routing traversal class."""
from aiohttp.abc import AbstractMatchInfo
from aiohttp.abc import AbstractRouter
from aiohttp.web_exceptions import HTTPBadRequest
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from plone.server import app_settings
from plone.server import _
from plone.server import logger
from plone.server.api.content import DefaultOPTIONS
from plone.server.auth.participation import AnonymousParticipation
from plone.server.browser import ErrorResponse
from plone.server.browser import Response
from plone.server.browser import UnauthorizedResponse
from plone.server.contentnegotiation import content_type_negotiation
from plone.server.contentnegotiation import language_negotiation
from plone.server.interfaces import IApplication
from plone.server.interfaces import IDatabase
from plone.server.interfaces import IDefaultLayer
from plone.server.interfaces import IOPTIONS
from plone.server.interfaces import IRendered
from plone.server.interfaces import IRequest
from plone.server.interfaces import ITranslated
from plone.server.interfaces import ITraversableView
from plone.server.interfaces import SHARED_CONNECTION
from plone.server.interfaces import SUBREQUEST_METHODS
from plone.server.interfaces import WRITING_VERBS
from plone.server.registry import ACTIVE_LAYERS_KEY
from plone.server.transactions import locked
from plone.server.transactions import abort
from plone.server.transactions import commit
from plone.server.utils import apply_cors
from plone.server.utils import import_class
from plone.server.utils import get_authenticated_user_id
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
from ZODB.POSException import ConflictError

import aiohttp
import asyncio
import json
import traceback
import uuid


async def do_traverse(request, parent, path):
    """Traverse for the code API."""
    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    if ISite.providedBy(parent) and \
       path[0] != request._db_id:
        # Tried to access a site outsite the request
        raise HTTPUnauthorized()

    if IApplication.providedBy(parent) and \
       path[0] != request._site_id:
        # Tried to access a site outsite the request
        raise HTTPUnauthorized()

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


async def subrequest(
        orig_request, path, relative_to_site=True,
        headers={}, body=None, params=None, method='GET'):
    """Subrequest, initial implementation doing a real request."""
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
        request.application = parent

    if not path:
        return parent, path

    assert request is not None  # could be used for permissions, etc

    try:
        if path[0].startswith('_'):
            raise HTTPUnauthorized()
        context = parent[path[0]]
    except TypeError:
        return parent, path
    except KeyError:
        return parent, path

    if IDatabase.providedBy(context):
        if SHARED_CONNECTION:
            request.conn = context.conn
        else:
            # Create a new conection
            request.conn = context.open()
        # Check the transaction
        request._db_write_enabled = False
        request._db_id = context.id
        context = request.conn.root()

    if ISite.providedBy(context):
        request._site_id = context.id
        request.site = context
        request.site_settings = context['_registry']
        layers = request.site_settings.get(ACTIVE_LAYERS_KEY, [])
        for layer in layers:
            alsoProvides(request, import_class(layer))

    return await traverse(request, context, path[1:])


def _url(request):
    try:
        return request.url.human_repr()
    except AttributeError:
        # older version of aiohttp
        return request.path


def generate_unauthorized_response(e, request):
    # We may need to check the roles of the users to show the real error
    eid = uuid.uuid4().hex
    message = _('Not authorized to render operation') + ' ' + eid
    user = get_authenticated_user_id(request)
    extra = {
        'r': _url(request),
        'u': user
    }
    logger.error(
        message,
        exc_info=e,
        extra=extra)
    return UnauthorizedResponse(message)


def generate_error_response(e, request, error, status=400):
    # We may need to check the roles of the users to show the real error
    eid = uuid.uuid4().hex
    message = _('Error on execution of view') + ' ' + eid
    user = get_authenticated_user_id(request)
    extra = {
        'r': _url(request),
        'u': user
    }
    logger.error(
        message,
        exc_info=e,
        extra=extra)

    return ErrorResponse(
        error,
        message,
        status
    )


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
            try:
                async with locked(self.resource):
                    request._db_write_enabled = True
                    txn = request.conn.transaction_manager.begin(request)
                    # We try to avoid collisions on the same instance of
                    # plone.server
                    view_result = await self.view()
                    if isinstance(view_result, ErrorResponse) or \
                            isinstance(view_result, UnauthorizedResponse):
                        # If we don't throw an exception and return an specific
                        # ErrorReponse just abort
                        await abort(txn, request)
                    else:
                        await commit(txn, request)

            except Unauthorized as e:
                await abort(txn, request)
                view_result = generate_unauthorized_response(e, request)
            except ConflictError as e:
                view_result = generate_error_response(
                    e, request, 'ConflictDB', 409)
            except Exception as e:
                await abort(txn, request)
                view_result = generate_error_response(
                    e, request, 'ServiceError')
        else:
            try:
                view_result = await self.view()
            except Unauthorized as e:
                view_result = generate_unauthorized_response(e, request)
            except Exception as e:
                view_result = generate_error_response(e, request, 'ViewError')

        # If we want to close the connection after the request
        if SHARED_CONNECTION is False and hasattr(request, 'conn'):
            request.conn.close()

        futures_to_wait = request._futures.values()
        if futures_to_wait:
            await asyncio.gather(futures_to_wait)

        # Make sure its a Response object to send to renderer
        if not isinstance(view_result, Response):
            view_result = Response(view_result)
        elif view_result is None:
            # Always provide some response to work with
            view_result = Response({})

        # Apply cors if its needed
        cors_headers = apply_cors(request)
        cors_headers.update(view_result.headers)
        view_result.headers = cors_headers

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
        result = None
        try:
            result = await self.real_resolve(request)
        except Exception as e:
            logger.error(
                "Exception on resolve execution",
                exc_info=e)
            raise e
        if result is not None:
            return result
        else:
            raise HTTPNotFound()

    async def real_resolve(self, request):
        """Main function to resolve a request."""
        alsoProvides(request, IRequest)
        alsoProvides(request, IDefaultLayer)

        request._futures = {}

        request.security = IInteraction(request)

        method = app_settings['http_methods'][request.method]

        language = language_negotiation(request)
        language_object = language(request)

        try:
            resource, tail = await self.traverse(request)
        except Exception as _exc:
            request.resource = request.tail = None
            request.exc = _exc
            # XXX should only should traceback if in some sort of dev mode?
            raise HTTPBadRequest(text=json.dumps({
                'success': False,
                'exception_message': str(_exc),
                'exception_type': getattr(type(_exc), '__name__', str(type(_exc))),  # noqa
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

        await self.apply_authorization(request)

        translator = queryMultiAdapter(
            (language_object, resource, request),
            ITranslated)
        if translator is not None:
            resource = translator.translate()

        # Add anonymous participation
        if len(request.security.participations) == 0:
            # logger.info("Anonymous User")
            request.security.add(AnonymousParticipation(request))

        # Site registry lookup
        try:
            view = queryMultiAdapter(
                (resource, request), method, name=view_name)
        except AttributeError:
            view = None

        # Traverse view if its needed
        if traverse_to is not None and view is not None:
            if not ITraversableView.providedBy(view):
                return None
            else:
                try:
                    view = view.publishTraverse(traverse_to)
                except Exception as e:
                    logger.error(
                        "Exception on view execution",
                        exc_info=e)
                    return None

        permission = getUtility(IPermission, name='plone.AccessContent')

        allowed = IInteraction(request).check_permission(permission.id, resource)

        if not allowed:
            # Check if its a CORS call:
            if IOPTIONS != method or not app_settings['cors']:
                # Check if the view has permissions explicit
                if view is None or not view.__allow_access__:
                    logger.warn("No access content {content} with {auths}".format(
                        content=resource,
                        auths=str([x.principal.id
                                   for x in request.security.participations])))
                    raise HTTPUnauthorized()

        if view is None and method == IOPTIONS:
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
            return None

    async def traverse(self, request):
        """Wrapper that looks for the path based on aiohttp API."""
        path = tuple(p for p in request.path.split('/') if p)
        root = self._root
        return await traverse(request, root, path)

    async def apply_authorization(self, request):
        # User participation
        participation = IParticipation(request)
        # Lets extract the user from the request
        await participation()
        if participation.principal is not None:
            request.security.add(participation)
