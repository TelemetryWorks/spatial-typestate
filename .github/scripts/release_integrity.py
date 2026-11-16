"""Verify every retained PyPI publish attestation; never sign or upload anything."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_guard as guard

ISSUER = 'https://token.actions.githubusercontent.com'
OID = '1.3.6.1.4.1.57264.1.'
PREDICATE = 'https://docs.pypi.org/attestations/publish/v1'


def verify_claims(claims, version, commit):
    repository = 'https://github.com/' + guard.REPOSITORY
    expected = {'8': ISSUER, '9': repository + '/' + guard.WORKFLOW + '@refs/tags/v' + version,
                '10': commit, '11': 'github-hosted', '12': repository, '13': commit,
                '14': 'refs/tags/v' + version, '18': repository + '/' + guard.WORKFLOW + '@refs/tags/v' + version,
                '19': commit}
    if any(claims.get(OID + key) != value for key, value in expected.items()):
        raise ValueError('PyPI certificate issuer/repository/workflow/ref/source identity mismatch')


def verify_file(path, provenance, version, commit, offline=False):
    if path.name not in guard.names(version)[1:]:
        raise ValueError('unexpected Python release filename')
    # Import only on the verification path; normal pipeline unit tests use fixtures.
    from pypi_attestations import Distribution, GitHubPublisher, Provenance
    expected = GitHubPublisher(repository=guard.REPOSITORY, workflow=Path(guard.WORKFLOW).name, environment='pypi')
    record = Provenance.model_validate(provenance)
    if not record.attestation_bundles:
        raise ValueError('PyPI provenance has no bundles')
    bundles = []
    for group in record.attestation_bundles:
        if group.publisher != expected or not group.attestations:
            raise ValueError('PyPI Trusted Publisher/environment differs')
        for attestation in group.attestations:
            # This validates certificate chain, transparency evidence, identity and
            # the single distribution subject digest BEFORE trusting certificate claims.
            predicate, _ = attestation.verify(expected, Distribution.from_file(path), offline=offline)
            if predicate != PREDICATE:
                raise ValueError('expected a PEP 740 publish attestation')
            verify_claims(attestation.certificate_claims, version, commit)
            bundles.append(attestation.to_bundle().to_json())
    return bundles


def verify(directory, version, commit, offline=False):
    record = guard.check(directory, version, commit)
    receipts = {}
    for name in guard.names(version)[1:]:
        provenance = json.loads((directory / (name + '.pypi-provenance.json')).read_text())
        bundles = verify_file(directory / name, provenance, version, commit, offline)
        # Keep every verified publish bundle as well as the original Integrity API object.
        for index, bundle in enumerate(bundles):
            (directory / (name + f'.publish-{index}.sigstore.json')).write_text(bundle + '\n', encoding='utf-8')
        receipts[name] = {'sha256': record['files'][name], 'verified_publish_bundles': len(bundles),
                          'file_page': f'https://pypi.org/project/{guard.PROJECT}/{version}/#files'}
    guard.write_json(directory / 'pypi-integrity-verified.json', receipts)
    return receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--version', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--offline', action='store_true', help='No TUF refresh; provision verifier trust cache independently first')
    args = parser.parse_args()
    verify(args.directory, args.version, args.commit, args.offline)


if __name__ == '__main__':
    main()
