from plone.server import utils
from plone.server.testing import FakeRequest
from plone.server.transactions import get_current_request

import gc
import resource


def test_module_resolve_path():
    assert utils.resolve_module_path('plone.server') == 'plone.server'
    assert utils.resolve_module_path('plone.server.tests') == 'plone.server.tests'
    assert utils.resolve_module_path('..test_queue') == 'plone.server.tests.test_queue'
    assert utils.resolve_module_path('....api') == 'plone.server.api'


class TestGetCurrentRequest:
    def test_gcr_memory(self):
        self.request = FakeRequest()

        count = 0
        current = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0
        while True:
            count += 1
            get_current_request()

            if count % 1000000 == 0:
                break

            if count % 100000 == 0:
                gc.collect()
                new = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0 / 1024.0
                if new - current > 10:  # memory leak, this shouldn't happen
                    assert new == current
