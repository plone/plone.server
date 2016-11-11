# -*- coding: utf-8 -*-
from plone.server.content.interfaces import WRITE_PERMISSIONS_KEY
from plone.server.content.interfaces import IDexterityContent
from plone.server.content.utils import iterSchemata
from plone.jsonserializer.interfaces import IDeserializeFromJson
from plone.jsonserializer.exceptions import DeserializationError
from plone.jsonserializer.interfaces import IFieldDeserializer
from plone.server.content.utils import mergedTaggedValueDict
from zope.component import adapter
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.event import notify
from zope.interface import Interface
from zope.interface import implementer
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema import getFields
from zope.schema import getValidationErrors
from zope.schema.interfaces import ValidationError
from zope.security.interfaces import IPermission
from zope.security import checkPermission


@implementer(IDeserializeFromJson)
@adapter(IDexterityContent, Interface)
class DeserializeFromJson(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.permission_cache = {}

    def __call__(self, data, validate_all=False):

        modified = False
        errors = []

        for schema in iterSchemata(self.context):
            write_permissions = mergedTaggedValueDict(
                schema, WRITE_PERMISSIONS_KEY)

            for name, field in getFields(schema).items():

                if field.readonly:
                    continue

                if name in data:

                    if not self.check_permission(write_permissions.get(name)):
                        continue

                    # Deserialize to field value
                    deserializer = queryMultiAdapter(
                        (field, self.context, self.request),
                        IFieldDeserializer)
                    if deserializer is None:
                        continue

                    try:
                        value = deserializer(data[name])
                    except ValueError as e:
                        errors.append({
                            'message': e.message, 'field': name, 'error': e})
                    except ValidationError as e:
                        errors.append({
                            'message': e.doc(), 'field': name, 'error': e})
                    else:
                        f = schema.get(name)
                        try:
                            f.validate(value)
                        except ValidationError as e:
                            errors.append({
                                'message': e.doc(), 'field': name, 'error': e})
                        else:
                            setattr(schema(self.context), name, value)

            if validate_all:
                validation = getValidationErrors(schema, schema(self.context))

                if len(validation):
                    for e in validation:
                        errors.append({
                            'message': e[1].doc(),
                            'field': e[0],
                            'error': e
                        })
        if errors:
            raise DeserializationError(errors)

        if modified:
            notify(ObjectModifiedEvent(self.context))

        return self.context

    def check_permission(self, permission_name):
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = queryUtility(IPermission,
                                      name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                self.permission_cache[permission_name] = bool(
                    checkPermission(permission.title, self.context))
        return self.permission_cache[permission_name]
