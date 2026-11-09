"""Required public project fields must survive metadata preparation and rebuilds."""
from email.parser import Parser
from pathlib import Path
import io
import json
import tarfile
import tempfile
import zipfile
import sys
import tomllib
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import check_package_metadata as metadata


class ProjectMetadataTests(unittest.TestCase):
    @staticmethod
    def valid():
        return Parser().parsestr(
            "Metadata-Version: 2.4\n"
            "Name: spatial-typestate\nVersion: 0.1.0\n"
            "License-Expression: Apache-2.0\nLicense-File: LICENSE\n"
            "Project-URL: Repository, https://github.com/TelemetryWorks/spatial-typestate\n"
            "Project-URL: Documentation, https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/PYTHON-GUIDE.md\n"
            "Project-URL: Issues, https://github.com/TelemetryWorks/spatial-typestate/issues\n"
            "\nDescription fixture\n"
        )

    def test_valid_static_fields_and_extra_license_files(self):
        message = self.valid()
        message["License-File"] = "licenses/dependency/LICENSE"
        self.assertIsNone(metadata.validate_project_metadata(message))

    def test_project_url_multiset_rejects_missing_wrong_extra_duplicate(self):
        for kind in ("missing", "wrong", "extra", "duplicate"):
            with self.subTest(kind=kind):
                message = self.valid()
                urls = message.get_all("Project-URL")
                del message["Project-URL"]
                if kind == "missing":
                    urls.pop()
                elif kind == "wrong":
                    urls[-1] = "Issues, https://example.invalid/issues"
                elif kind == "extra":
                    urls.append("Homepage, https://example.invalid")
                else:
                    urls[-1] = urls[0]
                for url in urls:
                    message["Project-URL"] = url
                with self.assertRaisesRegex(ValueError, "unexpected Project-URL values"):
                    metadata.validate_project_metadata(message)

    def test_missing_and_altered_license_expression(self):
        for value in (None, "MIT"):
            with self.subTest(value=value):
                message = self.valid()
                del message["License-Expression"]
                if value is not None:
                    message["License-Expression"] = value
                with self.assertRaisesRegex(ValueError, "unexpected License-Expression"):
                    metadata.validate_project_metadata(message)

    def test_legacy_license_and_missing_license_file(self):
        message = self.valid()
        message["License"] = "Apache-2.0"
        with self.assertRaisesRegex(ValueError, "legacy License field must be absent"):
            metadata.validate_project_metadata(message)
        del message["License"]
        del message["License-File"]
        with self.assertRaisesRegex(ValueError, "missing project License-File"):
            metadata.validate_project_metadata(message)

    def test_dynamic_fields_cannot_bypass_static_validation(self):
        for field in ("Project-URL", "License-Expression"):
            with self.subTest(field=field):
                message = self.valid()
                message["Dynamic"] = field
                with self.assertRaisesRegex(ValueError, "project metadata must not be Dynamic"):
                    metadata.validate_project_metadata(message)

    def test_metadata_version_is_explicit(self):
        message = self.valid()
        message.replace_header("Metadata-Version", "2.3")
        with self.assertRaisesRegex(ValueError, "unexpected Metadata-Version"):
            metadata.validate_project_metadata(message)

    @staticmethod
    def write_wheel(path, message, origin):
        with zipfile.ZipFile(path, "w") as wheel:
            wheel.writestr("spatial_typestate-0.1.0.dist-info/METADATA", message.as_bytes(policy=message.policy.clone(max_line_length=0)))
            wheel.writestr("spatial_typestate-0.1.0.dist-info/licenses/LICENSE", "fixture licence")
            wheel.writestr("spatial_typestate/_provenance.json", json.dumps({
                "source": {"fixture": "same source"}, "source_origin": origin,
            }))

    def prepared_fixture(self, root, message):
        info = root / "prepared/spatial_typestate-0.1.0.dist-info"
        (info / "licenses").mkdir(parents=True)
        (info / "METADATA").write_bytes(message.as_bytes(policy=message.policy.clone(max_line_length=0)))
        (info / "licenses/LICENSE").write_text("fixture licence", encoding="utf-8")
        self.write_wheel(root / "fixture.whl", message, "checkout")

    def sdist_fixture(self, root, message):
        (root / "from-sdist").mkdir()
        source = {"artifact_kind": "sdist", "source": {"fixture": "same source"}}
        with tarfile.open(root / "fixture.tar.gz", "w:gz") as archive:
            for name, raw in {
                "fixture/PKG-INFO": message.as_bytes(policy=message.policy.clone(max_line_length=0)),
                "fixture/spatial_typestate/_provenance.json": json.dumps(source).encode(),
            }.items():
                member = tarfile.TarInfo(name)
                member.size = len(raw)
                archive.addfile(member, io.BytesIO(raw))
        self.write_wheel(root / "fixture.whl", message, "checkout")
        self.write_wheel(root / "from-sdist/fixture.whl", message, "sdist")

    def test_prepared_entrypoint_rejects_matching_omissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            message = self.valid()
            del message["Project-URL"]
            self.prepared_fixture(root, message)
            # Parity succeeds, but neither metadata surface has the required URLs.
            with self.assertRaisesRegex(ValueError, "unexpected Project-URL values"):
                metadata.verify_prepared(root)

    def test_sdist_entrypoint_rejects_matching_omissions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            message = self.valid()
            del message["Project-URL"]
            self.sdist_fixture(root, message)
            # Only archive-structure inspection is outside this fixture's scope.
            with patch.object(metadata, "sdist_report", return_value={}):
                with self.assertRaisesRegex(ValueError, "unexpected Project-URL values"):
                    metadata.verify(root)

    def test_prepared_entrypoint_validates_each_surface(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.prepared_fixture(root, self.valid())
            with patch.object(metadata, "validate_project_metadata", wraps=metadata.validate_project_metadata) as validate:
                metadata.verify_prepared(root)
            self.assertEqual(validate.call_count, 2)
            self.assertIsNot(validate.call_args_list[0].args[0], validate.call_args_list[1].args[0])

    def test_sdist_entrypoint_validates_each_surface(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.sdist_fixture(root, self.valid())
            with (patch.object(metadata, "sdist_report", return_value={}),
                  patch.object(metadata, "validate_project_metadata", wraps=metadata.validate_project_metadata) as validate):
                metadata.verify(root)
            self.assertEqual(validate.call_count, 2)
            self.assertIsNot(validate.call_args_list[0].args[0], validate.call_args_list[1].args[0])

    def test_manifest_agrees_with_independent_public_targets_and_license(self):
        project = tomllib.loads((PROJECT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(project["urls"], {
            "Repository": "https://github.com/TelemetryWorks/spatial-typestate",
            "Documentation": "https://github.com/TelemetryWorks/spatial-typestate/blob/main/docs/PYTHON-GUIDE.md",
            "Issues": "https://github.com/TelemetryWorks/spatial-typestate/issues",
        })
        self.assertEqual(project["license"], "Apache-2.0")
        self.assertEqual(project["license-files"], ["LICENSE", "licenses/**/*"])
        self.assertNotIn("dynamic", project)


if __name__ == "__main__":
    unittest.main()
