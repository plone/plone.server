
import uuid

from zope.interface import implementer
from plone.server.uuid.interfaces import IUUIDGenerator


@implementer(IUUIDGenerator)
class UUID1Generator(object):
    """Default UUID implementation.
    Uses uuid.uuid4()
    """

    def __call__(self):
        return uuid.uuid4().hex