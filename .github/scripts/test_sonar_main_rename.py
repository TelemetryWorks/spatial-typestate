"""Temporary one-time branch setup controls: no network or credentials."""

import io
from pathlib import Path
import textwrap
import unittest
from unittest import mock
import urllib.error


WORKFLOW = Path(__file__).resolve().parents[1] / 'workflows/sonar-main-rename.yml'


class MainRenameTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')
        code = self.text.split('          # BEGIN SONAR_MAIN_RENAME\n')[1].split('          # END SONAR_MAIN_RENAME')[0]
        self.ns = {'__name__': 'offline'}
        exec(compile(textwrap.dedent(code), str(WORKFLOW), 'exec'), self.ns)
        self.component = {'component': {'key': 'spatial-typestate', 'organization': 'telemetryworks',
                                      'qualifier': 'TRK', 'visibility': 'public'}}
        self.master = {'branches': [{'name': 'master', 'isMain': True}]}
        self.main = {'branches': [{'name': 'main', 'isMain': True}]}

    def test_only_private_header_is_on_exact_rename_request(self):
        call = mock.Mock(side_effect=[(200, self.component), (200, self.master), (204, None), (200, self.main)])
        result = self.ns['setup'](call, 'planted-secret')
        self.assertEqual(call.call_args_list, [mock.call('GET', '/api/components/show', None),
                         mock.call('GET', '/api/project_branches/list', None),
                         mock.call('POST', '/api/project_branches/rename', 'planted-secret'),
                         mock.call('GET', '/api/project_branches/list', None)])
        self.assertEqual(result['http_statuses'], [200, 200, 204, 200])
        self.assertNotIn('planted-secret', str(result))

    def test_already_main_is_idempotent_no_post(self):
        call = mock.Mock(side_effect=[(200, self.component), (200, self.main), (200, self.main)])
        self.assertEqual(self.ns['setup'](call, 'secret')['action'], 'already main; no mutation')
        self.assertTrue(all(args.args[0] == 'GET' for args in call.call_args_list))

    def test_identity_or_branch_conflicts_stop_before_post(self):
        invalid = [[], [{'name': 'other', 'isMain': True}], [{'name': 'master', 'isMain': False}],
                   [{'name': 'master', 'isMain': True}, {'name': 'main', 'isMain': False}],
                   [{'name': 'master', 'isMain': True, 'analysisDate': 'already analysed'}]]
        for branches in invalid:
            call = mock.Mock(side_effect=[(200, self.component), (200, {'branches': branches})])
            with self.assertRaises(RuntimeError):
                self.ns['setup'](call, 'secret')
            self.assertEqual(call.call_count, 2)
        self.component['component']['organization'] = 'other'
        call = mock.Mock(return_value=(200, self.component))
        with self.assertRaises(RuntimeError):
            self.ns['setup'](call, 'secret')
        self.assertEqual(call.call_count, 1)

    def test_permissions_redirects_and_other_endpoints_fail_without_bodies(self):
        opener = mock.Mock()
        for status in (401, 403, 302):
            opener.open.side_effect = urllib.error.HTTPError('https://sonarcloud.io', status, 'secret', {}, io.BytesIO(b'secret'))
            with mock.patch('urllib.request.build_opener', return_value=opener):
                with self.assertRaises(RuntimeError) as error:
                    self.ns['request']('POST', '/api/project_branches/rename', 'secret')
            self.assertNotIn('secret', str(error.exception))
        with self.assertRaises(RuntimeError):
            self.ns['request']('POST', '/api/projects/update_visibility', 'secret')
        with self.assertRaises(RuntimeError):
            self.ns['NoRedirect']().redirect_request(None, None, 302, '', {}, 'https://evil.invalid')

    def test_explicit_guard_isolated_inline_no_checkout(self):
        self.assertIn('github.event.number == 10', self.text)
        self.assertIn("vars.SONAR_MAIN_RENAME_SETUP == 'pr-10-once'", self.text)
        self.assertIn('github.event.pull_request.head.repo.full_name == github.repository', self.text)
        self.assertIn('shell: python3 -I {0}', self.text)
        self.assertNotIn('checkout', self.text)
        self.assertEqual(self.text.count('secrets.SONAR_TOKEN'), 1)
