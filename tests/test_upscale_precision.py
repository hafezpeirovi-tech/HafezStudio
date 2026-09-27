"""CPU-only tests for the exact I/O adapter used by SeedVR2."""
import importlib.util
import io
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location("bridge", Path(__file__).resolve().parents[1] / "electron/upscale-seed-bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

class PrecisionTests(unittest.TestCase):
    def test_decoder_preserves_sub_8bit_values(self):
        cap = object.__new__(bridge.Capture16)
        cap.width, cap.height = 2, 1
        values = np.array([[[32768, 32769, 32770], [32771, 32772, 32773]]], dtype="<u2")
        cap.proc = type("Process", (), {"stdout": io.BytesIO(values.tobytes())})()
        result = cap.read_rgb()
        self.assertEqual(result.dtype, np.float32)
        self.assertEqual(len(np.unique(result)), 6)
        np.testing.assert_allclose(result * 65535, values, atol=.004)

    def test_encoder_preserves_sub_8bit_values(self):
        import torch
        sink = io.BytesIO()
        writer = object.__new__(bridge.Writer16)
        writer.proc = type("Process", (), {"stdin": sink})()
        values = np.arange(32768, 32774, dtype="<u2").reshape(1, 1, 2, 3)
        writer.write(torch.tensor(values.astype(np.float32) / 65535))
        np.testing.assert_array_equal(np.frombuffer(sink.getvalue(), dtype="<u2"), values.flatten())

    def test_partial_frame_rejected(self):
        cap = object.__new__(bridge.Capture16)
        cap.width, cap.height = 2, 1
        cap.proc = type("Process", (), {"stdout": io.BytesIO(b"abc")})()
        with self.assertRaisesRegex(RuntimeError, "Truncated"):
            cap.read_rgb()

if __name__ == "__main__":
    unittest.main()
