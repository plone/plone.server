from zope.interface import Interface
from zope.interface.interfaces import IInterface

from zope import schema

from zope.schema.interfaces import IField
from zope.schema.interfaces import InvalidDottedName

class InvalidRegistryKey(InvalidDottedName):
    """A registry key is a dotted name with up to one '/'.
    """

class IPersistentField(IField):
    """A field that can be persistent along with a record.

    We provide our own implementation of the basic field types that are
    supported by the registry.

    A persistent field may track which interface and field it originally
    was constructed from. This is done by the registerInterface() method
    on the IRegistry, for example. Only the interface/field names are stored,
    not actual object references.
    """

    interfaceName = schema.DottedName(title=u"Dotted name to an interface the field was constructed from", required=False)
    fieldName = schema.ASCIILine(title=u"Name of the field in the original interface, if any", required=False)

class IFieldRef(Interface):
    """A reference to another field.

    This allows a record to use a field that belongs to another record. Field
    refs are allowed in the Record() constructor.

    Note that all attributes are read-only.
    """

    recordName = schema.DottedName(title=u"Name of the record containing the reference field")
    originalField = schema.Object(title=u"Referenced field", schema=IField)

class IRecord(Interface):
    """A record stored in the registry.

    A record may be "bound" or "unbound". If bound, it will have a
    __parent__ attribute giving the IRegistry it belongs to. It will then
    get and set its field and value attributes from the internal storage in
    the registry. If unbound, it will store its own values.

    A record becomes bound when added to the registry. Records retrieved from
    the registry are always bound.
    """

    field = schema.Object(title=u"A field describing this record",
                          schema=IPersistentField)

    value = schema.Field(title=u"The value of this record",
                         description=u"Must be valid according to the record's field")

class IRecordEvent(Interface):
    """Base interface for record level events
    """

    record = schema.Object(title=u"The record that was added.",
                           description=u"Both __name__ and __parent__ will be set before the event is fired",
                           schema=IRecord)

class IRecordAddedEvent(IRecordEvent):
    """Event fired when a record is added to a registry.
    """

class IRecordRemovedEvent(IRecordEvent):
    """Event fired when a record is removed from a registry.
    """

class IRecordModifiedEvent(IRecordEvent):
    """Event fired when a record's value is modified.
    """

    oldValue = schema.Field(title=u"The record's previous value")
    newValue = schema.Field(title=u"The record's new value")

class IInterfaceAwareRecord(Interface):
    """A record will be marked with this interface if it knows which
    interface its field came from.
    """

    interfaceName = schema.DottedName(title=u"Dotted name to interface")

    interface = schema.Object(title=u"Interface that provided the record",
                              description=u"May be None if the interface is no longer available",
                              schema=IInterface,
                              readonly=True)

    fieldName = schema.ASCIILine(title=u"Name of the field in the original interface")

class IRegistry(Interface):
    """The configuration registry
    """

    def __getitem__(key):
        """Get the value under the given key. A record must have been
        installed for this key for this to be valid. Otherwise, a KeyError is
        raised.
        """

    def get(key, default=None):
        """Attempt to get the value under the given key. If it does not
        exist, return the given default.
        """


    def __setitem__(key, value):
        """Set the value under the given key. A record must have been
        installed for this key for this to be valid. Otherwise, a KeyError is
        raised. If value is not of a type that's allowed by the record, a
        ValidationError is raised.
        """

    def __contains__(key):
        """Determine if the registry contains a record for the given key.
        """

    records = schema.Dict(
            title=u"The records of the registry",
            key_type=schema.DottedName(
                    title=u"Name of the record",
                    description=u"By convention, this should include the "
                                 "package name and optionally an interface "
                                 "named, if the record can be described by a "
                                 "field in an interface (see also "
                                 "registerInterface() below), e.g. "
                                 "my.package.interfaces.IMySettings.somefield.",
                ),
            value_type=schema.Object(
                    title=u"The record for this name",
                    schema=IRecord,
                ),
        )

    def forInterface(interface, check=True, omit=(), prefix=None):
        """Get an IRecordsProxy for the given interface. If `check` is True,
        an error will be raised if one or more fields in the interface does
        not have an equivalent setting.
        """

    def registerInterface(interface, omit=(), prefix=None):
        """Create a set of records based on the given interface. For each
        schema field in the interface, a record will be inserted with a
        name like `${interface.__identifier__}.${field.__name__}`, and a
        value equal to default value of that field. Any field with a name
        listed in `omit`, or with the `readonly` property set to True, will
        be ignored. Supply an alternative identifier with `prefix`.
        """

class IRecordsProxy(Interface):
    """This object is returned by IRegistry.forInterface(). It will be
    made to provide the relevant interface, i.e. it will have the
    attributes that the interface promises. Those attributes will be retrieved
    from or written to the underlying IRegistry.
    """

    __schema__ = schema.Object(title=u"Interface providing records",
                               schema=IInterface,
                               readonly=True)

    __registry__ = schema.Object(title=u"Registry where records will be looked up",
                                 schema=IRegistry,
                                 readonly=True)

    __omitted__ = schema.Tuple(title=u"Fields that are not stored in the registry",
                               description=u"If any of these are accessed, you will get an AttributeError",
                               value_type=schema.ASCIILine(title=u"Fieldname"),
                               readonly=True)
