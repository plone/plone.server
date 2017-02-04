# -*- coding: utf-8 -*-
from plone.server.behaviors.attachment import IAttachment
from plone.server.testing import PloneFunctionalTestCase
from plone.server.tests import TEST_RESOURCES_DIR
from zope import schema
from zope.interface import Interface

import json
import os


class FunctionalTestServer(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def _get_site(self):
        """
        sometimes the site does not get updated data from zodb
        this seems to make it
        """
        return self.layer.new_root()['plone']

    def test_get_plone(self):
        """Get the root plone site."""
        resp = self.layer.requester('GET', '/plone/plone/@sharing')
        response = json.loads(resp.text)
        self.assertTrue(response['local']['prinrole']['plone.SiteAdmin']['root'] == 'Allow')
        self.assertTrue(response['local']['prinrole']['plone.Owner']['root'] == 'Allow')

