# -*- coding: utf-8 -*-
from plone.server.content.interfaces import FIELDSETS_KEY
from plone.server.content.interfaces import ISchema
from plone.server.content.interfaces import ISchemaPlugin
from plone.server.content.interfaces import READ_PERMISSIONS_KEY
from plone.server.content.interfaces import WRITE_PERMISSIONS_KEY
from plone.server.content.interfaces import INDEX_KEY
from plone.server.content.interfaces import CATALOG_KEY
from plone.server.content.model import Fieldset
from zope.component import adapter
from zope.interface import implementer
from zope.interface.interface import TAGGED_DATA
import os.path
import sys

# Directive


class DirectiveClass(type):
    """A Directive is used to apply tagged values to a Schema
    """

    def __init__(self, name, bases, attrs):
        attrs.setdefault('finalize', None)
        super(DirectiveClass, self).__init__(name, bases, attrs)
        self.__instance = super(DirectiveClass, self).__call__()

    def __call__(self, *args, **kw):
        instance = self.__instance
        frame = sys._getframe(1)
        tags = frame.f_locals.setdefault(TAGGED_DATA, {})
        value = instance.factory(*args, **kw)
        instance.store(tags, value)

Directive = DirectiveClass('Directive', (), dict(__module__='plone.supermodel.directives',),)


class MetadataListDirective(Directive):
    """Store a list value in the tagged value under the key.
    """
    key = None

    def store(self, tags, value):
        tags.setdefault(self.key, []).extend(value)


class MetadataDictDirective(Directive):
    """Store a dict value in the tagged value under the key.
    """
    key = None

    def store(self, tags, value):
        tags.setdefault(self.key, {}).update(value)


# Plugin

@adapter(ISchema)
@implementer(ISchemaPlugin)
class CheckerPlugin(object):

    key = None

    def __init__(self, schema):
        self.schema = schema
        self.value = schema.queryTaggedValue(self.key, None)

    def fieldNames(self):
        raise NotImplementedError()

    def check(self):
        schema = self.schema
        for fieldName in self.fieldNames():
            if fieldName not in schema:
                raise ValueError(
                    u"The directive %s applied to interface %s "
                    u"refers to unknown field name %s" % (self.key, schema.__identifier__, fieldName)
                    )
            yield fieldName

    def __call__(self):
        for fieldName in self.check():
            pass


class DictCheckerPlugin(CheckerPlugin):

    def fieldNames(self):
        if self.value is None:
            return []
        return self.value.keys()


class ListCheckerPlugin(CheckerPlugin):

    def fieldNames(self):
        if self.value is None:
            return
        for fieldName in self.value:
            yield fieldName


class ListPositionCheckerPlugin(CheckerPlugin):

    position = None

    def fieldNames(self):
        if self.value is None:
            return
        for item in self.value:
            yield item[self.position]


# Implementations

class load(Directive):
    """Directive used to specify the XML model file
    """

    def store(self, tags, value):
        tags[SCHEMA_NAME_KEY] = value["schema"]

    def factory(self, filename, schema=u""):
        return dict(filename=filename, schema=schema)


@adapter(ISchema)
@implementer(ISchemaPlugin)
class SupermodelSchemaPlugin(object):

    order = -1000

    def __init__(self, interface):
        self.interface = interface

    def __call__(self):
        interface = self.interface
        filename = interface.queryTaggedValue(FILENAME_KEY, None)
        if filename is None:
            return
        schema = interface.queryTaggedValue(SCHEMA_NAME_KEY, u"")

        moduleName = interface.__module__
        module = sys.modules.get(moduleName, None)

        directory = moduleName

        if hasattr(module, '__path__'):
            directory = module.__path__[0]
        else:
            while "." in moduleName:
                moduleName, _ = moduleName.rsplit('.', 1)
                module = sys.modules.get(moduleName, None)
                if hasattr(module, '__path__'):
                    directory = module.__path__[0]
                    break

        directory = os.path.abspath(directory)
        # Let / act as path separator on all platforms
        filename = filename.replace('/', os.path.sep)
        filename = os.path.abspath(os.path.join(directory, filename))


class fieldset(MetadataListDirective):
    """Directive used to create fieldsets
    """
    key = FIELDSETS_KEY

    def factory(self, name, label=None, description=None, fields=None, **kw):
        fieldset = Fieldset(name, label=label, description=description, fields=fields)
        for (key, value) in kw.items():
            setattr(fieldset, key, value)
        return [fieldset]


class FieldsetCheckerPlugin(CheckerPlugin):

    key = FIELDSETS_KEY

    def fieldNames(self):
        if self.value is None:
            return
        for fieldset in self.value:
            for fieldName in fieldset.fields:
                yield fieldName


class read_permission(MetadataDictDirective):
    """Directive used to set a field read permission
    """
    key = READ_PERMISSIONS_KEY

    def factory(self, **kw):
        return kw


class write_permission(read_permission):
    """Directive used to set a field write permission
    """
    key = WRITE_PERMISSIONS_KEY


class ReadPermissionsPlugin(DictCheckerPlugin):
    key = READ_PERMISSIONS_KEY


class WritePermissionsPlugin(DictCheckerPlugin):
    key = WRITE_PERMISSIONS_KEY


class catalog(MetadataDictDirective):
    """Directive used to set a field read permission
    """
    key = CATALOG_KEY

    def factory(self, **kw):
        return kw


class CatalogPlugin(DictCheckerPlugin):
    key = CATALOG_KEY


class index(MetadataDictDirective):
    """Directive used to set a field read permission
    """
    key = INDEX_KEY

    def factory(self, **kw):
        return kw


class IndexPlugin(DictCheckerPlugin):
    key = INDEX_KEY

