"""Standalone pre-upload verifier: stdlib only, fixed paths, never uploads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

PROJECT = 'spatial-typestate'
REPOSITORY = 'TelemetryWorks/spatial-typestate'
BUILDER = REPOSITORY + '/.github/workflows/build-release.yml'
SUMS = 'SHA256SUMS'

PROBE_FILE = 'permission-probe.txt'
PROBE_SBOM = 'permission-probe.cdx.json'
PROBE_BUNDLES = ('permission-probe.intoto.jsonl', 'permission-probe.sbom.sigstore.jsonl')
PROBE_CONTENT = b'TelemetryWorks token-permissions probe only; NOT a release artifact.\n'
PROBE_BOM = b'{"bomFormat":"CycloneDX","specVersion":"1.5","version":1,"components":[]}\n'


def require_publish(version, commit):
    if (not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', version, flags=re.ASCII)
            or not re.fullmatch(r'[a-f0-9]{40}', commit)
            or os.environ.get('GITHUB_SHA') != commit
            or os.environ.get('GITHUB_REPOSITORY') != REPOSITORY
            or os.environ.get('GITHUB_EVENT_NAME') != 'push'
            or os.environ.get('GITHUB_REF_TYPE') != 'tag'
            or os.environ.get('GITHUB_REF') != 'refs/tags/v' + version):
        raise ValueError('PyPI staging requires the independent original-repository version tag push')


def files(version):
    prefix = 'spatial_typestate-' + version
    python = [prefix + '-cp311-abi3-manylinux_2_28_x86_64.whl',
              prefix + '-cp311-abi3-win_amd64.whl', prefix + '.tar.gz']
    payload = set(python) | {f'{PROJECT}-{version}.crate', 'release-manifest.json',
                            'core.cdx.json', 'python.cdx.json', 'linux-runtime.json',
                            'windows-consumer-3.11.json', 'windows-consumer-3.14.json'}
    sidecars = [f'{PROJECT}-{version}' + suffix for suffix in (
        '.crates.intoto.jsonl', '.crate.sbom.sigstore.jsonl', '.python.sbom.sigstore.jsonl')]
    return python, payload, sidecars


def check_payload(root, version):
    python, payload, sidecars = files(version)
    expected = {}
    for line in (root / SUMS).read_text(encoding='ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64}) {2}([A-Za-z0-9_.-]+)', line)
        if not match or match[2] in expected or match[2] == SUMS:
            raise ValueError('invalid checksum manifest')
        expected[match[2]] = match[1]
    if set(expected) != payload or {p.name for p in root.iterdir()} != payload | set(sidecars) | {SUMS}:
        raise ValueError('unexpected or missing payload/sidecar')
    for path in root.iterdir():
        if path.is_symlink() or not path.is_file():
            raise ValueError('unsafe payload')
        if path.name in expected:
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected[path.name]:
                    raise ValueError('checksum mismatch')
    return python, payload, sidecars


def signature_policy(commit, source_ref):
    return ['--repo', REPOSITORY, '--signer-workflow', BUILDER,
            '--source-ref', source_ref, '--source-digest', commit, '--deny-self-hosted-runners']


def verify_bundles(root, subjects, sbom_subjects, bundles, sbom_file, policy):
    # This exact GH CLI path is shared by publication staging and its permission probe.
    for name in sorted(subjects):
        subprocess.run(['gh', 'attestation', 'verify', str(root / name), '--bundle', str(root / bundles[0]),
                        *policy], check=True)
    expected = json.loads((root / sbom_file).read_text(encoding='utf-8'))
    for name in sbom_subjects:
        raw = subprocess.check_output(
            ['gh', 'attestation', 'verify', str(root / name), '--bundle', str(root / bundles[1]),
             '--predicate-type', 'https://cyclonedx.org/bom', '--format', 'json', *policy],
            text=True, encoding='utf-8')
        predicates = [entry['verificationResult']['statement']['predicate'] for entry in json.loads(raw)]
        if not predicates or any(predicate != expected for predicate in predicates):
            raise ValueError('signed Python SBOM predicate differs from payload SBOM')


def verify_signatures(root, version, commit, python, payload, sidecars):
    verify_bundles(root, payload, python, (sidecars[0], sidecars[2]), 'python.cdx.json',
                   signature_policy(commit, 'refs/tags/v' + version))


def verify_permissions(root, commit, source_ref):
    event = os.environ.get('GITHUB_EVENT_NAME')
    ref_ok = ((event == 'pull_request' and re.fullmatch(r'refs/pull/[1-9]\d*/merge', source_ref, flags=re.ASCII))
              or (event == 'workflow_dispatch' and source_ref.startswith('refs/heads/')))
    if (os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or not ref_ok
            or os.environ.get('GITHUB_REF_TYPE') != 'branch'
            or commit != os.environ.get('GITHUB_SHA') or source_ref != os.environ.get('GITHUB_REF')
            or not re.fullmatch(r'[a-f0-9]{40}', commit)):
        raise ValueError('permission probe requires the original repository PR or branch dry run')
    expected = {PROBE_FILE, PROBE_SBOM, *PROBE_BUNDLES}
    if {p.name for p in root.iterdir()} != expected or any(p.is_symlink() or not p.is_file() for p in root.iterdir()):
        raise ValueError('unexpected permission fixture files')
    if (root / PROBE_FILE).read_bytes() != PROBE_CONTENT or (root / PROBE_SBOM).read_bytes() != PROBE_BOM:
        raise ValueError('permission fixture must be fixed non-release content')
    verify_bundles(root, {PROBE_FILE, PROBE_SBOM}, [PROBE_FILE], PROBE_BUNDLES, PROBE_SBOM,
                   signature_policy(commit, source_ref))
    print('PASS real provenance and SBOM verification with the publish-pypi token permissions; no staging/upload')


def stage(root, output, version, commit):
    require_publish(version, commit)
    if output.exists() or output.is_symlink():
        raise ValueError('PyPI upload directory must not already exist')
    python, payload, sidecars = check_payload(root, version)
    # No uploadable directory exists until EVERY signature and SBOM binding passes.
    verify_signatures(root, version, commit, python, payload, sidecars)
    output.mkdir()
    for name in python:
        shutil.copyfile(root / name, output / name)
    print('PASS pre-upload signatures and SBOM bindings; staged exactly two wheels and one sdist')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['stage', 'verify-permissions'])
    args = parser.parse_args()
    if args.mode == 'stage':
        stage(Path('target/release-artifacts'), Path('pypi-dist'), os.environ['RELEASE_VERSION'], os.environ['GITHUB_SHA'])
    else:
        verify_permissions(Path('target/permission-probe'), os.environ['GITHUB_SHA'], os.environ['GITHUB_REF'])


if __name__ == '__main__':
    main()
