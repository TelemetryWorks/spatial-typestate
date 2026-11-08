"""Temporary exact-issue disposition controls; no network or credentials."""

import copy
import io
import json
from pathlib import Path
import textwrap
import unittest
from unittest import mock
import urllib.error
import urllib.parse


WORKFLOW = Path(__file__).resolve().parents[1] / 'workflows/sonar-issue-dispositions.yml'


class DispositionTests(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')
        code = self.text.split('          # BEGIN SONAR_DISPOSITIONS\n')[1].split('          # END SONAR_DISPOSITIONS')[0]
        self.ns = {'__name__': 'offline'}
        exec(compile(textwrap.dedent(code), str(WORKFLOW), 'exec'), self.ns)
        self.specs = self.ns['SPECS']
        self.posts = []

    def item(self, key, target=False):
        spec = self.specs[key]
        return {'key': key, 'project': 'spatial-typestate', 'organization': 'telemetryworks',
                **{field: spec[field] for field in ('rule', 'component', 'line', 'hash')},
                'type': 'VULNERABILITY', 'issueStatus': spec['target'] if target else 'OPEN',
                'resolution': spec['legacy'] if target else None,
                'comments': [{'markdown': spec['comment']}] if target else [],
                'transitions': [spec['transition']] if not target else []}

    def event(self, key):
        return {'diffs': [{'key': 'resolution', 'oldValue': '', 'newValue': self.specs[key]['legacy']},
                          {'key': 'status', 'oldValue': 'OPEN', 'newValue': 'RESOLVED'}]}

    def server(self, targeted=()):
        items = {key: self.item(key, key in targeted) for key in self.specs}
        history = {key: [self.event(key)] if key in targeted else [] for key in self.specs}
        def call(method, endpoint, token=None, issue=None):
            if endpoint == '/api/components/show':
                return {'component': {'key': 'spatial-typestate', 'organization': 'telemetryworks',
                                      'visibility': 'public', 'qualifier': 'TRK'}}
            if endpoint == '/api/project_branches/list':
                return {'branches': [{'name': 'main', 'isMain': True, 'commit': {'sha': self.ns['REVIEWED_MAIN']}}]}
            if endpoint == '/api/issues/search':
                response = copy.deepcopy(list(items.values()))
                if token is None:
                    for item in response:
                        item['transitions'] = []
                return {'paging': {'total': 3, 'pageIndex': 1}, 'issues': response}
            if endpoint == '/api/issues/changelog':
                return {'changelog': copy.deepcopy(history[issue])}
            self.assertEqual((method, endpoint), ('POST', '/api/issues/do_transition'))
            self.assertIn(issue, self.specs)
            self.posts.append(issue)
            items[issue] = self.item(issue, True)
            history[issue].append(self.event(issue))
            # The documented transition response need not repeat search's
            # organization/hash fields. Public search verifies the full identity.
            return {'issue': {'key': issue, 'issueStatus': self.specs[issue]['target']}}
        return call, items, history

    def test_exact_three_atomic_transitions_and_public_audit(self):
        call, items, history = self.server()
        result = self.ns['apply'](call, 'planted-secret')
        self.assertEqual(self.posts, list(self.specs))
        self.assertNotIn('planted-secret', json.dumps(result))
        self.assertEqual([r['issueStatus'] for r in result['issues']], ['FALSE_POSITIVE', 'ACCEPTED', 'ACCEPTED'])
        for key, spec in self.specs.items():
            self.assertEqual(items[key]['comments'], [{'markdown': spec['comment']}])
            self.assertEqual(len(history[key]), 1)
        self.posts.clear()
        repeated = self.ns['apply'](call, 'planted-secret')
        self.assertEqual(self.posts, [])
        self.assertTrue(all(r['action'] == 'verified prior target' for r in repeated['issues']))

    def test_partial_prior_success_skips_only_verified_modern_target(self):
        first = next(iter(self.specs))
        call, _, _ = self.server([first])
        self.ns['apply'](call, 'secret')
        self.assertEqual(self.posts, list(self.specs)[1:])

    def test_every_identity_field_for_every_issue_stops_all_posts(self):
        for key in self.specs:
            changes = {'key': 'foreign', 'rule': 'other', 'component': 'other', 'line': -1,
                       'hash': 'changed', 'project': 'other', 'organization': 'other',
                       'type': 'CODE_SMELL', 'pullRequest': '13', 'issueStatus': 'CONFIRMED'}
            for field, value in changes.items():
                call, items, _ = self.server()
                items[key][field] = value
                self.posts.clear()
                with self.subTest(key=key, field=field), self.assertRaises(RuntimeError):
                    self.ns['apply'](call, 'secret')
                self.assertEqual(self.posts, [])

    def test_target_without_matching_audit_or_with_wrong_legacy_stops_all(self):
        first = next(iter(self.specs))
        for field, value in (('comments', []), ('resolution', 'ACCEPTED')):
            call, items, _ = self.server([first])
            items[first][field] = value
            with self.assertRaises(RuntimeError):
                self.ns['apply'](call, 'secret')
            self.assertEqual(self.posts, [])

    def test_missing_permission_on_last_issue_stops_before_first_post(self):
        call, items, _ = self.server()
        items[list(self.specs)[-1]]['transitions'] = []
        with self.assertRaisesRegex(RuntimeError, 'Administer Issues'):
            self.ns['apply'](call, 'secret')
        self.assertEqual(self.posts, [])

    def test_unreviewed_main_revision_stops_all_writes(self):
        server, _, _ = self.server()
        def call(method, endpoint, token=None, issue=None):
            result = server(method, endpoint, token, issue)
            if endpoint == '/api/project_branches/list':
                result['branches'][0]['commit']['sha'] = 'changed'
            return result
        with self.assertRaisesRegex(RuntimeError, 'main branch'):
            self.ns['apply'](call, 'secret')
        self.assertEqual(self.posts, [])

    def test_exact_payload_combines_transition_and_literal_comment(self):
        opener = mock.MagicMock()
        response = opener.open.return_value.__enter__.return_value
        response.status, response.read.return_value = 200, b'{"issue":{}}'
        for key, spec in self.specs.items():
            with mock.patch('urllib.request.build_opener', return_value=opener) as build:
                self.ns['request']('POST', '/api/issues/do_transition', 'planted-secret', key)
                request = opener.open.call_args.args[0]
                self.assertEqual(request.full_url, 'https://sonarcloud.io/api/issues/do_transition')
                self.assertEqual(urllib.parse.parse_qs(request.data.decode()),
                                 {'issue': [key], 'transition': [spec['transition']], 'comment': [spec['comment']]})
                self.assertNotIn('planted-secret', request.full_url + request.data.decode())
                self.assertEqual(build.call_args.args[0].proxies, {})
                self.assertEqual(opener.open.call_args.kwargs['timeout'], 30)
                response.read.assert_called_with(1024 * 1024 + 1)
                self.assertNotIn('http', spec['comment'])
                self.assertIn('docs/evals/2026-11-07-sonar-main-triage.md', spec['comment'])

    def test_unlisted_keys_foreign_hosts_and_redirects_fail(self):
        for method, endpoint, issue in [('POST', '/api/issues/do_transition', 'foreign'),
                                        ('GET', '/api/issues/changelog', 'foreign'),
                                        ('POST', '/api/issues/add_comment', next(iter(self.specs))),
                                        ('GET', 'https://evil.invalid/api/issues/search', None)]:
            with self.subTest(endpoint=endpoint), self.assertRaises(RuntimeError):
                self.ns['request'](method, endpoint, 'secret', issue)
        redirect = self.ns['NoRedirect']()
        with self.assertRaises(RuntimeError):
            redirect.redirect_request(None, None, 302, '', {}, 'https://evil.invalid')

    def test_http_errors_never_echo_token_headers_or_bodies(self):
        opener = mock.Mock()
        for status in (401, 403, 302, 500):
            opener.open.side_effect = urllib.error.HTTPError('https://sonarcloud.io', status,
                'planted-secret', {'Authorization': 'planted-secret'}, io.BytesIO(b'planted-secret'))
            with mock.patch('urllib.request.build_opener', return_value=opener):
                with self.assertRaises(RuntimeError) as raised:
                    self.ns['request']('GET', '/api/issues/search', 'planted-secret')
            self.assertNotIn('planted-secret', str(raised.exception))
            if status in (401, 403):
                self.assertIn('Administer Issues', str(raised.exception))

    def test_guard_no_checkout_isolated_python_and_single_secret_reference(self):
        self.assertIn('github.event.number == 13', self.text)
        self.assertIn("vars.SONAR_ISSUE_DISPOSITIONS == 'three-2026-11-08-once'", self.text)
        self.assertIn('github.event.pull_request.head.repo.full_name == github.repository', self.text)
        self.assertIn('shell: python3 -I {0}', self.text)
        self.assertNotIn('checkout', self.text)
        self.assertEqual(self.text.count('secrets.SONAR_TOKEN'), 1)
