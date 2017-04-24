# -*- coding: utf-8 -*-
from aiohttp import web
from plone.server.api.service import Service

import aiohttp
import logging


logger = logging.getLogger(__name__)


class WebsocketsView(Service):
    async def __call__(self):
        ws = web.WebSocketResponse()
        await ws.prepare(self.request)

        async for msg in ws:
            if msg.tp == aiohttp.WSMsgType.text:
                if msg.data == 'close':
                    await ws.close()
                else:
                    ws.send_str(msg.data + '/answer')
            elif msg.tp == aiohttp.WSMsgType.error:
                logger.debug('ws connection closed with exception {0:s}'
                             .format(ws.exception()))

        logger.debug('websocket connection closed')

        return {}
