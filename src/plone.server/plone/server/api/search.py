# -*- coding: utf-8 -*-
from plone.server import configure
from plone.server.api.service import Service
from plone.server.interfaces import ICatalogUtility
from plone.server.interfaces import IResource
from zope.component import queryUtility
from plone.server.utils import get_content_path
from plone.server.async import IQueueUtility


@configure.service(context=IResource, method='GET', permission='plone.SearchContent',
                   name='@search')
async def search_get(context, request):
    q = request.GET.get('q')
    search = queryUtility(ICatalogUtility)
    if search is None:
        return {
            'items_count': 0,
            'member': []
        }

    return await search.get_by_path(
        site=request.site,
        path=get_content_path(context),
        query=q)


@configure.service(context=IResource, method='POST', permission='plone.RawSearchContent',
                   name='@search')
async def search_post(context, request):
    q = await request.json()
    search = queryUtility(ICatalogUtility)
    if search is None:
        return {
            'items_count': 0,
            'member': []
        }

    return await search.query(context, q)


@configure.service(context=IResource, method='POST', permission='plone.ReindexContent',
                   name='@catalog-reindex')
class CatalogReindex(Service):

    def __init__(self, context, request, security=False):
        super(CatalogReindex, self).__init__(context, request)
        self._security_reindex = security

    async def __call__(self):
        search = queryUtility(ICatalogUtility)
        await search.reindex_all_content(self.context, self._security_reindex)
        return {}


@configure.service(context=IResource, method='POST', permission='plone.ReindexContent',
                   name='@async-catalog-reindex')
class AsyncCatalogReindex(Service):

    def __init__(self, context, request, security=False):
        super(AsyncCatalogReindex, self).__init__(context, request)
        self._security_reindex = security

    async def __call__(self):
        util = queryUtility(IQueueUtility)
        if util:
            await util.add(CatalogReindex(
                self.context, self.request, self._security_reindex))
        return {}


@configure.service(context=IResource, method='POST', permission='plone.ManageCatalog',
                   name='@catalog')
async def catalog_post(context, request):
    search = queryUtility(ICatalogUtility)
    await search.initialize_catalog(context)
    return {}


@configure.service(context=IResource, method='DELETE', permission='plone.ManageCatalog',
                   name='@catalog')
async def catalog_delete(context, request):
    search = queryUtility(ICatalogUtility)
    await search.remove_catalog(context)
    return {}
