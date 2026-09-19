"""Regression excerpts from the owner's September 5 cached review markers.

The ASR is deliberately not corrected in these fixtures. Rules must fail closed
on its uncertain fragments instead of presenting them as finished sentences.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine/src/hermes_video"))
from curation_rules import curate_complete_statement, is_complete_statement


def segments(*texts):
    return [{"id": index, "start": index * 8.0, "end": (index + 1) * 8.0, "text": text}
            for index, text in enumerate(texts)]


class SourceBoundaryTests(unittest.TestCase):
    def test_community_independent_prefix_is_selected_without_manual_rewrite(self):
        source = segments(
            "تریدینگ‌ویو یک بخش کامیونیتی داره که برترین استراتژیا و معامله‌گرا می‌گن یک سری اندیکاتور و یک سری",
            "استراتژی‌های خودشون رو اونجا قرار می‌دن به صورت کاملاً رایگان بعضی از این استراتژیا وقتی می‌دازیش",
        )
        decision = curate_complete_statement(source, 0)
        self.assertEqual(decision["text"], "تریدینگ‌ویو یک بخش کامیونیتی داره.")
        self.assertFalse(decision["needs_manual_copy"])
        self.assertEqual(decision["segment_ids"], [0])

    def test_real_analysis_paralysis_clause_survives(self):
        source = segments("به این وضعیت توی روانشناسی ترید می‌گن فلج تحلیلی؛ تو انقدر تایم فریم‌ها و چارت‌ها رو بالا پایین می‌کنی که")
        self.assertEqual(curate_complete_statement(source, 0)["text"], "به این وضعیت توی روانشناسی ترید می‌گن فلج تحلیلی.")

    def test_real_screener_fragment_cannot_jump_to_later_technical_asr(self):
        source = segments(
            "تو نباید دونه دونه چارت‌ها رو باز کنی تا ببینی کدومش داره الان موقعیت معاملاتی مناسبی بهت می‌ده تریدر",
            "باوش می‌ره تو قسمت اسکرینر تریدینگ‌ویو و",
            "می‌گه من نماد‌های رو می‌خوام که EMA‌یشون مثلا",
            "آرس‌های زیر سی دارن و بالای EMA‌ی پنجان یه دکمه می‌زنه",
        )
        decision = curate_complete_statement(source, 0)
        self.assertEqual(decision["text"], "…")
        self.assertTrue(decision["needs_manual_copy"])

    def test_real_cost_fragment_cannot_jump_to_unrelated_complete_sounding_clause(self):
        source = segments(
            "می‌خواد معاملات سوده‌ای داشته باشه پس به نظرم ارزش اون اکانت اسنشیال خریدن برای بک‌تست گرفتن و",
            "دیدن اون استراتیجه توی کامیونیتی واقعاً بالاست این‌که وقت بذاری یک ماهت رو حد اقل یا حد",
            "اکثر که ببینی اصلا چه چیزهایی داره تو کامیونیتی گفته میشه، چه چیزهایی ممکنه بهت کمک بکنه شاید آدمی هستی",
        )
        self.assertEqual(curate_complete_statement(source, 0)["text"], "…")

    def test_price_motion_fragment_and_dangling_modal_are_not_complete(self):
        source = segments(
            "مقدار حرکت قیمتیش واقعا خیلی نزدیکه به بروکر اواندا، تریدینگ‌ویو، یا بروکر‌های معتبر دیگه خیلی",
            "کمکتون میکنه توی بک‌تستی که می‌گیرین یعنی توی بک‌تستی که می‌گیرین می‌بینین معامله‌تون TP خورده ولی ممکنه",
        )
        self.assertEqual(curate_complete_statement(source, 0)["text"], "…")
        for text in (
            "معامله‌تون TP خورده ولی ممکنه.",
            "بعضی از این استراتژیا وقتی می‌دازیش.",
            "این استراتژی وقتی اجرا می‌شه.",
            "این روش برای اجرا شاید.",
        ):
            with self.subTest(text=text):
                self.assertFalse(is_complete_statement(text))

    def test_backtest_counts_do_not_splice_into_following_tp_sl_clause(self):
        source = segments(
            "می‌گه 60 تا معامله بوده، 30 تای سود شده، 20 تای ضرر.",
            "تبقیه TPO اصطابی که اون استراتژی برای تو مشخص میکنه، می‌تونی سود ده بودن یا ضرر ده بودن اون استراتژی رو",
        )
        decision = curate_complete_statement(source, 0)
        self.assertEqual(decision["text"], "…")
        self.assertNotIn("TPO", decision["text"])

    def test_director_marker_mid_sentence_stays_reviewable(self):
        source = segments(
            "کشیدن خط باز می‌کنن و خیلی‌ها از قدرتی که این",
            "تریدینگ‌ویو داره و کارهایی که می‌تونین بهش بکنین واقعاً با خبر نیستید؛ یعنی فقط باز می‌کنین که یک تحلیل رو انجام بدین. اوه، سلام چطوری؟",
        )
        self.assertEqual(curate_complete_statement(source, 0)["text"], "…")

    def test_final_management_clause_keeps_spoken_register(self):
        quote = "و تو فقط وظیفه‌ت اونجا این میشه که مدیریت سرمایه رو رعایت بکنی"
        decision = curate_complete_statement(segments("کرده. " + quote + ". همین. سابسکرایب کن."), 0)
        self.assertEqual(decision["text"], quote + ".")
        self.assertFalse(decision["needs_manual_copy"])

    def test_editorial_quote_from_later_segment_is_not_published_at_old_anchor(self):
        source = segments("این بخش هنوز برای.", "این جمله درباره سیستم کامل است.")
        decision = curate_complete_statement(source, 0, [source[1]["text"]])
        self.assertEqual(decision["text"], "…")

    def test_later_corrected_take_reports_its_real_anchor(self):
        source = segments("من این الگوریتم رو طوری ساختم که", "نه بذار دوباره بگم",
                          "من این الگوریتم رو طوری ساختم که سیگنال رو سریع می‌فرسته")
        decision = curate_complete_statement(source, 0)
        self.assertEqual(decision["source"], "later-corrected-take")
        self.assertEqual(decision["anchor_segment_id"], 2)
        self.assertEqual(decision["anchor_start"], 16.0)

    def test_real_complete_conditional_has_both_condition_and_result(self):
        self.assertTrue(is_complete_statement("وقتی سیگنال می‌رسه نتیجه را بررسی می‌کنیم"))
        self.assertTrue(is_complete_statement("این ابزار سیگنال رو سریع می‌فرسته"))
        self.assertTrue(is_complete_statement("این روش برای تحلیل مناسب است"))


if __name__ == "__main__":
    unittest.main()
