# -*- coding: utf-8 -*-
from copy import deepcopy
from datetime import datetime
from persistent import Persistent

from dateutil.tz import tzlocal
from plone.behavior.interfaces import IBehaviorAssignable
from zope.annotation import IAttributeAnnotatable
from zope.interface import implementer
from zope.interface.declarations import Implements
from zope.interface.declarations import ObjectSpecificationDescriptor
from zope.interface.declarations import getObjectSpecification
from zope.interface.declarations import implementedBy
from zope.schema.interfaces import IContextAwareDefaultFactory
from plone.server.content.interfaces import IDexterityContainer
from plone.server.content.interfaces import IDexterityContent
from plone.server.content.interfaces import IDexterityItem
from plone.server.content.schema import SCHEMA_CACHE
from plone.server.uuid.interfaces import IAttributeUUID
from plone.server.uuid.interfaces import IUUID
import asyncio
import six
from zope.event import notify
from BTrees.OOBTree import OOBTree
from BTrees.Length import Length
from plone.server.content.utils import setitem, uncontained
from plone.server.content.utils import notifyContainerModified
from plone.server.content.utils import containedEvent
from persistent.dict import PersistentDict
from persistent.list import PersistentList

_marker = object()
_zone = tzlocal()


def _default_from_schema(context, schema, fieldname):
    """helper to lookup default value of a field
    """
    if schema is None:
        return _marker
    field = schema.get(fieldname, None)
    if field is None:
        return _marker
    if IContextAwareDefaultFactory.providedBy(
            getattr(field, 'defaultFactory', None)
    ):
        bound = field.bind(context)
        return deepcopy(bound.default)
    else:
        return deepcopy(field.default)


class FTIAwareSpecification(ObjectSpecificationDescriptor):
    """A __providedBy__ decorator that returns the interfaces provided by
    the object, plus the schema interface set in the FTI.
    """

    def __get__(self, inst, cls=None):  # noqa
        # We're looking at a class - fall back on default
        if inst is None:
            return getObjectSpecification(cls)

        direct_spec = getattr(inst, '__provides__', None)

        # avoid recursion - fall back on default
        if getattr(self, '__recursion__', False):
            return direct_spec

        spec = direct_spec

        # If the instance doesn't have a __provides__ attribute, get the
        # interfaces implied by the class as a starting point.
        if spec is None:
            spec = implementedBy(cls)

        # Find the data we need to know if our cache needs to be invalidated
        portal_type = getattr(inst, 'portal_type', None)

        # If the instance has no portal type, then we're done.
        if portal_type is None:
            return spec

        # Find the cached value. This calculation is expensive and called
        # hundreds of times during each request, so we require a fast cache
        cache = getattr(inst, '_v__providedBy__', None)

        # See if we have a current cache. Reasons to do this include:
        #
        #  - The FTI was modified.
        #  - The instance was modified and persisted since the cache was built.
        #  - The instance has a different direct specification.
        updated = (
            inst._p_mtime,
            SCHEMA_CACHE.modified(portal_type),
            SCHEMA_CACHE.invalidations,
            hash(direct_spec)
        )
        if cache is not None and cache[:-1] == updated:
            if cache[-1] is not None:
                return cache[-1]
            return spec

        main_schema = SCHEMA_CACHE.get(portal_type)
        if main_schema:
            dynamically_provided = [main_schema]
        else:
            dynamically_provided = []

        # block recursion
        self.__recursion__ = True
        try:
            assignable = IBehaviorAssignable(inst, None)
            if assignable is not None:
                for behavior_registration in assignable.enumerateBehaviors():
                    if behavior_registration.marker:
                        dynamically_provided.append(
                            behavior_registration.marker
                        )
        finally:
            del self.__recursion__

        if not dynamically_provided:
            # rare case if no schema nor behaviors with markers are set
            inst._v__providedBy__ = updated + (None, )
            return spec

        dynamically_provided.append(spec)
        all_spec = Implements(*dynamically_provided)
        inst._v__providedBy__ = updated + (all_spec, )

        return all_spec


@implementer(
    IDexterityContent,
    IAttributeAnnotatable,
    IAttributeUUID
)
class DexterityContent(Persistent):
    """Base class for Dexterity content
    """
    __parent__ = __name__ = None

    __providedBy__ = FTIAwareSpecification()

    # portal_type is set by the add view and/or factory
    portal_type = None

    def __init__(  # noqa
            self,
            id=None,
            **kwargs):

        if id is not None:
            self.id = id
        now = datetime.now(tz=_zone)
        self.creation_date = now
        self.modification_date = now

        for (k, v) in kwargs.items():
            setattr(self, k, v)

    # def __getattr__(self, name):
    #     # python basics:  __getattr__ is only invoked if the attribute wasn't
    #     # found by __getattribute__
    #     #
    #     # optimization: sometimes we're asked for special attributes
    #     # such as __conform__ that we can disregard (because we
    #     # wouldn't be in here if the class had such an attribute
    #     # defined).
    #     # also handle special dynamic providedBy cache here.
    #     if name.startswith('__') or name == '_v__providedBy__':
    #         raise AttributeError(name)

    #     # attribute was not found; try to look it up in the schema and return
    #     # a default
    #     value = _default_from_schema(
    #         self,
    #         SCHEMA_CACHE.get(self.portal_type),
    #         name
    #     )
    #     if value is not _marker:
    #         return value

    #     # do the same for each subtype
    #     assignable = IBehaviorAssignable(self, None)
    #     if assignable is not None:
    #         for behavior_registration in assignable.enumerateBehaviors():
    #             if behavior_registration.interface:
    #                 value = _default_from_schema(
    #                     self,
    #                     behavior_registration.interface,
    #                     name
    #                 )
    #                 if value is not _marker:
    #                     return value

    #     raise AttributeError(name)

    # Let __name__ and id be identical. Note that id must be ASCII in Zope 2,
    # but __name__ should be unicode. Note that setting the name to something
    # that can't be encoded to ASCII will throw a UnicodeEncodeError

    def _get__name__(self):
        return self.id

    def _set__name__(self, value):
        if isinstance(value, str):
            value = str(value)  # may throw, but that's OK - id must be ASCII
        self.id = value

    __name__ = property(_get__name__, _set__name__)

    def UID(self):
        """Returns the item's globally unique id."""
        return IUUID(self)


def synccontext(context):
    """Return connections asyncio executor instance (from context) to be used
    together with "await" syntax to queue or commit to be executed in
    series in a dedicated thread.

    :param request: current request

    Example::

        await sync(request)(txn.commit)

    """
    loop = asyncio.get_event_loop()
    assert getattr(context, '_p_jar', None) is not None, \
        'Request has no conn'
    assert getattr(context._p_jar, 'executor', None) is not None, \
        'Connection has no executor'
    return lambda *args, **kwargs: loop.run_in_executor(
        context._p_jar.executor, *args, **kwargs)


@implementer(IDexterityItem)
class Item(DexterityContent):
    """A non-containerish, CMFish item
    """

    __providedBy__ = FTIAwareSpecification()

    # Be explicit about which __getattr__ to use
    # __getattr__ = DexterityContent.__getattr__


@implementer(
    IDexterityContainer,
    IAttributeAnnotatable,
    IAttributeUUID)
class OrderedContainer(DexterityContent):
    """Base class for folderish items
    """

    __providedBy__ = FTIAwareSpecification()

    def __init__(self, id=None, **kwargs):
        self._data = PersistentDict()
        self._order = PersistentList()
        DexterityContent.__init__(self, id, **kwargs)

    def __getattr__(self, name, default=None):
        return DexterityContent.__getattr__(self, name)

    def keys(self):
        return self._order[:]

    def __iter__(self):
        return iter(self.keys())

    def __getitem__(self, key):
        return self._data[key]

    async def asyncget(self, key):
        return await synccontext(self)(self._data.__getitem__, key)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def values(self):
        return [self._data[i] for i in self._order]

    def __len__(self):
        return len(self._data)

    def items(self):
        return [(i, self._data[i]) for i in self._order]

    def __contains__(self, key):
        return key in self._data

    has_key = __contains__

    def __setitem__(self, key, object):
        existed = key in self._data

        bad = False
        if not isinstance(key, six.string_types):
            bad = True
        if bad:
            raise TypeError("'%s' is invalid, the key must be an "
                            "ascii or unicode string" % key)
        if len(key) == 0:
            raise ValueError("The key cannot be an empty string")

        # We have to first update the order, so that the item is available,
        # otherwise most API functions will lie about their available values
        # when an event subscriber tries to do something with the container.
        if not existed:
            self._order.append(key)

        # This function creates a lot of events that other code listens to.
        try:
            setitem(self, self._data.__setitem__, key, object)
        except Exception:
            if not existed:
                self._order.remove(key)
            raise

        return key

    def __delitem__(self, key):
        uncontained(self._data[key], self, key)
        del self._data[key]
        self._order.remove(key)

    def updateOrder(self, order):
        """ See `IOrderedContainer`.

        >>> oc = OrderedContainer()
        >>> oc['foo'] = 'bar'
        >>> oc['baz'] = 'quux'
        >>> oc['zork'] = 'grue'
        >>> oc.keys()
        ['foo', 'baz', 'zork']
        >>> oc.updateOrder(['baz', 'foo', 'zork'])
        >>> oc.keys()
        ['baz', 'foo', 'zork']
        >>> oc.updateOrder(['baz', 'zork', 'foo'])
        >>> oc.keys()
        ['baz', 'zork', 'foo']
        >>> oc.updateOrder(['baz', 'zork', 'foo'])
        >>> oc.keys()
        ['baz', 'zork', 'foo']
        >>> oc.updateOrder(('zork', 'foo', 'baz'))
        >>> oc.keys()
        ['zork', 'foo', 'baz']
        >>> oc.updateOrder(['baz', 'zork'])
        Traceback (most recent call last):
        ...
        ValueError: Incompatible key set.
        >>> oc.updateOrder(['foo', 'bar', 'baz', 'quux'])
        Traceback (most recent call last):
        ...
        ValueError: Incompatible key set.
        >>> oc.updateOrder(1)
        Traceback (most recent call last):
        ...
        TypeError: order must be a tuple or a list.
        >>> oc.updateOrder('bar')
        Traceback (most recent call last):
        ...
        TypeError: order must be a tuple or a list.
        >>> oc.updateOrder(['baz', 'zork', 'quux'])
        Traceback (most recent call last):
        ...
        ValueError: Incompatible key set.
        >>> del oc['baz']
        >>> del oc['zork']
        >>> del oc['foo']
        >>> len(oc)
        0
        """

        if not isinstance(order, list) and \
            not isinstance(order, tuple):
            raise TypeError('order must be a tuple or a list.')

        if len(order) != len(self._order):
            raise ValueError("Incompatible key set.")

        was_dict = {}
        will_be_dict = {}
        new_order = PersistentList()

        for i in range(len(order)):
            was_dict[self._order[i]] = 1
            will_be_dict[order[i]] = 1
            new_order.append(order[i])

        if will_be_dict != was_dict:
            raise ValueError("Incompatible key set.")

        self._order = new_order
        notifyContainerModified(self)


class Lazy(object):
    """Lazy Attributes.
    """

    def __init__(self, func, name=None):
        if name is None:
            name = func.__name__
        self.data = (func, name)

    def __get__(self, inst, class_):
        if inst is None:
            return self

        func, name = self.data
        value = func(inst)
        inst.__dict__[name] = value

        return value


@implementer(
    IDexterityContainer,
    IAttributeAnnotatable,
    IAttributeUUID)
class BTreeContainer(DexterityContent):

    def __init__(self, id=None, **kwargs):
        # We keep the previous attribute to store the data
        # for backward compatibility
        self._BTreeContainer__data = self._newContainerData()
        self.__len = Length()
        DexterityContent.__init__(self, id, **kwargs)

    def _newContainerData(self):
        """Construct an item-data container

        Subclasses should override this if they want different data.

        The value returned is a mapping object that also has get,
        has_key, keys, items, and values methods.
        The default implementation uses an OOBTree.
        """
        return OOBTree()

    def __contains__(self, key):
        """See interface IReadContainer
        """
        return key in self.__data

    @Lazy
    def _BTreeContainer__len(self):
        l = Length()
        ol = len(self.__data)
        if ol > 0:
            l.change(ol)
        self._p_changed = True
        return l

    def __len__(self):
        return self.__len()

    def _setitemf(self, key, value):
        # make sure our lazy property gets set
        l = self.__len
        self.__data[key] = value
        l.change(1)

    def __iter__(self):
        return iter(self.__data)

    def __getitem__(self, key):
        '''See interface `IReadContainer`'''
        return self.__data[key]

    def get(self, key, default=None):
        '''See interface `IReadContainer`'''
        return self.__data.get(key, default)

    async def asyncget(self, key):
        return await synccontext(self)(self.__data.__getitem__, key)

    def __setitem__(self, key, value):
        if not key:
            raise ValueError("empty names are not allowed")
        object, event = containedEvent(value, self, key)
        self._setitemf(key, value)
        if event:
            notify(event)
            notifyContainerModified(self)

    def __delitem__(self, key):
        # make sure our lazy property gets set
        l = self.__len
        item = self.__data[key]
        del self.__data[key]
        l.change(-1)
        uncontained(item, self, key)

    has_key = __contains__

    def items(self, key=None):
        return self.__data.items(key)

    def keys(self, key=None):
        return self.__data.keys(key)

    def values(self, key=None):
        return self.__data.values(key)

