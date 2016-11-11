# -*- coding: utf-8 -*-
from plone.server.content.content import Container
from plone.server.content.content import Item
from plone.server.content.fti import DexterityFTI
from plone.server.content.interfaces import IDexterityFTI
from plone.server.content.interfaces import READ_PERMISSIONS_KEY
from plone.server.content.schema import SCHEMA_CACHE
from plone.mocktestcase import MockTestCase
from zope.interface import Interface
from zope.interface import provider
from zope.security.interfaces import IPermission
from zope.security.permission import Permission
import unittest
import zope.schema


class TestAttributeProtection(MockTestCase):

    def setUp(self):
        SCHEMA_CACHE.clear()

    def test_item(self):

        # Mock schema model
        class ITestSchema(Interface):
            test = zope.schema.TextLine(title='Test')

        ITestSchema.setTaggedValue(
            READ_PERMISSIONS_KEY,
            dict(test='zope2.View', foo='foo.View')
        )

        from plone.server.content.interfaces import IFormFieldProvider

        @provider(IFormFieldProvider)
        class ITestBehavior(Interface):
            test2 = zope.schema.TextLine(title='Test')

        ITestBehavior.setTaggedValue(
            READ_PERMISSIONS_KEY,
            dict(test2='zope2.View', foo2='foo.View')
        )

        # Mock a test behavior
        from plone.behavior.registration import BehaviorRegistration
        registration = BehaviorRegistration(
            title='Test Behavior',
            description='Provides test behavior',
            interface=ITestBehavior,
            marker=Interface,
            factory=None
        )
        from plone.behavior.interfaces import IBehavior
        self.mock_utility(
            registration,
            IBehavior,
            ITestBehavior.__identifier__
        )
        from plone.server.content.behavior import DexterityBehaviorAssignable
        from plone.server.content.interfaces import IDexterityContent
        from plone.behavior.interfaces import IBehaviorAssignable
        self.mock_adapter(
            DexterityBehaviorAssignable,
            IBehaviorAssignable,
            (IDexterityContent,)
        )

        # Mock FTI
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.mock_utility(fti_mock, IDexterityFTI, 'testtype')

        # Mock permissions
        self.mock_utility(
            Permission('zope2.View', u'View'),
            IPermission,
            'zope2.View'
        )
        self.mock_utility(
            Permission('foo.View', u'View foo'),
            IPermission,
            'foo.View'
        )

        # Content item
        item = Item('test')
        item.portal_type = 'testtype'
        item.test = 'foo'
        item.foo = 'bar'

        # mock security manager
        securityManager_mock = self.mocker.mock()
        getSecurityManager_mock = self.mocker.replace(
            'zopepolicy.ZopeSecurityPolicy.getSecurityManager'
        )

        # expectations
        # run 1
        # lookupSchema is always called twice: cache and __providedBy__
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result(tuple())
        self.expect(
            securityManager_mock.checkPermission('View', item)
        ).result(False)

        # run 2
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result(tuple())
        self.expect(
            securityManager_mock.checkPermission('View foo', item)
        ).result(True)

        # run 3
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result(tuple())

        # # run 4
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result([ITestBehavior.__identifier__])
        self.expect(
            securityManager_mock.checkPermission('View', item)
        ).result(True)

        # # run 5
        self.expect(fti_mock.lookupSchema()).result(None)
        self.expect(fti_mock.behaviors).result([ITestBehavior.__identifier__])
        self.expect(
            securityManager_mock.checkPermission('View', item)
        ).result(True)

        # for all 5 runs
        self.expect(
            getSecurityManager_mock()
        ).result(
            securityManager_mock
        ).count(4)

        self.mocker.replay()

        # run 1: schema and no behavior access to schema protected attribute
        SCHEMA_CACHE.clear()
        self.assertFalse(
            item.__allow_access_to_unprotected_subobjects__('test', 'foo')
        )

        # # run 2: schema and no behavior access to known non schema attribute
        SCHEMA_CACHE.clear()
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('foo', 'bar')
        )

        # # run 3: schema and no behavior, unknown attributes are allowed
        SCHEMA_CACHE.clear()
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('random', 'stuff')
        )

        # # run 4: schema and behavior
        SCHEMA_CACHE.clear()
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('test2', 'foo2')
        )

        # run 5: no schema but behavior
        SCHEMA_CACHE.clear()
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('test2', 'foo2')
        )

    def test_container(self):

        # Mock schema model
        class ITestSchema(Interface):
            test = zope.schema.TextLine(title='Test')

        ITestSchema.setTaggedValue(
            READ_PERMISSIONS_KEY,
            dict(test='zope2.View', foo='foo.View')
        )

        from plone.server.content.interfaces import IFormFieldProvider

        @provider(IFormFieldProvider)
        class ITestBehavior(Interface):
            test2 = zope.schema.TextLine(title='Test')

        ITestBehavior.setTaggedValue(
            READ_PERMISSIONS_KEY,
            dict(test2='zope2.View', foo2='foo.View')
        )

        # Mock a test behavior
        from plone.behavior.registration import BehaviorRegistration
        registration = BehaviorRegistration(
            title='Test Behavior',
            description='Provides test behavior',
            interface=ITestBehavior,
            marker=Interface,
            factory=None
        )
        from plone.behavior.interfaces import IBehavior
        self.mock_utility(
            registration,
            IBehavior,
            ITestBehavior.__identifier__
        )
        from plone.server.content.behavior import DexterityBehaviorAssignable
        from plone.server.content.interfaces import IDexterityContent
        from plone.behavior.interfaces import IBehaviorAssignable
        self.mock_adapter(
            DexterityBehaviorAssignable,
            IBehaviorAssignable,
            (IDexterityContent,)
        )

        # Mock FTI
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.mock_utility(fti_mock, IDexterityFTI, 'testtype')

        # Mock permissions
        self.mock_utility(
            Permission('zope2.View', u'View'),
            IPermission,
            'zope2.View'
        )
        self.mock_utility(
            Permission('foo.View', u'View foo'),
            IPermission,
            'foo.View'
        )

        # Content item
        container = Container('test')
        container.portal_type = 'testtype'
        container.test = 'foo'
        container.foo = 'bar'

        # mock security manager
        securityManager_mock = self.mocker.mock()
        getSecurityManager_mock = self.mocker.replace(
            'zopepolicy.ZopeSecurityPolicy.getSecurityManager'
        )

        # expectations
        # run 1
        # lookupSchema is always called twice: cache and __providedBy__
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result(tuple())
        self.expect(
            securityManager_mock.checkPermission('View', container)
        ).result(False)

        # run 2
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result(tuple())
        self.expect(
            securityManager_mock.checkPermission('View foo', container)
        ).result(True)

        # run 3
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result(tuple())

        # # run 4
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result([ITestBehavior.__identifier__])
        self.expect(
            securityManager_mock.checkPermission('View', container)
        ).result(True)

        # # run 5
        self.expect(fti_mock.lookupSchema()).result(None)
        self.expect(fti_mock.behaviors).result([ITestBehavior.__identifier__])
        self.expect(
            securityManager_mock.checkPermission('View', container)
        ).result(True)

        # for all 5 runs
        self.expect(
            getSecurityManager_mock()
        ).result(
            securityManager_mock
        ).count(4)

        self.mocker.replay()

        # run 1: schema and no behavior access to schema protected attribute
        SCHEMA_CACHE.clear()
        self.assertFalse(
            container.__allow_access_to_unprotected_subobjects__(
                'test',
                'foo'
            )
        )

        # # run 2: schema and no behavior access to known non schema attribute
        SCHEMA_CACHE.clear()
        self.assertTrue(
            container.__allow_access_to_unprotected_subobjects__(
                'foo',
                'bar'
            )
        )

        # # run 3: schema and no behavior, unknown attributes are allowed
        SCHEMA_CACHE.clear()
        self.assertTrue(
            container.__allow_access_to_unprotected_subobjects__(
                'random',
                'stuff'
            )
        )

        # # run 4: schema and behavior
        SCHEMA_CACHE.clear()
        self.assertTrue(
            container.__allow_access_to_unprotected_subobjects__(
                'test2',
                'foo2'
            )
        )

        # run 5: no schema but behavior
        SCHEMA_CACHE.clear()
        self.assertTrue(
            container.__allow_access_to_unprotected_subobjects__(
                'test2',
                'foo2'
            )
        )

    def test_no_tagged_value(self):

        # Mock schema model
        class ITestSchema(Interface):
            test = zope.schema.TextLine(title='Test')

        # Mock FTI
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result(tuple())
        self.mock_utility(fti_mock, IDexterityFTI, 'testtype')

        # Content item
        item = Item('test')
        item.portal_type = 'testtype'
        item.test = 'foo'
        item.foo = 'bar'

        self.mocker.replay()

        SCHEMA_CACHE.clear()

        # Everything allowed
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('test', 'foo')
        )
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('foo', 'bar')
        )

        # Unknown attributes are allowed
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('random', 'stuff')
        )

    def test_no_read_permission(self):

        # Mock schema model
        class ITestSchema(Interface):
            test = zope.schema.TextLine(title='Test')
        ITestSchema.setTaggedValue(READ_PERMISSIONS_KEY, dict(foo='foo.View'))

        # Mock FTI
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(ITestSchema)
        self.expect(fti_mock.behaviors).result(tuple())

        self.mock_utility(fti_mock, IDexterityFTI, 'testtype')

        # Mock permissions
        self.mock_utility(
            Permission('foo.View', u'View foo'), IPermission, u'foo.View'
        )

        # Content item
        item = Item('test')
        item.portal_type = 'testtype'
        item.test = 'foo'
        item.foo = 'bar'

        # Check permission
        securityManager_mock = self.mocker.mock()
        self.expect(
            securityManager_mock.checkPermission('View foo', item)
        ).result(True)
        getSecurityManager_mock = self.mocker.replace(
            'zopepolicy.ZopeSecurityPolicy.getSecurityManager'
        )
        self.expect(
            getSecurityManager_mock()
        ).result(securityManager_mock).count(1)

        self.mocker.replay()

        SCHEMA_CACHE.clear()

        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('test', 'foo')
        )
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('foo', 'bar')
        )

        # Unknown attributes are allowed
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('random', 'stuff')
        )

    def test_no_schema(self):

        # Mock FTI
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).result(None)
        self.expect(fti_mock.behaviors).result(tuple())
        self.mock_utility(fti_mock, IDexterityFTI, 'testtype')

        # Content item
        item = Item('test')
        item.portal_type = 'testtype'
        item.test = 'foo'
        item.foo = 'bar'

        self.mocker.replay()

        SCHEMA_CACHE.clear()

        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('test', 'foo')
        )
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('foo', 'bar')
        )
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('random', 'stuff')
        )

    def test_schema_exception(self):

        # Mock FTI
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))

        self.expect(fti_mock.lookupSchema()).throw(AttributeError)
        self.expect(fti_mock.behaviors).result(tuple())

        self.mock_utility(fti_mock, IDexterityFTI, 'testtype')

        # Content item
        item = Item('test')
        item.portal_type = 'testtype'
        item.test = 'foo'
        item.foo = 'bar'

        self.mocker.replay()

        SCHEMA_CACHE.clear()

        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('test', 'foo')
        )
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('foo', 'bar')
        )
        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('random', 'stuff')
        )

    def test_empty_name(self):

        # Mock FTI
        fti_mock = self.mocker.proxy(DexterityFTI('testtype'))
        self.expect(fti_mock.lookupSchema()).count(0)
        self.expect(fti_mock.behaviors).count(0)
        self.mock_utility(fti_mock, IDexterityFTI, 'testtype')

        # Content item
        item = Item('test')
        item.portal_type = 'testtype'

        self.mocker.replay()

        SCHEMA_CACHE.clear()

        self.assertTrue(
            item.__allow_access_to_unprotected_subobjects__('', 'foo')
        )


def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
