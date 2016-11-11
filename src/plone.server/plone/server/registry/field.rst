=================
Persistent fields
=================

The persistent fields that are found in ``plone.registry.field`` are siblings of the ones found in zope.schema,
with persistence mixed in.
To avoid potentially breaking the registry with persistent references to symbols that may go away,
we purposefully limit the number of fields supported.
We also disallow some properties, and add some additional checks on others.

The standard fields
===================

We will show each supported field in turn. For all fields, note that:

* the ``order`` property will return ``-1`` no matter what setting the ``constraint`` property is diallowed
* the ``key_type`` and ``value_type`` properties, where applicable, must be set to a persistent field.
* for ``Choice`` fields, only named vocabularies and vocabularies based on simple values are supported:
  sources and ``IVocabulary`` objects are not.

Imports needed::

    >>> from plone.registry import field
    >>> from zope import schema
    >>> from persistent import Persistent

Bytes
-----

The bytes field describes a string of bytes::

    >>> f = field.Bytes(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.Bytes)
    True

    >>> f.order
    -1

    >>> field.Bytes(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint('ABC')
    True

BytesLine
---------

The bytes field describes a string of bytes, disallowing newlines::

    >>> f = field.BytesLine(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.BytesLine)
    True

    >>> f.order
    -1

    >>> field.BytesLine(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(b'AB\nC')
    False

ASCII
-----

The ASCII field describes a string containing only ASCII characters::

    >>> f = field.ASCII(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.ASCII)
    True

    >>> f.order
    -1

    >>> field.ASCII(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint('ab\nc')
    True

ASCIILine
---------

The ASCII line field describes a string containing only ASCII characters and disallowing newlines::

    >>> f = field.ASCIILine(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.ASCIILine)
    True

    >>> f.order
    -1

    >>> field.ASCIILine(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint('ab\nc')
    False

Text
----

The text field describes a unicode string::

    >>> f = field.Text(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.Text)
    True

    >>> f.order
    -1

    >>> field.Text(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(u'ab\nc')
    True

TextLine
--------

The text line field describes a unicode string, disallowing newlines::

    >>> f = field.TextLine(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.TextLine)
    True

    >>> f.order
    -1

    >>> field.TextLine(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(u'ab\nc')
    False

Bool
----

The bool field describes a boolean::

    >>> f = field.Bool(title=u"Test")
    >>> isinstance(f, schema.Bool)
    True

    >>> f.order
    -1

    >>> field.Bool(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(False)
    True

Int
---

The int field describes an integer or long::

    >>> f = field.Int(title=u"Test", min=-123, max=1234)
    >>> isinstance(f, schema.Int)
    True

    >>> f.order
    -1

    >>> field.Int(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(123)
    True

Float
-----

The float field describes a float::

    >>> f = field.Float(title=u"Test", min=-123.0, max=1234.0)
    >>> isinstance(f, schema.Float)
    True

    >>> f.order
    -1

    >>> field.Float(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(123)
    True

Decimal
-------

The decimal field describes a decimal::

    >>> import decimal
    >>> f = field.Decimal(title=u"Test", min=decimal.Decimal('-123.0'), max=decimal.Decimal('1234.0'))
    >>> isinstance(f, schema.Decimal)
    True

    >>> f.order
    -1

    >>> field.Decimal(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(123)
    True

Password
--------

The password field describes a unicode string used for a password::

    >>> f = field.Password(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.Password)
    True

    >>> f.order
    -1

    >>> field.Password(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(u'ab\nc')
    False

SourceText
----------

The source  text field describes a unicode string with source code::

    >>> f = field.SourceText(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.SourceText)
    True

    >>> f.order
    -1

    >>> field.SourceText(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(u'ab\nc')
    True

URI
---

The URI field describes a URI string::

    >>> f = field.URI(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.URI)
    True

    >>> f.order
    -1

    >>> field.URI(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(u'abc')
    True

Id
--

The id field describes a URI string or a dotted name::

    >>> f = field.Id(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.Id)
    True

    >>> f.order
    -1

    >>> field.Id(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(u'abc')
    True

DottedName
----------

The dotted name field describes a Python dotted name::

    >>> f = field.DottedName(title=u"Test", min_length=0, max_length=10)
    >>> isinstance(f, schema.DottedName)
    True

    >>> f.order
    -1

    >>> field.DottedName(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(u'abc')
    True

Datetime
--------

The date/time field describes a Python datetime object::

    >>> f = field.Datetime(title=u"Test")
    >>> isinstance(f, schema.Datetime)
    True

    >>> f.order
    -1

    >>> field.Datetime(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> import datetime
    >>> f.constraint(datetime.datetime.now())
    True

Date
----

The date field describes a Python date object::

    >>> f = field.Date(title=u"Test")
    >>> isinstance(f, schema.Date)
    True

    >>> f.order
    -1

    >>> field.Date(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> import datetime
    >>> f.constraint(datetime.date.today())
    True

Timedelta
---------

The time-delta field describes a Python timedelta object::

    >>> f = field.Timedelta(title=u"Test")
    >>> isinstance(f, schema.Timedelta)
    True

    >>> f.order
    -1

    >>> field.Timedelta(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> import datetime
    >>> f.constraint(datetime.timedelta(1))
    True

Tuple
-----

The tuple field describes a tuple::

    >>> f = field.Tuple(title=u"Test", min_length=0, max_length=10,
    ...     value_type=field.TextLine(title=u"Value"))
    >>> isinstance(f, schema.Tuple)
    True

    >>> f.order
    -1

    >>> field.Tuple(title=u"Test", min_length=0, max_length=10,
    ...     value_type=schema.TextLine(title=u"Value"))
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> f.value_type = schema.TextLine(title=u"Value")
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> field.Tuple(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint((1,2))
    True

List
----

The list field describes a tuple::

    >>> f = field.List(title=u"Test", min_length=0, max_length=10,
    ...     value_type=field.TextLine(title=u"Value"))
    >>> isinstance(f, schema.List)
    True

    >>> f.order
    -1

    >>> field.List(title=u"Test", min_length=0, max_length=10,
    ...     value_type=schema.TextLine(title=u"Value"))
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> f.value_type = schema.TextLine(title=u"Value")
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> field.List(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint([1,2])
    True

Set
---

The set field describes a set::

    >>> f = field.Set(title=u"Test", min_length=0, max_length=10,
    ...     value_type=field.TextLine(title=u"Value"))
    >>> isinstance(f, schema.Set)
    True

    >>> f.order
    -1

    >>> field.Set(title=u"Test", min_length=0, max_length=10,
    ...     value_type=schema.TextLine(title=u"Value"))
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> f.value_type = schema.TextLine(title=u"Value")
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> field.Set(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(set([1,2]))
    True

Frozenset
---------

The set field describes a frozenset::

    >>> f = field.FrozenSet(title=u"Test", min_length=0, max_length=10,
    ...     value_type=field.TextLine(title=u"Value"))
    >>> isinstance(f, schema.FrozenSet)
    True

    >>> f.order
    -1

    >>> field.FrozenSet(title=u"Test", min_length=0, max_length=10,
    ...     value_type=schema.TextLine(title=u"Value"))
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> f.value_type = schema.TextLine(title=u"Value")
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> field.FrozenSet(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(frozenset([1,2]))
    True

Dict
----

The set field describes a dict::

    >>> f = field.Dict(title=u"Test", min_length=0, max_length=10,
    ...     key_type=field.ASCII(title=u"Key"),
    ...     value_type=field.TextLine(title=u"Value"))
    >>> isinstance(f, schema.Dict)
    True

    >>> f.order
    -1

    >>> field.Dict(title=u"Test", min_length=0, max_length=10,
    ...     key_type=schema.ASCII(title=u"Key"),
    ...     value_type=field.TextLine(title=u"Value"))
    Traceback (most recent call last):
    ...
    ValueError: The property `key_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> f.key_type = schema.ASCII(title=u"Key")
    Traceback (most recent call last):
    ...
    ValueError: The property `key_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> field.Dict(title=u"Test", min_length=0, max_length=10,
    ...     key_type=field.ASCII(title=u"Key"),
    ...     value_type=schema.TextLine(title=u"Value"))
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> f.value_type = schema.TextLine(title=u"Value")
    Traceback (most recent call last):
    ...
    ValueError: The property `value_type` may only contain objects providing `plone.registry.interfaces.IPersistentField`.

    >>> field.Dict(title=u"Test", constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint(dict())
    True

Choice
------

A choice field represents a selection from a vocabulary.
For persistent fields, the vocabulary cannot be a ``source`` or any kind of object:
it must either be a list of primitives, or a named vocabulary::

    >>> f = field.Choice(title=u"Test", values=[1,2,3])
    >>> isinstance(f, schema.Choice)
    True

    >>> f.order
    -1

With a list of values given, the ``vocabulary`` property returns a vocabulary
constructed from the values on the fly, and ``vocabularyName`` is ``None``::

    >>> f.vocabulary
    <zope.schema.vocabulary.SimpleVocabulary object at ...>

    >>> f.vocabularyName is None
    True

We will get an error if we use anything other than primitives::

    >>> f = field.Choice(title=u"Test", values=[object(), object()])
    Traceback (most recent call last):
    ...
    ValueError: Vocabulary values may only contain primitive values.

If a vocabulary name given, it is stored in ``vocabularyName``, and the ``vocabulary`` property returns ``None``::

    >>> f = field.Choice(title=u"Test", vocabulary='my.vocab')
    >>> f.vocabulary is None
    True

    >>> f.vocabularyName
    'my.vocab'

Other combinations are now allowed, such as specifying no vocabulary::

    >>> field.Choice(title=u"Test")
    Traceback (most recent call last):
    ...
    AssertionError: You must specify either values or vocabulary.

Or specifying both types::

    >>> field.Choice(title=u"Test", values=[1,2,3], vocabulary='my.vocab')
    Traceback (most recent call last):
    ...
    AssertionError: You cannot specify both values and vocabulary.

Or specifying an object source::

    >>> from zope.schema.vocabulary import SimpleVocabulary
    >>> dummy_vocabulary = SimpleVocabulary.fromValues([1,2,3])
    >>> field.Choice(title=u"Test", source=dummy_vocabulary)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields do not support sources, only named vocabularies or vocabularies based on simple value sets.

Or specifying an object vocabulary::

    >>> field.Choice(title=u"Test", vocabulary=dummy_vocabulary)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields only support named vocabularies or vocabularies based on simple value sets.

As with other fields, you also cannot set a constraint::

    >>> field.Choice(title=u"Test", values=[1,2,3], constraint=lambda x: True)
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint = lambda x: False
    Traceback (most recent call last):
    ...
    ValueError: Persistent fields does not support setting the `constraint` property

    >>> f.constraint('ABC')
    True

``IPersistentField`` adapters
=============================

It is possible to adapt any non-persistent field to its related ``IPersistentField`` using the adapter factories in ``plone.registry`` fieldfactory.
These are set up in ``configure.zcml`` and explicitly registered in the test setup in ``tests.py``.
Custom adapters are of course also possible::

    >>> from plone.registry.interfaces import IPersistentField

    >>> f = schema.TextLine(title=u"Test")
    >>> IPersistentField.providedBy(f)
    False

    >>> p = IPersistentField(f)
    >>> IPersistentField.providedBy(p)
    True

    >>> isinstance(p, field.TextLine)
    True

Unsupported field types will not be adaptable by default::

    >>> f = schema.Object(title=u"Object", schema=IPersistentField)
    >>> IPersistentField(f, None) is None
    True

    >>> f = schema.InterfaceField(title=u"Interface")
    >>> IPersistentField(f, None) is None
    True

After adaptation, the rules of persistent fields apply:
The ``order`` attribute is perpetually ``-1``.
Custom constraints are not allowed, and key and value type will be adapted to persistent fields as well.
If any of these constraints can not be met, the adaptation will fail.

For constraints, the non-persistent value is simply ignored and the default method from the class will be used.

::

    >>> f = schema.TextLine(title=u"Test", constraint=lambda x: False)
    >>> f.constraint
    <function <lambda> at ...>

    >>> p = IPersistentField(f)
    >>> p.constraint
    <bound method TextLine.constraint of <plone.registry.field.TextLine object at ...>>

The order property is similarly ignored::

    >>> f.order > 0
    True

    >>> p.order
    -1

Key/value types will be adapted if possible::

    >>> f = schema.Dict(title=u"Test",
    ...     key_type=schema.Id(title=u"Id"),
    ...     value_type=schema.TextLine(title=u"Value"))
    >>> p = IPersistentField(f)
    >>> p.key_type
    <plone.registry.field.Id object at ...>

    >>> p.value_type
    <plone.registry.field.TextLine object at ...>

If they cannot be adapted, there will be an error::

    >>> f = schema.Dict(title=u"Test",
    ...     key_type=schema.Id(title=u"Id"),
    ...     value_type=schema.Object(title=u"Value", schema=IPersistentField))
    >>> p = IPersistentField(f)
    Traceback (most recent call last):
    ...
    TypeError: ('Could not adapt', <zope.schema._field.Dict object at ...>, <InterfaceClass plone.registry.interfaces.IPersistentField>)

    >>> f = schema.Dict(title=u"Test",
    ...     key_type=schema.InterfaceField(title=u"Id"),
    ...     value_type=schema.TextLine(title=u"Value"))
    >>> p = IPersistentField(f)
    Traceback (most recent call last):
    ...
    TypeError: ('Could not adapt', <zope.schema._field.Dict object at ...>, <InterfaceClass plone.registry.interfaces.IPersistentField>)

There is additional validation for choice fields that warrant a custom adapter.
These ensure that vocabularies are either stored as a list of simple values, or as named vocabularies.

::

    >>> f = schema.Choice(title=u"Test", values=[1,2,3])
    >>> p = IPersistentField(f)
    >>> p.vocabulary
    <zope.schema.vocabulary.SimpleVocabulary object at ...>
    >>> p._values
    [1, 2, 3]
    >>> p.vocabularyName is None
    True

    >>> f = schema.Choice(title=u"Test", vocabulary='my.vocab')
    >>> p = IPersistentField(f)
    >>> p.vocabulary is None
    True
    >>> p._values is None
    True
    >>> p.vocabularyName
    'my.vocab'

Complex vocabularies or sources are not allowed::

    >>> from zope.schema.vocabulary import SimpleVocabulary
    >>> dummy_vocabulary = SimpleVocabulary.fromItems([('a', 1), ('b', 2)])
    >>> f = schema.Choice(title=u"Test", source=dummy_vocabulary)
    >>> p = IPersistentField(f)
    Traceback (most recent call last):
    ...
    TypeError: ('Could not adapt', <zope.schema._field.Choice object at ...>, <InterfaceClass plone.registry.interfaces.IPersistentField>)


    >>> f = schema.Choice(title=u"Test", vocabulary=dummy_vocabulary)
    >>> p = IPersistentField(f)
    Traceback (most recent call last):
    ...
    TypeError: ('Could not adapt', <zope.schema._field.Choice object at ...>, <InterfaceClass plone.registry.interfaces.IPersistentField>)
