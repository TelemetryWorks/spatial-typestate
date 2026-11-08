"""Temporary one-time baseline controls; no network or credentials."""

import io
from pathlib import Path
import textwrap
import unittest
from unittest import mock
import urllib.error


WORKFLOW = Path(__file__).resolve().parents[1] / 'workflows/sonar-baseline-setup.yml'


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')
        code = self.text.split('          # BEGIN SONAR_BASELINE\n')[1].split('          # END SONAR_BASELINE')[0]
        self.ns = {'__name__': 'offline'}
        exec(compile(textwrap.dedent(code), str(WORKFLOW), 'exec'), self.ns)
        self.project = {'component': {'key': 'spatial-typestate', 'organization': 'telemetryworks',
                                     'qualifier': 'TRK', 'visibility': 'public'}}
        self.branches = {'branches': [{'name': 'main', 'isMain': True}]}
        self.target = {'settings': [{'key': key, 'value': value} for key, value in self.ns['TARGET'].items()]}

    def test_empty_definition_sets_exact_two_values_in_documented_order(self):
        call = mock.Mock(side_effect=[(200, self.project), (200, self.branches), (200, {'settings': []}),
                                     (204, None), (204, None), (200, self.target)])
        result = self.ns['setup'](call, 'planted-secret')
        self.assertEqual(call.call_args_list, [mock.call('GET', '/api/components/show', None),
                         mock.call('GET', '/api/project_branches/list', None),
                         mock.call('GET', '/api/settings/values', 'planted-secret'),
                         mock.call('POST', '/api/settings/set', 'planted-secret', 'sonar.leak.period'),
                         mock.call('POST', '/api/settings/set', 'planted-secret', 'sonar.leak.period.type'),
                         mock.call('GET', '/api/settings/values', 'planted-secret')])
        self.assertNotIn('planted-secret', str(result))
        self.assertEqual(result['baseline_date'], '2026-11-07')

    def test_exact_existing_values_never_post(self):
        call = mock.Mock(side_effect=[(200, self.project), (200, self.branches), (200, self.target), (200, self.target)])
        result = self.ns['setup'](call, 'secret')
        self.assertEqual(result['action'], 'already exact target; no mutation')
        self.assertTrue(all(c.args[0] == 'GET' for c in call.call_args_list))

    def test_foreign_or_partial_values_stop_without_overwrite_or_echo(self):
        for settings in ([{'key': 'sonar.leak.period', 'value': 'planted-secret'}],
                         [{'key': 'sonar.leak.period', 'value': '2026-11-07'}],
                         [{'key': 'other', 'value': 'planted-secret'}]):
            call = mock.Mock(side_effect=[(200, self.project), (200, self.branches), (200, {'settings': settings})])
            with self.assertRaises(RuntimeError) as error:
                self.ns['setup'](call, 'planted-secret')
            self.assertEqual(call.call_count, 3)
            self.assertNotIn('planted-secret', str(error.exception))

    def test_identity_and_main_branch_mismatches_stop_before_credentials(self):
        self.project['component']['organization'] = 'other'
        call = mock.Mock(return_value=(200, self.project))
        with self.assertRaises(RuntimeError):
            self.ns['setup'](call, 'secret')
        self.assertEqual(call.call_count, 1)
        self.project['component']['organization'] = 'telemetryworks'
        self.branches['branches'][0]['name'] = 'master'
        call = mock.Mock(side_effect=[(200, self.project), (200, self.branches)])
        with self.assertRaises(RuntimeError):
            self.ns['setup'](call, 'secret')
        self.assertEqual(call.call_count, 2)

    def test_http_permissions_redirect_and_foreign_endpoints_fail(self):
        opener = mock.Mock()
        for status in (401, 403, 302):
            opener.open.side_effect = urllib.error.HTTPError('https://sonarcloud.io', status, 'secret', {}, io.BytesIO(b'secret'))
            with mock.patch('urllib.request.build_opener', return_value=opener):
                with self.assertRaises(RuntimeError) as error:
                    self.ns['request']('GET', '/api/settings/values', 'secret')
            self.assertNotIn('secret', str(error.exception))
        with self.assertRaises(RuntimeError):
            self.ns['request']('POST', '/api/settings/set', 'secret', 'foreign')
        with self.assertRaises(RuntimeError):
            self.ns['request']('GET', 'https://evil.invalid/api/settings/values', 'secret')
        with self.assertRaises(RuntimeError):
            self.ns['NoRedirect']().redirect_request(None, None, 302, '', {}, 'https://evil.invalid')

    def test_fixed_payload_no_proxy_verified_tls_default_timeout_and_bound(self):
        opener = mock.MagicMock()
        response = opener.open.return_value.__enter__.return_value
        response.status, response.read.return_value = 204, b''
        with mock.patch('urllib.request.build_opener', return_value=opener) as build:
            self.ns['request']('POST', '/api/settings/set', 'secret', 'sonar.leak.period')
            request = opener.open.call_args.args[0]
            self.assertEqual(request.full_url, 'https://sonarcloud.io/api/settings/set')
            self.assertEqual(request.data, b'component=spatial-typestate&key=sonar.leak.period&value=2026-11-07')
            self.assertEqual(build.call_args.args[0].proxies, {})
            self.assertEqual(opener.open.call_args.kwargs['timeout'], 30)
            response.read.assert_called_with(1024 * 1024 + 1)

    def test_explicit_one_time_guard_and_isolated_inline_only(self):
        self.assertIn('github.event.number == 12', self.text)
        self.assertIn("vars.SONAR_BASELINE_SETUP == 'date-2026-11-07-once'", self.text)
        self.assertIn('github.event.pull_request.head.repo.full_name == github.repository', self.text)
        self.assertIn('shell: python3 -I {0}', self.text)
        self.assertNotIn('checkout', self.text)
        self.assertEqual(self.text.count('secrets.SONAR_TOKEN'), 1)
