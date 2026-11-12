"""Exercise the actual development distribution, not DayZ gameplay."""

import hashlib
import importlib.util
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile


REPOSITORY = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("wgza_build", REPOSITORY / "tools/build.py")
build_tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_tool)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()
        for name in ("WGZA_DogTags", "packaging", "docs", "server"):
            shutil.copytree(REPOSITORY / name, self.repository / name)
        self.source = self.repository / "WGZA_DogTags"
        self.output = self.root / "output"

    def test_pbo_header_and_source_payloads(self):
        data = build_tool.pack_pbo(self.source)
        # Assert public wire-format fields independently of the production reader.
        self.assertEqual(data[:21], b"\0" + struct.pack("<5I", 0x56657273, 0, 0, 0, 0))
        self.assertEqual(data[21:42], b"prefix\0WGZA_DogTags\0\0"[:21])
        self.assertEqual(data[-21:-20], b"\0")
        self.assertEqual(hashlib.sha1(data[:-21]).digest(), data[-20:])
        recovered = build_tool.verify_pbo(data)
        source_files = {str(p.relative_to(self.source)).replace("/", "\\"): p.read_bytes() for p in self.source.rglob("*") if p.is_file() and p.name != "$PBOPREFIX$"}
        self.assertEqual(recovered, source_files)

    def test_distribution_contains_checksums_and_required_server_config(self):
        destination = build_tool.build(self.repository, self.output)
        with zipfile.ZipFile(destination) as archive:
            self.assertIsNone(archive.testzip())
            names = set(archive.namelist())
            self.assertEqual(names, {
                "@WGZA_DogTags/Addons/WGZA_DogTags.pbo",
                "@WGZA_DogTags/mod.cpp",
                "@WGZA_DogTags/TESTING.md",
                "@WGZA_DogTags/server/README.md",
                "@WGZA_DogTags/server/types_WGZA_DogTags.xml",
                "@WGZA_DogTags/SHA256SUMS",
            })
            for line in archive.read("@WGZA_DogTags/SHA256SUMS").decode().splitlines():
                expected, name = line.split("  ", 1)
                self.assertEqual(hashlib.sha256(archive.read("@WGZA_DogTags/" + name)).hexdigest(), expected)
            root = ET.fromstring(archive.read("@WGZA_DogTags/server/types_WGZA_DogTags.xml"))
            tag = root.find("type[@name='WGZA_DogTag']")
            self.assertIsNotNone(tag)
            self.assertEqual(tag.findtext("nominal"), "0")
            self.assertEqual(tag.findtext("min"), "0")
            self.assertGreater(int(tag.findtext("lifetime")), 0)

    def test_build_is_repeatable_and_does_not_modify_source(self):
        before = {str(p.relative_to(self.repository)): p.read_bytes() for p in self.repository.rglob("*") if p.is_file()}
        first = build_tool.build(self.repository, self.output).read_bytes()
        # Timestamps and irrelevant files must not change distribution bytes.
        (self.repository / "local-secret.env").write_text("do-not-distribute")
        for path in self.source.rglob("*"):
            if path.is_file():
                import os
                os.utime(path, (123, 123))
        second = build_tool.build(self.repository, self.output).read_bytes()
        self.assertEqual(first, second)
        for name, content in before.items():
            self.assertEqual((self.repository / name).read_bytes(), content)
        self.assertNotIn(b"do-not-distribute", build_tool.pack_pbo(self.source))

    def test_rejects_checksum_corruption(self):
        data = bytearray(build_tool.pack_pbo(self.source))
        data[-30] ^= 1
        with self.assertRaisesRegex(ValueError, "checksum"):
            build_tool.verify_pbo(bytes(data))

    def test_rejects_truncated_archive(self):
        data = build_tool.pack_pbo(self.source)
        for removed in (1, 21, len(data) - 1):
            with self.subTest(removed=removed), self.assertRaises(ValueError):
                build_tool.verify_pbo(data[:-removed])

    def test_rejects_unindexed_payload_even_with_correct_checksum(self):
        data = build_tool.pack_pbo(self.source)
        body = data[:-21] + b"unexpected"
        forged = body + b"\0" + hashlib.sha1(body).digest()
        with self.assertRaisesRegex(ValueError, "Unexpected bytes"):
            build_tool.verify_pbo(forged)

    def test_rejects_case_collisions(self):
        (self.source / "CONFIG.cpp").write_text("collision")
        with self.assertRaisesRegex(ValueError, "collision"):
            build_tool.pack_pbo(self.source)

    def test_rejects_symlinked_source_files_and_directories(self):
        external = self.root / "private.txt"
        external.write_text("private")
        link = self.source / "private.c"
        link.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build_tool.pack_pbo(self.source)
        link.unlink()
        (self.source / "external").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build_tool.pack_pbo(self.source)

    def test_rejects_accidental_credentials_inside_addon(self):
        for name in (".env", "credentials.json", "server.log"):
            with self.subTest(name=name):
                path = self.source / name
                path.write_text("private")
                with self.assertRaisesRegex(ValueError, "Unexpected runtime file"):
                    build_tool.pack_pbo(self.source)
                path.unlink()

    def test_rejects_wrong_prefix_or_missing_script_module(self):
        prefix = self.source / "$PBOPREFIX$"
        prefix.write_text("WrongPrefix")
        with self.assertRaisesRegex(ValueError, "prefix"):
            build_tool.pack_pbo(self.source)
        prefix.write_text("WGZA_DogTags\n")
        shutil.rmtree(self.source / "scripts/5_Mission")
        with self.assertRaisesRegex(ValueError, "5_Mission"):
            build_tool.pack_pbo(self.source)

    def test_rejects_output_inside_source(self):
        for output in (self.repository, self.source, self.source / "dist"):
            with self.subTest(output=output), self.assertRaisesRegex(ValueError, "output"):
                build_tool.build(self.repository, output)

    def test_does_not_follow_existing_output_file_symlink(self):
        self.output.mkdir()
        victim = self.root / "keep.txt"
        victim.write_text("keep")
        (self.output / "WGZA_DogTags-dev.zip").symlink_to(victim)
        with self.assertRaisesRegex(ValueError, "symlinked ZIP"):
            build_tool.build(self.repository, self.output)
        self.assertEqual(victim.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
