# -*- coding: utf-8 -*-
from plone.server import BEHAVIOR_CACHE
from plone.server import configure
from plone.server.content import get_cached_factory
from plone.server.directives import merged_tagged_value_dict
from plone.server.directives import write_permission
from plone.server.events import notify
from plone.server.interfaces import IResource
from plone.server.interfaces import IResourceDeserializeFromJson
from plone.server.interfaces import IResourceFieldDeserializer
from plone.server.json.exceptions import DeserializationError
from zope.component import queryMultiAdapter
from zope.component import queryUtility
from zope.interface import Interface
from zope.interface.exceptions import Invalid
from zope.lifecycleevent import ObjectModifiedEvent
from zope.schema import getFields
from zope.schema.interfaces import ValidationError
from zope.security.interfaces import IInteraction
from zope.security.interfaces import IPermission
from zope.security.interfaces import NoInteraction


@configure.adapter(
    for_=(IResource, Interface),
    provides=IResourceDeserializeFromJson)
class DeserializeFromJson(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.permission_cache = {}

    async def __call__(self, data, validate_all=False):

        modified = False
        errors = []

        factory = get_cached_factory(self.context.portal_type)
        main_schema = factory.schema
        self.set_schema(
            main_schema, self.context, data, errors, validate_all, False)

        for behavior_schema in factory.behaviors or ():
            if behavior_schema.__identifier__ in data:
                behavior = behavior_schema(self.context)
                self.set_schema(
                    behavior_schema, behavior, data, errors,
                    validate_all, True)

        for dynamic_behavior in self.context.__behaviors__ or ():
            dynamic_behavior_obj = BEHAVIOR_CACHE[dynamic_behavior]
            if dynamic_behavior_obj.__identifier__ in data:
                behavior = dynamic_behavior_obj(self.context)
                self.set_schema(
                    dynamic_behavior_obj, behavior, data, errors,
                    validate_all, True)

        if errors:
            raise DeserializationError(errors)

        if modified:
            await notify(ObjectModifiedEvent(self.context))

        return self.context

    def set_schema(
            self, schema, obj, data, errors,
            validate_all=False, behavior=False):
        write_permissions = merged_tagged_value_dict(schema, write_permission.key)
        for name, field in getFields(schema).items():

            if field.readonly:
                continue

            if behavior:
                data_value = data[schema.__identifier__][name] if name in data[schema.__identifier__] else None  # noqa
                found = True if name in data[schema.__identifier__] else False
            else:
                data_value = data[name] if name in data else None
                found = True if name in data else False

            f = schema.get(name)
            if found:

                if not self.check_permission(write_permissions.get(name)):
                    continue

                # Deserialize to field value
                deserializer = queryMultiAdapter(
                    (f, obj, self.request),
                    IResourceFieldDeserializer)
                if deserializer is None:
                    continue

                try:
                    value = deserializer(data_value)
                except ValueError as e:
                    errors.append({
                        'message': e.message, 'field': name, 'error': e})
                except ValidationError as e:
                    errors.append({
                        'message': e.doc(), 'field': name, 'error': e})
                except Invalid as e:
                    errors.append({
                        'message': e.args[0], 'field': name, 'error': e})
                else:
                    try:
                        field.set(obj, value)
                    except:
                        setattr(obj, name, value)
            else:
                if f.required and not hasattr(obj, name):
                    errors.append({
                        'message': 'Required parameter', 'field': name,
                        'error': ValueError('Required parameter')})

        if validate_all:
            invariant_errors = []
            try:
                schema.validateInvariants(object, invariant_errors)
            except Invalid:
                # Just collect errors
                pass
            validation = [(None, e) for e in invariant_errors]

            if len(validation):
                for e in validation:
                    errors.append({
                        'message': e[1].doc(),
                        'field': e[0],
                        'error': e
                    })

    def check_permission(self, permission_name):
        if permission_name is None:
            return True

        if permission_name not in self.permission_cache:
            permission = queryUtility(IPermission,
                                      name=permission_name)
            if permission is None:
                self.permission_cache[permission_name] = True
            else:
                try:
                    self.permission_cache[permission_name] = bool(
                        IInteraction(self.request).check_permission(
                            permission.title, self.context))
                except NoInteraction:
                    # not authenticated
                    return False
        return self.permission_cache[permission_name]
