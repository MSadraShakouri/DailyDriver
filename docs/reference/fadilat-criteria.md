# فضیلت boundaries — criteria, formulas, and sources

This note records which fiqh criteria DailyDriver implements for the green
(فضیلت) bands, where each comes from, and how the "practical minutes" that
circulate in popular tables relate to the formulas.  Marja: **Ayatollah
Khamenei** (the app's deadlines — sunset, shar'i midnight — already follow
his risāla).

## What the app computes

| Boundary | Criterion | Formula |
|----------|-----------|---------|
| Fajr adhan | Fajr ṣādiq | sun at **−17.7°** (Tehran Geophysics convention) |
| Fajr green ends (اسفار) | whiteness spreading | sun at **−14°** |
| Sunrise / deadline of Fajr | sunrise | sun at **−0.833°** |
| Dhuhr adhan | zuwal | sun crosses the meridian |
| Dhuhr green ends (مثله) | post-zuwal shadow = gnomon | `cot h = tan\|φ−δ\| + 1` |
| Dhuhr/Asr deadline | sunset | sun at **−0.833°** |
| Maghrib adhan | red twilight (حمره) gone | sun at **−4.5°** |
| Maghrib green ends (زوال شفق) | white twilight (شفق ابیض) gone | sun at **−14°** |
| Maghrib/Isha deadline | shar'i midnight | midpoint(geometric sunset → next fajr adhan) |

All bands are computed from (lat, lon, tz, date) at runtime; the only
constants are the fiqh angles above.

## The decisive texts

**Khamenei's risāla** (Tawẓīḥ al-Masā'il; Hidāyat al-ʿIbād, m 637/640):

> «وقت فضیلت ظهر از زوال تا رسیدن سایه شاخص به اندازه خودش می‌باشد و فضیلت
> عصر از بعد از رسیدن سایه شاخص به اندازه خودش تا دو برابر (بنابر قول مشهور)»

**His office's istiftā** (farsi.khamenei.ir/treatise-content?id=24) fixes how
the shadow is measured — from the noon minimum, i.e. *incrementally*:

> «مراد از دو هفتم یا چهار هفتم شاخص این نیست که تمام سایه‌ی شاخص را در
> نظر بگیریم، بلکه مقدار سایه‌ای که پس از نهایت کوتاه شدن، شروع به بلند
> شدن کرده است در نظر گرفته می‌شود»

Makarem's office answers the same way for northern cities where the noon
shadow already exceeds the gnomon: mark the shadow tip at zuwal and measure
the increase.  Under this convention the criterion is reachable every day at
every Iranian latitude — there is **no winter degenerate case** (that problem
exists only for the Shafiʿī total-shadow reading of the same phrase).

Sistani's risāla uses the 7ths of the incremental shadow with a worked
example (70 cm gnomon, 10 cm noon shadow; asr's فضیلت ends when the total
shadow reaches 70 cm = one full gnomon) — the same noon-mark arithmetic.

## The "practical minutes" and where they come from

hawzah.net (article 99881, Khamenei-affiliated) popularises the windows as
fixed minutes after the adhan:

| Practical constant | Reproduced by the formulas? |
|--------------------|-----------------------------|
| Fajr فضیلت ≈ +21 min | ✅ seasonal gap (17.7° → 14°) over a Tehran year: 18–26 min, **annual average 20.6** |
| Maghrib فضیلت ≈ +51 min | ✅ seasonal gap (4.5° → 14°): 46–59 min, **annual average 50.9** |
| Dhuhr فضیلت "≈ +1h40" | ❌ not the fadilat boundary — the مثله criterion averages **≈3h20** over a Tehran year.  +1h40 sits in the zone of the **2/7 shadow mark** (end of نافلهٔ ظهر; annual average ≈1h50), which popular tables sometimes blur into "فضیلت". |

The risāla text governs: dhuhr's green ends at مثله (incremental shadow =
one gnomon = the moment Iranian calendars publish as **اذان عصر**), not at a
fixed 1h40.  That identification is also why "اذان عصر" appears as the
validation label for the dhuhr green boundary: it is the same instant, named
by what the almanacs use it for.

## Validation trail

- pishkhanak.com (University-of-Tehran angles): minute-exact match on all
  six adhan/sunset times for Tehran, Karaj, Qom, Mashhad.
- tala.ir / mavaqeet.com (اذان‌گو): second-level agreement (≤8 s) including
  shar'i midnight.
- hawzah 99881 constants: reproduced as annual averages (see table above);
  pinned as regression tests in `tests/features/prayer/test_windows.py`.

## Sources

- farsi.khamenei.ir/treatise-content?id=24 (istiftā on the incremental mark)
- tebyan.net/news/524106 (marja-by-marja فضیلت comparison; Khamenei excerpt)
- hawzah.net/fa/Article/View/99881 (practical-minutes table)
- sistani.org/persian/book/26575/6324 (7ths system with worked example)
- makarem.ir ahkam category (northern-cities zuwal-mark answer)
- pishkhanak.com / tala.ir / mavaqeet.com (Geophysics-convention tables)
