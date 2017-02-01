# -*- coding: utf-8 -*-
from plone.server import configure
from plone.server.content import iter_schemata
from plone.server.directives import merged_tagged_value_dict
from plone.server.directives import read_permission
from plone.server.directives import write_permission
from plone.server.interfaces import DEFAULT_READ_PERMISSION
from plone.server.interfaces import DEFAULT_WRITE_PERMISSION
from plone.server.interfaces import IRequest
from plone.server.interfaces import IResource
from plone.server.transactions import get_current_request
from zope.component import adapter
from zope.interface import implementer
from zope.security._zope_security_checker import selectChecker
from zope.security.checker import _available_by_default
from zope.security.checker import CheckerPublic
from zope.security.checker import CheckerPy
from zope.security.checker import TracebackSupplement
from zope.security.interfaces import ForbiddenAttribute
from zope.security.interfaces import IChecker
from zope.security.interfaces import IInteraction
from zope.security.interfaces import Unauthorized
from zope.security.proxy import Proxy
from plone.server.interfaces import Allow
from plone.server.interfaces import Deny
from plone.server.interfaces import Unset
from plone.server.auth import principalRoleManager


globalRolesForPrincipal = principalRoleManager.getRolesForPrincipal

SettingAsBoolean = {
    Allow: True,
    Deny: False,
    Unset: None,
    None: None,
    1: True,
    0: False}

_marker = object()


@implementer(IChecker)
class ViewPermissionChecker(CheckerPy):
    def check_setattr(self, obj, name):
        if self.set_permissions:
            permission = self.set_permissions.get(name)
        else:
            permission = None

        if permission is not None:
            if permission is CheckerPublic:
                return  # Public

            request = get_current_request()
            if IInteraction(request).checkPermission(permission, obj):
                return  # allowed
            else:
                __traceback_supplement__ = (TracebackSupplement, obj)
                raise Unauthorized(obj, name, permission)

        __traceback_supplement__ = (TracebackSupplement, obj)
        raise ForbiddenAttribute(name, obj)

    def check(self, obj, name):
        permission = self.get_permissions.get(name)
        if permission is not None:
            if permission is CheckerPublic:
                return  # Public
            request = get_current_request()
            if IInteraction(request).checkPermission(permission, obj):
                return
            else:
                __traceback_supplement__ = (TracebackSupplement, obj)
                raise Unauthorized(obj, name, permission)
        elif name in _available_by_default:
            return

        if name != '__iter__' or hasattr(obj, name):
            __traceback_supplement__ = (TracebackSupplement, obj)
            raise ForbiddenAttribute(name, obj)

    check_getattr = check

    # IChecker.proxy
    def proxy(self, obj):
        return obj
        # TODO: Figure out, how to not wrap __providedBy__, __call__ etc
        # Once they have been checked


@configure.adapter(
    for_=IRequest,
    provides=IChecker)
class DexterityPermissionChecker(object):
    def __init__(self, request):
        self.request = request
        self.getters = {}
        self.setters = {}

    def check_getattr(self, obj, name):
        # Lookup or cached permission lookup
        portal_type = getattr(obj, 'portal_type', None)
        permission = self.getters.get((portal_type, name), _marker)

        # Lookup for the permission
        if permission is _marker:
            if name in _available_by_default:
                return
            permission = DEFAULT_READ_PERMISSION

        adapted = IResource(obj, None)

        if adapted is not None:
            for schema in iter_schemata(adapted):
                mapping = merged_tagged_value_dict(schema, read_permission.key)
                if name in mapping:
                    permission = mapping.get(name)
                    break
            self.getters[(portal_type, name)] = permission

        if IInteraction(self.request).checkPermission(permission, obj):
            return  # has permission

        __traceback_supplement__ = (TracebackSupplement, obj)
        raise Unauthorized(obj, name, permission)

    # IChecker.setattr
    def check_setattr(self, obj, name):
        # Lookup or cached permission lookup
        portal_type = getattr(obj, 'portal_type', None)
        permission = self.setters.get((portal_type, name), _marker)

        # Lookup for the permission
        if permission is _marker:
            if name in _available_by_default:
                return
            permission = DEFAULT_WRITE_PERMISSION

        adapted = IResource(obj, None)

        if adapted is not None:
            for schema in iter_schemata(adapted):
                mapping = merged_tagged_value_dict(schema, write_permission.key)
                if name in mapping:
                    permission = mapping.get(name)
                    break
            self.setters[(portal_type, name)] = permission

        if IInteraction(self.request).checkPermission(permission, obj):
            return  # has permission

        __traceback_supplement__ = (TracebackSupplement, obj)
        raise Unauthorized(obj, name, permission)

    # IChecker.check
    check = check_getattr

    # IChecker.proxy
    def proxy(self, obj):
        if isinstance(obj, Proxy):
            return obj
        # zope.security registered
        checker = selectChecker(obj)
        if checker is not None:
            return Proxy(obj, checker)
        return Proxy(obj, self)


