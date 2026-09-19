"""Local fixture bytes + mocked ASR; no model, media decode, or network calls."""
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine/src/hermes_video"))
import caption_provenance as provenance
from subtitle_pipeline import build_review_segments, build_srt_cues


class CaptionProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.media = Path(self.directory.name) / "synthetic-media.fixture"
        self.content = b"local content identity fixture only"
        self.media.write_bytes(self.content)

    def manifest(self):
        return {"cam1_path": str(self.media), "fps": 25.0, "mapped_words": [],
                "caption_evidence": {"protocol": provenance.PROTOCOL, "source_evidence_id": "run",
                                     "clock": provenance.declared_xml_clock(25.0, 25, "FALSE")},
                "source_word_evidence": {"evidence_id": "run", "kind": "original-asr-not-audio-verified",
                                         "media_identity": {"path": str(self.media),
                                             "strength": provenance.IDENTITY_STRENGTH,
                                             "sha256": hashlib.sha256(self.content).hexdigest()}}}

    def test_streamed_hash_actual_bytes_progress_and_nonmutation(self):
        progress = []
        sha = provenance.hash_media_content(self.media, chunk_bytes=3, progress=lambda *row: progress.append(row))
        self.assertEqual(sha, hashlib.sha256(self.content).hexdigest())
        self.assertEqual(self.media.read_bytes(), self.content)
        self.assertEqual(progress[0][:2], (0, len(self.content)))
        self.assertEqual(progress[-1][:2], (len(self.content), len(self.content)))

    def test_long_hash_emits_periodic_heartbeat_between_start_and_finish(self):
        progress = []
        with patch.object(provenance.time, "monotonic", side_effect=[0, 2.1, 4.2, 6.3, 6.4]):
            provenance.hash_media_content(self.media, chunk_bytes=12, progress=lambda *row: progress.append(row))
        self.assertGreater(len(progress), 2)
        self.assertEqual([row[0] for row in progress], [0, 12, 24, len(self.content), len(self.content)])

    def test_cooperative_cancel_and_keyboard_interrupt_produce_no_hash(self):
        with self.assertRaises(InterruptedError):
            provenance.hash_media_content(self.media, chunk_bytes=3, cancelled=Mock(side_effect=[False, True]))
        with self.assertRaises(KeyboardInterrupt):
            provenance.hash_media_content(self.media, progress=Mock(side_effect=KeyboardInterrupt))
        self.assertEqual(self.media.read_bytes(), self.content)

    def test_source_change_during_hash_is_rejected(self):
        def mutate_at_start(done, total, elapsed):
            if done == 0:
                self.media.write_bytes(self.content + b"changed")
        with self.assertRaisesRegex(RuntimeError, "Source media changed"):
            provenance.hash_media_content(self.media, progress=mutate_at_start)

    def test_exact_declared_ntsc_and_integer_clock_not_guessed_from_float(self):
        clock = provenance.declared_xml_clock(30000 / 1001, 30, "TRUE")
        self.assertEqual((clock["numerator"], clock["denominator"]), (30000, 1001))
        self.assertEqual(clock["origin"], "premiere-xml-export-declared-rate")
        self.assertEqual(provenance.declared_xml_clock(25, 25, "FALSE")["denominator"], 1)
        for rate in (29.97, 29.98, 24.5):
            self.assertEqual(provenance.declared_xml_clock(rate, 30, "TRUE")["status"], "disabled")
        for timebase, ntsc in ((True, "TRUE"), (30, {}), (0, "FALSE"), (30, "unknown")):
            self.assertEqual(provenance.declared_xml_clock(30, timebase, ntsc)["status"], "disabled")

    def test_legacy_manifest_is_no_op_without_even_reading_media(self):
        for legacy in ({}, {"cam1_path": "missing-original", "fps": 25.0},
                       {**self.manifest(), "caption_evidence": {"protocol": "legacy"}}):
            with patch.object(provenance, "hash_media_content") as reader:
                source, report = provenance.verify_fresh_caption_source(legacy, timebase=25, ntsc="FALSE")
            reader.assert_not_called()
            self.assertIsNone(source)
            self.assertEqual(report["reason"], "legacy-no-caption-provenance")

    def test_fresh_source_verification_has_real_hash_rational_clock_and_no_mutation(self):
        manifest = self.manifest()
        original = copy.deepcopy(manifest)
        progress = Mock()
        source, report = provenance.verify_fresh_caption_source(manifest, timebase=25, ntsc="FALSE", progress=progress)
        self.assertEqual(source["media_sha256"], hashlib.sha256(self.content).hexdigest())
        self.assertEqual(source["fps"], (25, 1))
        self.assertTrue(progress.called)
        self.assertFalse(report["publication_ready"])
        self.assertEqual(manifest, original)
        json.dumps(report)

    def test_changed_bytes_even_with_same_size_and_mtime_are_rejected(self):
        manifest = self.manifest()
        old_stat = self.media.stat()
        self.media.write_bytes(b"x" * len(self.content))
        os.utime(self.media, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
        with self.assertRaisesRegex(RuntimeError, "Source media changed since prepare"):
            provenance.verify_fresh_caption_source(manifest, timebase=25, ntsc="FALSE")

    def test_changed_path_missing_fingerprint_and_clock_mismatch_never_authorize(self):
        manifest = self.manifest()
        manifest["source_word_evidence"]["media_identity"]["path"] = str(self.media.with_name("different"))
        with self.assertRaisesRegex(RuntimeError, "identity changed"):
            provenance.verify_fresh_caption_source(manifest, timebase=25, ntsc="FALSE")
        for mutate in (lambda m: m["source_word_evidence"]["media_identity"].pop("sha256"),
                       lambda m: m["caption_evidence"]["clock"].update(denominator=1001),
                       lambda m: m["source_word_evidence"]["media_identity"].update(strength="path-size-mtime-not-content-hash")):
            manifest = self.manifest()
            mutate(manifest)
            source, report = provenance.verify_fresh_caption_source(manifest, timebase=25, ntsc="FALSE")
            self.assertIsNone(source)
            self.assertEqual(report["status"], "disabled")

    def test_unsupported_clock_still_hashes_unchanged_fresh_content(self):
        manifest = self.manifest()
        manifest["fps"] = 29.97
        manifest["caption_evidence"]["clock"] = provenance.declared_xml_clock(29.97, 30, "TRUE")
        with patch.object(provenance, "hash_media_content", wraps=provenance.hash_media_content) as reader:
            source, report = provenance.verify_fresh_caption_source(manifest, timebase=30, ntsc="TRUE")
        reader.assert_called_once()
        self.assertIsNone(source)
        self.assertEqual(report["reason"], "unverified-or-changed-xml-clock")
        self.assertTrue(report["content_verified"])

    def test_unsupported_or_missing_clock_cannot_hide_changed_fresh_content(self):
        for clock in (None, provenance.declared_xml_clock(29.97, 30, "TRUE")):
            with self.subTest(clock=clock):
                manifest = self.manifest()
                manifest["fps"] = 29.97
                manifest["caption_evidence"]["clock"] = clock
                self.media.write_bytes(b"x" * len(self.content))
                with patch.object(provenance, "hash_media_content", wraps=provenance.hash_media_content) as reader:
                    with self.assertRaisesRegex(RuntimeError, "Source media changed since prepare"):
                        provenance.verify_fresh_caption_source(manifest, timebase=30, ntsc="TRUE")
                reader.assert_called_once()
                self.media.write_bytes(self.content)

    def test_exact_final_variant_keep_frames_are_never_rounded_or_mutated(self):
        source, _ = provenance.verify_fresh_caption_source(self.manifest(), timebase=25, ntsc="FALSE")
        clips = [[0, 100, 250, 350]]
        original = copy.deepcopy(clips)
        context = provenance.variant_caption_context(source, clips)
        self.assertEqual([context["keeps"][0][key] for key in
                          ("start_frame", "end_frame", "source_in_frame", "source_out_frame")], clips[0])
        self.assertEqual(clips, original)
        for bad in ([[0.0, 100, 250, 350]], [[False, 100, 250, 350]], [[0, 100]]):
            self.assertIsNone(provenance.variant_caption_context(source, bad))
        self.assertIsNone(provenance.variant_caption_context(None, clips))

    def test_fresh_mocked_asr_reaches_optional_caption_merge_without_fabricated_hash(self):
        import autocut
        asr_segment = SimpleNamespace(text="روش روشن", start=10, end=11.2, avg_logprob=-.1,
            words=[SimpleNamespace(word="روش", start=10, end=10.4, probability=.99),
                   SimpleNamespace(word="روشن", start=10.4, end=11.2, probability=.99)])
        model = Mock()
        model.transcribe.return_value = ([asr_segment], SimpleNamespace(language="fa", language_probability=1))
        evidence = {}
        mapping = [{"orig_start_ms": 10000, "orig_end_ms": 11200, "tl_start_ms": 0, "tl_end_ms": 1200}]
        with patch.object(autocut.ctranslate2, "get_cuda_device_count", return_value=0), patch.object(
                autocut, "WhisperModel", return_value=model), patch.dict("os.environ", {"HERMES_COPY_MODE": "source-faithful"}):
            words = autocut.transcribe_and_map(str(self.media), mapping, [], evidence_sink=evidence)
            segments = build_review_segments(words, max_duration=.5)
            manifest = self.manifest()
            manifest["source_word_evidence"] = evidence
            manifest["mapped_words"] = words
            manifest["caption_evidence"]["source_evidence_id"] = evidence["evidence_id"]
            source, report = provenance.verify_fresh_caption_source(manifest, timebase=25, ntsc="FALSE")
            context = provenance.variant_caption_context(source, [[0, 100, 250, 350]])
            audit = {}
            result = build_srt_cues(segments, caption_context=context, layout_audit=audit)
        model.transcribe.assert_called_once()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "روش روشن")
        self.assertTrue(audit["applied"])
        self.assertEqual(evidence["media_identity"]["sha256"], hashlib.sha256(self.content).hexdigest())
        self.assertEqual(result[0]["source_word_ids"], [word["source_word_id"] for word in words])
        self.assertEqual(self.media.read_bytes(), self.content)
        json.dumps({"source": report, "layout": audit})

    def test_same_stat_content_replacement_during_mocked_asr_cannot_commit_evidence(self):
        import autocut
        initial = self.media.stat()
        def changed_asr(*args, **kwargs):
            self.media.write_bytes(b"x" * len(self.content))
            os.utime(self.media, ns=(initial.st_atime_ns, initial.st_mtime_ns))
            segment = SimpleNamespace(text="روش", start=10, end=10.4, avg_logprob=-.1,
                words=[SimpleNamespace(word="روش", start=10, end=10.4, probability=.99)])
            return [segment], SimpleNamespace(language="fa", language_probability=1)
        model = Mock()
        model.transcribe.side_effect = changed_asr
        evidence = {}
        with patch.object(autocut.ctranslate2, "get_cuda_device_count", return_value=0), patch.object(
                autocut, "WhisperModel", return_value=model), self.assertRaisesRegex(RuntimeError, "content fingerprint mismatch"):
            autocut.transcribe_and_map(str(self.media), [], [], evidence_sink=evidence)
        self.assertEqual(evidence, {})


if __name__ == "__main__":
    unittest.main()
