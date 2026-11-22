"""Org-standard release gates, immutable payload checks and read-only verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_guard as g

BUILDER = '.github/workflows/build-release.yml'
KNOWN_SHA = 'fc6b60a9a7f3aa44122e51473cbe52026ae6330826b15401610489ca0b355abf'
KNOWN_URL = 'https://static.crates.io/crates/spatial-typestate/spatial-typestate-0.1.0.crate'
PREDICATE = 'https://cyclonedx.org/bom'


def command(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def publishing():
    return (os.environ.get('GITHUB_REPOSITORY') == g.REPOSITORY
            and os.environ.get('GITHUB_EVENT_NAME') == 'push'
            and os.environ.get('GITHUB_REF_TYPE') == 'tag'
            and os.environ.get('GITHUB_REF', '').startswith(g.TAG_PREFIX))


def require_publish():
    if not publishing():
        raise ValueError('publication requires an independent original-repository tag-push guard')


def pages(path, key=None):
    result = []
    for page in range(1, 101):
        data = g.gh_json(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
        rows = data[key] if key else data
        result.extend(rows)
        if len(rows) < 100:
            return result
    raise ValueError('GitHub pagination exceeded bound')


def remote_tag(version, commit):
    obj = g.gh_json(f'repos/{g.REPOSITORY}/git/ref/tags/v{version}')['object']
    if obj['type'] != 'tag':
        raise ValueError('remote tag must be annotated')
    for _ in range(8):
        if obj['type'] != 'tag':
            break
        obj = g.gh_json(f'repos/{g.REPOSITORY}/git/tags/{obj["sha"]}')['object']
    if obj.get('type') != 'commit' or obj.get('sha') != commit:
        raise ValueError('remote annotated tag does not peel to event SHA')


def notes(version):
    text = (g.ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    match = re.search(r'^## \[' + re.escape(version) + r'\] - (\d{4}-\d{2}-\d{2})\n(.*?)(?=^## |\Z)', text, re.M | re.S)
    if not match:
        raise ValueError('missing dated changelog section')
    import datetime
    datetime.date.fromisoformat(match[1])
    release = g.ROOT / 'docs/releases' / f'v{version}.md'
    if not release.is_file() or not release.read_text(encoding='utf-8').startswith('# '):
        raise ValueError('missing committed release notes with title')
    return release.read_text(encoding='utf-8').splitlines()[0][2:], match[2].strip() + '\n'


def gate():
    version = tomllib.loads((g.ROOT / 'Cargo.toml').read_text())['package']['version']
    commit = os.environ['GITHUB_SHA']
    g.source_guard(version, commit)
    findings = []
    for check in (lambda: remote_tag(version, commit),
                  lambda: command('git', 'merge-base', '--is-ancestor', commit, 'origin/main'),
                  lambda: check_ci(commit), lambda: notes(version)):
        try:
            check()
        except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as error:
            findings.append(str(error))
    if publishing() and findings:
        raise ValueError('tag release blocked: ' + '; '.join(findings))
    print(json.dumps({'mode': 'publish' if publishing() else 'unsigned dry run', 'findings': findings}))
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as output:
        output.write(f'version={version}\npublish={str(publishing()).lower()}\ncrates={g.PROJECT}\n')


def check_ci(commit):
    expected = {'.github/workflows/' + name for name in ('ci.yml', 'python.yml', 'codeql.yml', 'sonar-analysis.yml')}
    runs = pages(f'repos/{g.REPOSITORY}/actions/runs?head_sha={commit}', 'workflow_runs')
    success = {r['path'] for r in runs if r['head_sha'] == commit and r['event'] == 'push'
               and r['head_branch'] == 'main' and r['conclusion'] == 'success'}
    if not expected.issubset(success):
        raise ValueError('intended main CI missing at exact release commit: ' + ', '.join(sorted(expected - success)))


def sidecars(version):
    prefix = f'{g.PROJECT}-{version}'
    return [prefix + '.crates.intoto.jsonl', prefix + '.crate.sbom.sigstore.jsonl',
            prefix + '.python.sbom.sigstore.jsonl']


def payload_names(version):
    return set(g.names(version)) | {g.MANIFEST, g.SUMS, 'core.cdx.json', 'python.cdx.json',
                                   'linux-runtime.json', 'windows-consumer-3.11.json', 'windows-consumer-3.14.json'}


def payload(directory, version, commit, signed=False):
    # Sidecars are signed AFTER payload freezing, not included in SHA256SUMS.
    expected_sidecars = set(sidecars(version)) if signed else set()
    actual_sidecars = {p.name for p in directory.iterdir() if p.name.endswith('.jsonl')}
    if actual_sidecars != expected_sidecars:
        raise ValueError('unexpected or missing attestation sidecar')
    if {path.name for path in directory.iterdir()} != payload_names(version) | expected_sidecars:
        raise ValueError('unexpected or missing frozen payload filename')
    with tempfile.TemporaryDirectory() as temporary:
        clean = Path(temporary)
        for path in directory.iterdir():
            if path.name in expected_sidecars:
                if not path.is_file() or path.is_symlink():
                    raise ValueError('unsafe attestation sidecar')
            else:
                if not path.is_file() or path.is_symlink():
                    raise ValueError('unsafe payload entry')
                shutil.copyfile(path, clean / path.name)
        return g.check(clean, version, commit)


def signatures(directory, version, commit):
    record = payload(directory, version, commit, signed=True)
    workflow = g.REPOSITORY + '/' + BUILDER
    common = ['--repo', g.REPOSITORY, '--signer-workflow', workflow,
              '--source-ref', 'refs/tags/v' + version, '--source-digest', commit, '--deny-self-hosted-runners']
    sums = (directory / g.SUMS).read_text().splitlines()
    for line in sums:
        name = line.split('  ')[1]
        command('gh', 'attestation', 'verify', directory / name, '--bundle', directory / sidecars(version)[0], *common)
    for index, name in enumerate(g.names(version)):
        result = g.run('gh', 'attestation', 'verify', directory / name, '--bundle',
                       directory / sidecars(version)[1 if index == 0 else 2],
                       '--predicate-type', PREDICATE, '--format', 'json', *common)
        statements = [entry['verificationResult']['statement']['predicate'] for entry in json.loads(result)]
        expected = json.loads((directory / ('core.cdx.json' if index == 0 else 'python.cdx.json')).read_text())
        if not statements or any(statement != expected for statement in statements):
            raise ValueError('signed SBOM predicate differs from payload SBOM')
    return record


def compare_crate(directory, version, commit, compiler):
    payload(directory, version, commit, signed=publishing())
    actual = g.run('rustc', '--version').split()[1]
    if compiler != '1.99.0' or actual != compiler:
        raise ValueError('build/publish compiler mismatch')
    # Never compile in this path: the read-only builder already did default verification.
    command('cargo', 'package', '--locked', '--no-verify', '--jobs', '2')
    candidate = g.ROOT / 'target/package' / g.names(version)[0]
    g.crate_check(candidate, version, commit)
    if candidate.read_bytes() != (directory / candidate.name).read_bytes():
        raise ValueError('repackaged crate differs from frozen verified bytes')


def known_good():
    # Owner-reviewed public 0.1.0 digest, pinned independently of this download.
    fixture = g.ROOT / '.github/release-fixtures/spatial-typestate-0.1.0.sha256'
    if fixture.read_text(encoding='ascii') != KNOWN_SHA + '  spatial-typestate-0.1.0.crate\n':
        raise ValueError('trusted known-good fixture changed')
    raw = g.public(KNOWN_URL)
    if len(raw) != 64458 or hashlib.sha256(raw).hexdigest() != KNOWN_SHA:
        raise ValueError('known-good registry archive mismatch')
    print('PASS published spatial-typestate 0.1.0 against independent pinned checksum fixture')


def publish_crate(directory, version, commit):
    require_publish()
    record = signatures(directory, version, commit)
    existing = g.public_json(f'https://crates.io/api/v1/crates/{g.PROJECT}/{version}', missing=True)
    if existing is None:
        command('cargo', 'publish', '--locked', '--no-verify', '--jobs', '2', '--registry', 'crates-io')
    # Existing is never permission to trust or re-upload: compare served bytes too.
    with tempfile.TemporaryDirectory() as temporary:
        g.crate_public(Path(temporary), record)
    print('PASS crates.io serves the verified archive, index checksum and Trusted Publisher source')


def find_release(version):
    # Tag lookup does not reliably find a draft left by an interrupted creation.
    rows = pages(f'repos/{g.REPOSITORY}/releases')
    selected = [r for r in rows if r['tag_name'] == 'v' + version]
    if len(selected) > 1:
        raise ValueError('ambiguous release drafts')
    return selected[0] if selected else None


def latest(version):
    # Stable X.Y.Z only; no accidental upload-date ordering.
    current = tuple(map(int, version.split('.')))
    rows = pages(f'repos/{g.REPOSITORY}/releases')
    stable = [tuple(map(int, r['tag_name'][1:].split('.'))) for r in rows
              if not r['draft'] and not r['prerelease'] and re.fullmatch(r'v\d+\.\d+\.\d+', r['tag_name'])]
    return not stable or current >= max(stable)


def verify_assets(release, directory, allow_missing):
    expected = {p.name: p for p in directory.iterdir()}
    actual = {asset['name']: asset for asset in release['assets']}
    if len(actual) != len(release['assets']) or not set(actual).issubset(expected):
        raise ValueError('unexpected or duplicate release assets')
    if not allow_missing and set(actual) != set(expected):
        raise ValueError('release assets incomplete')
    with tempfile.TemporaryDirectory() as temporary:
        for name, asset in actual.items():
            path = expected[name]
            if asset['size'] != path.stat().st_size or asset.get('digest') != 'sha256:' + g.digest(path):
                raise ValueError('existing release asset size/digest differs; never replace')
            command('gh', 'release', 'download', release['tag_name'], '--repo', g.REPOSITORY,
                    '--pattern', name, '--dir', temporary)
            if (Path(temporary) / name).read_bytes() != path.read_bytes():
                raise ValueError('existing release asset bytes differ; never replace')
    return set(expected) - set(actual)


def release_assets(directory, version, commit):
    require_publish()
    remote_tag(version, commit)
    signatures(directory, version, commit)
    title, body = notes(version)
    release = find_release(version)
    if release is None:
        command('gh', 'release', 'create', 'v' + version, '--repo', g.REPOSITORY, '--verify-tag',
                '--draft', '--latest=false', '--title', title, '--notes', body)
        release = find_release(version)
    if release is None or release['name'] != title or release['body'].strip() != body.strip():
        raise ValueError('release title/body differs from committed notes')
    missing = verify_assets(release, directory, allow_missing=release['draft'])
    if not release['draft']:
        return  # A published release is read-only, even on a recovery run.
    for name in sorted(missing):
        command('gh', 'release', 'upload', 'v' + version, '--repo', g.REPOSITORY, directory / name)
    verify_assets(find_release(version), directory, allow_missing=False)
    command('gh', 'release', 'edit', 'v' + version, '--repo', g.REPOSITORY, '--verify-tag',
            '--draft=false', '--prerelease=false', '--latest=' + str(latest(version)).lower())
    final = find_release(version)
    if final is None or final['draft']:
        raise ValueError('release publication not confirmed')
    verify_assets(final, directory, allow_missing=False)


def docs_rs(version):
    for attempt in range(12):
        data = g.public_json(f'https://docs.rs/crate/{g.PROJECT}/{version}/status.json', missing=True)
        if data is not None and data.get('doc_status') is True and data.get('version') == version:
            return
        if attempt < 11:
            time.sleep(10)
    raise ValueError('docs.rs not successful at bounded deadline (pending/failed); publication verification failed')


def verify(directory, version, commit):
    require_publish()
    record = signatures(directory, version, commit)
    remote_tag(version, commit)
    release = find_release(version)
    if release is None or release['draft']:
        raise ValueError('public GitHub release missing')
    verify_assets(release, directory, allow_missing=False)
    # Keep online proof separate: immutable release payload/sidecars are never resealed.
    with tempfile.TemporaryDirectory() as temporary:
        evidence = Path(temporary)
        for path in directory.iterdir():
            if path.name not in sidecars(version):
                shutil.copyfile(path, evidence / path.name)
        g.crate_public(evidence, record)
        g.pypi_public(evidence, record)
        g.checksums(evidence)
        import release_integrity
        release_integrity.verify(evidence, version, commit)
    docs_rs(version)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['gate', 'check', 'signatures', 'compare', 'known-good', 'publish-crate', 'assets', 'verify'])
    parser.add_argument('--directory', choices=['target/release-artifacts'], default='target/release-artifacts')
    parser.add_argument('--compiler', default=os.environ.get('BUILD_RUST_VERSION', '1.99.0'))
    args = parser.parse_args()
    directory = g.output_directory(g.ROOT / 'target/release-artifacts')
    if args.mode == 'gate':
        gate()
        return
    if args.mode == 'known-good':
        known_good()
        return
    version = os.environ['RELEASE_VERSION']
    commit = os.environ['GITHUB_SHA']
    g.context(version, commit)
    if args.mode == 'check':
        payload(directory, version, commit, signed=publishing())
    elif args.mode == 'signatures':
        require_publish()
        signatures(directory, version, commit)
    elif args.mode == 'compare':
        compare_crate(directory, version, commit, args.compiler)
    elif args.mode == 'publish-crate':
        publish_crate(directory, version, commit)
    elif args.mode == 'assets':
        release_assets(directory, version, commit)
    else:
        verify(directory, version, commit)


if __name__ == '__main__':
    main()
