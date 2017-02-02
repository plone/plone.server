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
from zope.security.interfaces import ISecurityPolicy
from zope.security.interfaces import IInteraction
from zope.security.proxy import removeSecurityProxy
from plone.server.auth import principalPermissionManager
from plone.server.auth import rolePermissionManager
from plone.server.auth import principalRoleManager
from plone.server.interfaces import Allow, Deny, Unset, AllowSingle
from plone.server.interfaces import IRolePermissionMap
from plone.server.interfaces import IPrincipalPermissionMap
from plone.server.interfaces import IPrincipalRoleMap
from plone.server.interfaces import IRequest
from plone.server.interfaces import IGroups
from zope.component import getUtility
from plone.server.transactions import get_current_request
from plone.server import configure


codePrincipalPermissionSetting = principalPermissionManager.getSetting
codeRolesForPermission = rolePermissionManager.getRolesForPermission
codeRolesForPrincipal = principalRoleManager.getRolesForPrincipal


SettingAsBoolean = {
        Allow: True,
        Deny: False,
        Unset: None,
        AllowSingle: 'o',
        None: None
    }


def levelSettingAsBoolean(level, value):
    # We want to check if its allow
    let = SettingAsBoolean[value]
    return let == level if type(let) is str else let


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


@zope.interface.implementer(IInteraction)
@zope.interface.provider(ISecurityPolicy)
class Interaction(object):

    def __init__(self, request=None):
        self.participations = []
        self._cache = {}
        self.principal = None

        if request is not None:
            self.request = request
        else:
            # Try  magic request lookup if request not given
            self.request = get_current_request()

    def add(self, participation):
        if participation.interaction is not None:
            raise ValueError("%r already belongs to an interaction"
                             % participation)
        participation.interaction = self
        self.participations.append(participation)

    def remove(self, participation):
        if participation.interaction is not self:
            raise ValueError("%r does not belong to this interaction"
                             % participation)
        self.participations.remove(participation)
        participation.interaction = None

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

            self.principal = principal
            # Check the permission
            if self.cached_decision(
                    obj,
                    principal.id,
                    self._groupsFor(principal),
                    permission):
                return True

            seen[principal.id] = 1  # mark as seen

        return False

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

        # Check direct permissions
        # First recursive function to get the permissions of a principal
        decision = self.cached_prinper(
            parent, principal, groups, permission, 'o')
        if (decision is None) and groups:
            # Second get the permissions of the groups on the tree
            decision = self._group_based_cashed_prinper(
                parent, principal, groups, permission, 'o')
        if decision is not None:
            cache_decision_prin[permission] = decision
            return decision

        # Check Roles permission
        roles = self.cached_roles(parent, permission, 'o')
        if roles:
            prin_roles = self.cached_principal_roles(parent, principal, 'o')
            if groups:
                prin_roles = self.cached_principal_roles_w_groups(
                    parent, principal, groups, prin_roles, 'o')
            for role, setting in prin_roles.items():
                if setting and (role in roles):
                    cache_decision_prin[permission] = decision = True
                    return decision

        cache_decision_prin[permission] = decision = False
        return decision

    def cached_prinper(self, parent, principal, groups, permission, level):
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

        # We reached the end of the recursive we check global / local
        if parent is None:
            # We check the global configuration
            prinper = self._globalPermissionsFor(permission, principal)
            if prinper:
                cache_prin_per[permission] = prinper
                return prinper

            # If we did not found the permission for the user look at code
            prinper = SettingAsBoolean[
                codePrincipalPermissionSetting(permission, principal, None)]
            cache_prin_per[permission] = prinper
            return prinper

        # Get the local map of the permissions
        # As we want to quit as soon as possible we check first locally
        prinper = IPrincipalPermissionMap(parent, None)
        if prinper is not None:
            prinper = levelSettingAsBoolean(
                level, prinper.getSetting(permission, principal, None))
            if prinper is not None:
                cache_prin_per[permission] = prinper
                return prinper

        # Find the permission recursivelly set to a user
        parent = removeSecurityProxy(getattr(parent, '__parent__', None))
        prinper = self.cached_prinper(
            parent, principal, groups, permission, 'p')
        cache_prin_per[permission] = prinper
        return prinper

    def cached_principal_roles(self, parent, principal, level):
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

        # We reached the end so we go to see the global ones
        if parent is None:
            # Then the code roles
            roles = dict(
                [(role, SettingAsBoolean[setting])
                 for (role, setting) in codeRolesForPrincipal(principal)])
            roles['plone.Anonymous'] = True  # Everybody has Anonymous

            # First the global roles
            groles = self._globalRolesFor(principal)
            roles.update(groles)
            
            cache_principal_roles[principal] = roles
            return roles

        roles = self.cached_principal_roles(
            removeSecurityProxy(getattr(parent, '__parent__', None)),
            principal, 'p')

        # We check the local map of roles
        prinrole = IPrincipalRoleMap(parent, None)

        if prinrole:
            roles = roles.copy()
            for role, setting in prinrole.getRolesForPrincipal(
                    principal):
                roles[role] = levelSettingAsBoolean(level, setting)

        cache_principal_roles[principal] = roles
        return roles

    def _group_based_cashed_prinper(self, parent, principal, groups,
                                    permission, level):
        denied = False
        for group_id, ggroups in groups:
            decision = self.cached_prinper(parent, group_id, ggroups,
                                           permission, level)
            if (decision is None) and ggroups:
                decision = self._group_based_cashed_prinper(
                    parent, group_id, ggroups, permission, level)

            if decision is None:
                continue

            if decision:
                return decision

            denied = True

        if denied:
            return False

        return None

    def cached_roles(self, parent, permission, level):
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
            permission, 'p')
        roleper = IRolePermissionMap(parent, None)
        if roleper:
            roles = roles.copy()
            for role, setting in roleper.getRolesForPermission(permission):
                if setting is Allow:
                    roles[role] = 1
                if setting is AllowSingle and level == 'o':
                    roles[role] = 1
                elif role in roles:
                    del roles[role]

        cache_roles[permission] = roles
        return roles

    def cached_principal_roles_w_groups(self, parent,
                                        principal, groups, prin_roles, level):
        denied = {}
        allowed = {}
        for group_id, ggroups in groups:
            group_roles = dict(self.cached_principal_roles(parent, group_id, level))
            if ggroups:
                group_roles = self.cached_principal_roles_w_groups(
                    parent, group_id, ggroups, group_roles, level)
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

            groups = getUtility(IGroups)
            group = groups.getPrincipal(group_id)

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

    def _globalRolesFor(self, principal):
        # check if its the actual user
        # We may need to have an interface to look for users info
        roles = {}
        if self.principal and principal == self.principal.id:
            roles = self.principal.roles.copy()
            return roles

        groups = getUtility(IGroups)
        if groups:
            group = groups.getPrincipal(principal)
            return group.roles.copy()

    def _globalPermissionsFor(self, principal, permission):
        permissions = {}
        if self.principal and principal == self.principal.id:
            permissions = self.principal.permissions.copy()
            return permissions

        groups = getUtility(IGroups)
        if groups:
            group = groups.getPrincipal(principal)
            if group:
                return group.permissions.copy()


