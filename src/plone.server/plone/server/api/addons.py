# -*- coding: utf-8 -*-
from plone.server import _
from plone.server import AVAILABLE_ADDONS
from plone.server.api.service import Service
from plone.server.browser import ErrorResponse
from plone.server.config import IAddons


class Install(Service):
    async def __call__(self):
        data = await self.request.json()
        id_to_install = data.get('id', None)
        if id_to_install not in AVAILABLE_ADDONS:
            return ErrorResponse(
                'RequiredParam',
                _("Property 'id' is required to be valid"))

        registry = self.request.site_settings
        config = registry.forInterface(IAddons)

        if id_to_install in config.enabled:
            return ErrorResponse(
                'Duplicate',
                _("Addon already installed"))
        handler = AVAILABLE_ADDONS[id_to_install]['handler']
        handler.install(self.request)
        config.enabled |= {id_to_install}


class Uninstall(Service):
    async def __call__(self):
        data = await self.request.json()
        id_to_install = data.get('id', None)
        if id_to_install not in AVAILABLE_ADDONS:
            return ErrorResponse(
                'RequiredParam',
                _("Property 'id' is required to be valid"))

        registry = self.request.site_settings
        config = registry.forInterface(IAddons)

        if id_to_install not in config.enabled:
            return ErrorResponse(
                'Duplicate',
                _("Addon not installed"))

        handler = AVAILABLE_ADDONS[id_to_install]['handler']
        handler.uninstall(self.request)
        config.enabled -= {id_to_install}


class getAddons(Service):
    async def __call__(self):
        result = {
            'available': [],
            'installed': []
        }
        for key, addon in AVAILABLE_ADDONS.items():
            result['available'].append({
                'id': key,
                'title': addon['title']
            })

        registry = self.request.site_settings
        config = registry.forInterface(IAddons)

        for installed in config.enabled:
            result['installed'].append(installed)
        return result
