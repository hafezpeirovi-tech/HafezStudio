import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
from autocut import write_director_youtube_package


class DirectorYoutubePackageTests(unittest.TestCase):
    def fixture(self):
        return {
            "name": "03 - Hafez Director Cut",
            "timeline_duration": 70.0,
            "mapping": [
                {"old_start": 0.0, "old_end": 10.0, "new_start": 0.0, "new_end": 10.0},
                {"old_start": 30.0, "old_end": 90.0, "new_start": 10.0, "new_end": 70.0},
            ],
        }

    def render(self, chapters, markers=(), segments=None):
        variant = self.fixture()
        youtube = {"chapters": chapters, "description": "متن گوینده بدون بازنویسی"}
        segments = segments or [{"id": 1, "start": 40.0}, {"id": 2, "start": 20.0}, {"id": 3, "start": 90.0}]
        inputs = copy.deepcopy((youtube, segments, variant, markers))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "youtube.md"
            write_director_youtube_package(str(path), youtube, segments, variant, list(markers))
            result = path.read_text(encoding="utf-8-sig")
        self.assertEqual((youtube, segments, variant, markers), inputs)
        return result

    def test_chapter_uses_director_clock_not_prepare_or_safe(self):
        result = self.render([{"segment_id": 1, "title": "اسکرینر"}])
        self.assertIn("00:20 اسکرینر", result)
        self.assertNotIn("00:40 اسکرینر", result)
        self.assertIn("03 - Hafez Director Cut", result)

    def test_removed_segment_and_end_boundary_cannot_be_chapters(self):
        result = self.render([
            {"segment_id": 2, "title": "حذف‌شده"},
            {"segment_id": 3, "title": "خارج از ویدیو"},
        ])
        self.assertNotIn("حذف‌شده", result)
        self.assertNotIn("خارج از ویدیو", result)

    def test_director_marker_is_already_mapped_and_not_remapped(self):
        result = self.render([], [{"type": "CHAPTER", "start": 50.0, "comment": "بک‌تست"}])
        self.assertIn("00:50 بک‌تست", result)
        self.assertNotIn("00:30 بک‌تست", result)

    def test_outside_director_markers_are_rejected(self):
        result = self.render([], [
            {"type": "CHAPTER", "start": -25.0, "comment": "منفی"},
            {"type": "CHAPTER", "start": 70.0, "comment": "بعد از پایان"},
        ])
        self.assertNotIn("منفی", result)
        self.assertNotIn("بعد از پایان", result)

    def test_package_is_explicitly_draft_and_does_not_rewrite_description(self):
        result = self.render([])
        self.assertIn("نیازمند بازبینی", result)
        self.assertIn("تأیید آماده‌بودن برای انتشار نیست", result)
        self.assertIn("متن گوینده بدون بازنویسی", result)


if __name__ == "__main__":
    unittest.main()
