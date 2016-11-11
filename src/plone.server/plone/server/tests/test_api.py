# -*- coding: utf-8 -*-
from plone.server.testing import PloneFunctionalTestCase
from plone.server.tests import TEST_RESOURCES_DIR

import json
import os


class FunctionalTestServer(PloneFunctionalTestCase):
    """Functional testing of the API REST."""

    def _get_site(self):
        """
        sometimes the site does not get updated data from zodb
        this seems to make it
        """
        return self.layer.app._dbs['plone']['plone']

    def test_get_root(self):
        """Get the application root."""
        resp = self.layer.requester('GET', '/')
        response = json.loads(resp.text)
        self.assertEqual(response['static_file'], ['favicon.ico'])
        self.assertEqual(response['databases'], ['plone'])

    def test_get_database(self):
        """Get the database object."""
        resp = self.layer.requester('GET', '/plone')
        response = json.loads(resp.text)
        self.assertTrue(len(response['sites']) == 1)

    def test_get_plone(self):
        """Get the root plone site."""
        resp = self.layer.requester('GET', '/plone/plone')
        response = json.loads(resp.text)
        self.assertTrue(len(response['items']) == 0)

    def test_get_contenttypes(self):
        """Check list of content types."""
        resp = self.layer.requester('GET', '/plone/plone/@types')
        self.assertTrue(resp.status_code == 200)
        response = json.loads(resp.text)
        self.assertTrue(len(response) > 1)
        self.assertTrue(any("Item" in s['title'] for s in response))
        self.assertTrue(any("Plone Site" in s['title'] for s in response))

    def test_get_contenttype(self):
        """Get a content type definition."""
        resp = self.layer.requester('GET', '/plone/plone/@types/Item')
        self.assertTrue(resp.status_code == 200)
        response = json.loads(resp.text)
        self.assertTrue(len(response['schemas']), 2)
        self.assertTrue(response['title'] == 'Item')

    def test_get_registries(self):
        """Get the list of registries."""
        resp = self.layer.requester('GET', '/plone/plone/@registry')
        self.assertTrue(resp.status_code == 200)
        response = json.loads(resp.text)
        self.assertTrue(len(response) >= 10)
        self.assertTrue(
            'plone.server.config.ILayers.active_layers' in response)

    def test_get_registry(self):
        """Check a value from registry."""
        resp = self.layer.requester(
            'GET',
            '/plone/plone/@registry/plone.server.config.ICors.enabled')
        response = json.loads(resp.text)
        self.assertTrue(response[0])

    def test_create_contenttype(self):
        """Try to create a contenttype."""
        resp = self.layer.requester(
            'POST',
            '/plone/plone/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        self.assertTrue(resp.status_code == 201)

    def test_create_delete_contenttype(self):
        """Create and delete a content type."""
        resp = self.layer.requester(
            'POST',
            '/plone/plone/',
            data=json.dumps({
                "@type": "Item",
                "title": "Item1",
                "id": "item1"
            })
        )
        self.assertTrue(resp.status_code == 201)
        resp = self.layer.requester('DELETE', '/plone/plone/item1')
        self.assertTrue(resp.status_code == 200)

    def test_register_registry(self):
        """Try to create a contenttype."""
        resp = self.layer.requester(
            'POST',
            '/plone/plone/@registry',
            data=json.dumps({
                "interface": "plone.server.config.ICors"
            })
        )
        self.assertTrue(resp.status_code == 201)

    def test_update_registry(self):
        """Try to create a contenttype."""
        resp = self.layer.requester(
            'PATCH',
            '/plone/plone/@registry/plone.server.config.ICors.enabled',
            data=json.dumps({
                "value": False
            })
        )
        self.assertTrue(resp.status_code == 204)
        resp = self.layer.requester(
            'GET',
            '/plone/plone/@registry/plone.server.config.ICors.enabled')
        response = json.loads(resp.text)
        self.assertFalse(response[0])

    def test_file_upload(self):
        resp = self.layer.requester(
            'POST',
            '/plone/plone/',
            data=json.dumps({
                "@type": "File",
                "title": "File1",
                "id": "file1"
            })
        )
        self.assertTrue(resp.status_code == 201)
        site = self._get_site()
        self.assertTrue('file1' in site)
        fi = open(os.path.join(TEST_RESOURCES_DIR, 'plone.png'), 'rb')
        data = fi.read()
        fi.close()
        resp = self.layer.requester(
            'PATCH',
            '/plone/plone/file1/@upload/file',
            data=data)
        self.assertEqual(site['file1'].file.data, data)

    def test_file_download(self):
        # first, get a file on...
        self.test_file_upload()
        resp = self.layer.requester(
            'GET',
            '/plone/plone/file1/@download/file')
        site = self._get_site()
        self.assertEqual(site['file1'].file.data, resp.content)
