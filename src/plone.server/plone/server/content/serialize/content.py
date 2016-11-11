# -*- coding: utf-8 -*-
from plone.server.content.interfaces import IContainer
from plone.server.content.interfaces import IContent
from plone.server.content.interfaces import IBigContainer
from plone.server.content.interfaces import IFTI
from plone.server.content.utils import iterSchemata
from plone.server.content.utils import iterSchemataForType
from plone.jsonserializer.interfaces import IFieldSerializer
from plone.jsonserializer.interfaces import IFieldsetSerializer
from plone.jsonserializer.interfaces import ISchemaSerializer
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.jsonserializer.interfaces import ISerializeToJsonSummary
from plone.jsonserializer.serializer.converters import json_compatible
from plone.server.browser import get_physical_path
from plone.server.content.directives.interfaces import FIELDSETS_KEY
from plone.server.content.directives.interfaces import READ_PERMISSIONS_KEY
from plone.server.content.utils import mergedTaggedValueDict
from plone.server.content.utils import sortedFields
from zope.component import adapter
from zope.component import ComponentLookupError
from zope.component import getMultiAdapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.interface import implementer
from zope.interface import Interface
from zope.schema import getFields
from zope.security.interfaces import IInteraction
from zope.security.interfaces import IPermission

MAX_ALLOWED = 200


@implementer(ISerializeToJson)
@adapter(IContent, Interface)
class SerializeToJson(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.permission_cache = {}

    def __call__(self):
        parent = self.context.__parent__
        if parent is not None:
            try:
                parent_summary = getMultiAdapter(
                    (parent, self.request), ISerializeToJsonSummary)()
            except ComponentLookupError:
                parent_summary = {}
        else:
            parent_summary = {}

        result = {
            '@id': '/'.join(get_physical_path(self.context)),
            'id': self.context.id,
            '@type': self.context.portal_type,
            'parent': parent_summary,
            'created': json_compatible(self.context.creation_date),
            'modified': json_compatible(self.context.modification_date),
            'UID': self.context.UID(),
        }

        for schema in iterSchemata(self.context):

            read_permissions = mergedTaggedValueDict(schema, READ_PERMISSIONS_KEY)

            for name, field in getFields(schema).items():

                if not self.check_permission(read_permissions.get(name)):
                    continue
                serializer = queryMultiAdapter(
                    (field, self.context, self.request),
                    IFieldSerializer)
                value = serializer()
                result[json_compatible(name)] = value

        return result

    def check_permission(self, permission_name):
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = queryUtility(IPermission,
                                      name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                security = IInteraction(self.request)
                self.permission_cache[permission_name] = bool(
                    security.checkPermission(permission.title, self.context))
        return self.permission_cache[permission_name]


@implementer(ISerializeToJson)
@adapter(IContainer, Interface)
class SerializeFolderToJson(SerializeToJson):

    def __call__(self):
        result = super(SerializeFolderToJson, self).__call__()

        security = IInteraction(self.request)
        length = len(self.context)

        if length > MAX_ALLOWED:
            result['items'] = []
        else:
            result['items'] = [
                getMultiAdapter((member, self.request), ISerializeToJsonSummary)()
                for ident, member in self.context.items()
                if not ident.startswith('_') and
                bool(security.checkPermission('plone.AccessContent', self.context))
            ]
        result['length'] = length

        return result


@implementer(ISerializeToJson)
@adapter(IBigContainer, Interface)
class SerializeBigFolderToJson(SerializeToJson):

    def __call__(self):
        result = super(SerializeFolderToJson, self).__call__()

        security = IInteraction(self.request)

        length = len(self.context)

        if length > MAX_ALLOWED:
            result['items'] = []
        else:
            result['items'] = [
                getMultiAdapter((member, self.request), ISerializeToJsonSummary)()
                for ident, member in self.context.items()
                if not ident.startswith('_') and
                bool(security.checkPermission('plone.AccessContent', self.context))
            ]
        result['length'] = length

        return result


@implementer(ISerializeToJson)
@adapter(IFTI, Interface)
class SerializeFTIToJson(SerializeToJson):

    def __call__(self):
        fti = self.context
        result = {
            'title': fti.id,
            'type': 'object',
            '$schema': 'http://json-schema.org/draft-04/hyper-schema#',
            'fieldsets': [],
            'required': [],
            'schemas': {},
            'properties': {
            },
        }

        for schema in iterSchemataForType(fti.id):

            schema_serializer = getMultiAdapter(
                (schema, fti, self.request), ISchemaSerializer)
            result['schemas'][schema_serializer.name] = schema_serializer()

            fieldsets = schema.queryTaggedValue(FIELDSETS_KEY, [])
            fieldset_fields = set()
            for fieldset in fieldsets:
                fields = fieldset.fields
                # Keep a list so we can figure out what doesn't belong
                # to a fieldset
                fieldset_fields.update(fields)

                # Write the fieldset and any fields it contains
                fieldset_serializer = getMultiAdapter(
                    (fieldset, schema, fti, self.request), IFieldsetSerializer)
                result['fieldsets'].append({
                    'id': fieldset_serializer.name,
                    'title': fieldset_serializer.name,
                    'fields': fieldset_serializer()
                })

            # Handle any fields that aren't part of a fieldset
            non_fieldset_fields = [name for name, field in sortedFields(schema)
                                   if name not in fieldset_fields]

            for fieldName in non_fieldset_fields:
                field = schema[fieldName]
                if field.required:
                    result['required'].append(fieldName)
                serializer = getMultiAdapter(
                    (field, schema, fti, self.request), IFieldSerializer)
                result['properties'][fieldName] = serializer()

            invariants = []
            for i in schema.queryTaggedValue('invariants', []):
                invariants.append("%s.%s" % (i.__module__, i.__name__))
            result['invariants'] = invariants

        if len(result['fieldsets']) == 0:
            del result['fieldsets']
        return result

