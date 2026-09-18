"""
Kontent ma'lumotlarini tekshiruvchi vosita.

Ishlatish:
    python validate_data.py

Nimani tekshiradi:
  • savollarning tuzilishi (savol / variantlar / javob / tushuntirish);
  • "javob" indeksi variantlar chegarasidan chiqmaganini;
  • takrorlangan savol yoki variantlarni;
  • Telegram HTML qoidalariga mosligini — noto'g'ri teg (masalan <->)
    yoki escape qilinmagan & belgisi xabar yuborilmasligiga olib keladi;
  • matn va tugmalar uzunligini (Telegram chegaralari).

Savol/alifbo ma'lumotlarini tahrirlagandan keyin shu faylni ishga tushiring.
Xato topilsa dastur 1 kodi bilan tugaydi (CI uchun qulay).
"""

from __future__ import annotations

import collections
import re
import sys

from alphabet_data import ALPHABET_DATA
from test_data import TEST_QUESTIONS, TEST_LANG_NAMES

# main.py ni import qilish uchun token kerak — tekshiruv uchun soxtasi yetadi
import os
os.environ.setdefault("BOT_TOKEN", "0:VALIDATION")

from main import (  # noqa: E402  (importdan oldin token o'rnatilishi shart)
    FAKTLAR,
    KUTUBXONA,
    MOTIVATSIYA_QUOTES,
    QUIZ_QUESTIONS,
    QUIZ_CATEGORIES,
    TELEGRAM_MESSAGE_LIMIT,
    build_books_text,
)

# Telegram Bot API qo'llab-quvvatlaydigan HTML teglari
ALLOWED_TAGS = {
    "b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
    "a", "code", "pre", "span", "tg-spoiler", "blockquote",
}

# Inline tugma matni uchun amaliy chegara
BUTTON_TEXT_LIMIT = 64

xatolar: list[str] = []


def xato(joy: str, *xabar) -> None:
    xatolar.append(f"{joy}: " + " ".join(str(x) for x in xabar))


def html_tekshir(matn: str, joy: str) -> None:
    """Matn Telegram HTML sifatida yuborilsa xato bermasligini tekshiradi."""
    if not matn:
        return

    stack: list[str] = []

    for m in re.finditer(r"<(/?)([a-zA-Z-]*)([^>]*)>", matn):
        yopuvchi, teg = m.group(1), m.group(2).lower()

        if teg not in ALLOWED_TAGS:
            xato(joy, f"Telegram qo'llamaydigan teg: {m.group(0)[:40]!r}")
            continue

        if yopuvchi:
            if not stack or stack.pop() != teg:
                xato(joy, f"mos kelmaydigan yopuvchi teg: {m.group(0)!r}")
        else:
            stack.append(teg)

    if stack:
        xato(joy, f"yopilmagan teg(lar): {stack}")

    for m in re.finditer(r"&(?!amp;|lt;|gt;|quot;|#\d+;)", matn):
        parcha = matn[max(0, m.start() - 15):m.start() + 15].replace("\n", " ")
        xato(joy, f"escape qilinmagan & belgisi: ...{parcha}...")


def savollarni_tekshir(nom: str, savollar: list[dict]) -> None:
    print(f"\n[{nom}] — {len(savollar)} ta savol")
    matnlar = collections.Counter()

    for i, q in enumerate(savollar):
        joy = f"{nom}[{i}]"

        yetishmayotgan = [k for k in ("savol", "variantlar", "javob") if k not in q]
        if yetishmayotgan:
            xato(joy, f"kalit(lar) yo'q: {yetishmayotgan}")
            continue

        variantlar = q["variantlar"]

        if not isinstance(variantlar, list) or len(variantlar) < 2:
            xato(joy, f"variantlar noto'g'ri: {variantlar!r}")
            continue

        if len(variantlar) > 4:
            xato(joy, f"4 tadan ko'p variant ({len(variantlar)}) — klaviatura sig'maydi")

        if len(set(variantlar)) != len(variantlar):
            xato(joy, f"takrorlangan variant: {variantlar}")

        if not isinstance(q["javob"], int) or not 0 <= q["javob"] < len(variantlar):
            xato(joy, f"javob indeksi noto'g'ri: {q['javob']} (variantlar: {len(variantlar)})")

        if not q.get("tushuntirish"):
            xato(joy, "tushuntirish yo'q yoki bo'sh")

        html_tekshir(q["savol"], f"{joy}.savol")
        html_tekshir(str(q.get("tushuntirish", "")), f"{joy}.tushuntirish")

        for variant in variantlar:
            html_tekshir(str(variant), f"{joy}.variant")
            if len(f"A) {variant}") > BUTTON_TEXT_LIMIT:
                xato(joy, f"tugma matni juda uzun ({len(str(variant))} belgi): {variant!r}")

        matnlar[q["savol"]] += 1

    takrorlangan = [t for t, n in matnlar.items() if n > 1]
    if takrorlangan:
        xato(nom, f"{len(takrorlangan)} ta takrorlangan savol, masalan: {takrorlangan[0][:60]!r}")


def main() -> int:
    print("=" * 55)
    print("KONTENT MA'LUMOTLARINI TEKSHIRISH")
    print("=" * 55)

    savollarni_tekshir("QUIZ", QUIZ_QUESTIONS)

    for kod, savollar in TEST_QUESTIONS.items():
        savollarni_tekshir(f"TEST:{kod}", savollar)

    # Quiz kategoriyalari QUIZ_QUESTIONS chegarasidan chiqmasligi kerak
    print("\n[QUIZ kategoriyalari]")
    for kalit, (nom, boshi, oxiri) in QUIZ_CATEGORIES.items():
        if not 0 <= boshi < oxiri <= len(QUIZ_QUESTIONS):
            xato("QUIZ_CATEGORIES", f"{kalit} ({nom}) chegaradan chiqdi: {boshi}-{oxiri}")
    print(f"  {len(QUIZ_CATEGORIES)} kategoriya, jami {len(QUIZ_QUESTIONS)} savol")

    print("\n[TEST nomlari]")
    for kod in TEST_QUESTIONS:
        if kod not in TEST_LANG_NAMES:
            xato("TEST_LANG_NAMES", f"'{kod}' uchun nom yozilmagan")
    print(f"  {list(TEST_QUESTIONS)}")

    print("\n[ALIFBO]")
    for kod, matn in ALPHABET_DATA.items():
        html_tekshir(matn, f"alifbo[{kod}]")
        if len(matn) > TELEGRAM_MESSAGE_LIMIT:
            xato(f"alifbo[{kod}]", f"{len(matn)} belgi — {TELEGRAM_MESSAGE_LIMIT} dan uzun")
    print(f"  {len(ALPHABET_DATA)} ta alifbo, eng uzuni "
          f"{max(len(v) for v in ALPHABET_DATA.values())} belgi")

    print("\n[KUTUBXONA]")
    for kategoriya, kitoblar in KUTUBXONA.items():
        for i, kitob in enumerate(kitoblar):
            for kalit in ("nom", "muallif", "tavsif"):
                if not kitob.get(kalit):
                    xato(f"KUTUBXONA[{kategoriya}][{i}]", f"'{kalit}' bo'sh")
        uzunlik = len(build_books_text(kategoriya))
        if uzunlik > TELEGRAM_MESSAGE_LIMIT:
            print(f"  ℹ️ '{kategoriya}' {uzunlik} belgi — bir necha xabarga bo'linadi")
    print(f"  {len(KUTUBXONA)} kategoriya, "
          f"{sum(len(v) for v in KUTUBXONA.values())} kitob")

    print("\n[MOTIVATSIYA / FAKTLAR]")
    for i, iqtibos in enumerate(MOTIVATSIYA_QUOTES):
        for kalit in ("quote", "muallif", "tarjima"):
            if not iqtibos.get(kalit):
                xato(f"MOTIVATSIYA[{i}]", f"'{kalit}' bo'sh")
    for i, fakt in enumerate(FAKTLAR):
        html_tekshir(fakt, f"FAKTLAR[{i}]")
    print(f"  {len(MOTIVATSIYA_QUOTES)} iqtibos, {len(FAKTLAR)} fakt")

    print("\n" + "=" * 55)
    if xatolar:
        print(f"❌ {len(xatolar)} TA MUAMMO TOPILDI:\n")
        for x in xatolar:
            print("  •", x)
        return 1

    print("✅ MUAMMO TOPILMADI — barcha ma'lumotlar to'g'ri")
    return 0


if __name__ == "__main__":
    sys.exit(main())
