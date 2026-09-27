import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("upscale_worker", Path(__file__).resolve().parents[1] / "electron/upscale-worker.py")
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

class UpscaleTests(unittest.TestCase):
    def info(self, **changes):
        return {"streams": [{"codec_type": "video", "pix_fmt": "yuv420p", "avg_frame_rate": "30000/1001", "r_frame_rate": "30000/1001", **changes}]}

    def test_sdr(self):
        self.assertAlmostEqual(worker.validate_video(self.info())[1], 29.97002997)

    def test_accept_10bit_sdr(self):
        self.assertAlmostEqual(worker.validate_video(self.info(pix_fmt="yuv422p10le"))[1], 29.97002997)

    def test_reject_hdr(self):
        with self.assertRaisesRegex(ValueError, "HDR"):
            worker.validate_video(self.info(color_transfer="smpte2084"))

    def test_reject_vfr(self):
        with self.assertRaisesRegex(ValueError, "Variable"):
            worker.validate_video(self.info(avg_frame_rate="29900/1001"))

    def test_reject_rotation(self):
        with self.assertRaisesRegex(ValueError, "Rotated"):
            worker.validate_video(self.info(side_data_list=[{"rotation": 90}]))

    def test_reject_interlaced(self):
        with self.assertRaisesRegex(ValueError, "Interlaced"):
            worker.validate_video(self.info(field_order="tt"))

    def test_quality_no_noise(self):
        args = worker.seed_arguments(Path("runtime"), Path("in.mov"), Path("out.mp4"), 1080)
        self.assertEqual(args[args.index("--dit_model") + 1], "seedvr2_ema_3b_fp16.safetensors")
        self.assertEqual(args[args.index("--input_noise_scale") + 1], "0")
        self.assertEqual(args[args.index("--color_correction") + 1], "lab")
        self.assertIn("--uniform_batch_size", args)
        self.assertIn("--temporal_overlap", args)

if __name__ == "__main__":
    unittest.main()
