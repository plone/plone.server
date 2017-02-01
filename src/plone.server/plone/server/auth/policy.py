##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Define Zope's default security policy
"""

import zope.interface

from zope.security.checker import CheckerPublic
from zope.security.management import system_user
from zope.security.simplepolicies import ParanoidSecurityPolicy
from zope.security.interfaces import ISecurityPolicy
from zope.security.interfaces import IInteraction
from zope.security.proxy import removeSecurityProxy
from plone.server.auth import principalPermissionManager
from plone.server.auth import rolePermissionManager
from plone.server.auth import principalRoleManager
from plone.server.interfaces import Allow, Deny, Unset
from plone.server.interfaces import IRolePermissionMap
from plone.server.interfaces import IPrincipalPermissionMap
from plone.server.interfaces import IPrincipalRoleMap
from plone.server.interfaces import IRequest
from plone.server.auth.groups import PloneGroup
from plone.server.transactions import get_current_request
from plone.server import configure


SettingAsBoolean = {Allow: True, Deny: False, Unset: None, None: None}
codePrincipalPermissionSetting = principalPermissionManager.getSetting
codeRolesForPermission = rolePermissionManager.getRolesForPermission
codeRolesForPrincipal = principalRoleManager.getRolesForPrincipal


class CacheEntry:
    pass


@configure.adapter(
    for_=IRequest,
    provides=IInteraction)
def get_current_interaction(request):
    interaction = getattr(request, 'security', None)
    if IInteraction.providedBy(interaction):
        return interaction
    return Interaction(request)


@zope.interface.provider(ISecurityPolicy)
class Interaction(ParanoidSecurityPolicy):
    def __init__(self, request=None):
        ParanoidSecurityPolicy.__init__(self)
        self._cache = {}

        if request is not None:
            self.request = request
        else:
            # Try  magic request lookup if request not given
            self.request = get_current_request()

    def invalidate_cache(self):
        self._cache = {}

    def checkPermission(self, permission, obj):
        # Always allow public attributes
        if permission is CheckerPublic:
            return True

        # Remove implicit security proxy (if used)
        obj = removeSecurityProxy(obj)

        # Iterate through participations ('principals')
        # and check permissions they give
        seen = {}
        for participation in self.participations:
            principal = getattr(participation, 'principal', None)

            # Invalid participation (no principal)
            if principal is None:
                continue

            # System user always has access
            if principal is system_user:
                return True

            # Speed up by skipping seen principals
            if principal.id in seen:
                continue

            # Check the permission
            if self.cached_decision(
                    obj,
                    principal.id,
                    self._groupsFor(principal),
                    permission):
                return True

            seen[principal.id] = 1  # mark as seen

        return False

    def cached_principal_roles(self, parent, principal):
        # Redefine it to get global roles
        cache = self.cache(parent)
        try:
            cache_principal_roles = cache.principal_roles
        except AttributeError:
            cache_principal_roles = cache.principal_roles = {}
        try:
            return cache_principal_roles[principal]
        except KeyError:
            pass

        if parent is None:
            roles = dict(
                [(role, SettingAsBoolean[setting])
                 for (role, setting) in codeRolesForPrincipal(principal)])
            roles['plone.Anonymous'] = True  # Everybody has Anonymous
            cache_principal_roles[principal] = roles
            return roles

        roles = self.cached_principal_roles(
            removeSecurityProxy(getattr(parent, '__parent__', None)),
            principal)

        prinrole = IPrincipalRoleMap(parent, None)

        if prinrole:
            roles = roles.copy()
            for role, setting in prinrole.getRolesForPrincipal(
                    principal,
                    self.request):
                roles[role] = SettingAsBoolean[setting]

        cache_principal_roles[principal] = roles
        return roles

    def cache(self, parent):
        cache = self._cache.get(id(parent))
        if cache:
            cache = cache[0]
        else:
            cache = CacheEntry()
            self._cache[id(parent)] = cache, parent
        return cache

    def cached_decision(self, parent, principal, groups, permission):
        # Return the decision for a principal and permission

        cache = self.cache(parent)
        try:
            cache_decision = cache.decision
        except AttributeError:
            cache_decision = cache.decision = {}

        cache_decision_prin = cache_decision.get(principal)
        if not cache_decision_prin:
            cache_decision_prin = cache_decision[principal] = {}

        try:
            return cache_decision_prin[permission]
        except KeyError:
            pass

        # cache_decision_prin[permission] is the cached decision for a
        # principal and permission.

        decision = self.cached_prinper(parent, principal, groups, permission)
        if (decision is None) and groups:
            decision = self._group_based_cashed_prinper(parent, principal,
                                                        groups, permission)
        if decision is not None:
            cache_decision_prin[permission] = decision
            return decision

        roles = self.cached_roles(parent, permission)
        if roles:
            prin_roles = self.cached_principal_roles(parent, principal)
            if groups:
                prin_roles = self.cached_principal_roles_w_groups(
                    parent, principal, groups, prin_roles)
            for role, setting in prin_roles.items():
                if setting and (role in roles):
                    cache_decision_prin[permission] = decision = True
                    return decision

        cache_decision_prin[permission] = decision = False
        return decision

    def cached_prinper(self, parent, principal, groups, permission):
        # Compute the permission, if any, for the principal.
        cache = self.cache(parent)
        try:
            cache_prin = cache.prin
        except AttributeError:
            cache_prin = cache.prin = {}

        cache_prin_per = cache_prin.get(principal)
        if not cache_prin_per:
            cache_prin_per = cache_prin[principal] = {}

        try:
            return cache_prin_per[permission]
        except KeyError:
            pass

        if parent is None:
            prinper = SettingAsBoolean[
                codePrincipalPermissionSetting(permission, principal, None)]
            cache_prin_per[permission] = prinper
            return prinper

        prinper = IPrincipalPermissionMap(parent, None)
        if prinper is not None:
            prinper = SettingAsBoolean[
                prinper.getSetting(permission, principal, None)]
            if prinper is not None:
                cache_prin_per[permission] = prinper
                return prinper

        parent = removeSecurityProxy(getattr(parent, '__parent__', None))
        prinper = self.cached_prinper(parent, principal, groups, permission)
        cache_prin_per[permission] = prinper
        return prinper

    def _group_based_cashed_prinper(self, parent, principal, groups,
                                    permission):
        denied = False
        for group_id, ggroups in groups:
            decision = self.cached_prinper(parent, group_id, ggroups,
                                           permission)
            if (decision is None) and ggroups:
                decision = self._group_based_cashed_prinper(
                    parent, group_id, ggroups, permission)

            if decision is None:
                continue

            if decision:
                return decision

            denied = True

        if denied:
            return False

        return None

    def cached_roles(self, parent, permission):
        cache = self.cache(parent)
        try:
            cache_roles = cache.roles
        except AttributeError:
            cache_roles = cache.roles = {}
        try:
            return cache_roles[permission]
        except KeyError:
            pass

        if parent is None:
            roles = dict(
                [(role, 1)
                 for (role, setting) in codeRolesForPermission(permission)
                 if setting is Allow])
            cache_roles[permission] = roles
            return roles

        roles = self.cached_roles(
            removeSecurityProxy(getattr(parent, '__parent__', None)),
            permission)
        roleper = IRolePermissionMap(parent, None)
        if roleper:
            roles = roles.copy()
            for role, setting in roleper.getRolesForPermission(permission):
                if setting is Allow:
                    roles[role] = 1
                elif role in roles:
                    del roles[role]

        cache_roles[permission] = roles
        return roles

    def cached_principal_roles_w_groups(self, parent,
                                        principal, groups, prin_roles):
        denied = {}
        allowed = {}
        for group_id, ggroups in groups:
            group_roles = dict(self.cached_principal_roles(parent, group_id))
            if ggroups:
                group_roles = self.cached_principal_roles_w_groups(
                    parent, group_id, ggroups, group_roles)
            for role, setting in group_roles.items():
                if setting:
                    allowed[role] = setting
                else:
                    denied[role] = setting

        denied.update(allowed)
        denied.update(prin_roles)
        return denied

    def _findGroupsFor(self, principal, seen):
        result = []
        for group_id in getattr(principal, 'groups', ()):
            if group_id in seen:
                # Dang, we have a cycle.  We don't want to
                # raise an exception here (or do we), so we'll skip it
                continue
            seen.append(group_id)

            request = get_current_request()
            if not hasattr(request, '_cache_groups'):
                request._cache_groups = {}
            if principal not in request._cache_groups.keys():
                request._cache_groups[principal] = PloneGroup(request, principal)
            group = request._cache_groups[principal]

            result.append((group_id,
                           self._findGroupsFor(group, seen)))
            seen.pop()

        return tuple(result)

    def _groupsFor(self, principal):
        groups = self._cache.get(principal.id)
        if groups is None:
            groups = getattr(principal, 'groups', ())
            if groups:
                groups = self._findGroupsFor(principal, [])
            else:
                groups = ()

            self._cache[principal.id] = groups

        return groups



