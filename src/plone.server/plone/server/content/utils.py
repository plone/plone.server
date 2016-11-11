# -*- coding: utf-8 -*-
from datetime import datetime
from dateutil.tz import tzutc
from plone.behavior.interfaces import IBehaviorAssignable
from plone.server.content.interfaces import IFTI
from plone.server.content.schema import SCHEMA_CACHE
from zope.component import createObject
from zope.component import getUtility
from zope.lifecycleevent import ObjectMovedEvent
from zope.lifecycleevent import ObjectAddedEvent
from zope.lifecycleevent import ObjectCreatedEvent
from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent import ObjectRemovedEvent
from ZODB.interfaces import IBroken
from zope.dottedname.resolve import resolve
from zope.event import notify
from zope.schema.interfaces import IField
from zope.security.interfaces import Unauthorized
from zope.interface import implementer

import logging
import time


log = logging.getLogger(__name__)

# Not thread safe, but downside of a write conflict is very small
_dottedCache = {}


def uncontained(object, container, name=None):

    try:
        oldparent = object.__parent__
        oldname = object.__name__
    except AttributeError:
        # The old object doesn't implements IContained
        # Maybe we're converting old data:
        if hasattr(object, '__Broken_state__'):
            state = object.__Broken_state__
            oldparent = state['__parent__']
            oldname = state['__name__']
        else:
            if not fixing_up:
                raise
            oldparent = None
            oldname = None

    if oldparent is not container or oldname != name:
        if oldparent is not None or oldname is not None:
            notify(ObjectModifiedEvent(container))
        return

    event = ObjectRemovedEvent(object, oldparent, oldname)
    notify(event)

    if not IBroken.providedBy(object):
        object.__parent__ = None
        object.__name__ = None
    notify(ObjectModifiedEvent(container))


def mergedTaggedValueDict(schema, name):
    """Look up the tagged value 'name' in schema and all its bases, assuming
    that the value under 'name' is a dict. Return a dict that consists of
    all dict items, with those from more-specific interfaces overriding those
    from more-general ones.
    """
    tv = {}
    for iface in reversed(schema.__iro__):
        tv.update(iface.queryTaggedValue(name, {}))
    return tv


def utcnow():
    """Construct a UTC datetime from time.time()."""
    t = time.time()
    return datetime._fromtimestamp(t, True, tzutc)


def resolveDottedName(dottedName):
    """Resolve a dotted name to a real object
    """
    global _dottedCache
    if dottedName not in _dottedCache:
        _dottedCache[dottedName] = resolve(dottedName)
    return _dottedCache[dottedName]


def iterSchemataForType(portal_type):
    """XXX: came from p.a.deco.utils, very similar to iterSchemata  # noqa

    Not fully merged codewise with iterSchemata as that breaks
    test_webdav.test_readline_mimetype_additional_schemata.
    """
    main_schema = SCHEMA_CACHE.get(portal_type)
    if main_schema:
        yield main_schema
    for schema in getAdditionalSchemata(portal_type=portal_type):
        yield schema


def iterSchemata(context):
    """Return an iterable containing first the object's schema, and then
    any form field schemata for any enabled behaviors.
    """
    main_schema = SCHEMA_CACHE.get(context.portal_type)
    if main_schema:
        yield main_schema
    for schema in getAdditionalSchemata(context=context):
        yield schema


def getAdditionalSchemata(context=None, portal_type=None):
    """Get additional schemata for this context or this portal_type.

    Additional form field schemata can be defined in behaviors.

    Usually either context or portal_type should be set, not both.
    The idea is that for edit forms or views you pass in a context
    (and we get the portal_type from there) and for add forms you pass
    in a portal_type (and the context is irrelevant then).  If both
    are set, the portal_type might get ignored, depending on which
    code path is taken.
    """
    log.debug('getAdditionalSchemata with context %r and portal_type %s',
              context, portal_type)
    if context is None and portal_type is None:
        return
    if context:
        behavior_assignable = IBehaviorAssignable(context, None)
    else:
        behavior_assignable = None
    log.debug('Behavior assignable found for context.')
    if behavior_assignable:
        for behavior_reg in behavior_assignable.enumerateBehaviors():
            form_schema = IFormFieldProvider(behavior_reg.interface, None)
            if form_schema is not None:
                yield form_schema


def createContent(portal_type, **kw):
    fti = getUtility(IFTI, name=portal_type)
    content = createObject(fti.factory, **kw)

    # Note: The factory may have done this already, but we want to be sure
    # that the created type has the right portal type. It is possible
    # to re-define a type through the web that uses the factory from an
    # existing type, but wants a unique portal_type!
    content.portal_type = fti.getId()
    schemas = iterSchemataForType(portal_type)
    fields = dict(kw)  # create a copy

    for schema in schemas:
        # schema.names() doesn't return attributes from superclasses in derived
        # schemas. therefore we have to iterate over all items from the passed
        # keywords arguments and set it, if the behavior has the questioned
        # attribute.
        behavior = schema(content)
        for name, value in kw.items():
            try:
                # hasattr swallows exceptions.
                getattr(behavior, name)
            except AttributeError:
                # fieldname not available
                continue
            setattr(behavior, name, value)
            if name in fields:
                del fields[name]

    for (key, value) in fields.items():
        setattr(content, key, value)

    notify(ObjectCreatedEvent(content))
    return content


def addContentToContainer(container, object, request=None, checkConstraints=True):
    """Add an object to a container.

    The portal_type must already be set correctly. If checkConstraints
    is False no check for addable content types is done. The new object,
    wrapped in its new acquisition context, is returned.
    """
    try:
        assert object.portal_type is not None
    except (AssertionError, AttributeError):
        raise ValueError('object must have its portal_type set')

    if checkConstraints:
        container_fti = container.getTypeInfo()

        fti = getUtility(IFTI, name=object.portal_type)
        if not fti.isConstructionAllowed(container, request):
            raise Unauthorized(
                'Cannot create {0:s}'.format(object.portal_type))

        if container_fti is not None \
           and not container_fti.allowType(object.portal_type):
            raise ValueError(
                'Disallowed subobject type: {0:s}'.format(
                    object.portal_type)
            )

    name = getattr(object, 'id', None)
    if name is None:
        raise AttributeError()
    # name = INameChooser(container).chooseName(name, object)
    object.id = name
    object.__name__ = name
    container[name] = object
    return container[name]


def createContentInContainer(container, portal_type, checkConstraints=True,
                             request=None, **kw):
    content = createContent(portal_type, **kw)
    return addContentToContainer(
        container,
        content,
        checkConstraints=checkConstraints,
        request=request
    )


def safe_bytes(st):
    if isinstance(st, str):
        st = st.encode('utf8')
    return st


def safe_str(st):
    if isinstance(st, bytes):
        st = st.decode('utf8')
    return st


def all_merged_tagged_values_dict(ifaces, key):
    """mergedTaggedValueDict of all interfaces for a given key

    usally interfaces is a list of schemas
    """
    info = dict()
    for iface in ifaces:
        info.update(mergedTaggedValueDict(iface, key))
    return info


def containedEvent(object, container, name=None):

    if hasattr(object, '__parent__'):
        oldparent = object.__parent__
    else:
        oldparent = None
    oldname = object.__name__

    if oldparent is container:
        # No events
        return object, None

    if oldparent is None:
        event = ObjectAddedEvent(object, container, name)
    else:
        event = ObjectMovedEvent(object, oldparent, oldname, container, name)

    return event


def sortedFields(schema):
    """Like getFieldsInOrder, but does not include fields from bases
    """
    fields = []
    for name in schema.names(all=False):
        field = schema[name]
        if IField.providedBy(field):
            fields.append((name, field, ))
    fields.sort(key=lambda item: item[1].order)
    return fields


