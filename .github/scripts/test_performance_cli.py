"""Security-boundary checks without building or timing benchmarks."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/performance_study.py'
spec = importlib.util.spec_from_file_location('study', SCRIPT)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class CriterionArgumentTests(unittest.TestCase):
    def test_repeat_commands_environment_and_resume(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            fingerprint = 'fixture-fingerprint'
            manifest = {'fingerprint': fingerprint, 'configs': {
                name: {'executable': name + '.exe'} for name in study.CONFIGS}}
            (output / 'manifest.json').write_text(json.dumps(manifest))
            measurements = []

            def collect(home, label, metadata):
                measurements.append(metadata.copy())
                self.assertEqual(home.parent.name, label)
                (home.parent / study.RESULT_FILE).write_text(json.dumps({
                    'metadata': metadata, 'estimates': []}))

            with (mock.patch.object(study, 'OUT', output),
                  mock.patch.object(study, 'fingerprint', return_value=fingerprint),
                  mock.patch.object(study, 'collect', side_effect=collect),
                  mock.patch.object(study.subprocess, 'run') as execute,
                  mock.patch.dict(os.environ, {'SPATIAL_BENCH_REVERSE': 'old-value'})):
                study.run('fixture', list(study.CONFIGS), '^amortization', 2)
                self.assertEqual([item['config'] for item in measurements], [
                    'lto-std', 'lto-no-std', 'nolto-std',
                    'lto-no-std', 'lto-std', 'nolto-std',
                    'lto-std', 'lto-no-std', 'nolto-std'])
                for call, item in zip(execute.call_args_list, measurements):
                    self.assertEqual(call.args[0], [item['config'] + '.exe', '--bench',
                                                   '--noplot', '^amortization'])
                    env = call.kwargs['env']
                    self.assertEqual(env['RAYON_NUM_THREADS'], '2')
                    self.assertEqual(env['SPATIAL_BENCH_SEED'], '5573589319906701683')
                    self.assertEqual(env.get('SPATIAL_BENCH_REVERSE'),
                                     '1' if item['repeat'] == 2 else None)
                    self.assertTrue(call.kwargs['check'])
                study.run('fixture', list(study.CONFIGS), '^amortization', 2)
                self.assertEqual(execute.call_count, 9)

    def test_documented_and_builtin_filters_are_preserved(self):
        for value in (None, '', '^amortization', study.SUBSET, 'point.*valid$', '^--literal'):
            self.assertEqual(study.criterion_filter(value), value)

    def test_optionlike_values_fail_before_any_manifest_read_or_execution(self):
        for value in ('--list', '--sample-size=1', '-x'):
            with mock.patch.object(Path, 'read_text') as read, mock.patch.object(study.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    study.run('unused', ['lto-std'], value, 2)
                read.assert_not_called()
                run.assert_not_called()

    def test_real_cli_rejects_option_before_prepare_or_measure(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--prepare', '--run', '--filter=--list'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn('invalid criterion_filter value', result.stderr)
        self.assertNotIn('BUILD', result.stdout)
        self.assertNotIn('MEASURE', result.stdout)
