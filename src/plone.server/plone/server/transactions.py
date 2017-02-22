# -*- coding: utf-8 -*-
"""
Insane experimental library for running multiple concurrent transactions
on a single ZODB connection. This should not be possible to do safely, but
we'll see how far we get and learn more about ZODB while doing it...
"""
from concurrent.futures import ThreadPoolExecutor
from plone.server.interfaces import SHARED_CONNECTION
from plone.server.utils import get_authenticated_user_id
from plone.server.exceptions import RequestNotFound
from transaction._manager import _new_transaction
from transaction.interfaces import ISavepoint
from transaction.interfaces import ISavepointDataManager
from zope.interface import implementer
from zope.proxy import ProxyBase
from zope.security.interfaces import Unauthorized

import asyncio
import inspect
import threading
import time
import transaction
import ZODB.Connection


try:
    from aiohttp.web_server import RequestHandler
except ImportError:
    from aiohttp.web import RequestHandler


ASYNCIO_LOCKS = {}


class RequestAwareTransactionManager(transaction.TransactionManager):
    """Transaction manager for storing the managed transaction in the
    current request

    """
    # ITransactionManager
    def begin(self, request=None):
        """Return new request specific transaction

        :param request: current request

        """
        if request is None:
            request = get_current_request()

        user = get_authenticated_user_id(request)
        txn = getattr(request, '_txn', None)
        if txn is not None:
            txn.abort()
        txn = request._txn = transaction.Transaction(self._synchs, self)
        if user is not None:
            txn.user = user
        _new_transaction(txn, self._synchs)
        request._txn_time = time.time()

        return txn

    # with
    def __enter__(self):
        raise NotImplementedError()

    def __exit__(self, type_, value, traceback):
        raise NotImplementedError()

    # async with
    async def __aenter__(self):
        return self.begin(get_current_request())

    async def __aexit__(self, type_, value, traceback):
        request = get_current_request()
        txn = self.get(request)
        if value is None:
            await commit(txn, request)
        else:
            await abort(txn, request)

    async def commit(self, request=None):
        """ See ITransactionManager.
        """
        if request is None:
            request = get_current_request()
        txn = self.get(request)
        return await commit(txn, request)

    async def abort(self, request=None):
        """ See ITransactionManager.
        """
        if request is None:
            request = get_current_request()
        txn = self.get(request)
        return await abort(txn, request)

    # ITransactionManager
    def get(self, request=None):
        """Return the current request specific transaction

        :param request: current request

        """
        if request is None:
            request = get_current_request()

        if getattr(request, '_txn', None) is None:
            request._txn = transaction.Transaction(self._synchs, self)
            request._txn_time = time.time()
        return request._txn

    # ITransactionManager
    def free(self, txn):
        pass

    def __call__(self, request):
        return RequestBoundTransactionManagerContextManager(self, request)


class RequestBoundTransactionManagerContextManager(object):
    def __init__(self, tm, request):
        assert isinstance(tm, RequestAwareTransactionManager)
        self.tm = tm
        self.request = request

    # with
    def __enter__(self):
        raise NotImplementedError()

    def __exit__(self, type_, value, traceback):
        raise NotImplementedError()

    # async with
    async def __aenter__(self):
        return self.tm.begin(self.request)

    async def __aexit__(self, type_, value, traceback):
        request = self.request
        txn = self.tm.get(request)
        if value is None:
            await commit(txn, request)
        else:
            await abort(txn, request)


@implementer(ISavepointDataManager)
class RequestDataManager(object):
    """Transaction data manager separate from the ZODB connection, but
    still allowing only a single concurrent transaction to be committed
    at time

    """
    def __init__(self, request, connection):
        self.request = request
        self.connection = connection
        self._registered_objects = []
        self._savepoint_storage = None

    @property
    def txn_manager(self):
        return self.connection.transaction_manager

    def abort(self, txn):
        with self.connection.lock:  # Conn can only abort one txn at time
            self.connection._registered_objects = self._registered_objects
            self.connection._savepoint_storage = self._savepoint_storage
            self.connection.abort(txn)
        self._registered_objects = []
        self._savepoint_storage = None
        try:
            delattr(self.request, '_txn_dm')
        except AttributeError:
            # There was no object registered so there is no _txn_dm
            pass

    def tpc_begin(self, txn):
        self.connection._registered_objects = self._registered_objects
        self.connection._savepoint_storage = self._savepoint_storage
        return self.connection.tpc_begin(txn)

    def commit(self, txn):
        with self.connection.lock:  # Conn can only commit one txn at time
            self.connection.commit(txn)
        try:
            delattr(self.request, '_txn_dm')
        except AttributeError:
            # There was no object registered so there is no _txn_dm
            pass

    def tpc_vote(self, txn):
        self.connection.tpc_vote(txn)

    def tpc_finish(self, txn):
        self.connection.tpc_finish(txn)
        self._registered_objects = []
        self._savepoint_storage = None

    def tpc_abort(self, txn):
        self.connection.tpc_abort(txn)
        self._registered_objects = []
        self._savepoint_storage = None

    def sortKey(self):
        return self.connection.sortKey()

    def savepoint(self):
        self.connection._registered_objects = self._registered_objects
        self.connection._savepoint_storage = self._savepoint_storage
        savepoint = self.connection.savepoint()
        self._registered_objects = []
        self._savepoint_storage = None
        return savepoint


class RequestAwareConnection(ZODB.Connection.Connection):
    lock = threading.Lock()

    def _getReadCurrent(self):
        try:
            request = get_current_request()
        except RequestNotFound:
            return dict()
        try:
            return request._txn_readCurrent
        except AttributeError:
            request._txn_readCurrent = {}
            return request._txn_readCurrent

    def _setReadCurrent(self, value):
        try:
            request = get_current_request()
        except RequestNotFound:
            return
        request._txn_readCurrent = value

    _readCurrent = property(_getReadCurrent, _setReadCurrent)

    def _register(self, obj=None):
        request = get_current_request()
        if hasattr(request, '_db_write_enabled') and not request._db_write_enabled:
            raise Unauthorized('Adding content not permited')

        try:
            assert request._txn_dm is not None
        except (AssertionError, AttributeError):
            if not SHARED_CONNECTION and hasattr(request, 'conn'):
                request._txn_dm = request.conn
            else:
                request._txn_dm = RequestDataManager(request, self)
            self.transaction_manager.get(request).join(request._txn_dm)

        if obj is not None:
            request._txn_dm._registered_objects.append(obj)


class RequestAwareDB(ZODB.DB):
    klass = RequestAwareConnection


class TransactionProxy(ProxyBase):
    __slots__ = ('_wrapped',
                 '_txn', '_txn_time', '_txn_dm', '_txn_readCurrent')

    def __init__(self, obj):
        super(TransactionProxy, self).__init__(obj)
        self._txn = None
        self._txn_time = None
        self._txn_dm = None
        self._txn_readCurrent = {}


@implementer(ISavepoint)
class DummySavepoint:
    valid = property(lambda self: self.transaction is not None)

    def __init__(self, datamanager):
        self.datamanager = datamanager

    def rollback(self):
        pass


@implementer(ISavepointDataManager)
class CallbackTransactionDataManager(object):

    def __init__(self, callback, *args, **kwargs):
        self.callback = lambda: callback(*args, **kwargs)

    def commit(self, t):
        pass

    def sortKey(self):
        return '~'  # sort after connections

    def abort(self, t):
        pass

    def tpc_begin(self, t):
        pass

    def tpc_vote(self, t):
        pass

    def tpc_finish(self, t):
        self.callback()

    def tpc_abort(self, t):
        pass

    def savepoint(self):
        return DummySavepoint(self)


# Utility functions

def locked(obj):
    """Return object specfic volatile asyncio lock.

    This is used together with "with" syntax to asynchronously lock
    objects while they are mutated to prevent other concurrent requests
    accessing the object by accident.

    :param obj: object to be locked

    Example::

        with locked(ob):

            # do something

    """
    try:
        return ASYNCIO_LOCKS.get(obj._p_oid) or \
            ASYNCIO_LOCKS.setdefault(obj._p_oid, asyncio.Lock())
    except AttributeError:  # obj has no _p_oid
        return ASYNCIO_LOCKS.get(id(obj)) or \
            ASYNCIO_LOCKS.setdefault(id(obj), asyncio.Lock())


def tm(request):
    """Return shared transaction manager (from request)

    This is used together with "with" syntax for wrapping mutating
    code into a request owned transaction.

    :param request: request owning the transaction

    Example::

        with tm(request) as txn:  # begin transaction txn

            # do something

        # transaction txn commits or raises ConflictError

    """
    assert getattr(request, 'conn', None) is not None, \
        'Request has no conn'
    return request.conn.transaction_manager


async def commit(txn, request):
    if asyncio.iscoroutinefunction(txn.commit):
        await txn.commit()
    elif SHARED_CONNECTION is False:
        await txn.acommit()
    else:
        await sync(request)(txn.commit)


async def abort(txn, request):
    if asyncio.iscoroutinefunction(txn.abort):
        await txn.abort()
    elif SHARED_CONNECTION is False:
        txn.abort()
    else:
        await sync(request)(txn.abort)


def sync(request):
    """Return connections asyncio executor instance (from request) to be used
    together with "await" syntax to queue or commit to be executed in
    series in a dedicated thread.

    :param request: current request

    Example::

        await sync(request)(txn.commit)

    """
    assert getattr(request, 'conn', None) is not None, \
        'Request has no conn'
    assert getattr(request.conn, 'executor', None) is not None, \
        'Connection has no executor'
    return lambda *args, **kwargs: request.app.loop.run_in_executor(
        request.conn.executor, *args, **kwargs)


def get_current_request():
    """Return the current request by heuristically looking it up from stack
    """
    frame = inspect.currentframe()
    while frame is not None:
        request = getattr(frame.f_locals.get('self'), 'request', None)
        if request is not None:
            return request
        elif isinstance(frame.f_locals.get('self'), RequestHandler):
            return frame.f_locals['request']
        # if isinstance(frame.f_locals.get('self'), RequestHandler):
        #     return frame.f_locals.get('self').request
        # elif IView.providedBy(frame.f_locals.get('self')):
        #     return frame.f_locals['request']
        frame = frame.f_back
    raise RequestNotFound(RequestNotFound.__doc__)


try:
    import plone.server.optimizations  # noqa
except (ImportError, AttributeError):  # pragma NO COVER PyPy / PURE_PYTHON
    pass
else:
    from plone.server.optimizations import get_current_request  # noqa


def synccontext(context):
    """Return connections asyncio executor instance (from context) to be used
    together with "await" syntax to queue or commit to be executed in
    series in a dedicated thread.

    :param request: current request

    Example::

        await synccontext(request)(txn.commit)

    """
    loop = asyncio.get_event_loop()
    assert getattr(context, '_p_jar', None) is not None, \
        'Request has no conn'
    assert getattr(context._p_jar, 'executor', None) is not None, \
        'Connection has no executor'
    return lambda *args, **kwargs: loop.run_in_executor(
        context._p_jar.executor, *args, **kwargs)
