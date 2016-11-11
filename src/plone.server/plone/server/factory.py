# -*- coding: utf-8 -*-
from aiohttp import web
from datetime import datetime
from datetime import timedelta
from pkg_resources import iter_entry_points
from plone.server import DICT_LANGUAGES
from plone.server import DICT_RENDERS
from plone.server import jose
from plone.server.async import IAsyncUtility
from plone.server.auth.participation import RootParticipation
from plone.server.types import IStaticDirectory
from plone.server.types import IStaticFile
from plone.server.types import StaticFile
from plone.server.contentnegotiation import ContentNegotiatorUtility
from plone.server.interfaces import IApplication
from plone.server.interfaces import IContentNegotiation
from plone.server.interfaces import IDataBase
from plone.server.transactions import RequestAwareDB
from plone.server.transactions import RequestAwareTransactionManager
from plone.server.traversal import TraversalRouter
from plone.server.utils import import_class
from ZEO.ClientStorage import ClientStorage
from ZODB import DB
from ZODB.DemoStorage import DemoStorage
from zope.component import getAllUtilitiesRegisteredFor
from zope.component import getGlobalSiteManager
from zope.component import getUtility
from zope.component import provideUtility
from zope.configuration.config import ConfigurationConflictError
from zope.configuration.config import ConfigurationMachine
from zope.configuration.xmlconfig import include
from zope.configuration.xmlconfig import registerCommonDirectives
from zope.interface import implementer
from zope.securitypolicy.principalpermission import PrincipalPermissionManager

import asyncio
import base64
import json
import logging
import sys
import ZODB.FileStorage


try:
    from Crypto.PublicKey import RSA
except ImportError:
    RSA = None

logger = logging.getLogger(__name__)


@implementer(IApplication)
class ApplicationRoot(object):

    def __init__(self, config_file):
        self._dbs = {}
        self._config_file = config_file
        self._async_utilities = {}
        self._websockets_ttl = 60

    def add_async_utility(self, config):
        interface = import_class(config['provides'])
        factory = import_class(config['factory'])
        utility_object = factory(config['settings'])
        provideUtility(utility_object, interface)
        task = asyncio.ensure_future(utility_object.initialize(app=self))
        self.add_async_task(config['provides'], task, config)

    def add_async_task(self, ident, task, config):
        if ident in self._async_utilities:
            raise KeyError("Already exist an async utility with this id")
        self._async_utilities[ident] = {
            'task': task,
            'config': config
        }

    def cancel_async_utility(self, ident):
        if ident in self._async_utilities:
            self._async_utilities[ident]['task'].cancel()
        else:
            raise KeyError("Ident does not exist as utility")

    def del_async_utility(self, config):
        self.cancel_async_utility(config['provides'])
        interface = import_class(config['provides'])
        utility = getUtility(interface)
        gsm = getGlobalSiteManager()
        gsm.unregisterUtility(utility, provided=interface)

    def set_creator_password(self, password):
        self._creator_password = base64.b64decode(password)

    def set_priv_key(self, key):
        self._websockets_priv_key = key

    def set_pub_key(self, key):
        self._websockets_pub_key = key

    def generate_websocket_token(self, real_token):
        exp = datetime.utcnow() + timedelta(
            seconds=self._websockets_ttl)

        claims = {
            'iat': int(datetime.utcnow().timestamp()),
            'exp': int(exp.timestamp()),
            'token': real_token
        }
        jwe = jose.encrypt(claims, self._websockets_pub_key)
        token = jose.serialize_compact(jwe)
        return token.decode('utf-8')

    def extract_websocket_token(self, jwt_token):
        jwt = jose.decrypt(
            jose.deserialize_compact(jwt_token), self._websockets_priv_key)
        return jwt.claims['token']

    def check_token(self, password):
        if self._creator_password == base64.b64decode(password):
            return True
        else:
            return False

    def root_participation(self, request):
        header_auth = request.headers.get('AUTHORIZATION')
        token = None
        if header_auth is not None:
            schema, _, encoded_token = header_auth.partition(' ')
            if schema.lower() == 'basic' or schema.lower() == 'bearer':
                token = encoded_token.encode('ascii')

        if 'ws_token' in request.GET:
            token = self.extract_websocket_token(request.GET['ws_token'].encode('utf-8'))

        if token and self.check_token(token):
            return RootParticipation(request)
        return None

    def __contains__(self, key):
        return True if key in self._dbs else False

    def __len__(self):
        return len(self._dbs)

    def __getitem__(self, key):
        return self._dbs[key]

    def __delitem__(self, key):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """

        del self._dbs[key]

    def __iter__(self):
        return iter(self._dbs.items())

    def __setitem__(self, key, value):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """

        self._dbs[key] = value


class DataBaseToJson(object):

    def __init__(self, dbo, request):
        self.dbo = dbo

    def __call__(self):
        return {
            'sites': self.dbo.keys()
        }


class ApplicationToJson(object):

    def __init__(self, application, request):
        self.application = application
        self.request = request

    def __call__(self):
        result = {
            'databases': [],
            'static_file': [],
            'static_directory': []
        }

        allowed = self.request.security.checkPermission(
            'plone.GetDatabases', self.application)

        for x in self.application._dbs.keys():
            if IDataBase.providedBy(self.application._dbs[x]) and allowed:
                result['databases'].append(x)
            if IStaticFile.providedBy(self.application._dbs[x]):
                result['static_file'].append(x)
            if IStaticDirectory.providedBy(self.application._dbs[x]):
                result['static_directory'].append(x)
        return result


class RootSpecialPermissions(PrincipalPermissionManager):
    """No Role Map on Application and DB so permissions set to users.

    It will not affect Plone sites as they don't have parent pointers to DB/APP
    """
    def __init__(self, db):
        super(RootSpecialPermissions, self).__init__()
        self.grantPermissionToPrincipal('plone.AddPortal', 'RootUser')
        self.grantPermissionToPrincipal('plone.GetPortals', 'RootUser')
        self.grantPermissionToPrincipal('plone.DeletePortals', 'RootUser')
        self.grantPermissionToPrincipal('plone.AccessContent', 'RootUser')
        self.grantPermissionToPrincipal('plone.GetDatabases', 'RootUser')
        self.grantPermissionToPrincipal('plone.GetAPIDefinition', 'RootUser')
        # Access anonymous - needs to be configurable
        self.grantPermissionToPrincipal(
            'plone.AccessContent', 'Anonymous User')


@implementer(IDataBase)
class DataBase(object):
    def __init__(self, id, db):
        self.id = id
        self._db = db
        self._conn = None
        self.tm_ = RequestAwareTransactionManager()

    def open(self):
        tm_ = RequestAwareTransactionManager()
        return self._db.open(transaction_manager=self.tm_)

    def _open(self):
        self._conn = self._db.open(transaction_manager=self.tm_)

        @self._conn.onCloseCallback
        def on_close():
            self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._open()
        return self._conn

    @property
    def _p_jar(self):
        if self._conn is None:
            self._open()
        return self._conn

    def __getitem__(self, key):
        # is there any request active ? -> conn there
        return self.conn.root()[key]

    def keys(self):
        return list(self.conn.root().keys())

    def __setitem__(self, key, value):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """
        self.conn.root()[key] = value

    def __delitem__(self, key):
        """ This operation can only be done throw HTTP request

        We can check if there is permission to delete a site
        XXX TODO
        """

        del self.conn.root()[key]

    def __iter__(self):
        return iter(self.conn.root().items())

    def __contains__(self, key):
        # is there any request active ? -> conn there
        return key in self.conn.root()

    def __len__(self):
        return len(self.conn.root())


def make_app(config_file=None, settings=None):
    # Initialize aiohttp app
    app = web.Application(router=TraversalRouter())

    if config_file is not None:
        with open(config_file, 'r') as config:
            settings = json.load(config)
    elif settings is not None:
        settings = settings
    else:
        raise Exception('Neither configuration or settings')

    # Create root Application
    root = ApplicationRoot(config_file)
    root.app = app
    provideUtility(root, IApplication, 'root')

    # Initialize global (threadlocal) ZCA configuration
    app.config = ConfigurationMachine()
    registerCommonDirectives(app.config)

    include(app.config, 'configure.zcml', sys.modules['plone.server'])
    for ep in iter_entry_points('plone.server'):  # auto-include applications
        include(app.config, 'configure.zcml', ep.load())
    try:
        app.config.execute_actions()
    except ConfigurationConflictError as e:
        logger.error(str(e._conflicts))
        raise e

    content_type = ContentNegotiatorUtility('content_type', DICT_RENDERS.keys())
    language = ContentNegotiatorUtility('language', DICT_LANGUAGES.keys())

    provideUtility(content_type, IContentNegotiation, 'content_type')
    provideUtility(language, IContentNegotiation, 'language')

    for database in settings['databases']:
        for key, dbconfig in database.items():
            config = dbconfig.get('configuration', {})
            if dbconfig['storage'] == 'ZODB':
                # Open it not Request Aware so it creates the root object
                fs = ZODB.FileStorage.FileStorage(dbconfig['path'])

                db = DB(fs)
                db.close()
                # Set request aware database for app
                db = RequestAwareDB(dbconfig['path'], **config)
                dbo = DataBase(key, db)
            elif dbconfig['storage'] == 'ZEO':
                # Try to open it normal to create the root object
                address = (dbconfig['address'], dbconfig['port'])

                cs = ClientStorage(address)
                db = DB(cs)
                db.close()

                # Set request aware database for app
                cs = ClientStorage(address)
                db = RequestAwareDB(cs, **config)
                dbo = DataBase(key, db)
            elif dbconfig['storage'] == 'DEMO':
                storage = DemoStorage(name=dbconfig['name'])
                db = DB(storage)
                db.close()
                # Set request aware database for app
                db = RequestAwareDB(storage)
                dbo = DataBase(key, db)
            root[key] = dbo

    for static in settings['static']:
        for key, file_path in static.items():
            root[key] = StaticFile(file_path)

    root.set_creator_password(settings['creator']['password'])

    if RSA is not None:
        key = RSA.generate(2048)
        pub_jwk = {'k': key.publickey().exportKey('PEM')}
        priv_jwk = {'k': key.exportKey('PEM')}
        root.set_priv_key(priv_jwk)
        root.set_pub_key(pub_jwk)

    # Set router root from the ZODB connection
    app.router.set_root(root)

    for utility in getAllUtilitiesRegisteredFor(IAsyncUtility):
        # In case there is Utilties that are registered from zcml
        ident = asyncio.ensure_future(utility.initialize(app=app), loop=app.loop)
        root.add_async_utility(ident, {})

    for util in settings['utilities']:
        root.add_async_utility(util)

    return app
