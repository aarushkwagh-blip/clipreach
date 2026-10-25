import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/clipreach/scripts/clipreach.py'
spec = importlib.util.spec_from_file_location('clipreach', SCRIPT)
clipreach = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clipreach)


class ValidationTests(unittest.TestCase):
    def test_plan_rejects_invalid_or_unsafe_values(self):
        valid = {'title': 'A useful moment', 'start': 2, 'end': 8}
        self.assertEqual(clipreach.validate_plan({'clips': [valid]}, 10), [valid])
        for update in ({'start': -1}, {'end': 11}, {'end': 2}, {'start': True},
                       {'end': float('nan')}, {'focus_x': 2}, {'layout': 'shell'}, {'title': ''}):
            with self.subTest(update=update), self.assertRaises(ValueError):
                clipreach.validate_plan({'clips': [{**valid, **update}]}, 10)

    def test_transcript_rejects_unordered_or_outside_word_times(self):
        valid = {'start': 1, 'end': 4, 'text': 'Hello world', 'words': [
            {'start': 1, 'end': 2, 'word': 'Hello'}, {'start': 2, 'end': 3, 'word': 'world'}]}
        self.assertEqual(clipreach.validate_transcript({'segments': [valid]}, 10), [valid])
        for words in ([{'start': 0, 'end': 2, 'word': 'bad'}],
                      [{'start': 1, 'end': 5, 'word': 'bad'}],
                      [{'start': 2, 'end': 3, 'word': 'first'}, {'start': 1, 'end': 2, 'word': 'second'}]):
            with self.subTest(words=words), self.assertRaises(ValueError):
                clipreach.validate_transcript({'segments': [{**valid, 'words': words}]}, 10)

    def test_captions_trim_rebase_and_escape_transcript_text(self):
        segments = [{'start': 9, 'end': 12, 'text': 'Hello {\\pos(0,0)} world'}]
        result = clipreach.captions(segments, 10, 11, 1080, 1920)
        self.assertIn('Dialogue: 0,0:00:00.00,0:00:01.00', result)
        self.assertNotIn('{\\pos', result)
        self.assertIn('｛＼pos(0,0)｝', result)

    def test_word_captions_keep_actual_gaps_and_clip_boundaries(self):
        segments = [{'start': 10, 'end': 12, 'text': 'Hello world', 'words': [
            {'start': 10, 'end': 10.5, 'word': 'Hello'}, {'start': 10.7, 'end': 11, 'word': 'world'}]}]
        result = clipreach.captions(segments, 10.2, 11.5, 1080, 1920)
        self.assertIn('Dialogue: 0,0:00:00.00,0:00:00.80', result)
        self.assertIn('{\\kf30}Hello {\\k20}{\\kf30}world', result)
        self.assertEqual(clipreach.ass_time(59.999), '0:01:00.00')

    def test_invalid_url_fails_before_download(self):
        for url in ['file:///etc/passwd', 'javascript:alert(1)', 'not-a-url']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                clipreach.download(type('Args', (), {'url': url, 'out': 'unused'})())

    def test_doctor_reports_missing_caption_support(self):
        fake = subprocess.CompletedProcess([], 0, stdout='', stderr='')
        with contextlib.redirect_stdout(io.StringIO()), patch.object(clipreach.shutil, 'which', return_value='/bin/ffmpeg'), patch.object(clipreach, 'run', return_value=fake):
            self.assertEqual(clipreach.doctor(None), 1)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        filters = subprocess.run(['ffmpeg', '-hide_banner', '-filters'], capture_output=True, text=True, check=True).stdout
        encoders = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True, check=True).stdout
        if ' ass ' not in filters or 'libx264' not in encoders:
            raise unittest.SkipTest('FFmpeg needs libass and libx264')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="clipreach test's ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.video = self.root / "source's video.mp4"
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-f', 'lavfi', '-i', 'testsrc2=size=320x180:rate=25',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100', '-t', '4',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(self.video)], check=True)
        self.transcript = self.root / 'transcript.json'
        self.transcript.write_text(json.dumps({'segments': [{'start': 0, 'end': 4, 'text': 'A caption in the clip.'}]}))
        self.plan = self.root / 'plan.json'

    def command(self, out, *extra):
        return [sys.executable, str(SCRIPT), 'render', str(self.video), '--transcript', str(self.transcript),
                '--plan', str(self.plan), '--out', str(out), '--width', '180', *extra]

    def test_real_render_both_layouts_and_no_overwrite(self):
        self.plan.write_text(json.dumps({'clips': [
            {'title': '../../outside', 'start': 0.5, 'end': 2, 'layout': 'pad'},
            {'title': 'Crop right', 'start': 2, 'end': 3.5, 'layout': 'crop', 'focus_x': 1}]}))
        out = self.root / 'clips'
        subprocess.run(self.command(out), capture_output=True, text=True, check=True)
        manifest = json.loads((out / 'clips.json').read_text())
        self.assertEqual(len(manifest['clips']), 2)
        for item in manifest['clips']:
            info = clipreach.probe(out / item['file'])
            self.assertEqual((info['width'], info['height']), (180, 320))
            self.assertTrue(info['audio'])
            self.assertAlmostEqual(info['duration'], 1.5, delta=0.15)
            self.assertIn('Dialogue:', (out / item['captions']).read_text())
        before = (out / 'clip-001.mp4').read_bytes()
        result = subprocess.run(self.command(out), capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((out / 'clip-001.mp4').read_bytes(), before)
        self.assertFalse((self.root / 'outside.mp4').exists())

    def test_invalid_later_clip_creates_no_partial_output(self):
        self.plan.write_text(json.dumps({'clips': [
            {'title': 'Valid', 'start': 0, 'end': 1}, {'title': 'Outside', 'start': 2, 'end': 9}]}))
        out = self.root / 'invalid-clips'
        result = subprocess.run(self.command(out), capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(out.exists())
        self.assertTrue(self.video.exists())

    def test_silent_video_still_renders(self):
        silent = self.root / 'silent.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-i', str(self.video), '-an', '-c:v', 'copy', str(silent)], check=True)
        self.video = silent
        self.plan.write_text(json.dumps({'clips': [{'title': 'Silent clip', 'start': 0, 'end': 1}]}))
        out = self.root / 'silent-clips'
        subprocess.run(self.command(out), capture_output=True, text=True, check=True)
        self.assertFalse(clipreach.probe(out / 'clip-001.mp4')['audio'])


if __name__ == '__main__':
    unittest.main()
