from __future__ import absolute_import

import unittest
import json
import mock

from tests.integration import flask_setup


class BaseTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        super(BaseTest, cls).setUpClass()
        flask_setup.setupApp()

    def setUp(self) -> None:
        self.test_client = flask_setup.API_APP.app.test_client()
        flask_setup.cleanSite()


class TestAPI(BaseTest):
    def test_get_root(self):
        resp = self.test_client.get('/')
        self.assertEqual(404, resp.status_code)

    def test_get_transactions(self):
        resp = self.test_client.get('/transactions')
        self.assertEqual(200, resp.status_code)
        self.assertEqual({'transactions': []}, resp.json)

    def test_get_transaction_not_found(self):
        resp = self.test_client.get('/transactions/029acf00-bc04-4ffa-ae02-323778c6463f')
        self.assertEqual(404, resp.status_code)
        self.assertEqual({'error': {'message': 'Resource not found'}}, resp.json)

    @unittest.skip("Not validating payload proply")
    def test_post_bad_payload(self):
        payload = {}
        resp = self.test_client.post('/transactions',
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload))

        self.assertEqual(400, resp.status_code)
        self.assertEqual({}, resp.json)

    def test_post_and_get_transaction(self):
        payload = {
            'transaction': {
                'name': 'test',
                'username': 'usernanme_test',
                'password': 'fake_password',
                'status': 'new'
            }}
        expected_response = {
            'transaction': {
                'id': mock.ANY,
                'name': 'test',
                'username': 'usernanme_test',
                'password': 'fake_password',
                'status': 'new'
            }}
        resp = self.test_client.post('/transactions',
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload))

        self.assertEqual(201, resp.status_code)
        self.assertEqual(expected_response, resp.json)

    @unittest.skip("ReadOnly and WriteOnly not being honored")
    def test_get_and_get_transaction_read_only(self):
        payload = {
            'transaction': {
                'name': 'test',
                'username': 'usernanme_test',
                'password': 'fake_password',
                'status': 'new'
            }}
        expected_response = {
            'transaction': {
                'id': mock.ANY,
                'name': 'test',
                'username': 'usernanme_test',
            }}
        resp = self.test_client.post('/transactions',
                                     headers={'Content-Type': 'application/json'},
                                     data=json.dumps(payload))

        self.assertEqual(201, resp.status_code)
        self.assertEqual(expected_response, resp.json)
