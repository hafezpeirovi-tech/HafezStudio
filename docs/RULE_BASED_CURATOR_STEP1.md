# Hafez Studio — Rule-Based Curator / Step 1

این سند قرارداد اجرایی مرحله اول است. در این معماری، مدل زبانی فقط پیشنهاد می‌دهد؛
هیچ متن، Asset، چیدمان یا Motion بدون عبور از Rule Engine وارد Premiere نمی‌شود.

## جریان داده

```text
Transcript + AI proposals
          │
          ▼
Text Curator ──► complete spoken copy / corrected later take / editable «…» placeholder
          │
          ▼
Template Curator ──► approved family: text-animation-title / 2. Title.mogrt
          │
          ▼
Multi-frame Tracker ──► face union + presenter/body union over full cue lifetime
          │
          ▼
Spatial Grid ──► collision-free region + position/scale/max-width controls
          │
          ▼
Bilingual Contract ──► V4 English Relaxe + V5 Persian semantic companion
          │
          ▼
Premiere Plan (editable MOGRT layers; PNG is only a safety guide)
```

## 1. Text Curator

- اولویت اول عین لحن محاوره‌ای گوینده است.
- جمله تنها وقتی تأیید می‌شود که ۴ تا ۱۸ کلمه، حداکثر ۱۱۸ کاراکتر، فعل/گزاره
  پایانی و پایان بسته داشته باشد.
- بریدن کاراکتری یا کلمه‌ای ممنوع است.
- اگر Take اول ناقص باشد، تا ۴۰ Segment جلوتر دنبال Take کامل با حداقل سه واژه
  آغازین یکسان می‌گردد.
- اگر Take کامل یا بازنویسی معنایی معتبر پیدا نشود، Cue حذف نمی‌شود: متن مستقل
  `…` با Flag برابر `NEEDS_COPY_REVIEW` ساخته می‌شود تا در MOGRT جایگزین شود.
- `…` هرگز به انتهای یک Fragment چسبانده نمی‌شود.

فایل اجرایی: `engine/src/hermes_video/curation_rules.py`

## 2. اولین خانواده Asset

- Family ID: `text-animation-title`
- Asset: `2. Title.mogrt`
- Scope: Personal Mode
- کاربرد فعلی: Hook و Chapter
- کنترل عنوان: `Main Text`
- Typeface عنوان انگلیسی: `Relaxe`
- Motion Contract: Ease-In Cubic، Ease-Out Cubic، Motion Blur، Lift 50px،
  Blur 10→0، Opacity 0→100؛ Linear مجاز نیست.
- Grain در Source Builder، Preview، Config، Premiere Control Map و Python وجود ندارد.

Asset شخصی از `%LOCALAPPDATA%\Hafez Studio\assets` خوانده می‌شود و داخل محصول
قابل‌فروش Bundle نمی‌شود.

## 3. قرارداد دوزبانه

هر Cue منتخب دو Layer قابل‌ویرایش تولید می‌کند:

| Track | نقش | Template | فونت |
|---|---|---|---|
| V4 | English display title | `2. Title.mogrt` | Relaxe |
| V5 | Persian semantic companion | `Hafez Word Lift Statement.mogrt` | فونت فارسی پروژه |

خروجی Plan شامل `template_layers`، `bilingual_typography`، `template_family`،
`asset_mode` و `template_rule` است. FCP XML نیز V4 و V5 خالی را از قبل رزرو
می‌کند تا Finisher روی Track نامطمئن یا مشترک ننویسد.

## 4. Temporal Spatial QA

برای هر Cue کل بازه `start..end` با فاصله تقریبی ۰٫۴۵ ثانیه و حداکثر ۱۱ نمونه
بررسی می‌شود. خروجی Tracker شامل موارد زیر است:

- `face_union_bbox`: اجتماع تمام Face Boxهای کشف‌شده؛
- `subject_union_bbox`: اجتماع Envelope محافظه‌کارانه مو، شانه، سینه و Gesture؛
- `tracking_sample_frames` و `tracking_coverage` برای Audit؛
- `collision_free` بر اساس کل بازه، نه فقط فریم ورود.

در صورت Detection ناموفق، یک Presenter Zone محافظه‌کارانه مرکزی استفاده می‌شود.
Qwen Vision در این مرحله تصمیم‌گیر نیست و فقط در Visual QA نهایی اضافه خواهد شد.

## 5. مرز Step 1 و ادامه مسیر

Step 1 موتور تصمیم، Schema و اولین Family را تثبیت می‌کند. مرحله بعدی روی همین
قرارداد، History پایدار خانواده‌ها (حداکثر چهار Family)، SFX فریم‌دقیق، Asset
Importer دوحالته و Qwen Visual Critic را اضافه می‌کند؛ بدون تغییر قراردادهای
فعلی و بدون تولید گرافیک از صفر.
