# -*- encoding: utf-8 -*-
from zope.interface import implementer
from plone.server.auth.role import checkRole
from zope.security.permission import allPermissions
from plone.server.interfaces import IPrincipalRoleManager
from plone.server.auth.securitymap import SecurityMap
from plone.server.interfaces import Allow, Deny, Unset
from plone.server.interfaces import IPrincipalPermissionManager
from plone.server.interfaces import IRolePermissionManager


@implementer(IPrincipalRoleManager)
class PrincipalRoleManager(SecurityMap):
    """Code mappings between principals and roles."""

    def assignRoleToPrincipal(self, role_id, principal_id, check=True):
        ''' See the interface IPrincipalRoleManager '''

        if check:
            checkRole(None, role_id)

        self.addCell(role_id, principal_id, Allow)

    def removeRoleFromPrincipal(self, role_id, principal_id, check=True):
        ''' See the interface IPrincipalRoleManager '''

        if check:
            checkRole(None, role_id)

        self.addCell(role_id, principal_id, Deny)

    def unsetRoleForPrincipal(self, role_id, principal_id):
        ''' See the interface IPrincipalRoleManager '''

        # Don't check validity intentionally.
        # After all, we certainly want to unset invalid ids.

        self.delCell(role_id, principal_id)

    def getPrincipalsForRole(self, role_id):
        ''' See the interface IPrincipalRoleMap '''
        return self.getRow(role_id)

    def getRolesForPrincipal(self, principal_id):
        ''' See the interface IPrincipalRoleMap '''
        return self.getCol(principal_id)

    def getSetting(self, role_id, principal_id, default=Unset):
        ''' See the interface IPrincipalRoleMap '''
        return self.queryCell(role_id, principal_id, default)

    def getPrincipalsAndRoles(self):
        ''' See the interface IPrincipalRoleMap '''
        return self.getAllCells()

# Roles are our rows, and principals are our columns
principalRoleManager = PrincipalRoleManager()  # noqa


@implementer(IPrincipalPermissionManager)
class PrincipalPermissionManager(SecurityMap):
    """Mappings between principals and permissions."""

    def grantPermissionToPrincipal(self, permission_id, principal_id,
                                   check=True):
        ''' See the interface IPrincipalPermissionManager '''

        self.addCell(permission_id, principal_id, Allow)

    def grantAllPermissionsToPrincipal(self, principal_id):
        ''' See the interface IPrincipalPermissionManager '''

        for permission_id in allPermissions(None):
            self.grantPermissionToPrincipal(permission_id, principal_id, False)

    def denyPermissionToPrincipal(self, permission_id, principal_id,
                                  check=True):
        ''' See the interface IPrincipalPermissionManager '''

        self.addCell(permission_id, principal_id, Deny)

    def unsetPermissionForPrincipal(self, permission_id, principal_id):
        ''' See the interface IPrincipalPermissionManager '''

        # Don't check validity intentionally.
        # After all, we certianly want to unset invalid ids.

        self.delCell(permission_id, principal_id)

    def getPrincipalsForPermission(self, permission_id):
        ''' See the interface IPrincipalPermissionManager '''
        return self.getRow(permission_id)

    def getPermissionsForPrincipal(self, principal_id):
        ''' See the interface IPrincipalPermissionManager '''
        return self.getCol(principal_id)

    def getSetting(self, permission_id, principal_id, default=Unset):
        ''' See the interface IPrincipalPermissionManager '''
        return self.queryCell(permission_id, principal_id, default)

    def getPrincipalsAndPermissions(self):
        ''' See the interface IPrincipalPermissionManager '''
        return self.getAllCells()


# Permissions are our rows, and principals are our columns
principalPermissionManager = PrincipalPermissionManager()


@implementer(IRolePermissionManager)
class RolePermissionManager(SecurityMap):
    """Mappings between roles and permissions."""

    def grantPermissionToRole(self, permission_id, role_id, check=True):
        '''See interface IRolePermissionMap'''

        if check:
            checkRole(None, role_id)

        self.addCell(permission_id, role_id, Allow)

    def grantAllPermissionsToRole(self, role_id):
        for permission_id in allPermissions(None):
            self.grantPermissionToRole(permission_id, role_id, False)

    def denyPermissionToRole(self, permission_id, role_id, check=True):
        '''See interface IRolePermissionMap'''

        if check:
            checkRole(None, role_id)

        self.addCell(permission_id, role_id, Deny)

    def unsetPermissionFromRole(self, permission_id, role_id):
        '''See interface IRolePermissionMap'''

        # Don't check validity intentionally.
        # After all, we certianly want to unset invalid ids.

        self.delCell(permission_id, role_id)

    def getRolesForPermission(self, permission_id):
        '''See interface IRolePermissionMap'''
        return self.getRow(permission_id)

    def getPermissionsForRole(self, role_id):
        '''See interface IRolePermissionMap'''
        return self.getCol(role_id)

    def getSetting(self, permission_id, role_id, default=Unset):
        '''See interface IRolePermissionMap'''
        return self.queryCell(permission_id, role_id, default)

    def getRolesAndPermissions(self):
        '''See interface IRolePermissionMap'''
        return self.getAllCells()

# Permissions are our rows, and roles are our columns
rolePermissionManager = RolePermissionManager()

