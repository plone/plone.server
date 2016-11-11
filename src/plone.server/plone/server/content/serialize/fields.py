# -*- coding: utf-8 -*-
# from plone.namedfile.interfaces import INamedField
# from plone.namedfile.interfaces import INamedFileField
# from plone.namedfile.interfaces import INamedImageField
from datetime import timedelta
from plone.server.content.interfaces import IContent
from plone.server.content.interfaces import IFTI
from plone.jsonserializer.interfaces import IFieldDeserializer
from plone.jsonserializer.interfaces import IFieldSerializer
from plone.jsonserializer.interfaces import IFieldsetSerializer
from plone.jsonserializer.interfaces import ISchemaSerializer
from plone.jsonserializer.serializer.converters import json_compatible
from plone.server.registry.interfaces import IRegistry
from plone.server.content.interfaces import IFieldset
from plone.server.content.interfaces import IFieldNameExtractor
from plone.server.content.interfaces import ISchema
from plone.server.content.interfaces import IToUnicode
from plone.server.content.model import Schema
from plone.server.content.utils import sortedFields
from zope.component import adapter
from zope.component import getMultiAdapter
from zope.component import queryUtility
from zope.i18nmessageid import Message
from zope.interface import implementedBy
from zope.interface import implementer
from zope.interface import Interface
from zope.schema.interfaces import ICollection
from zope.schema.interfaces import IDatetime
from zope.schema.interfaces import IDict
from zope.schema.interfaces import IField
from zope.schema.interfaces import IFromUnicode
from zope.schema.interfaces import ITime
from zope.schema.interfaces import ITimedelta
from zope.schema.interfaces import ITextLine
from zope.schema.interfaces import IObject
from zope.schema.interfaces import IChoice
from zope.schema.interfaces import IBool
from zope.schema.interfaces import IInt
from zope.schema.interfaces import IFloat
from zope.schema.interfaces import IDate
from zope.schema.interfaces import IText
from plone.server.interfaces import IRichText
import zope.schema


@adapter(IField, IContent, Interface)
@implementer(IFieldSerializer)
class DefaultFieldSerializer(object):

    def __init__(self, field, context, request):
        self.context = context
        self.request = request
        self.field = field

    def __call__(self):
        return json_compatible(self.get_value())

    def get_value(self, default=None):
        return getattr(self.field.interface(self.context),
                       self.field.__name__,
                       default)


@adapter(ISchema, IFTI, Interface)
@implementer(ISchemaSerializer)
class DefaultSchemaSerializer(object):

    def __init__(self, schema, fti, request):
        self.schema = schema
        self.fti = fti
        self.request = request

    def __call__(self):
        result = {'based_on': self.bases,
                  'invariants': self.invariants,
                  'fields': self.field_ids}

        return result

    @property
    def name(self):
        return self.schema.__name__

    @property
    def field_ids(self):
        return [n for n, s in sortedFields(self.schema)]

    @property
    def bases(self):
        return [b.__identifier__ for b in self.schema.__bases__
                if b is not Schema]

    @property
    def invariants(self):
        return ''


@adapter(IFieldset, ISchema, IFTI, Interface)
@implementer(IFieldsetSerializer)
class DefaultFieldsetSerializer(object):

    def __init__(self, fieldset, schema, fti, request):
        self.fieldset = fieldset
        self.schema = schema
        self.fti = fti
        self.request = request

    def __call__(self):
        result = {'label': self.label,
                  'properties': {}
                  }

        result['properties'] = self.fields
        return result

    @property
    def name(self):
        return self.fieldset.__name__

    @property
    def label(self):
        return self.fieldset.label

    @property
    def fields(self):
        result = {}
        for field_name in self.fieldset.fields:
            field = self.schema[field_name]
            serializer = getMultiAdapter((field, self.schema, self.fti, self.request), IFieldSerializer)
            result[field_name] = serializer()
        return result


@adapter(IField, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class DefaultFTIFieldSerializer(object):

    # Elements we won't write
    filtered_attributes = ['order', 'unique', 'defaultFactory']

    # Elements that are of the same type as the field itself
    field_type_attributes = ('min', 'max', 'default', )

    # Elements that are of the same type as the field itself, but are
    # otherwise not validated
    non_validated_field_type_attributes = ('missing_value', )

    # Attributes that contain another field. Unfortunately,
    field_instance_attributes = ('key_type', 'value_type', )

    # Fields that are always written
    forced_fields = frozenset(['default', 'missing_value'])

    def __init__(self, field, schema, fti, request):
        self.field = field
        self.schema = schema
        self.fti = fti
        self.request = request
        self.klass = fti.klass
        self.field_attributes = {}

        # Build a dict of the parameters supported by this field type.
        # Each parameter is itself a field, which can be used to convert
        # text input to an appropriate object.
        for schema in implementedBy(self.field.__class__).flattened():
            self.field_attributes.update(zope.schema.getFields(schema))

        self.field_attributes['defaultFactory'] = zope.schema.Object(
            __name__='defaultFactory',
            title=u"defaultFactory",
            schema=Interface
        )

    def __call__(self):
        schema = {'type': self.field_type}
        for attribute_name in sorted(self.field_attributes.keys()):
            attribute_field = self.field_attributes[attribute_name]
            if attribute_name in self.filtered_attributes:
                continue

            element_name = attribute_field.__name__
            attribute_field = attribute_field.bind(self.field)
            force = (element_name in self.forced_fields)
            value = attribute_field.get(self.field)

            # if ignoreDefault and value == attributeField.default:
            #     return None

            # # The value points to another field. Recurse.
            # if IField.providedBy(value):
            #     value_fieldType = IFieldNameExtractor(value)()
            #     handler = queryUtility(
            #         IFieldExportImportHandler,
            #         name=value_fieldType
            #     )
            #     if handler is None:
            #         return None
            #     return handler.write(
            #         value, name=None,
            #         type=value_fieldType,
            #         elementName=elementName
            #     )

            # For 'default', 'missing_value' etc, we want to validate against
            # the imported field type itself, not the field type of the attribute
            if element_name in self.field_type_attributes or \
                    element_name in self.non_validated_field_type_attributes:
                attribute_field = self.field

            if isinstance(value, bytes):
                text = value.decode('utf-8')
            elif isinstance(value, str):
                text = value
            elif value is not None and (force or value != self.field.missing_value):
                text = str(value)

                # handle i18n
                # if isinstance(value, Message):
                #     child.set(ns('domain', I18N_NAMESPACE), value.domain)
                #     if not value.default:
                #         child.set(ns('translate', I18N_NAMESPACE), '')
                #     else:
                #         child.set(ns('translate', I18N_NAMESPACE), child.text)
                #         child.text = converter.toUnicode(value.default)
                schema[attribute_name] = text

        return schema

    @property
    def field_type(self):
        name_extractor = IFieldNameExtractor(self.field)
        return name_extractor()


@adapter(IText, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTITextSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'string'


@adapter(ITextLine, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTITextLineSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'string'


@adapter(IFloat, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTIFloatSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'number'


@adapter(IInt, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTIIntegerSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'integer'


@adapter(IBool, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTIBooleanSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'boolean'


@adapter(ICollection, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTICollectionSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'array'


@adapter(IChoice, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTIChoiceSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'string'


@adapter(IObject, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTIObjectSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'object'


@adapter(IRichText, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTIRichTextSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'string'


@adapter(IDate, ISchema, IFTI, Interface)
@implementer(IFieldSerializer)
class FTIDateSerializer(DefaultFTIFieldSerializer):

    @property
    def field_type(self):
        return 'string'

