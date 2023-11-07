#!/usr/bin/env python
import sys
import base64
import unittest

sys.path.append('.')
from zabbix_utils.api import ZabbixAPI, ZabbixAPIVersion


class IntegrationAPITest(unittest.TestCase):
    """Test working with a real Zabbix API instance"""

    def setUp(self):
        self.url = 'https://127.0.0.1:443'
        self.user = 'Admin'
        self.password = 'zabbix'
        self.api = ZabbixAPI(
            url=self.url,
            user=self.user,
            password=self.password,
            skip_version_check=True,
            validate_certs=False,
            http_user='http_user',
            http_password='http_pass'
        )

    def tearDown(self):
        if self.api:
            self.api.logout()

    def test_login(self):
        """Tests login function works properly"""

        self.assertEqual(
            type(self.api), ZabbixAPI, "Login was going wrong")
        self.assertEqual(
            type(self.api.api_version()), ZabbixAPIVersion, "Version getting was going wrong")

    def test_basic_auth(self):
        """Tests basic_auth function works properly"""

        self.assertEqual(
            self.api.use_basic, True, "Basic auth was going wrong")
        self.assertEqual(
            self.api.basic_cred, base64.b64encode(
                "http_user:http_pass".encode()
        ).decode(), "Basic auth credentials generation was going wrong")

    def test_version_get(self):
        """Tests getting version info works properly"""

        version = None
        if self.api:
            version = self.api.apiinfo.version()
        self.assertEqual(
            version, str(self.api.api_version()), "Request apiinfo.version was going wrong")

    def test_check_auth(self):
        """Tests checking authentication state works properly"""

        resp = None
        if self.api:
            if self.api.session_id == self.api.token:
                resp = self.api.user.checkAuthentication(token=self.api.session_id)
            else:
                resp = self.api.user.checkAuthentication(sessionid=self.api.session_id)
        self.assertEqual(
            type(resp), dict, "Request user.checkAuthentication was going wrong")

    def test_user_get(self):
        """Tests getting users info works properly"""

        users = None
        if self.api:
            users = self.api.user.get(
                output=['userid', 'alias']
            )
        self.assertEqual(type(users), list, "Request user.get was going wrong")


if __name__ == '__main__':
    unittest.main()
