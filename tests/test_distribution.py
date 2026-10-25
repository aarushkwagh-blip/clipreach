import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


installer = load('installer', ROOT / 'install.py')
packaging = load('packaging', ROOT / 'scripts/package.py')
setup = load('setup_clipreach', ROOT / 'skills/clipreach/scripts/setup.py')


class DistributionTests(unittest.TestCase):
    def test_every_agent_installs_complete_skill_and_preserves_existing_edits(self):
        for scope, mapping in [('user', installer.USER_PATHS), ('project', installer.PROJECT_PATHS)]:
            for agent, relative in mapping.items():
                with self.subTest(scope=scope, agent=agent), tempfile.TemporaryDirectory() as temp:
                    command = [sys.executable, str(ROOT / 'install.py'), '--agent', agent, '--scope', scope,
                               '--home', temp, '--project', temp]
                    result = subprocess.run(command + ['--dry-run'], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    target = Path(temp) / relative / 'clipreach'
                    self.assertFalse(target.exists())
                    for _ in range(2):
                        result = subprocess.run(command, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue((target / 'scripts/setup.py').is_file())
                    self.assertTrue((target / 'scripts/clipreach.py').is_file())
                    self.assertTrue((target / 'requirements.txt').is_file())
                    (target / 'SKILL.md').write_text('my edits')
                    result = subprocess.run(command, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual((target / 'SKILL.md').read_text(), 'my edits')

    def test_archives_have_components_without_marketplace_caches_or_media(self):
        with tempfile.TemporaryDirectory() as temp:
            packaging.build(temp)
            for name in ['clipreach.zip', 'clipreach-plugin.zip']:
                with ZipFile(Path(temp) / name) as archive:
                    names = archive.namelist()
                    self.assertEqual(len(names), len(set(names)))
                    self.assertIsNone(archive.testzip())
                    self.assertTrue(all(n.startswith('clipreach/') for n in names))
                    self.assertFalse(any('marketplace.json' in n or '__pycache__' in n or '/._' in n or n.endswith('.mp4') for n in names))
                    skill = 'clipreach/skills/clipreach' if name.endswith('-plugin.zip') else 'clipreach'
                    self.assertIn(f'{skill}/SKILL.md', names)
                    self.assertIn(f'{skill}/scripts/setup.py', names)
                    self.assertIn(f'{skill}/requirements.txt', names)
                    if name.endswith('-plugin.zip'):
                        manifest = json.loads(archive.read('clipreach/plugin.json'))
                        self.assertEqual(manifest['name'], 'clipreach')
                        self.assertLessEqual(len(manifest['extensions']['com.openai']['interface']['shortDescription']), 30)

    def test_versions_and_requirements_stay_in_sync(self):
        paths = ['plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json', 'gemini-extension.json']
        self.assertEqual({json.loads((ROOT / p).read_text())['version'] for p in paths}, {'0.2.0'})
        self.assertEqual((ROOT / 'requirements.txt').read_bytes(), (ROOT / 'skills/clipreach/requirements.txt').read_bytes())

    def test_setup_check_does_not_create_a_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / 'not-created'
            result = subprocess.run([sys.executable, str(ROOT / 'skills/clipreach/scripts/setup.py'), '--runtime', str(runtime)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(runtime.exists())

    def test_setup_refuses_an_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / 'keep.txt'
            marker.write_text('keep')
            result = subprocess.run([sys.executable, str(ROOT / 'skills/clipreach/scripts/setup.py'), '--install', '--runtime', temp], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(marker.read_text(), 'keep')
            self.assertFalse((Path(temp) / 'pyvenv.cfg').exists())


if __name__ == '__main__':
    unittest.main()
