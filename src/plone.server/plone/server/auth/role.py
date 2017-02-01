from persistent import Persistent

from zope.interface import implementer
from zope.component import getUtilitiesFor
from zope.location import Location

from plone.server.interfaces import IRole

from zope.i18nmessageid import ZopeMessageFactory as _
NULL_ID = _('<role not activated>')


@implementer(IRole)
class Role(object):

    def __init__(self, id, title, description=""):
        self.id = id
        self.title = title
        self.description = description


@implementer(IRole)
class LocalRole(Persistent, Location):

    def __init__(self, title, description=""):
        self.id = NULL_ID
        self.title = title
        self.description = description


def setIdOnActivation(role, event):
    """Set the permission id upon registration activation.

    Let's see how this notifier can be used. First we need to create an event
    using the permission instance and a registration stub:

    >>> class Registration:
    ...     def __init__(self, obj, name):
    ...         self.component = obj
    ...         self.name = name

    >>> role1 = LocalRole('Role 1', 'A first role')
    >>> role1.id
    u'<role not activated>'
    >>> import zope.component.interfaces
    >>> event = zope.component.interfaces.Registered(
    ...     Registration(role1, 'role1'))

    Now we pass the event into this function, and the id of the role should be
    set to 'role1'.

    >>> setIdOnActivation(role1, event)
    >>> role1.id
    'role1'
    """
    role.id = event.object.name


def unsetIdOnDeactivation(role, event):
    """Unset the permission id up registration deactivation.

    Let's see how this notifier can be used. First we need to create an event
    using the permission instance and a registration stub:

    >>> class Registration:
    ...     def __init__(self, obj, name):
    ...         self.component = obj
    ...         self.name = name

    >>> role1 = LocalRole('Role 1', 'A first role')
    >>> role1.id = 'role1'

    >>> import zope.component.interfaces
    >>> event = zope.component.interfaces.Unregistered(
    ...     Registration(role1, 'role1'))

    Now we pass the event into this function, and the id of the role should be
    set to NULL_ID.

    >>> unsetIdOnDeactivation(role1, event)
    >>> role1.id
    u'<role not activated>'
    """
    role.id = NULL_ID


def checkRole(context, role_id):
    names = [name for name, util in getUtilitiesFor(IRole, context)]
    if role_id not in names:
        raise ValueError("Undefined role id", role_id)
