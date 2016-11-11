================
Using registries
================

You can create a new registry simply by instantiating the Registry class.
The class and its data structures are persistent, so you can store them in the ZODB.
You may want to provide the registry object as local utility for easy access as well, though we won't do that here.

::

    >>> from plone.registry import Registry
    >>> registry = Registry()

The registry starts out empty.
To access the registry's records, you can use the ``records`` property.
This exposes a dict API where keys are strings and values are objects providing ``IRecords``.

::

    >>> len(registry.records)
    0

Simple records
==============

Let's now create a record.
A record must have a name.
This should be a dotted name, and contain ASCII characters only.
By convention, it should be all lowercase and start with the name of the package that defines the record.

It is also possible to create a  number of records based on a single schema interface - see below.
For now, we will focus on simple records.

Before we can create the record, we must create the field that describes it.
Fields are based on the venerable ``zope.schema`` package.
``plone.registry`` only supports certain fields, and disallows use of a few properties even of those.
As a rule of thumb, so long as a field stores a Python primitive, it is supported; the same goes for attributes of fields.

Thus:

* Fields like ``Object``, ``InterfaceField`` and so on are *not* supported.
* A custom ``constraint`` method is *not* supported.
* The ``order`` attribute will *always* be set to ``-1``.
* For Choice fields, *only named vocabularies* are supported:
  you can *not* reference a particular *source* or *source binder*.
* The ``key_type`` and ``value_type`` properties of ``Dict``, ``List``, ``Tuple``, ``Set`` and ``Frozenset`` may *only* contain persistent fields.

See section "Persistent fields" for more details.

Creating a record
-----------------

The supported field types are found in the module ``plone.registry.field``.
These are named the same as the equivalent field in ``zope.schema``, and have the same constructors.
You must use one of these fields when creating records directly::

    >>> from plone.registry import field
    >>> age_field = field.Int(title=u"Age", min=0, default=18)

    >>> from plone.registry import Record
    >>> age_record = Record(age_field)

Note that in this case, we did not supply a value.
The value will therefore be the field default::

    >>> age_record.value
    18

We can set a different value, either in the ``Record`` constructor or via the ``value`` attribute::

    >>> age_record.value = 2
    >>> age_record.value
    2

Note that the value is validated against the field::

    >>> age_record.value = -1  # doctest: +SKIP_PYTHON_3
    Traceback (most recent call last):
    ...
    TooSmall: (-1, 0)

    >>> age_record.value = -1  # doctest: +SKIP_PYTHON_2
    Traceback (most recent call last):
    ...
    zope.schema._bootstrapinterfaces.TooSmall: (-1, 0)

    >>> age_record.value
    2

We can now add the field to the registry.
This is done via the ``record`` dictionary::

    >>> 'plone.registry.tests.age' in registry
    False
    >>> registry.records['plone.registry.tests.age'] = age_record

At this point, the record will gain ``__name__`` and ``__parent__`` attributes::

    >>> age_record.__name__
    'plone.registry.tests.age'

    >>> age_record.__parent__ is registry
    True

Creating a record with an initial value
---------------------------------------

We can create records more succinctly in *one go* by

1. creating the field,
2. creating the Record and setting its value as and
3. assigning it to the registry,

like this::

    >>> registry.records['plone.registry.tests.cms'] = \
    ...     Record(field.TextLine(title=u"CMS of choice"), u"Plone")

The record can now be obtained.
Note that it has a nice ``__repr__`` to help debugging.

    >>> registry.records['plone.registry.tests.cms']
    <Record plone.registry.tests.cms>

Accessing and manipulating record values
----------------------------------------

Once a record has been created and added to the registry,
you can access its value through dict-like operations on the registry itself::

    >>> 'plone.registry.tests.cms' in registry
    True

    >>> registry['plone.registry.tests.cms']  # doctest: +IGNORE_U
    u'Plone'

    >>> registry['plone.registry.tests.cms'] = u"Plone 3.x"

Again, values are validated::

    >>> registry['plone.registry.tests.cms'] = b'Joomla'  # doctest: +SKIP_PYTHON_3
    Traceback (most recent call last):
    ...
    WrongType: ('Joomla', <type 'unicode'>...)
    
    >>> registry['plone.registry.tests.cms'] = b'Joomla'  # doctest: +SKIP_PYTHON_2
    Traceback (most recent call last):
    ...
    zope.schema._bootstrapinterfaces.WrongType: (b'Joomla', <class 'str'>, 'value')

There is also a ``get()`` method::

    >>> registry.get('plone.registry.tests.cms')  # doctest: +IGNORE_U
    u'Plone 3.x'
    >>> registry.get('non-existent-key') is None
    True

Deleting records
----------------

Records may be deleted from the ``records`` property::

    >>> del registry.records['plone.registry.tests.cms']
    >>> 'plone.registry.tests.cms' in registry.records
    False
    >>> 'plone.registry.tests.cms' in registry
    False

Creating records from interfaces
================================

As an application developer, it is often desirable to define settings as traditional interfaces with ``zope.schema fields``.
``plone.registry`` includes support for creating a set of records from a single interface.

To test this, we have created an interface, ``IMailSettings``.
It has two fields: ``sender`` and ``smtp_host``::

    >>> from plone.registry.tests import IMailSettings

Note that this contains standard fields::

    >>> IMailSettings['sender']
    <zope.schema._bootstrapfields.TextLine object at ...>

    >>> IMailSettings['smtp_host']
    <zope.schema._field.URI object at ...>

We can create records from this interface like this::

    >>> registry.registerInterface(IMailSettings)

One record for each field in the interface has now been created.
Their names are the full dotted names to those fields::

    >>> sender_record = registry.records['plone.registry.tests.IMailSettings.sender']
    >>> smtp_host_record = registry.records['plone.registry.tests.IMailSettings.smtp_host']

The fields used in the records will be the equivalent persistent versions of the fields from the original interface::

    >>> sender_record.field
    <plone.registry.field.TextLine object at ...>

    >>> smtp_host_record.field
    <plone.registry.field.URI object at ...>

This feat is accomplished internally by adapting the field to the ``IPersistentField`` interface.
There is a default adapter factory that works for all fields defined in ``plone.registry.field``.
You can of course define your own adapter if you have a custom field type.
But bear in mind the golden rules of any persistent field::

* The field must store only primitives or other persistent fields
* It must not reference a function, class, interface or other method that could break if a package is uninstalled.

If we have a field for which there is no ``IPersistentField`` adapter, we will get an error::

    >>> from plone.registry.tests import IMailPreferences
    >>> IMailPreferences['settings']
    <zope.schema._field.Object object at ...>

    >>> registry.registerInterface(IMailPreferences)
    Traceback (most recent call last):
    ...
    TypeError: There is no persistent field equivalent for the field `settings` of type `Object`.

Whoops!
We can, however, tell ``registerInterface()`` to ignore one or more fields::

    >>> registry.registerInterface(IMailPreferences, omit=('settings',))

Once an interface's records have been registered, we can get and set their values as normal::

    >>> registry['plone.registry.tests.IMailSettings.sender']  # doctest: +IGNORE_U
    u'root@localhost'

    >>> registry['plone.registry.tests.IMailSettings.sender'] = u"webmaster@localhost"
    >>> registry['plone.registry.tests.IMailSettings.sender']  # doctest: +IGNORE_U
    u'webmaster@localhost'

If we sub-sequently re-register the same interface, the value will be retained if possible::

    >>> registry.registerInterface(IMailSettings)
    >>> registry['plone.registry.tests.IMailSettings.sender']  # doctest: +IGNORE_U
    u'webmaster@localhost'

However, if the value is no longer valid, we will revert to the default.
To test that, let's sneakily modify the field for a while::

    >>> old_field = IMailSettings['sender']
    >>> IMailSettings._InterfaceClass__attrs['sender'] = field.Int(title=u"Definitely not a string", default=2)
    >>> if hasattr(IMailSettings, '_v_attrs'):
    ...     del IMailSettings._v_attrs['sender']
    >>> registry.registerInterface(IMailSettings)
    >>> registry['plone.registry.tests.IMailSettings.sender']
    2

But let's put it back the way it was::

    >>> IMailSettings._InterfaceClass__attrs['sender'] = old_field
    >>> if hasattr(IMailSettings, '_v_attrs'):
    ...     del IMailSettings._v_attrs['sender']
    >>> registry.registerInterface(IMailSettings)
    >>> registry['plone.registry.tests.IMailSettings.sender']  # doctest: +IGNORE_U
    u'root@localhost'

Sometimes, you may want to use an interface as a template for multiple instances of a set of fields, rather than defining them all by hand.
This is especially useful when you want to allow third-party packages to provide information.
To accomplish this, we can provide a prefix with the ``registerInterface`` call.
This will take precedence over the ``__identifier__`` that is usually used.

    >>> registry.registerInterface(IMailSettings, prefix="plone.registry.tests.alternativesettings")

These values are now available in the same way as the original settings::

    >>> sender_record = registry.records['plone.registry.tests.alternativesettings.sender']
    >>> smtp_host_record = registry.records['plone.registry.tests.alternativesettings.smtp_host']
    >>> registry['plone.registry.tests.alternativesettings.sender'] = u'alt@example.org'

Accessing the original interface
--------------------------------

Now that we have these records, we can look up the original interface.
This does not break the golden rules:
internally, we only store the name of the interface, and resolve it at runtime.

Records that know about interfaces are marked with ``IInterfaceAwareRecord`` and have two additional properties:
``interface`` and ``fieldName``::

    >>> from plone.registry.interfaces import IInterfaceAwareRecord
    >>> IInterfaceAwareRecord.providedBy(age_record)
    False
    >>> IInterfaceAwareRecord.providedBy(sender_record)
    True

    >>> sender_record.interfaceName
    'plone.registry.tests.IMailSettings'

    >>> sender_record.interface is IMailSettings
    True

Using the records proxy
-----------------------

Once the records for an interface has been created, it is possible to obtain a proxy object that provides the given interface, but reads and writes its values to the registry.
This is useful, for example, to create a form using ``zope.formlib`` or  ``z3c.form`` that is configured with widgets based on the
interface.
Or simply as a more convenient API when working with multiple, related settings.

::

    >>> proxy = registry.forInterface(IMailSettings)
    >>> proxy
    <RecordsProxy for plone.registry.tests.IMailSettings>

If you use your registry values in code which might be encountered on normal HTML rendering paths (e.g. in a viewlet) you need to be aware that records might not exist or they are invalid.
``forInterface()`` will raise KeyError on this kind of situations::

    try:
        proxy = registry.forInterface(IMailSettings)
    except KeyError:
        # Gracefully handled cases
        # when GenericSetup installer has not been run or rerun
        # e.g. by returning or using some default values
        pass

The proxy is not a persistent object on its own::

    >>> from persistent.interfaces import IPersistent
    >>> IPersistent.providedBy(proxy)
    False

It does, however, provide the requisite interface::

    >>> IMailSettings.providedBy(proxy)
    True

You can distinguish between the proxy and a 'normal' object by checking for the ``IRecordsProxy`` marker interface::

    >>> from plone.registry.interfaces import IRecordsProxy
    >>> IRecordsProxy.providedBy(proxy)
    True

When we set a value, it is stored in the registry::

    >>> proxy.smtp_host = 'http://mail.server.com'
    >>> registry['plone.registry.tests.IMailSettings.smtp_host']
    'http://mail.server.com'

    >>> registry['plone.registry.tests.IMailSettings.smtp_host'] = 'smtp://mail.server.com'
    >>> proxy.smtp_host
    'smtp://mail.server.com'

Values not in the interface will raise an ``AttributeError``::

    >>> proxy.age
    Traceback (most recent call last):
    ...
    AttributeError: age

Note that by default, the forInterface() method will check that the necessary records have been registered.
For example, we cannot use any old interface::

    >>> registry.forInterface(IInterfaceAwareRecord)
    Traceback (most recent call last):
    ...
    KeyError: 'Interface `plone.registry.interfaces.IInterfaceAwareRecord` defines a field `...`, for which there is no record.'

By default, we also cannot use an interface for which only some records exist::

    >>> registry.forInterface(IMailPreferences)
    Traceback (most recent call last):
    ...
    KeyError: 'Interface `plone.registry.tests.IMailPreferences` defines a field `settings`, for which there is no record.'

It is possible to disable this check, however.
This will be a bit more efficient::

    >>> registry.forInterface(IMailPreferences, check=False)
    <RecordsProxy for plone.registry.tests.IMailPreferences>

A better way, however, is to explicitly declare that some fields are omitted::

    >>> pref_proxy = registry.forInterface(IMailPreferences, omit=('settings',))

In this case, the omitted fields will default to their 'missing' value::

    >>> pref_proxy.settings ==  IMailPreferences['settings'].missing_value
    True

However, trying to set the value will result in a ``AttributeError``::

    >>> pref_proxy.settings = None
    Traceback (most recent call last):
    ...
    AttributeError: settings

To access another instance of the field, supply the prefix::

    >>> alt_proxy = registry.forInterface(IMailSettings,
    ...     prefix="plone.registry.tests.alternativesettings")
    >>> alt_proxy.sender  # doctest: +IGNORE_U
    u'alt@example.org'

Collections of records proxies
------------------------------

A collection of record sets may be accessed using ``collectionOfInterface``::

    >>> collection = registry.collectionOfInterface(IMailSettings)

You can create a new record set::

    >>> proxy = collection.setdefault('example')
    >>> proxy.sender = u'collection@example.org'
    >>> proxy.smtp_host = 'smtp://mail.example.org'

Record sets are stored based under the prefix::

    >>> prefix = IMailSettings.__identifier__
    >>> registry.records.values(prefix+'/', prefix+'0')
    [<Record plone.registry.tests.IMailSettings/example.sender>,
     <Record plone.registry.tests.IMailSettings/example.smtp_host>]
    >>> registry['plone.registry.tests.IMailSettings/example.sender']  # doctest: +IGNORE_U
    u'collection@example.org'

Records may be set from an existing object::

    >>> class MailSettings:
    ...     sender = u'someone@example.com'
    ...     smtp_host = 'smtp://mail.example.com'
    >>> collection['example_com'] = MailSettings()
    >>> registry.records.values(prefix+'/', prefix+'0')
    [<Record plone.registry.tests.IMailSettings/example.sender>,
     <Record plone.registry.tests.IMailSettings/example.smtp_host>,
     <Record plone.registry.tests.IMailSettings/example_com.sender>,
     <Record plone.registry.tests.IMailSettings/example_com.smtp_host>]

The collection may be iterated over::

    >>> for name in collection: print(name)
    example
    example_com

And may be deleted::

    >>> del collection['example_com']
    >>> registry.records.values(prefix+'/', prefix+'0')
    [<Record plone.registry.tests.IMailSettings/example.sender>,
     <Record plone.registry.tests.IMailSettings/example.smtp_host>]

Using field references
======================

It is possible for one record to refer to another record's field.
This can be used to provide a simple "override" mechanism,
for example, where one record defines the field and a default value,
whilst another provides an override validated against the same field.

Let us first create the base record and set its value::

    >>> timeout_field = field.Int(title=u"Timeout", min=0)
    >>> registry.records['plone.registry.tests.timeout'] = Record(timeout_field, 10)

    >>> timeout_record = registry.records['plone.registry.tests.timeout']
    >>> timeout_record.value
    10

Next, we create a field reference for this record::

    >>> from plone.registry import FieldRef
    >>> timeout_override_field = FieldRef(timeout_record.__name__, timeout_record.field)

We can use this to create a new record::

    >>> registry.records['plone.registry.tests.timeout.override'] = Record(timeout_override_field, 20)
    >>> timeout_override_record = registry.records['plone.registry.tests.timeout.override']

The two values are separate::

    >>> timeout_record.value
    10
    >>> timeout_override_record.value
    20

    >>> registry['plone.registry.tests.timeout']
    10
    >>> registry['plone.registry.tests.timeout.override']
    20

Validation uses the underlying field::

    >>> registry['plone.registry.tests.timeout.override'] = -1  # doctest: +SKIP_PYTHON_3
    Traceback (most recent call last):
    ...
    TooSmall: (-1, 0)

    >>> registry['plone.registry.tests.timeout.override'] = -1  # doctest: +SKIP_PYTHON_2
    Traceback (most recent call last):
    ...
    zope.schema._bootstrapinterfaces.TooSmall: (-1, 0)

The reference field exposes the standard field properties, e.g.::

    >>> timeout_override_record.field.title  # doctest: +SKIP_PYTHON_3
    u'Timeout'
    >>> timeout_override_record.field.min
    0

To look up the underlying record name, we can use the ``recordName`` property::

    >>> timeout_override_record.field.recordName
    'plone.registry.tests.timeout'

