# Hafez Finisher for Adobe Premiere Pro 2026

این پنل فایل `*.premiere-plan.json` خروجی Hafez را می‌خواند، MOGRTهای انتخاب‌شده را روی سکانس فعال می‌چیند و متن و فونت هر Cue را تنظیم می‌کند.

## بارگذاری در حالت توسعه

1. Adobe Premiere Pro 2026 و سکانس `03 - Hafez Director Cut` را باز کن.
2. در Adobe UXP Developer Tool گزینه **Add Plugin** را بزن و همین پوشه را انتخاب کن.
3. روی **Load** بزن.
4. در Premiere از منوی **Window > UXP Plugins** پنل **Hafez Finisher** را باز کن.
5. روی دکمه اجرای پنل بزن و فایل `*.premiere-plan.json` همان پروژه را انتخاب کن.

PNGهای داخل XML یک fallback قابل‌مشاهده‌اند؛ پس حتی پیش از اجرای پنل هم متن‌ها در تایم‌لاین حاضر هستند. بعد از جایگذاری موفق MOGRT، پنل V3 را Mute می‌کند و MOGRTها روی V4 باقی می‌مانند.

نکته: کنترل‌های داخلی هر MOGRT ممکن است نام متفاوتی داشته باشند. پنل نام‌های رایج Text/Title/Font را پیدا می‌کند؛ Cueهایی که کنترل متن استاندارد ندارند در گزارش مشخص می‌شوند و PNG fallback آن‌ها همچنان آماده است.
