"""Temporary one-time helper controls; no credential or network access."""

import contextlib
import io
import json
from pathlib import Path
import textwrap
import unittest
from unittest import mock
import urllib.error


WORKFLOW = Path(__file__).resolve().parents[1] / 'workflows/sonar-visibility-setup.yml'


class VisibilityTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')
        code = self.text.split('          # BEGIN SONAR_VISIBILITY\n')[1].split('          # END SONAR_VISIBILITY')[0]
        self.ns = {'__name__': 'offline_test'}
        exec(compile(textwrap.dedent(code), str(WORKFLOW), 'exec'), self.ns)
        self.token = 'planted-secret-value'

    def component(self, visibility='private', **changes):
        return {'component': {'key': 'spatial-typestate', 'organization': 'telemetryworks',
                              'qualifier': 'TRK', 'visibility': visibility, **changes}}

    def test_private_only_mutation_and_public_verification(self):
        call = mock.Mock(side_effect=[(200, self.component()), (204, None),
                                     (200, self.component('public')), (200, self.component('public'))])
        result = self.ns['setup'](call, self.token)
        self.assertEqual(call.call_args_list, [mock.call('GET', '/api/components/show', self.token),
                         mock.call('POST', '/api/projects/update_visibility', self.token),
                         mock.call('GET', '/api/components/show', self.token),
                         mock.call('GET', '/api/components/show', None)])
        self.assertEqual(result['action'], 'set public')
        self.assertNotIn(self.token, json.dumps(result))

    def test_public_never_posts(self):
        call = mock.Mock(return_value=(200, self.component('public')))
        self.assertEqual(self.ns['setup'](call, self.token)['action'], 'already public; no mutation')
        self.assertTrue(all(args.args[0] == 'GET' for args in call.call_args_list))

    def test_identity_and_visibility_mismatch_never_posts_or_echoes(self):
        for changes in ({'key': self.token}, {'organization': 'other'}, {'visibility': None}, {'qualifier': 'FIL'}):
            call = mock.Mock(return_value=(200, self.component(**changes)))
            with self.assertRaises(RuntimeError) as error:
                self.ns['setup'](call, self.token)
            self.assertEqual(call.call_count, 1)
            self.assertNotIn(self.token, str(error.exception))

    def test_redirect_foreign_host_and_unapproved_method_rejected(self):
        for endpoint in ('https://evil.invalid/api/components/show', '/api/settings/values', '//evil.invalid'):
            with self.assertRaises(RuntimeError):
                self.ns['request']('GET', endpoint, self.token)
        with self.assertRaises(RuntimeError):
            self.ns['request']('PUT', '/api/projects/update_visibility', self.token)
        with self.assertRaises(RuntimeError):
            self.ns['NoRedirect']().redirect_request(None, None, 302, '', {}, 'https://evil.invalid')

    def test_permission_errors_never_echo_headers_or_body(self):
        for status in (401, 403, 302, 500):
            error = urllib.error.HTTPError('https://sonarcloud.io', status, self.token,
                                            {'Authorization': self.token}, io.BytesIO(self.token.encode()))
            opener = mock.Mock()
            opener.open.side_effect = error
            stream = io.StringIO()
            with mock.patch('urllib.request.build_opener', return_value=opener), contextlib.redirect_stdout(stream):
                with self.assertRaises(RuntimeError) as raised:
                    self.ns['request']('GET', '/api/components/show', self.token)
            self.assertNotIn(self.token, str(raised.exception) + stream.getvalue())
            if status in (401, 403):
                self.assertIn('grant Project administer', str(raised.exception))

    def test_fixed_requests_empty_proxy_certificate_defaults_size_and_timeout(self):
        opener = mock.MagicMock()
        response = opener.open.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = json.dumps(self.component('public')).encode()
        with mock.patch('urllib.request.build_opener', return_value=opener) as build:
            self.ns['request']('GET', '/api/components/show', self.token)
            self.assertEqual(build.call_args.args[0].proxies, {})
            req = opener.open.call_args.args[0]
            self.assertEqual(req.full_url, 'https://sonarcloud.io/api/components/show?component=spatial-typestate')
            self.assertEqual(opener.open.call_args.kwargs['timeout'], 30)
            response.read.assert_called_with(1024 * 1024 + 1)
        response.read.return_value = b'x' * (1024 * 1024 + 1)
        with mock.patch('urllib.request.build_opener', return_value=opener), self.assertRaises(RuntimeError):
            self.ns['request']('GET', '/api/components/show', self.token)

    def test_explicit_one_time_guard_and_no_repository_execution(self):
        self.assertIn('github.event.number == 10', self.text)
        self.assertIn("vars.SONAR_VISIBILITY_SETUP == 'pr-10-once'", self.text)
        self.assertIn('github.event.pull_request.head.repo.full_name == github.repository', self.text)
        self.assertIn("github.event.pull_request.user.login != 'dependabot[bot]'", self.text)
        self.assertIn('shell: python3 -I {0}', self.text)
        self.assertNotIn('checkout', self.text)
        self.assertNotIn('workflow_dispatch:', self.text)
        self.assertEqual(self.text.count('secrets.SONAR_TOKEN'), 1)


if __name__ == '__main__':
    unittest.main()
