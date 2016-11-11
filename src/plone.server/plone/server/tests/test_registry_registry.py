# -*- coding: utf-8 -*-
from plone.registry.fieldfactory import choicePersistentFieldAdapter
from plone.registry.fieldfactory import persistentFieldAdapter
from zope.component import eventtesting
from zope.component import provideAdapter
from zope.component import testing
from zope import schema
from zope.interface import Interface
import doctest
import re
import sys
import unittest


SKIP_PYTHON_2 = doctest.register_optionflag('SKIP_PYTHON_2')
SKIP_PYTHON_3 = doctest.register_optionflag('SKIP_PYTHON_3')
IGNORE_B = doctest.register_optionflag('IGNORE_B')
IGNORE_U = doctest.register_optionflag('IGNORE_U')


class PolyglotOutputChecker(doctest.OutputChecker):
    def check_output(self, want, got, optionflags):
        if optionflags & SKIP_PYTHON_3 and sys.version_info >= (3,):
            return True
        elif optionflags & SKIP_PYTHON_2:
            return True

        if hasattr(self, '_toAscii'):
            got = self._toAscii(got)
            want = self._toAscii(want)

        # Naive fix for comparing byte strings
        if got != want and optionflags & IGNORE_B:
            got = re.sub(r'^b([\'"])', r'\1', got)
            want = re.sub(r'^b([\'"])', r'\1', want)

        # Naive fix for comparing byte strings
        if got != want and optionflags & IGNORE_U:
            got = re.sub(r'^u([\'"])', r'\1', got)
            want = re.sub(r'^u([\'"])', r'\1', want)

        return doctest.OutputChecker.check_output(
            self, want, got, optionflags)


class IMailSettings(Interface):
    """Settings for email
    """

    sender = schema.TextLine(title=u"Mail sender", default=u"root@localhost")
    smtp_host = schema.URI(title=u"SMTP host server")


class IMailPreferences(Interface):
    """Settings for email
    """
    max_daily = schema.Int(
        title=u"Maximum number of emails per day",
        min=0,
        default=3
    )
    settings = schema.Object(
        title=u"Mail setings to use",
        schema=IMailSettings
    )


def setUp(test=None):
    testing.setUp()
    eventtesting.setUp()

    provideAdapter(persistentFieldAdapter)
    provideAdapter(choicePersistentFieldAdapter)


class TestBugs(unittest.TestCase):
    """Regression tests for bugs that have been fixed
    """

    def setUp(self):
        setUp(self)

    def tearDown(self):
        testing.tearDown(self)

    def test_bind_choice(self):
        from plone.registry.field import Choice

        from zope.schema.vocabulary import getVocabularyRegistry
        from zope.schema.vocabulary import SimpleVocabulary

        def vocabFactory(obj):
            return SimpleVocabulary.fromValues(['one', 'two'])

        reg = getVocabularyRegistry()
        reg.register('my.vocab', vocabFactory)

        class T(object):
            f = None

        f = Choice(__name__='f', title=u"Test", vocabulary="my.vocab")
        t = T()

        # Bug: this would give "AttributeError: can't set attribute" on
        # clone.vocabulary
        f.bind(t)

    def test_fieldref_interfaces(self):
        from plone.registry import field, FieldRef
        from plone.registry.interfaces import IFieldRef
        from zope.schema.interfaces import ICollection

        listField = field.List(value_type=field.ASCIILine())
        ref = FieldRef('some.record', listField)

        self.assertTrue(ICollection.providedBy(ref))
        self.assertTrue(IFieldRef.providedBy(ref))


class TestMigration(unittest.TestCase):

    def setUp(self):
        setUp(self)

    def tearDown(self):
        testing.tearDown(self)

    def test_auto_migration(self):

        from BTrees.OOBTree import OOBTree

        from plone.registry.registry import Registry, Records, _Records
        from plone.registry.record import Record
        from plone.registry import field

        # Create an "old-looking registry"

        registry = Registry()
        registry._records = Records(registry)
        registry._records.data = OOBTree()

        f = field.TextLine(title=u"Foo")

        record = Record(f, u"Bar")
        record.__dict__['field'] = f
        record.__dict__['value'] = u"Bar"

        registry._records.data['foo.bar'] = record

        # Attempt to access it

        value = registry['foo.bar']

        # Migration should have happened

        self.assertEqual(value, u"Bar")
        self.assertEqual(registry.records['foo.bar'].field.title, u"Foo")
        self.assertEqual(registry.records['foo.bar'].value, u"Bar")

        self.assertFalse(isinstance(registry._records, Records))
        self.assertTrue(isinstance(registry._records, _Records))


def test_suite():
    return unittest.TestSuite([
        doctest.DocFileSuite(
            'registry.rst',
            package='plone.registry',
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            setUp=setUp,
            tearDown=testing.tearDown,
            checker=PolyglotOutputChecker()
        ),
        doctest.DocFileSuite(
            'events.rst',
            package='plone.registry',
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            setUp=setUp,
            tearDown=testing.tearDown,
            checker=PolyglotOutputChecker()
        ),
        doctest.DocFileSuite(
            'field.rst',
            package='plone.registry',
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS,
            setUp=setUp,
            tearDown=testing.tearDown,
            checker=PolyglotOutputChecker()
        ),
        unittest.makeSuite(TestBugs),
        unittest.makeSuite(TestMigration),
    ])
