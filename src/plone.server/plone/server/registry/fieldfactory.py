# -*- coding: utf-8 -*-
from plone.server.registry.field import DisallowedProperty
from plone.server.registry.field import InterfaceConstrainedProperty
from plone.server.registry.field import is_primitive
from plone.server.registry.field import StubbornProperty
from plone.server.registry.interfaces import IPersistentField
from zope.component import adapter
from zope.interface import implementer
from zope.schema.interfaces import IChoice
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.interfaces import IField
from zope.schema.interfaces import ISource
from zope.schema.vocabulary import SimpleVocabulary
import plone.server.registry.field


@implementer(IPersistentField)
@adapter(IField)
def persistentFieldAdapter(context):
    """Turn a non-persistent field into a persistent one
    """

    if IPersistentField.providedBy(context):
        return context

    # See if we have an equivalently-named field

    class_name = context.__class__.__name__
    persistent_class = getattr(plone.server.registry.field, class_name, None)
    if persistent_class is None:
        return None

    if not issubclass(persistent_class, context.__class__):
        __traceback_info__ = "Can only clone a field of an equivalent type."
        return None

    ignored = list(DisallowedProperty.uses + StubbornProperty.uses)
    constrained = list(InterfaceConstrainedProperty.uses)

    instance = persistent_class.__new__(persistent_class)

    context_dict = dict(
        [(k, v) for k, v in context.__dict__.items() if k not in ignored]
    )

    for key, iface in constrained:
        value = context_dict.get(key, None)
        if value is None or value == context.missing_value:
            continue
        value = iface(value, None)
        if value is None:
            __traceback_info__ = (
                "The property `{0}` cannot be adapted to "
                "`{1}`.".format(key, iface.__identifier__,)
            )
            return None
        context_dict[key] = value

    instance.__dict__.update(context_dict)
    return instance


@implementer(IPersistentField)
@adapter(IChoice)
def choicePersistentFieldAdapter(context):
    """Special handling for Choice fields.
    """
    instance = persistentFieldAdapter(context)
    if instance is None:
        return None

    if ISource.providedBy(context.vocabulary) or \
            IContextSourceBinder.providedBy(context.vocabulary):
        safe = False

        # Attempt to reverse engineer a 'values' argument
        if isinstance(context.vocabulary, SimpleVocabulary):
            values = []
            safe = True
            for term in context.vocabulary:
                if term.token == str(term.value) and is_primitive(term.value):
                    values.append(term.value)
                else:
                    safe = False
                    break
            if safe:
                instance._values = values

        if not safe:
            __traceback_info__ = (
                "Persistent fields only support named vocabularies "
                "or vocabularies based on simple value sets."
            )
            return None

    return instance
