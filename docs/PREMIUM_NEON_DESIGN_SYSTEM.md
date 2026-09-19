# Hafez Studio · Premium Dark with Neon Glows

این سند قرارداد اجرایی مشترک رابط دسکتاپ و خروجی ویدیو است. منبع قطعی
مقادیر `config/brand-tokens.json` است و هیچ ماژولی مجاز نیست پالت مستقلی برای
خود تعریف کند.

## سلسله‌مراتب نور

- Canvas و سطح‌های عادی تقریباً مشکی و بدون نور باقی می‌مانند.
- در هر View حداکثر دو کارت می‌توانند حالت Luminous داشته باشند.
- سبز نئونی فقط برای Action، انتخاب فعال، مقدار مثبت و Highlight استفاده می‌شود.
- قرمز فقط معنی منفی، خطا، هشدار یا مقایسه نامطلوب دارد؛ حالت Disabled خاکستری است.
- Grain در UI، Preview، PNG fallback و MOGRT ممنوع است.

## مسیر داده

1. Electron فایل Token را از `resources/config` می‌خواند و از طریق IPC در اختیار Renderer می‌گذارد.
2. Renderer متغیرهای CSS برند را پیش از بارگذاری Config کاربر اعمال می‌کند.
3. Python همان JSON را اعتبارسنجی و به مقادیر RGBA مناسب Premiere تبدیل می‌کند.
4. Plan هر Cue کنترل‌های رنگ، Glow، Border و Radius را نگه می‌دارد.
5. Premiere Finisher فقط کنترل‌هایی را اعمال می‌کند که Template واقعاً Expose کرده است.
6. سازنده After Effects تمام Shape/Textهای اختصاصی را به `HAFEZ · BRAND TOKENS` متصل می‌کند.

## کنترل‌های استاندارد MOGRT

- `Primary Accent`
- `Negative Accent`
- `Surface Color`
- `Text Primary`
- `Text Secondary`
- `Glow Intensity`
- `Glow Radius`
- `Corner Radius`
- `Border Opacity`

MOGRTهای شخص ثالث که این Contract را ندارند بدون Crash وارد می‌شوند، اما فقط
کنترل‌های موجود خودشان قابل تغییر خواهد بود. برای انطباق کامل باید یک نسخه
Wrapper/Adapted در After Effects ساخته شود.
