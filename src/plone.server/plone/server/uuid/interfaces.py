from zope.interface import Interface

ATTRIBUTE_NAME = '_plone.uuid'


class IUUIDGenerator(Interface):
    """Utility for generating UUIDs
    """

    def __call__():
        """Generate a new UUID.
        """


class IUUIDAware(Interface):
    """Marker interface for objects that have UUIDs. These should be
    adaptable to IUUID.
    """


class IAttributeUUID(IUUIDAware):
    """Marker interface for objects that have UUIDs stored in a simple
    attribute.
    This interface also confers an event handler that will add UUIDs when
    objects are created (IObjectCreatedEvent).
    """


class IUUID(Interface):
    """Abstract representation of a UUID.
    Adapt an object to this interface to obtain its UUID. Adaptation will
    fail if the object does not have a UUID (yet).
    """


class IMutableUUID(Interface):
    """Adapt an object to this interface to manage the UUID of an object
    Be sure of what you are doing. UUID is supposed to be stable and
    widely used
    """
    def get():
        """Return the UUID of the context"""

    def set(uuid):
        """Set the unique id of the context with the uuid value.
        """