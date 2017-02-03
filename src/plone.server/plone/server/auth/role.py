from zope.interface import implementer
from zope.component import getUtilitiesFor

from plone.server.interfaces import IRole


@implementer(IRole)
class Role(object):

    def __init__(self, id, title, description=""):
        self.id = id
        self.title = title
        self.description = description


def check_role(context, role_id):
    names = [name for name, util in getUtilitiesFor(IRole, context)]
    if role_id not in names:
        raise ValueError("Undefined role id", role_id)
