from plone.server import configuration
from transaction import interfaces
from transaction._compat import reraise
from transaction._transaction import Status
from transaction._transaction import Transaction
from zope.configuration import xmlconfig
from zope.interface import providedBy
from zope.interface.adapter import AdapterLookupBase
from zope.interface.adapter import BaseAdapterRegistry

import asyncio
import os
import sys


BaseAdapterRegistry._delegated = (
    'lookup', 'queryMultiAdapter', 'lookup1', 'queryAdapter',
    'adapter_hook', 'lookupAll', 'names',
    'subscriptions', 'subscribers', 'asubscribers')


async def asubscribers(self, objects, provided):
    subscriptions = self.subscriptions(map(providedBy, objects), provided)
    if provided is None:
        result = ()
        for subscription in subscriptions:
            if asyncio.iscoroutinefunction(subscription):
                await subscription(*objects)
    else:
        result = []
        for subscription in subscriptions:
            if asyncio.iscoroutinefunction(subscription):
                subscriber = await subscription(*objects)
            if subscriber is not None:
                result.append(subscriber)
    return result


def subscribers(self, objects, provided):
    subscriptions = self.subscriptions(map(providedBy, objects), provided)
    if provided is None:
        result = ()
        for subscription in subscriptions:
            if not asyncio.iscoroutinefunction(subscription):
                subscription(*objects)
    else:
        result = []
        for subscription in subscriptions:
            if not asyncio.iscoroutinefunction(subscription):
                subscriber = subscription(*objects)
            if subscriber is not None:
                result.append(subscriber)
    return result


AdapterLookupBase.asubscribers = asubscribers
AdapterLookupBase.subscribers = subscribers


async def acommit(self):
    """See ITransaction."""
    if self.status is Status.DOOMED:
        raise interfaces.DoomedTransaction(
            'transaction doomed, cannot commit')

    if self._savepoint2index:
        self._invalidate_all_savepoints()

    if self.status is Status.COMMITFAILED:
        self._prior_operation_failed()  # doesn't return

    await self._acallBeforeCommitHooks()

    self._synchronizers.map(lambda s: s.beforeCompletion(self))
    self.status = Status.COMMITTING

    try:
        self._commitResources()
        self.status = Status.COMMITTED
    except:
        t = None
        v = None
        tb = None
        try:
            t, v, tb = self._saveAndGetCommitishError()
            await self._acallAfterCommitHooks(status=False)
            reraise(t, v, tb)
        finally:
            del t, v, tb
    else:
        self._free()
        self._synchronizers.map(lambda s: s.afterCompletion(self))
        await self._acallAfterCommitHooks(status=True)
    self.log.debug("commit")


async def _acallBeforeCommitHooks(self):
    # Call all hooks registered, allowing further registrations
    # during processing.  Note that calls to addBeforeCommitHook() may
    # add additional hooks while hooks are running, and iterating over a
    # growing list is well-defined in Python.
    for hook, args, kws in self._before_commit:
        await hook(*args, **kws)
    self._before_commit = []


async def _acallAfterCommitHooks(self, status=True):
    # Avoid to abort anything at the end if no hooks are registred.
    if not self._after_commit:
        return
    # Call all hooks registered, allowing further registrations
    # during processing.  Note that calls to addAterCommitHook() may
    # add additional hooks while hooks are running, and iterating over a
    # growing list is well-defined in Python.
    for hook, args, kws in self._after_commit:
        # The first argument passed to the hook is a Boolean value,
        # true if the commit succeeded, or false if the commit aborted.
        try:
            await hook(status, *args, **kws)
        except:
            # We need to catch the exceptions if we want all hooks
            # to be called
            self.log.error("Error in after commit hook exec in %s ",
                           hook, exc_info=sys.exc_info())

    # The transaction is already committed. It must not have
    # further effects after the commit.
    for rm in self._resources:
        try:
            rm.abort(self)
        except:
            # XXX should we take further actions here ?
            self.log.error("Error in abort() on manager %s",
                           rm, exc_info=sys.exc_info())
    self._after_commit = []
    self._before_commit = []

Transaction._acallBeforeCommitHooks = _acallBeforeCommitHooks
Transaction.acommit = acommit
Transaction._acallAfterCommitHooks = _acallAfterCommitHooks


original_xmlconfig_processxmlfile = xmlconfig.processxmlfile
original_xmlconfig_include = xmlconfig.include


def xmlconfig_processxmlfile(file, context, testing=False):
    # patch to allow parsing json and hjson files
    if getattr(file, 'name', '<string>').lower().endswith('.hjson'):
        file = configuration.convert_json_to_zcml(file)
    return original_xmlconfig_processxmlfile(file, context, testing)
xmlconfig.processxmlfile = xmlconfig_processxmlfile


def xmlconfig_include(_context, file=None, package=None, files=None):
    if file is None and package is not None:
        package_dir = os.path.dirname(package.__file__)
        for filetype in ('.hjson', '.json', '.zcml'):
            filename = 'configure' + filetype
            if os.path.exists(os.path.join(package_dir, filename)):
                file = filename
                break
    return original_xmlconfig_include(_context, file, package, files)
xmlconfig.include = xmlconfig_include
