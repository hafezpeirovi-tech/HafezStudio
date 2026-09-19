# کاتالوگ تدوینی Hermes Studio Elements

این فایل نسخهٔ خوانا برای تدوین‌گر است. مرجع قطعی و ماشین‌خوان،
`config/editorial-element-catalog.json` است و همان مرجع به پرامپت Editor و
Director تزریق می‌شود. انتخاب نهایی همیشه Rule-Based است؛ پیشنهاد مدل هوش
مصنوعی فقط پس از اعتبارسنجی قیود پذیرفته می‌شود.

## زبان بصری مشترک

- فونت: تمام متن‌ها با خانوادهٔ `Abar High FaNum` و وزن متناسب با نقش متن.
- رنگ‌ها: `#151215` جوهری، `#2C2321` شیشه، `#3C3B41` عمق، `#7E8F9E` سرد،
  `#8E674E` برنز، `#C0A382` شن، `#E0C7AF` شامپاینی، `#F3EFEB` متن اصلی.
- تمام قالب‌ها بدون Grain هستند.
- پیش‌فرض قالب‌های Overlay شفاف است؛ پس‌زمینه فقط با کنترل
  `Show Background` فعال می‌شود.
- همهٔ قالب‌ها کنترل رنگ، شدت Glow، شعاع Glow، شفافیت شیشه، Position و Scale
  دارند. متن، فونت و اندازهٔ فونت در Premiere قابل ویرایش است.
- ورود و خروج Transformها Bezier/Ease است و Linear مجاز نیست.

## فهرست کامل عناصر

| اولویت | شناسه / قالب | کاربرد اصلی | محرک‌ها و شرط داده | جای‌گذاری |
|---:|---|---|---|---|
| 100 | `hermes-subscribe` / Hafez Hermes Subscribe | CTA سابسکرایب | فقط عبارت نرمال‌شدهٔ دقیق «سابسکرایب کن»، حداکثر یک‌بار | Bottom Dock یا Center |
| 100 | `hermes-title-hero-3` / Hafez Hermes Title Hero 3 | Hook یا عنوان فصل تمام‌فریم؛ انتخاب اول | فصل، موضوع، شروع، نکتهٔ اصلی؛ متن کامل و قابل‌اعتماد | Center |
| 99 | `hermes-title-hero-2` / Hafez Hermes Title Hero 2 | ادعا، نتیجه یا عنوان بخش تمام‌فریم | نتیجه، اصل، جمع‌بندی، موضوع | Center |
| 97 | `hermes-flowchart` / Hafez Hermes Flowchart | فرایند، معماری، Workflow یا درخت تصمیم | حداقل سه مرحلهٔ واقعی با ترتیب روشن | Center |
| 96 | `hermes-glass-insight` / Hafez Hermes Glass Insight | نکته، Callout یا نتیجهٔ کوتاه | نکته، مهم، نتیجه، یعنی، در واقع | Side یا Center |
| 94 | `hermes-glass-kpi` / Hafez Hermes Glass KPI | یک عدد، درصد یا KPI برجسته | مقدار عددی معتبر الزامی است | Side یا Corner |
| 91 | `hermes-glass-quote` / Hafez Hermes Glass Quote | نقل‌قول یا اصل منتسب | متن نقل‌قول و منبع/گوینده باید موجود باشد | Side یا Center |
| 90 | `hermes-user-growth` / Hafez Hermes User Growth | درصد عملکرد، تکمیل یا هدف | درصد یا مقدار قابل محاسبه | Side یا Center |
| 86 | `hermes-revenue-chart` / Hafez Hermes Revenue Chart | درآمد/هزینه و روند زمانی | سری زمانی یا دست‌کم دو مقدار مالی واقعی | Side یا Center |
| 72 | `hermes-saving-balance` / Hafez Hermes Saving Balance | مبلغ، موجودی یا سود منفرد | مقدار پولی صریح؛ دکمهٔ جعلی ساخته نمی‌شود | Side |
| 70 | `hermes-weekly-progress` / Hafez Hermes Weekly Progress | پیشرفت روزانه/هفتگی و Streak | دادهٔ زمانی واقعی | Side |
| 62 | `hermes-glass-pill` / Hafez Hermes Glass Pill | URL، Handle، نام ابزار یا هویت کوتاه | متن کوتاه؛ برای جملهٔ بلند ممنوع | Bottom Dock یا Corner |
| 48 | `hermes-glass-selector` / Hafez Hermes Glass Selector | مقایسه یا انتخاب بین دو مورد | دقیقاً دو گزینهٔ واقعی | Center؛ کم‌تکرار |
| 45 | `hermes-price-list` / Hafez Hermes Price List | مقایسهٔ سه پلن/پکیج | دقیقاً سه پلن و قیمت معتبر | Center؛ تمام‌فریم |

## قواعد انتخاب و بازبینی

- در هر ویدیو حداکثر سه تا چهار خانوادهٔ Motion/MOGRT فعال می‌شود و History
  برای حفظ هویت بصری به انتخاب وزن می‌دهد.
- فیلد ناقص هرگز به‌عنوان جملهٔ کامل نمایش داده نمی‌شود؛ مقدار نامطمئن `…`
  باقی می‌ماند تا در Premiere جایگزین شود.
- مقدار، درصد، قیمت، نام شخص و نقل‌قول ساخته نمی‌شود؛ داده باید از Transcript
  یا Factهای تأییدشده بیاید.
- جای‌گذاری باید از Union تمام Bounding Boxهای صورت و بدن در طول حضور گرافیک
  عبور کند و داخل Safe Area بماند.
- Qwen Vision فقط Contrast، خوانایی، تعادل و تداخل را در QA نهایی بررسی می‌کند؛
  حق انتخاب آزادانهٔ قالب ندارد.
- SFX فقط از Curated Local Assetها انتخاب می‌شود و فریم اول ورود را Sync می‌کند.
  Ducking فقط روی موسیقی پس‌زمینه اعمال می‌شود.

## تحویل فنی

- پروژهٔ After Effects قابل‌ویرایش:
  `motion-pack/source/Hermes Studio Elements - Hafez Curated.aep`
- چهارده MOGRT قابل Import در Premiere:
  `motion-pack/dist/Hafez Hermes *.mogrt`
- اعتبارسنج مستقل بسته‌ها:
  `scripts/validate_editorial_mogrts.py`
- آخرین گزارش اعتبارسنجی:
  `proof/ae-elements-audit/mogrt-validation.json`
- Preview منتخب:
  `proof/ae-elements-audit/Hafez-Hermes-Editorial-Preview.png`
