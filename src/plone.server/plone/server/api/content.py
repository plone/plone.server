# -*- coding: utf-8 -*-
from aiohttp.web_exceptions import HTTPMethodNotAllowed
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web_exceptions import HTTPUnauthorized
from dateutil.tz import tzlocal
from plone.server import app_settings
from plone.server import configure
from plone.server import _
from plone.server.api.service import Service
from plone.server.browser import ErrorResponse
from plone.server.browser import Response
from plone.server.content import create_content_in_container
from plone.server.events import notify
from plone.server.events import ObjectFinallyCreatedEvent
from plone.server.events import ObjectFinallyDeletedEvent
from plone.server.events import ObjectFinallyModifiedEvent
from plone.server.events import ObjectFinallyVisitedEvent
from plone.server.events import ObjectPermissionsModifiedEvent
from plone.server.events import ObjectPermissionsViewEvent
from plone.server.exceptions import ConflictIdOnContainer
from plone.server.exceptions import PreconditionFailed
from plone.server.interfaces import IAbsoluteURL
from plone.server.interfaces import IResource
from plone.server.json.exceptions import DeserializationError
from plone.server.interfaces import IResourceDeserializeFromJson
from plone.server.interfaces import IResourceSerializeToJson
from plone.server.utils import get_authenticated_user_id
from plone.server.utils import iter_parents
from plone.server.auth import settings_for_object
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from plone.server.auth.role import local_roles

from plone.server.interfaces import IPrincipalPermissionMap
from plone.server.interfaces import IPrincipalRoleManager
from plone.server.interfaces import IRolePermissionManager
from plone.server.interfaces import IPrincipalPermissionManager
from plone.server.interfaces import IPrincipalRoleMap
from plone.server.interfaces import IRolePermissionMap

from zope.security.interfaces import IInteraction


_zone = tzlocal()


@configure.service(context=IResource, method='GET', permission='plone.ViewContent')
class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            IResourceSerializeToJson)
        result = serializer()
        await notify(ObjectFinallyVisitedEvent(self.context))
        return result


@configure.service(context=IResource, method='POST', permission='plone.AddContent')
class DefaultPOST(Service):

    async def __call__(self):
        """To create a content."""
        data = await self.get_data()
        type_ = data.get('@type', None)
        id_ = data.get('id', None)
        behaviors = data.get('@behaviors', None)

        if '__acl__' in data:
            # we don't allow to change the permisions on this patch
            del data['__acl__']

        if not type_:
            return ErrorResponse(
                'RequiredParam',
                _("Property '@type' is required"))

        # Generate a temporary id if the id is not given
        if not id_:
            new_id = None
        else:
            new_id = id_

        user = get_authenticated_user_id(self.request)
        # Create object
        try:
            obj = create_content_in_container(
                self.context, type_, new_id, id=new_id, creators=(user,),
                contributors=(user,))
        except PreconditionFailed as e:
            return ErrorResponse(
                'PreconditionFailed',
                str(e),
                status=412)
        except ConflictIdOnContainer as e:
            return ErrorResponse(
                'ConflictId',
                str(e),
                status=409)
        except ValueError as e:
            return ErrorResponse(
                'CreatingObject',
                str(e),
                status=400)

        for behavior in behaviors or ():
            obj.add_behavior(behavior)

        # Update fields
        deserializer = queryMultiAdapter((obj, self.request),
                                         IResourceDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(obj.portal_type),
                status=501)

        try:
            await deserializer(data, validate_all=True)
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                exc=e,
                status=400)

        # Local Roles assign owner as the creator user
        roleperm = IPrincipalRoleManager(obj)
        roleperm.assign_role_to_principal(
            'plone.Owner',
            user)

        await notify(ObjectFinallyCreatedEvent(obj, data))

        absolute_url = queryMultiAdapter((obj, self.request), IAbsoluteURL)

        headers = {
            'Access-Control-Expose-Headers': 'Location',
            'Location': absolute_url()
        }

        serializer = queryMultiAdapter(
            (obj, self.request),
            IResourceSerializeToJson
        )
        return Response(response=serializer(), headers=headers, status=201)


@configure.service(context=IResource, method='PUT', permission='plone.ModifyContent')
class DefaultPUT(Service):
    pass


@configure.service(context=IResource, method='PATCH', permission='plone.ModifyContent')
class DefaultPATCH(Service):
    async def __call__(self):
        data = await self.get_data()
        behaviors = data.get('@behaviors', None)
        for behavior in behaviors or ():
            self.context.add_behavior(behavior)

        deserializer = queryMultiAdapter((self.context, self.request),
                                         IResourceDeserializeFromJson)
        if deserializer is None:
            return ErrorResponse(
                'DeserializationError',
                'Cannot deserialize type {}'.format(self.context.portal_type),
                status=501)

        try:
            await deserializer(data)
        except DeserializationError as e:
            return ErrorResponse(
                'DeserializationError',
                str(e),
                status=400)

        await notify(ObjectFinallyModifiedEvent(self.context, data))

        return Response(response={}, status=204)


@configure.service(context=IResource, method='GET', permission='plone.SeePermissions',
                   name='@sharing')
async def sharing_get(context, request):
    roleperm = IRolePermissionMap(context)
    prinperm = IPrincipalPermissionMap(context)
    prinrole = IPrincipalRoleMap(context)
    result = {
        'local': {},
        'inherit': []
    }
    result['local']['roleperm'] = roleperm._bycol
    result['local']['prinperm'] = prinperm._bycol
    result['local']['prinrole'] = prinrole._bycol
    for obj in iter_parents(context):
        roleperm = IRolePermissionMap(obj)
        prinperm = IPrincipalPermissionMap(obj)
        prinrole = IPrincipalRoleMap(obj)
        result['inherit'].append({
            '@id': IAbsoluteURL(obj, request)(),
            'roleperm': roleperm._bycol,
            'prinperm': prinperm._bycol,
            'prinrole': prinrole._bycol,
        })
    await notify(ObjectPermissionsViewEvent(context))
    return result


@configure.service(context=IResource, method='GET', permission='plone.SeePermissions',
                   name='@all_permissions')
async def all_permissions(context, request):
    result = settings_for_object(context)
    await notify(ObjectPermissionsViewEvent(context))
    return result


PermissionMap = {
    'prinrole': {
        'Allow': 'assign_role_to_principal',
        'Deny': 'remove_role_from_principal',
        'AllowSingle': 'assign_role_to_principal_no_inherit',
        'Unset': 'unset_role_for_principal'
    },
    'roleperm': {
        'Allow': 'grant_permission_to_role',
        'Deny': 'deny_permission_to_role',
        'AllowSingle': 'grant_permission_to_role_no_inherit',
        'Unset': 'unset_permission_from_role'
    },
    'prinperm': {
        'Allow': 'grant_permission_to_principal',
        'Deny': 'deny_permission_to_principal',
        'AllowSingle': 'grant_permission_to_principal_no_inherit',
        'Unset': 'unset_permission_for_principal'
    }
}


@configure.service(context=IResource, method='POST', permission='plone.ChangePermissions',
                   name='@sharing')
async def sharing_post(context, request):
    """Change permissions"""
    lroles = local_roles()
    data = await request.json()
    if 'prinrole' not in data and \
            'roleperm' not in data and \
            'prinperm' not in data:
        raise AttributeError('prinrole or roleperm or prinperm missing')

    if 'type' not in data:
        raise AttributeError('type missing')

    setting = data['type']

    # we need to check if we are changing any info

    changed = False

    if 'prinrole' in data:
        if setting not in PermissionMap['prinrole']:
            raise AttributeError('Invalid Type')
        manager = IPrincipalRoleManager(context)
        operation = PermissionMap['prinrole'][setting]
        func = getattr(manager, operation)
        for user, roles in data['prinrole'].items():
            for role in roles:
                if role in lroles:
                    changed = True
                    func(role, user)
                else:
                    raise KeyError('No valid local role')

    if 'prinperm' in data:
        if setting not in PermissionMap['prinperm']:
            raise AttributeError('Invalid Type')
        manager = IPrincipalPermissionManager(context)
        operation = PermissionMap['prinperm'][setting]
        func = getattr(manager, operation)
        for user, permissions in data['prinperm'].items():
            for permision in permissions:
                changed = True
                func(permision, user)

    if 'roleperm' in data:
        if setting not in PermissionMap['roleperm']:
            raise AttributeError('Invalid Type')
        manager = IRolePermissionManager(context)
        operation = PermissionMap['roleperm'][setting]
        func = getattr(manager, operation)
        for role, permissions in data['roleperm'].items():
            for permission in permissions:
                changed = True
                func(permission, role)

    context._p_changed = 1
    if changed:
        await notify(ObjectPermissionsModifiedEvent(context, data))


@configure.service(
    context=IResource, method='GET', permission='plone.AccessContent',
    name='@canido')
async def can_i_do(context, request):
    if 'permission' not in request.GET:
        raise TypeError('No permission param')
    permission = request.GET['permission']
    return IInteraction(request).check_permission(permission, context)


@configure.service(context=IResource, method='DELETE', permission='plone.DeleteContent')
class DefaultDELETE(Service):

    async def __call__(self):
        content_id = self.context.id
        del self.context.__parent__[content_id]
        await notify(ObjectFinallyDeletedEvent(self.context))


@configure.service(context=IResource, method='OPTIONS', permission='plone.AccessPreflight')
class DefaultOPTIONS(Service):
    """Preflight view for Cors support on DX content."""

    def getRequestMethod(self):  # noqa
        """Get the requested method."""
        return self.request.headers.get(
            'Access-Control-Request-Method', None)

    async def preflight(self):
        """We need to check if there is cors enabled and is valid."""
        headers = {}

        if not app_settings['cors']:
            return {}

        origin = self.request.headers.get('Origin', None)
        if not origin:
            raise HTTPNotFound(text='Origin this header is mandatory')

        requested_method = self.getRequestMethod()
        if not requested_method:
            raise HTTPNotFound(
                text='Access-Control-Request-Method this header is mandatory')

        requested_headers = (
            self.request.headers.get('Access-Control-Request-Headers', ()))

        if requested_headers:
            requested_headers = map(str.strip, requested_headers.split(', '))

        requested_method = requested_method.upper()
        allowed_methods = app_settings['cors']['allow_methods']
        if requested_method not in allowed_methods:
            raise HTTPMethodNotAllowed(
                requested_method, allowed_methods,
                text='Access-Control-Request-Method Method not allowed')

        supported_headers = app_settings['cors']['allow_headers']
        if '*' not in supported_headers and requested_headers:
            supported_headers = [s.lower() for s in supported_headers]
            for h in requested_headers:
                if not h.lower() in supported_headers:
                    raise HTTPUnauthorized(
                        text='Access-Control-Request-Headers Header %s not allowed' % h)

        supported_headers = [] if supported_headers is None else supported_headers
        requested_headers = [] if requested_headers is None else requested_headers

        supported_headers = set(supported_headers) | set(requested_headers)

        headers['Access-Control-Allow-Headers'] = ','.join(
            supported_headers)
        headers['Access-Control-Allow-Methods'] = ','.join(
            app_settings['cors']['allow_methods'])
        headers['Access-Control-Max-Age'] = str(app_settings['cors']['max_age'])
        return headers

    async def render(self):
        """Need to be overwritten in case you implement OPTIONS."""
        return {}

    async def __call__(self):
        """Apply CORS on the OPTIONS view."""
        headers = await self.preflight()
        resp = await self.render()
        if isinstance(resp, Response):
            headers.update(resp.headers)
            resp.headers = headers
            return resp
        return Response(response=resp, headers=headers, status=200)
