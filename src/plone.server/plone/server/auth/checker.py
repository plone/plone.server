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
from plone.server.auth import principalRoleManager


globalRolesForPrincipal = principalRoleManager.getRolesForPrincipal


_marker = object()


@implementer(IChecker)
class ViewPermissionChecker(CheckerPy):
    """ This checker proxy is set on traversal to the view.

    The definition is set on the __call__ on Service definition

    """
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
