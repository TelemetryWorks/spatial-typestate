"""Tag-bound release checks and evidence staging. Registry uploads live in the workflow."""
import argparse
from email.parser import BytesParser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'python'))
import build_backend as backend
import check_package_metadata as metadata
import verify_artifacts as artifacts

PROJECT = 'spatial-typestate'
REPOSITORY = 'TelemetryWorks/spatial-typestate'
WORKFLOW = '.github/workflows/trusted-publishing.yml'
MANIFEST = 'release-manifest.json'
CARGO_MANIFEST = 'Cargo.toml'
TAG_PREFIX = 'refs/tags/v'
SUMS = 'SHA256SUMS'
SOURCE = 'source'
VERSION = 'version'
COMMIT = 'commit'
HASH = 'sha256'
PUBLIC = {'pypi.org', 'files.pythonhosted.org', 'crates.io', 'static.crates.io', 'index.crates.io', 'docs.rs'}


def run(*args, cwd=None):
    return subprocess.check_output([str(a) for a in args], cwd=cwd, text=True, encoding='utf-8').strip()


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def names(version):
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version):
        raise ValueError('release requires a stable X.Y.Z version')
    prefix = f'spatial_typestate-{version}'
    return [f'{PROJECT}-{version}.crate', f'{prefix}-cp311-abi3-manylinux_2_28_x86_64.whl',
            f'{prefix}-cp311-abi3-win_amd64.whl', f'{prefix}.tar.gz']


def context(version, commit):
    names(version)
    if (os.environ.get('GITHUB_REPOSITORY') != REPOSITORY
            or os.environ.get('GITHUB_EVENT_NAME') not in ('push', 'pull_request', 'workflow_dispatch')
            or not re.fullmatch(r'[a-f0-9]{40}', commit)
            or commit != os.environ.get('GITHUB_SHA')):
        raise ValueError('release requires the original repository and exact event commit')
    if os.environ['GITHUB_EVENT_NAME'] == 'push' and os.environ.get('GITHUB_REF') != TAG_PREFIX + version:
        raise ValueError('release requires the version tag push')


def source_guard(version, commit):
    context(version, commit)
    actual = [tomllib.loads((ROOT / path).read_text(encoding='utf-8'))[section]['version']
              for path, section in [(CARGO_MANIFEST, 'package'), ('python/native/Cargo.toml', 'package'),
                                    ('python/pyproject.toml', 'project')]]
    for lock in ('Cargo.lock', 'python/native/Cargo.lock'):
        packages = tomllib.loads((ROOT / lock).read_text())['package']
        core = [p for p in packages if p['name'] == PROJECT]
        if len(core) != 1 or core[0]['version'] != version:
            raise ValueError('lockfile self-package version differs')
    if actual != [version] * 3:
        raise ValueError('tag must match core, Python and native versions')
    if (run('git', 'rev-parse', 'HEAD') != commit
            or run('git', 'status', '--porcelain', '--untracked-files=all')):
        raise ValueError('release requires the clean triggering commit')
    source, origin = backend.source_record(ROOT / 'python')
    if origin != 'checkout' or source['git'] != {'base_commit': commit, 'state': 'clean'}:
        raise ValueError('invalid release source inventory')
    return source


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        raise ValueError('registry redirect refused')


def public(url, missing=False):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname not in PUBLIC or parsed.username or parsed.password
            or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError('unexpected public registry URL')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    request = urllib.request.Request(url, headers={'User-Agent': PROJECT + '-release-verification (https://github.com/' + REPOSITORY + ')' })
    try:
        with opener.open(request, timeout=30) as response:
            raw = response.read(32_000_001)
            if len(raw) > 32_000_000:
                raise ValueError('registry response exceeds bound')
            return raw
    except urllib.error.HTTPError as error:
        if missing and error.code == 404:
            return None
        raise ValueError('registry HTTP status ' + str(error.code)) from None


def public_json(url, missing=False):
    raw = public(url, missing)
    return None if raw is None else json.loads(raw)


def absent(version, registry='both'):
    endpoints = {'crates': f'https://crates.io/api/v1/crates/{PROJECT}/{version}',
                 'pypi': f'https://pypi.org/pypi/{PROJECT}/{version}/json'}
    for name, url in endpoints.items():
        if registry in ('both', name) and public_json(url, missing=True) is not None:
            raise ValueError(name + ' version already exists; stop, inspect public state, never republish')


def crate_check(path, version, commit):
    with tarfile.open(path) as archive:
        entries = archive.getmembers()
        prefix = f'{PROJECT}-{version}/'
        if any(not m.isfile() or not m.name.startswith(prefix) or '..' in Path(m.name).parts
               or '\\' in m.name for m in entries):
            raise ValueError('invalid crate entries')
        if len({m.name for m in entries}) != len(entries):
            raise ValueError('duplicate crate entries')
        vcs = json.load(archive.extractfile(prefix + '.cargo_vcs_info.json'))['git']
        manifest = tomllib.loads(archive.extractfile(prefix + CARGO_MANIFEST).read().decode())
        if (vcs.get('sha1') != commit or vcs.get('dirty', False) is not False
                or manifest['package']['version'] != version or manifest.get('dependencies')):
            raise ValueError('crate identity/version/dependency mismatch')
        expected_src = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'src').rglob('*.rs')}
        actual_src = {m.name.removeprefix(prefix) for m in entries if m.name.startswith(prefix + 'src/')}
        if actual_src != expected_src:
            raise ValueError('crate source set differs')
        for member in entries:
            relative = member.name.removeprefix(prefix)
            if relative in (CARGO_MANIFEST, '.cargo_vcs_info.json'):
                continue
            expected = ROOT / (CARGO_MANIFEST if relative == 'Cargo.toml.orig' else relative)
            if not expected.is_file() or archive.extractfile(member).read() != expected.read_bytes():
                raise ValueError('crate source differs: ' + relative)


def checksums(directory):
    files = sorted(p for p in directory.iterdir() if p.name != SUMS)
    if any(not p.is_file() or p.is_symlink() or not re.fullmatch(r'[A-Za-z0-9_.-]+', p.name) for p in files):
        raise ValueError('unsafe evidence file')
    (directory / SUMS).write_text(''.join(f'{digest(p)}  {p.name}\n' for p in files), encoding='ascii')


def check(directory, version, commit):
    record = json.loads((directory / MANIFEST).read_text())
    if record[VERSION] != version or record[COMMIT] != commit or record['tag'] != 'v' + version:
        raise ValueError('release manifest identity mismatch')
    lines = (directory / SUMS).read_text(encoding='ascii').splitlines()
    expected = {}
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)', line)
        if not match or match[2] in expected or match[2] == SUMS:
            raise ValueError('invalid checksum manifest')
        expected[match[2]] = match[1]
    actual = {p.name: digest(p) for p in directory.iterdir() if p.name != SUMS and p.is_file() and not p.is_symlink()}
    if expected != actual or any(p.is_symlink() or not p.is_file() for p in directory.iterdir()):
        raise ValueError('evidence checksum/file set mismatch')
    if (record.get('run_id') != os.environ['GITHUB_RUN_ID'] or not isinstance(record.get('run_attempt'), int)
            or not 1 <= record['run_attempt'] <= int(os.environ['GITHUB_RUN_ATTEMPT'])
            or record.get('workflow') != WORKFLOW
            or record[SOURCE]['git'] != {'base_commit': commit, 'state': 'clean'}
            or record[SOURCE]['versions'] != {'core': version, 'native': version, 'python': version}):
        raise ValueError('manifest run/source identity mismatch')
    if set(record['files']) != set(names(version)):
        raise ValueError('release must select exactly four artifacts')
    if any(actual.get(name) != sha for name, sha in record['files'].items()):
        raise ValueError('selected artifact differs from release manifest')
    return record


def stage(incoming, destination, version, commit):
    source = source_guard(version, commit)
    destination.mkdir(parents=True)
    for index, name in enumerate(names(version)):
        arm = 'verified-crate' if index == 0 else 'verified-python-' + ('windows-latest-3.11' if index == 2 else 'ubuntu-latest-3.11')
        path = incoming / arm / name
        if not path.is_file() or path.is_symlink():
            raise ValueError('canonical selected artifact missing')
        shutil.copyfile(path, destination / name)
    crate_check(destination / names(version)[0], version, commit)
    for name in names(version)[1:3]:
        artifacts.wheel_report(destination / name, commit)
        info, provenance = metadata.wheel(destination / name)
        metadata.validate_project_metadata(info)
        if info['Version'] != version or provenance[SOURCE] != source or provenance['source_origin'] != 'checkout':
            raise ValueError('selected wheel source/version differs')
    sdist = destination / names(version)[3]
    artifacts.sdist_report(sdist)
    with tarfile.open(sdist) as archive:
        records = [m for m in archive if m.name.endswith('/spatial_typestate/_provenance.json')]
        if len(records) != 1 or json.load(archive.extractfile(records[0]))[SOURCE] != source:
            raise ValueError('selected sdist source differs')
    runtime = json.loads((incoming / 'verified-python-ubuntu-latest-3.11/runtime-evidence.json').read_text())
    linux_sha = digest(destination / names(version)[1])
    observed = {(r['python'].split()[0].rsplit('.', 1)[0], r['glibc']) for r in runtime if r[HASH] == linux_sha}
    if observed != {('3.11', '2.28'), ('3.11', '2.36'), ('3.14', '2.28'), ('3.14', '2.36')}:
        raise ValueError('selected Linux wheel lacks four runtime records')
    write_json(destination / 'linux-runtime.json', runtime)
    for interpreter in ('3.11', '3.14'):
        receipt = json.loads((incoming / ('windows-consumer-' + interpreter) / 'windows-consumer.json').read_text())
        if (receipt[HASH] != digest(destination / names(version)[2]) or receipt[COMMIT] != commit
                or not receipt['python'].startswith(interpreter + '.')):
            raise ValueError('Windows consumers did not qualify the selected wheel')
        write_json(destination / ('windows-consumer-' + interpreter + '.json'), receipt)
    for name in ('core.cdx.json', 'python.cdx.json'):
        shutil.copyfile(incoming / 'verified-crate' / name, destination / name)
    write_json(destination / MANIFEST, {VERSION: version, COMMIT: commit, 'tag': 'v' + version,
               SOURCE: source, 'files': {name: digest(destination / name) for name in names(version)},
               'workflow': WORKFLOW, 'run_id': os.environ['GITHUB_RUN_ID'], 'run_attempt': int(os.environ['GITHUB_RUN_ATTEMPT'])})
    checksums(destination)


def installed(wheel, version, commit, output):
    inventory = json.loads((wheel.parent / 'artifact-inventory.json').read_text())
    selected = [entry for entry in inventory if entry['filename'] == wheel.name]
    if len(selected) != 1 or selected[0][HASH] != digest(wheel):
        raise ValueError('selected consumer wheel hash differs from build inventory')
    artifacts.wheel_report(wheel, commit)
    # A fresh venv and copied test assets keep imports and execution outside checkout.
    with tempfile.TemporaryDirectory(prefix='release-consumer-') as temporary:
        root = Path(temporary)
        environment = root / 'venv'
        subprocess.run([sys.executable, '-m', 'venv', environment], check=True)
        python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        cwd = root / 'cwd'
        cwd.mkdir()
        assets = root / 'tests'
        shutil.copytree(ROOT / 'python/tests', assets)
        subprocess.run([python, '-m', 'pip', '--isolated', 'install', '--no-deps', wheel], cwd=cwd, check=True)
        probe = """import importlib.metadata as m, importlib.resources as r, json, pathlib, sysconfig
import spatial_typestate as s
from spatial_typestate import _native as n
site=pathlib.Path(sysconfig.get_paths()['purelib']).resolve()
assert pathlib.Path(s.__file__).resolve().is_relative_to(site)
assert pathlib.Path(n.__file__).resolve().is_relative_to(site)
print(json.dumps({'version':m.version('spatial-typestate'),'record':json.loads(r.files(s).joinpath('_provenance.json').read_text())}))
"""
        data = json.loads(run(python, '-I', '-c', probe, cwd=cwd))
        if (data[VERSION] != version or data['record'][SOURCE]['git'] != {'base_commit': commit, 'state': 'clean'}):
            raise ValueError('installed wheel identity differs')
        for numpy in (False, True):
            if numpy:
                subprocess.run([python, '-m', 'pip', 'install', '--require-hashes', '--only-binary=:all:',
                                '-r', ROOT / 'python/requirements-interop.txt'], cwd=cwd, check=True)
            subprocess.run([python, '-I', '-m', 'unittest', 'discover', '-s', assets, '-v'], cwd=cwd, check=True)
        subprocess.run([python, '-I', ROOT / 'python/examples/lab_workflow.py', '--demonstrate-errors'], cwd=cwd, check=True)
    write_json(output, {HASH: digest(wheel), COMMIT: commit, VERSION: version,
                       'python': sys.version, 'stdlib_and_numpy': 'passed', 'outside_checkout': True})


def wait_json(url):
    for attempt in range(6):
        result = public_json(url, missing=True)
        if result is not None:
            return result
        if attempt < 5:
            time.sleep(5)
    raise ValueError('public evidence absent; stop and inspect, never repeat upload')


def crate_public(directory, record):
    version = record[VERSION]
    name = names(version)[0]
    data = wait_json(f'https://crates.io/api/v1/crates/{PROJECT}/{version}')['version']
    trust = data.get('trustpub_data') or {}
    # Compare the actual documented API shape, not only a green auth/upload step.
    if (data['checksum'] != record['files'][name] or data['yanked']
            or trust.get('provider') != 'github' or trust.get('repository') != REPOSITORY
            or trust.get('sha') != record[COMMIT]):
        raise ValueError('crates.io checksum/Trusted Publisher identity differs')
    index = public('https://index.crates.io/sp/at/' + PROJECT)
    selected = [json.loads(line) for line in index.splitlines() if json.loads(line)['vers'] == version]
    if len(selected) != 1 or selected[0]['cksum'] != record['files'][name] or selected[0]['yanked']:
        raise ValueError('crates.io index mismatch; do not republish')
    raw = public(f'https://static.crates.io/crates/{PROJECT}/{name}')
    if hashlib.sha256(raw).hexdigest() != record['files'][name]:
        raise ValueError('published crate bytes differ; any yank is an owner decision')
    write_json(directory / 'crates-public.json', data)


def pypi_public(directory, record):
    version = record[VERSION]
    data = wait_json(f'https://pypi.org/pypi/{PROJECT}/{version}/json')
    info = data['info']
    urls = {item['filename']: item for item in data['urls']}
    config = tomllib.loads((ROOT / 'python/pyproject.toml').read_text())['project']
    if (info['name'] != PROJECT or len(urls) != len(data['urls']) or set(urls) != set(names(version)[1:])
            or info['version'] != version or info['license_expression'] != 'Apache-2.0'
            or 'LICENSE' not in (info['license_files'] or []) or info['project_urls'] != config['urls']
            or {part.strip() for part in info['requires_python'].split(',')} != {'>=3.11', '<3.15'}):
        raise ValueError('PyPI public file set or licence/URL metadata differs')
    for name, item in urls.items():
        if item['yanked'] or item['digests'][HASH] != record['files'][name]:
            raise ValueError('PyPI digest/yanked status differs')
        raw = public(item['url'])
        if hashlib.sha256(raw).hexdigest() != record['files'][name]:
            raise ValueError('fresh PyPI file bytes differ')
        provenance = wait_json(f'https://pypi.org/integrity/{PROJECT}/{version}/{name}/provenance')
        write_json(directory / (name + '.pypi-provenance.json'), provenance)
    write_json(directory / 'pypi-public.json', data)


def merge_evidence(incoming, output, version, commit):
    output.mkdir()
    for group in ('crates-evidence', 'pypi-evidence'):
        directory = incoming / group
        check(directory, version, commit)
        for path in directory.iterdir():
            if path.name == SUMS:
                continue
            target = output / path.name
            if target.exists() and target.read_bytes() != path.read_bytes():
                raise ValueError('conflicting evidence; never overwrite')
            shutil.copyfile(path, target)
    required = {'crates-public.json', 'pypi-public.json', 'pypi-integrity-verified.json',
                'crate.provenance.sigstore.json', 'crate.sbom.sigstore.json',
                'python.provenance.sigstore.json', 'python.sbom.sigstore.json'}
    required.update(name + suffix for name in names(version)[1:]
                    for suffix in ('.pypi-provenance.json', '.publish-0.sigstore.json'))
    if not required.issubset({p.name for p in output.iterdir()}):
        raise ValueError('publication evidence incomplete')
    checksums(output)
    check(output, version, commit)


def gh_json(path, missing=False):
    result = subprocess.run(['gh', 'api', path], capture_output=True, text=True, check=False)
    if result.returncode:
        if missing and '(HTTP 404)' in result.stderr:
            return None
        raise ValueError('GitHub read failed; no release mutation permitted')
    return json.loads(result.stdout)


def release_assets(directory, record):
    from release_pipeline import require_publish
    require_publish()
    version, commit = record[VERSION], record[COMMIT]
    tag = 'v' + version
    prefix = 'repos/' + REPOSITORY
    obj = gh_json(prefix + '/git/ref/tags/' + tag)['object']
    for _ in range(8):
        if obj['type'] != 'tag':
            break
        obj = gh_json(prefix + '/git/tags/' + obj['sha'])['object']
    if obj.get('type') != 'commit' or obj.get('sha') != commit:
        raise ValueError('remote release tag differs; never move it')
    release_path = prefix + '/releases/tags/' + tag
    release = gh_json(release_path, missing=True)
    if release is None:
        subprocess.run(['gh', 'release', 'create', tag, '--repo', REPOSITORY, '--verify-tag',
                        '--target', commit, '--draft', '--latest=false', '--title', tag,
                        '--notes', 'Coordinated release: crate, wheels, sdist, source-graph CycloneDX SBOMs, '
                        'per-file PyPI provenance, Sigstore bundles and checksums. Verification: '
                        'https://github.com/' + REPOSITORY + '/blob/' + commit + '/docs/RELEASING.md'], check=True)
        release = gh_json(release_path)
    expected = {p.name for p in directory.iterdir()}
    existing = {a['name'] for a in release['assets']}
    if not existing.issubset(expected):
        raise ValueError('existing Release has unexpected assets; inspect, never overwrite')
    with tempfile.TemporaryDirectory() as temporary:
        for path in sorted(directory.iterdir()):
            if path.name in existing:
                subprocess.run(['gh', 'release', 'download', tag, '--repo', REPOSITORY,
                                '--pattern', path.name, '--dir', temporary], check=True)
                if (Path(temporary) / path.name).read_bytes() != path.read_bytes():
                    raise ValueError('existing release asset differs; never overwrite')
            else:
                subprocess.run(['gh', 'release', 'upload', tag, '--repo', REPOSITORY, str(path)], check=True)
    final = gh_json(release_path)
    if {a['name'] for a in final['assets']} != expected:
        raise ValueError('release asset set incomplete')
    if final['draft']:
        subprocess.run(['gh', 'release', 'edit', tag, '--repo', REPOSITORY,
                        '--verify-tag', '--draft=false', '--latest=false'], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['source', 'absent', 'check', 'stage', 'installed', 'crate-public', 'pypi-public', 'sums', 'merge', 'assets'])
    parser.add_argument('--directory', type=Path, default=Path('target/release-artifacts'))
    parser.add_argument('--incoming', type=Path, default=Path('target/incoming'))
    parser.add_argument('--wheel', type=Path)
    parser.add_argument('--registry', choices=['both', 'crates', 'pypi'], default='both')
    args = parser.parse_args()
    version = os.environ.get('RELEASE_VERSION', os.environ['GITHUB_REF_NAME'].removeprefix('v'))
    commit = os.environ.get('RELEASE_COMMIT', os.environ['GITHUB_SHA'])
    context(version, commit)
    if args.mode == 'source':
        source_guard(version, commit)
        with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as stream:
            stream.write(f'version={version}\ncommit={commit}\n')
    elif args.mode == 'absent':
        absent(version, args.registry)
    elif args.mode == 'stage':
        stage(args.incoming, args.directory, version, commit)
    elif args.mode == 'installed':
        installed(args.wheel.resolve(strict=True), version, commit, args.directory / 'windows-consumer.json')
    elif args.mode == 'sums':
        checksums(args.directory)
    elif args.mode == 'merge':
        merge_evidence(args.incoming, args.directory, version, commit)
    else:
        record = check(args.directory, version, commit)
        if args.mode == 'crate-public':
            crate_public(args.directory, record)
        elif args.mode == 'pypi-public':
            pypi_public(args.directory, record)
        elif args.mode == 'assets':
            release_assets(args.directory, record)


if __name__ == '__main__':
    main()
