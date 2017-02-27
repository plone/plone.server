# -*- coding: utf-8 -*-
from aiohttp.web import StreamResponse
from plone.server import configure
from plone.server.api.service import DownloadService
from plone.server.api.service import TraversableDownloadService
from plone.server.api.service import TraversableFieldService
from plone.server.interfaces import IFileManager
from plone.server.interfaces import IResource
from plone.server.interfaces import IStaticFile
from plone.server.api.content import DefaultOPTIONS
from zope.component import getMultiAdapter

import aiohttp
import mimetypes


# Static File
@configure.service(context=IStaticFile, method='GET', permission='plone.AccessContent')
class DefaultGET(DownloadService):
    async def __call__(self):
        if hasattr(self.context, 'file_path'):
            filepath = str(self.context.file_path.absolute())
            filename = self.context.file_path.name
            with open(filepath, 'rb') as f:
                resp = StreamResponse(headers=aiohttp.MultiDict({
                    'CONTENT-DISPOSITION': 'attachment; filename="%s"' % filename
                }))
                resp.content_type = mimetypes.guess_type(filename)
                data = f.read()
                resp.content_length = len(data)
                await resp.prepare(self.request)

                resp.write(data)
                return resp


# Field File
@configure.service(context=IResource, method='PATCH', permission='plone.ModifyContent',
                   name='@upload')
class UploadFile(TraversableFieldService):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.upload()


@configure.service(context=IResource, method='GET', permission='plone.ViewContent',
                   name='@download')
class DownloadFile(TraversableDownloadService):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.download()


@configure.service(context=IResource, method='POST', permission='plone.ModifyContent',
                   name='@tusupload')
class TusCreateFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_create()


@configure.service(context=IResource, method='HEAD', permission='plone.ModifyContent',
                   name='@tusupload')
class TusHeadFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_head()


@configure.service(context=IResource, method='PATCH', permission='plone.ModifyContent',
                   name='@tusupload')
class TusPatchFile(UploadFile):

    async def __call__(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_patch()


@configure.service(context=IResource, method='OPTIONS', permission='plone.AccessPreflight',
                   name='@tusupload')
class TusOptionsFile(DefaultOPTIONS, UploadFile):

    async def render(self):
        # We need to get the upload as async IO and look for an adapter
        # for the field to save there by chunks
        adapter = getMultiAdapter(
            (self.context, self.request, self.field), IFileManager)
        return await adapter.tus_options()
