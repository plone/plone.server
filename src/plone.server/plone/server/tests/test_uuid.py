import unittest

import sys


class TestUUID(unittest.TestCase):

    def setUp(self):
        import zope.component.testing
        import plone.server.uuid

        from zope.configuration import xmlconfig

        zope.component.testing.setUp()
        xmlconfig.file('configure.zcml', plone.server.uuid)

    def tearDown(self):
        import zope.component.testing
        zope.component.testing.tearDown()

    def test_default_generator(self):

        from zope.component import getUtility
        from plone.server.uuid.interfaces import IUUIDGenerator

        generator = getUtility(IUUIDGenerator)

        uuid1 = generator()
        uuid2 = generator()

        self.assertNotEqual(uuid1, uuid2)
        self.assertTrue(isinstance(uuid1, str))
        self.assertTrue(isinstance(uuid2, str))

    def test_attribute_uuid_not_set(self):

        from zope.interface import implementer

        from plone.server.uuid.interfaces import IAttributeUUID
        from plone.server.uuid.interfaces import IUUID

        @implementer(IAttributeUUID)
        class Context(object):
            pass

        context = Context()

        uuid = IUUID(context, None)
        self.assertEqual(uuid, None)

    def test_attribute_uuid_create_handler(self):

        from zope.interface import implementer
        from zope.event import notify
        from zope.lifecycleevent import ObjectCreatedEvent
        from zope.lifecycleevent import ObjectCopiedEvent

        from plone.server.uuid.interfaces import IAttributeUUID
        from plone.server.uuid.interfaces import IUUID
        from plone.server.uuid.interfaces import ATTRIBUTE_NAME

        @implementer(IAttributeUUID)
        class Context(object):
            pass

        context = Context()
        notify(ObjectCreatedEvent(context))

        uuid = IUUID(context, None)
        self.assertNotEqual(uuid, None)
        self.assertTrue(isinstance(uuid, str))

        # calling handler again won't change if UUID already present:
        notify(ObjectCreatedEvent(context))
        self.assertEqual(uuid, IUUID(context, None))

        # ...except when the UUID attribute was the result of a copy
        copied = Context()
        setattr(copied, ATTRIBUTE_NAME, IUUID(context, None))
        self.assertNotEqual(IUUID(copied, None), None)  # mimic copied state
        self.assertEqual(uuid, IUUID(copied, None))     # before handler
        notify(ObjectCopiedEvent(copied, original=context))
        self.assertNotEqual(uuid, None)
        self.assertNotEqual(uuid, IUUID(copied, None))  # copy has new UID

    def test_uuid_view_not_set(self):

        from zope.interface import implementer
        from zope.component import getMultiAdapter
        from zope.publisher.browser import TestRequest

        from plone.server.uuid.interfaces import IAttributeUUID

        @implementer(IAttributeUUID)
        class Context(object):
            pass

        context = Context()

        request = TestRequest()
        view = getMultiAdapter((context, request), name=u"uuid")
        response = view()

        self.assertEquals(u"", response)
        self.assertTrue(isinstance(response, str))

    def test_uuid_view(self):

        from zope.interface import implementer
        from zope.component import getMultiAdapter
        from zope.event import notify
        from zope.lifecycleevent import ObjectCreatedEvent
        from zope.publisher.browser import TestRequest

        from plone.server.uuid.interfaces import IAttributeUUID
        from plone.server.uuid.interfaces import IUUID

        @implementer(IAttributeUUID)
        class Context(object):
            pass

        context = Context()
        notify(ObjectCreatedEvent(context))

        uuid = IUUID(context, None)

        request = TestRequest()
        view = getMultiAdapter((context, request), name=u"uuid")
        response = view()

        self.assertEquals(str(uuid), response)
        self.assertTrue(isinstance(response, str))

    def test_uuid_mutable(self):
        from zope import interface
        from zope import lifecycleevent
        from zope import event
        from plone.server.uuid import interfaces

        @interface.implementer(interfaces.IAttributeUUID)
        class Context(object):
            pass

        context = Context()
        event.notify(lifecycleevent.ObjectCreatedEvent(context))

        mutable = interfaces.IMutableUUID(context)

        uuid1 = mutable.get()
        mutable.set('a uuid to set')
        uuid2 = mutable.get()
        uuid3 = interfaces.IUUID(context)

        self.failUnless(uuid1 != uuid2)
        self.failUnless(uuid2 == uuid3)
