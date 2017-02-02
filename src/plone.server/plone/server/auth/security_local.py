# -*- encoding: utf-8 -*-
from plone.server import configure
from plone.server.interfaces import IResource
from plone.server.interfaces import IPrincipalRoleManager
from plone.server.auth.securitymap import PloneSecurityMap
from plone.server.interfaces import Allow, Deny, Unset, AllowSingle
from plone.server.interfaces import IPrincipalPermissionManager
from plone.server.interfaces import IRolePermissionManager


@configure.adapter(
    for_=IResource,
    provides=IRolePermissionManager,
    trusted=True)
class PloneRolePermissionManager(PloneSecurityMap):
    """Provide adapter that manages role permission data in an object attribute
    """

    # the annotation key is a holdover from this module's old
    # location, but cannot change without breaking existing databases
    key = 'roleperm'

    def grantPermissionToRole(self, permission_id, role_id, inherit=True):
        if inherit:
            PloneSecurityMap.addCell(self, permission_id, role_id, Allow)
        else:
            PloneSecurityMap.addCell(self, permission_id, role_id, AllowSingle)

    def denyPermissionToRole(self, permission_id, role_id):
        PloneSecurityMap.addCell(self, permission_id, role_id, Deny)

    unsetPermissionFromRole = PloneSecurityMap.delCell
    getRolesForPermission = PloneSecurityMap.getRow
    getPermissionsForRole = PloneSecurityMap.getCol
    getRolesAndPermissions = PloneSecurityMap.getAllCells

    def getSetting(self, permission_id, role_id, default=Unset):
        return PloneSecurityMap.queryCell(
            self, permission_id, role_id, default)


@configure.adapter(
    for_=IResource,
    provides=IPrincipalPermissionManager,
    trusted=True)
class PlonePrincipalPermissionManager(PloneSecurityMap):
    """Mappings between principals and permissions."""

    # the annotation key is a holdover from this module's old
    # location, but cannot change without breaking existing databases
    # It is also is misspelled, but that's OK. It just has to be unique.
    # we'll keep it as is, to prevent breaking old data:
    key = 'prinperm'

    def grantPermissionToPrincipal(
            self, permission_id, principal_id, inherit=True):
        if inherit:
            PloneSecurityMap.addCell(self, permission_id, principal_id, Allow)
        else:
            PloneSecurityMap.addCell(
                self, permission_id, principal_id, AllowSingle)

    def denyPermissionToPrincipal(self, permission_id, principal_id):
        PloneSecurityMap.addCell(self, permission_id, principal_id, Deny)

    unsetPermissionForPrincipal = PloneSecurityMap.delCell
    getPrincipalsForPermission = PloneSecurityMap.getRow
    getPermissionsForPrincipal = PloneSecurityMap.getCol

    def getSetting(self, permission_id, principal_id, default=Unset):
        return PloneSecurityMap.queryCell(
            self, permission_id, principal_id, default)

    getPrincipalsAndPermissions = PloneSecurityMap.getAllCells


@configure.adapter(
    for_=IResource,
    provides=IPrincipalRoleManager,
    trusted=True)
class PlonePrincipalRoleManager(PloneSecurityMap):
    """Mappings between principals and roles with global."""

    key = 'prinrole'

    def assignRoleToPrincipal(self, role_id, principal_id, inherit=True):
        if inherit:
            PloneSecurityMap.addCell(self, role_id, principal_id, Allow)
        else:
            PloneSecurityMap.addCell(self, role_id, principal_id, AllowSingle)

    def removeRoleFromPrincipal(self, role_id, principal_id):
        PloneSecurityMap.addCell(self, role_id, principal_id, Deny)

    unsetRoleForPrincipal = PloneSecurityMap.delCell
    getPrincipalsForRole = PloneSecurityMap.getRow

    def getSetting(self, role_id, principal_id, default=Unset):
        return PloneSecurityMap.queryCell(
            self, role_id, principal_id, default)

    getPrincipalsAndRoles = PloneSecurityMap.getAllCells

    getPrincipalsForRole = PloneSecurityMap.getRow
    getRolesForPrincipal = PloneSecurityMap.getCol


