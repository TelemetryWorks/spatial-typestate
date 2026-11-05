"""Installed resource checks; content/source-byte checks also run at build time."""
import hashlib
import importlib.metadata
import importlib.resources
import json
import unittest


class ProvenanceTests(unittest.TestCase):
    def test_installed_record_and_compiler_notices(self):
        package=importlib.resources.files("spatial_typestate")
        record=json.loads(package.joinpath("_provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(record["artifact_kind"],"wheel")
        self.assertEqual(record["source"]["versions"]["python"],importlib.metadata.version("spatial-typestate"))
        self.assertEqual(record["source"]["versions"]["native"],record["source"]["versions"]["python"])
        files=record["source"]["files"]
        canonical=json.dumps(files,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(),record["source"]["sha256_lf"])
        self.assertTrue(record["build"]["locked"])
        notices=record["build"]["compiler_notices"]
        self.assertEqual(notices["state"],"present")
        for name,expected in notices["files"].items():
            self.assertEqual(hashlib.sha256(package.joinpath("_compiler_notices",name).read_bytes()).hexdigest(),expected)


if __name__=="__main__": unittest.main()
