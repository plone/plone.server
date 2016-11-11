# -*- coding: utf-8 -*-
"""This module defines persistent versions of various fields.

The idea is that when a record is created, we copy relevant field properties
from the transient schema field from zope.schema, into the corresponding
persistent field. Not all field types are supported, but the common types
are.
"""
from persistent import Persistent
from plone.server.registry.interfaces import IPersistentField
from zope.interface import implementer
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary
import zope.schema
import zope.schema._field

import sys
if sys.version_info >= (3,):
    basestring = str
    text_type = str
    _primitives = (int, bool, str, bytes, tuple,
                   list, set, frozenset, dict, float)
else:
    text_type = unicode
    _primitives = (int, long, bool, str, unicode, tuple,
                   list, set, frozenset, dict, float)

_missing_value_marker = object()


def is_primitive(value):
    return value is None or isinstance(value, _primitives)


class DisallowedProperty(object):
    """A property that may not be set on an instance. It may still be set
    defined in a base class.
    """
    uses = []

    def __init__(self, name):
        self._name = name
        DisallowedProperty.uses.append(name)

    def __get__(self, inst, type_=None):
        # look for the object in bases
        if type_ is not None:
            for c in type_.__mro__:
                if self._name in c.__dict__ and not \
                        isinstance(c.__dict__[self._name], DisallowedProperty):
                    function = c.__dict__[self._name]
                    return function.__get__(inst, type_)
        raise AttributeError(self._name)

    def __set__(self, inst, value):
        raise ValueError(
            u"Persistent fields does not support setting the `{0}` "
            u"property".format(self._name)
        )


class StubbornProperty(object):
    """A property that stays stubbornly at a single, pre-defined value.
    """
    uses = []

    def __init__(self, name, value):
        StubbornProperty.uses.append(name)
        self._name = name
        self._value = value

    def __set__(self, inst, value):
        pass

    def __get__(self, inst, type_=None):
        return self._value


class InterfaceConstrainedProperty(object):
    """A property that may only contain values providing a certain interface.
    """
    uses = []

    def __init__(self, name, interface):
        InterfaceConstrainedProperty.uses.append((name, interface))
        self._name = name
        self._interface = interface

    def __set__(self, inst, value):
        if (
            value != inst.missing_value
            and not self._interface.providedBy(value)
        ):
            raise ValueError(
                u"The property `{0}` may only contain objects "
                "providing `{1}`.".format(
                    self._name,
                    self._interface.__identifier__,
                )
            )
        inst.__dict__[self._name] = value


@implementer(IPersistentField)
class PersistentField(Persistent):
    """Base class for persistent field definitions.
    """
    # Persistent fields do not have an order
    order = StubbornProperty('order', -1)

    # We don't allow setting a custom constraint, as this would introduce a
    # dependency on a symbol such as a function that may go away
    constraint = DisallowedProperty('constraint')

    # Details about which interface/field name we originally came form, if any
    interfaceName = None
    fieldName = None


class PersistentCollectionField(
    PersistentField,
    zope.schema._field.AbstractCollection
):
    """Ensure that value_type is a persistent field
    """
    value_type = InterfaceConstrainedProperty('value_type', IPersistentField)


class Bytes(PersistentField, zope.schema.Bytes):
    pass


class BytesLine(PersistentField, zope.schema.BytesLine):
    pass


class ASCII(PersistentField, zope.schema.ASCII):
    pass


class ASCIILine(PersistentField, zope.schema.ASCIILine):
    pass


class Text(PersistentField, zope.schema.Text):
    pass


class TextLine(PersistentField, zope.schema.TextLine):
    pass


class Bool(PersistentField, zope.schema.Bool):
    pass


class Int(PersistentField, zope.schema.Int):
    pass


class Float(PersistentField, zope.schema.Float):
    pass


class Decimal(PersistentField, zope.schema.Decimal):
    pass


class Tuple(PersistentCollectionField, zope.schema.Tuple):
    pass


class List(PersistentCollectionField, zope.schema.List):
    pass


class Set(PersistentCollectionField, zope.schema.Set):
    pass


class FrozenSet(PersistentCollectionField, zope.schema.FrozenSet):
    pass


class Password(PersistentField, zope.schema.Password):
    pass


class Dict(PersistentField, zope.schema.Dict):

    key_type = InterfaceConstrainedProperty('key_type', IPersistentField)
    value_type = InterfaceConstrainedProperty('value_type', IPersistentField)


class Datetime(PersistentField, zope.schema.Datetime):
    pass


class Date(PersistentField, zope.schema.Date):
    pass


class Timedelta(PersistentField, zope.schema.Timedelta):
    pass


class SourceText(PersistentField, zope.schema.SourceText):
    pass


class URI(PersistentField, zope.schema.URI):
    pass


class Id(PersistentField, zope.schema.Id):
    pass


class DottedName(PersistentField, zope.schema.DottedName):
    pass


class Choice(PersistentField, zope.schema.Choice):
    # We can only support string name or primitive=list vocabularies
    _values = None
    _vocabulary = None

    def __init__(self, values=None, vocabulary=None, source=None, **kw):

        if vocabulary is not None and not isinstance(vocabulary, basestring):
            values = self._normalized_values(vocabulary)
            if values is None:
                raise ValueError(
                    "Persistent fields only support named vocabularies or "
                    "vocabularies based on simple value sets."
                    )
            vocabulary = None
        elif source is not None:
            raise ValueError(
                "Persistent fields do not support sources, only named "
                "vocabularies or vocabularies based on simple value sets."
            )

        assert not (values is None and vocabulary is None), (
               "You must specify either values or vocabulary.")
        assert values is None or vocabulary is None, (
               "You cannot specify both values and vocabulary.")

        self.vocabularyName = None

        if values is not None:
            for value in values:
                if not is_primitive(value):
                    raise ValueError(
                        "Vocabulary values may only contain primitive values."
                    )
            self._values = values
        else:
            self.vocabularyName = vocabulary

        self._init_field = bool(self.vocabularyName)
        super(zope.schema.Choice, self).__init__(**kw)
        self._init_field = False

    def _normalized_values(self, vocabulary):
        if getattr(vocabulary, '__iter__', None):
            if all([isinstance(term.value, text_type) for term in vocabulary]):
                return [term.value for term in vocabulary]
        return None

    @property
    def vocabulary(self):
        # may be set by bind()
        if self._vocabulary is not None:
            return self._vocabulary
        if self._values is not None:
            return SimpleVocabulary.fromValues(self._values)
    DisallowedProperty.uses.append('vocabulary')

    # override bind to allow us to keep constraints on the 'vocabulary'
    # property
    def bind(self, object):
        clone = zope.schema.Field.bind(self, object)
        # get registered vocabulary if needed:
        if IContextSourceBinder.providedBy(self.vocabulary):
            clone._vocabulary = self.vocabulary(object)
            assert zope.schema.interfaces.ISource.providedBy(clone.vocabulary)
        elif clone.vocabulary is None and self.vocabularyName is not None:
            vr = zope.schema.vocabulary.getVocabularyRegistry()
            clone._vocabulary = vr.get(object, self.vocabularyName)
            assert zope.schema.interfaces.ISource.providedBy(clone.vocabulary)
        return clone
