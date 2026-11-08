"""Security-boundary checks without building or timing benchmarks."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/performance_study.py'
spec = importlib.util.spec_from_file_location('study', SCRIPT)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


class CriterionArgumentTests(unittest.TestCase):
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
