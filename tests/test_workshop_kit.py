"""Validate what will be handed to the Windows publisher, not native signing."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('workshop_kit', ROOT / 'tools/workshop_kit.py')
KIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(KIT)


class WorkshopKitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repository = self.root / 'repository'
        for folder in ('WGZA_DogTags', 'server', 'tools', 'packaging', 'docs', 'assets'):
            shutil.copytree(ROOT / folder, self.repository / folder)

    def test_kit_retains_source_prefix_and_windows_publishing_inputs(self):
        destination = KIT.build_kit(self.repository, self.root / 'output')
        original = destination.read_bytes()
        self.assertEqual(KIT.build_kit(self.repository, self.root / 'output').read_bytes(), original)
        with zipfile.ZipFile(destination) as archive:
            self.assertIsNone(archive.testzip())
            prefix = 'WGZA_DogTags-Workshop-kit/'
            for file in (self.repository / 'WGZA_DogTags').rglob('*'):
                if file.is_file():
                    self.assertEqual(archive.read(prefix + file.relative_to(self.repository).as_posix()), file.read_bytes())
            for name in ('tools/Prepare-Workshop.ps1', 'packaging/mod.cpp', 'assets/wgza_tag_preview.png', 'docs/WORKSHOP.md', 'server/types_WGZA_DogTags.xml'):
                self.assertIn(prefix + name, archive.namelist())
            self.assertFalse(any(name.endswith(('.biprivatekey', '.pem', '.key', '.pbo', '.blend')) for name in archive.namelist()))

    def test_private_signing_keys_cannot_enter_addon_source_kit(self):
        (self.repository / 'WGZA_DogTags/private.biprivatekey').write_bytes(b'secret-test-fixture')
        with self.assertRaisesRegex(ValueError, 'Unexpected file'):
            KIT.build_kit(self.repository, self.root / 'output')

    def test_symlinked_source_cannot_read_outside_kit(self):
        outside = self.root / 'outside.c'
        outside.write_text('not-for-upload')
        (self.repository / 'WGZA_DogTags/link.c').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'Unsafe kit path'):
            KIT.build_kit(self.repository, self.root / 'output')
