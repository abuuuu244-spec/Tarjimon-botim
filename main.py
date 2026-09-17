import asyncio
import html
import inspect
import io
import logging
import os
import random
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

# .env faylini yuklash
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    URLInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    CallbackQuery,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeAllPrivateChats,
)

from oxfordLookup import getDefinitions
from test_data import TEST_QUESTIONS, TEST_LANG_NAMES
from alphabet_data import ALPHABET_DATA

import requests
from deep_translator import GoogleTranslator

import numpy as np

# OCR uchun
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from rapidocr_onnxruntime import RapidOCR
    rapid_ocr_engine = RapidOCR()
    RAPID_OCR_AVAILABLE = True
except Exception:
    rapid_ocr_engine = None
    RAPID_OCR_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except Exception:
    pytesseract = None
    PYTESSERACT_AVAILABLE = False

OCR_AVAILABLE = RAPID_OCR_AVAILABLE or PYTESSERACT_AVAILABLE or True

# Rasm tarjimalari matnlari kesh (boshqa tilga qayta tarjima qilish uchun)
photo_text_cache: dict[int, str] = {}


# ============================================================
# CONFIG
# ============================================================

API_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("Bot") or os.getenv("BOT")

if not API_TOKEN:
    raise ValueError(
        "BOT_TOKEN topilmadi!\n\n"
        "1. .env fayl yarating va quyidagini qo'shing:\n"
        "   BOT_TOKEN=your_bot_token_here\n\n"
        "2. Yoki environment variable o'rnating:\n"
        "   export BOT_TOKEN='your_token' (Linux/Mac)\n"
        "   set BOT_TOKEN=your_token (Windows CMD)\n"
        "   $env:BOT_TOKEN='your_token' (PowerShell)\n\n"
        "Tokenni @BotFather dan oling."
    )


DB_NAME = "bot.db"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    )
)

logger = logging.getLogger("TarjimonBot")


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()

# Translator Helper
def get_translator(source: str = "auto", target: str = "uz"):
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source=source, target=target)
    except Exception:
        return None


# ============================================================
# USER TARGET LANGUAGE SETTING
# ============================================================

user_target_lang = {}
user_test_sessions = {}
user_test_setup = {}
user_math_sessions = {}


# ============================================================
# KUTUBXONA DATA
# ============================================================

KUTUBXONA = {
    "💻 Dasturlash": [
        {
            "nom": "Python Crash Course",
            "muallif": "Eric Matthes",
            "tavsif": "Python dasturlash tilini noldan o'rganish uchun eng yaxshi kitob. Amaliy loyihalar bilan.",
        },
        {
            "nom": "Clean Code (Toza Kod)",
            "muallif": "Robert C. Martin",
            "tavsif": "Toza, o'qilishi oson va professional darajadagi sifatli kod yozish san'ati.",
        },
        {
            "nom": "Grokking Algorithms",
            "muallif": "Aditya Bhargava",
            "tavsif": "Algoritmlar va ma'lumotlar tuzilmalarini rasmlar orqali sodda va tushunarli o'rganish.",
        },
        {
            "nom": "Automate the Boring Stuff with Python",
            "muallif": "Al Sweigart",
            "tavsif": "Kundalik takrorlanuvchi ishlarni Python orqali avtomatlashtirish sirlari.",
        },
        {
            "nom": "The Pragmatic Programmer",
            "muallif": "David Thomas, Andrew Hunt",
            "tavsif": "Haqiqiy professional dasturchi bo'lish yo'lidagi oltin maslahatlar va tamoyillar.",
        },
        {
            "nom": "Designing Data-Intensive Applications",
            "muallif": "Martin Kleppmann",
            "tavsif": "Katta hajmli ma'lumotlar, taqsimlangan tizimlar va ishonchli arxitektura qurish.",
        },
        {
            "nom": "JavaScript: The Good Parts",
            "muallif": "Douglas Crockford",
            "tavsif": "JavaScript tilining eng muhim, kuchli va samarali tomonlari haqida qo'llanma.",
        },
    ],
    "🇬🇧 Ingliz tili": [
        {
            "nom": "English Grammar in Use",
            "muallif": "Raymond Murphy",
            "tavsif": "Dunyodagi eng mashhur va ishonchli ingliz tili grammatikasi darsligi.",
        },
        {
            "nom": "Word Power Made Easy",
            "muallif": "Norman Lewis",
            "tavsif": "Ingliz tili so'z boyligini ildizlar va etimologiya orqali jadal kengaytirish.",
        },
        {
            "nom": "English Vocabulary in Use",
            "muallif": "Michael McCarthy, Felicity O'Dell",
            "tavsif": "Kembrij universiteti tomonidan ishlab chiqilgan lug'at boyligini oshirish kursi.",
        },
        {
            "nom": "Practical English Usage",
            "muallif": "Michael Swan",
            "tavsif": "Ingliz tili nozikliklari, qoidalari va xatolarni to'g'irlash bo'yicha mukammal qo'llanma.",
        },
        {
            "nom": "Fluent Forever",
            "muallif": "Gabriel Wyner",
            "tavsif": "Istalgan chet tilini tez, unutilmas va oson o'rganish bo'yicha neyro-metodika.",
        },
        {
            "nom": "Essential English Grammar",
            "muallif": "Philip Gucker",
            "tavsif": "Boshlang'ich va o'rta darajadagilar uchun grammatikani tushunarli izohlash.",
        },
        {
            "nom": "IELTS Advantage: Writing Skills",
            "muallif": "Richard Brown, Lewis Richards",
            "tavsif": "IELTS akademik yozish (Writing) bo'limidan 7.0+ ball olish strategiyalari.",
        },
    ],
    "🔥 Motivatsiya": [
        {
            "nom": "Atomic Habits (Atom Odatlar)",
            "muallif": "James Clear",
            "tavsif": "Kichik odatlar orqali hayotda ulkan ijobiy o'zgarishlarga erishish. Dunyo bestselleri!",
        },
        {
            "nom": "Deep Work (Diqqat: Chalg'imasdan ishlash)",
            "muallif": "Cal Newport",
            "tavsif": "Shovqinli dunyoda chuqur diqqat bilan samarali ishlash va natijaga erishish.",
        },
        {
            "nom": "Think and Grow Rich (O'yla va boy bo'l)",
            "muallif": "Napoleon Hill",
            "tavsif": "Muvaffaqiyat, boylik va maqsad sari yo'naltirilgan tafakkur klassikasi.",
        },
        {
            "nom": "The 7 Habits of Highly Effective People",
            "muallif": "Stephen Covey",
            "tavsif": "Muvaffaqiyatli insonlarning 7 ta yetakchi odati va shaxsiy rivojlanish falsafasi.",
        },
        {
            "nom": "Ikigai (Uzoq va baxtli umr siri)",
            "muallif": "Héctor García, Francesc Miralles",
            "tavsif": "Yaponlarning har kuni quvonch bilan uyg'onish va uzoq umr ko'rish falsafasi.",
        },
        {
            "nom": "Can't Hurt Me",
            "muallif": "David Goggins",
            "tavsif": "Ongni boshqarish, iroda tarbiyasi va inson imkoniyatlari chegarasini yengish.",
        },
        {
            "nom": "Mindset: The New Psychology of Success",
            "muallif": "Carol Dweck",
            "tavsif": "O'sish tafakkuri va muvaffaqiyat psixologiyasi.",
        },
    ],
    "🔬 Fan & Koinot": [
        {
            "nom": "A Brief History of Time (Vaqtning qisqacha tarixi)",
            "muallif": "Stephen Hawking",
            "tavsif": "Koinot, qora tuynuklar, Katta Portlash va vaqt sirlari haqida ilmiy asar.",
        },
        {
            "nom": "Sapiens: Insoniyatning qisqacha tarixi",
            "muallif": "Yuval Noah Harari",
            "tavsif": "Qadimgi odamlardan to zamonaviy sivilizatsiyagacha bo'lgan inqilobiy sayohat.",
        },
        {
            "nom": "Cosmos (Koinot)",
            "muallif": "Carl Sagan",
            "tavsif": "Koinotni kashf etish sayohati va insoniyatning yulduzlar sari intilishi.",
        },
        {
            "nom": "The Selfish Gene (Xudbin gen)",
            "muallif": "Richard Dawkins",
            "tavsif": "Biologik evolyutsiya, tabiiy tanlanish va genlar siri haqida inqilobiy qarash.",
        },
        {
            "nom": "Astrophysics for People in a Hurry",
            "muallif": "Neil deGrasse Tyson",
            "tavsif": "Band insonlar uchun koinot va astrofizika asoslari ixcham va qiziqarli tilda.",
        },
        {
            "nom": "The Elegant Universe",
            "muallif": "Brian Greene",
            "tavsif": "Superstringlar nazariyasi, yashirin o'lchamlar va borliqning tub mohiyati.",
        },
        {
            "nom": "Guns, Germs, and Steel",
            "muallif": "Jared Diamond",
            "tavsif": "Nega ba'zi qit'a va xalqlar boshqalaridan texnologik ustun bo'lib rivojlandi?",
        },
    ],
    "📜 Tarix": [
        {
            "nom": "Boburnoma",
            "muallif": "Zahiriddin Muhammad Bobur",
            "tavsif": "Buyuk Boburiy imperiya asoschisining o'zbek adabiyotidagi tengsiz tarixiy memuari.",
        },
        {
            "nom": "Amir Temur (Temur Malik)",
            "muallif": "Harold Lamb",
            "tavsif": "Buyuk sarkarda Sohibqiron Amir Temur hayoti, yurishlari va harbiy mahorati.",
        },
        {
            "nom": "The Silk Roads (Ipak Yo'llari)",
            "muallif": "Peter Frankopan",
            "tavsif": "Sharq sivilizatsiyasi va Buyuk Ipak Yo'li orqali dunyo tarixiga yangicha nigoh.",
        },
        {
            "nom": "O'zbekiston tarixi",
            "muallif": "Bo'riboy Ahmedov",
            "tavsif": "Vatanimizning qadimgi Turon davridan boshlab mustaqillikkacha bo'lgan boy tarixi.",
        },
        {
            "nom": "Genghis Khan and the Making of the Modern World",
            "muallif": "Jack Weatherford",
            "tavsif": "Chingizxon va mo'g'ullar imperiyasining savdo, qonun va jahon taraqqiyotiga ta'siri.",
        },
        {
            "nom": "A History of the World in 100 Objects",
            "muallif": "Neil MacGregor",
            "tavsif": "Britaniya muzeyining 100 ta eng nodir buyumlari orqali 2 million yillik insoniyat tarixi.",
        },
        {
            "nom": "1984",
            "muallif": "George Orwell",
            "tavsif": "Tarixiy saboq bo'luvchi totalitar tuzum va erkinlik to'g'risidagi mashhur antiutopiya.",
        },
    ],
    "📐 Matematika & Mantiq": [
        {
            "nom": "Fermat's Enigma (Ferma siri)",
            "muallif": "Simon Singh",
            "tavsif": "350 yil davomida matematiklar yecholmagan eng buyuk boshqotirmani yechish tarixi.",
        },
        {
            "nom": "How Not to Be Wrong: The Power of Mathematical Thinking",
            "muallif": "Jordan Ellenberg",
            "tavsif": "Kundalik hayotda, biznesda va qaror qabul qilishda matematik fikrlash kuchi.",
        },
        {
            "nom": "The Joy of x (x ning jozibasi)",
            "muallif": "Steven Strogatz",
            "tavsif": "Matematika fanini sevib qolish va uning go'zalligini anglash bo'yicha sayohat.",
        },
        {
            "nom": "Gödel, Escher, Bach: An Eternal Golden Braid",
            "muallif": "Douglas Hofstadter",
            "tavsif": "Matematik mantiq, san'at, musiqa va sun'iy idrok o'rtasidagi sirli bog'liqlik.",
        },
        {
            "nom": "Evklidning 'Negizlar'i (Elements)",
            "muallif": "Evklid",
            "tavsif": "Geometriya va mantiqiy isbotlar tizimining ming yillik poydevori.",
        },
        {
            "nom": "The Math Book",
            "muallif": "Clifford A. Pickover",
            "tavsif": "Pifagordan to bugungi kunga qadar matematika tarixidagi 250 ta eng buyuk yutuq.",
        },
    ],
    "📖 O'zbek adabiyoti": [
        {
            "nom": "O'tkan kunlar",
            "muallif": "Abdulla Qodiriy",
            "tavsif": "O'zbek romanchiligining gultoji — Otabek va Kumushbibining sof muhabbati va fojiasi.",
        },
        {
            "nom": "Yulduzli tunlar",
            "muallif": "Pirimqul Qodirov",
            "tavsif": "Zahiriddin Muhammad Boburning murakkab hayoti, yurt sog'inchi va saltanat kurashlari.",
        },
        {
            "nom": "Dunyoning ishlari",
            "muallif": "O'tkir Hoshimov",
            "tavsif": "Onaga bo'lgan ehtirom, mehr-oqibat va bolalik xotiralari aks etgan betakror qissa.",
        },
        {
            "nom": "Kecha va kunduz",
            "muallif": "Abdulhamid Cho'lpon",
            "tavsif": "Jadid adabiyotining shoh asari — erk va istibdod, Zebi qismati orqali xalq fojiasi.",
        },
        {
            "nom": "Navoiy",
            "muallif": "Oybek",
            "tavsif": "Buyuk mutafakkir Alisher Navoiy hayoti, ijodi va davlat arbobi sifatidagi faoliyati.",
        },
        {
            "nom": "Shum bola",
            "muallif": "G'afur G'ulom",
            "tavsif": "O'zbek xalqining boy hazil tuyg'usi va qahramonning sarguzashtlari haqidagi asar.",
        },
    ],
    "🧠 Psixologiya & Biznes": [
        {
            "nom": "Thinking, Fast and Slow (Tez va sekin fikrlash)",
            "muallif": "Daniel Kahneman",
            "tavsif": "Nobel mukofoti sovrindoridan inson ongi qanday qaror qabul qilishi haqida tadqiqot.",
        },
        {
            "nom": "The Psychology of Money (Pul psixologiyasi)",
            "muallif": "Morgan Housel",
            "tavsif": "Boylik, moliyaviy barqarorlik va oqilona qarorlar ortidagi insoniy omillar.",
        },
        {
            "nom": "Zero to One",
            "muallif": "Peter Thiel",
            "tavsif": "Yangi g'oyalar yaratish, startaplar va kelajakni qurish qoidalari.",
        },
        {
            "nom": "Influence: The Psychology of Persuasion",
            "muallif": "Robert Cialdini",
            "tavsif": "Odamlarga ta'sir o'tkazish, ishontirish va manipulyatsiyadan himoyalanish sirlari.",
        },
        {
            "nom": "Rich Dad Poor Dad (Boy ota, kambag'al ota)",
            "muallif": "Robert Kiyosaki",
            "tavsif": "Moliyaviy erkinlikka erishish, aktivlar yaratish va investitsiya qilish sirlari.",
        },
        {
            "nom": "Good to Great (Yaxshidan buyukka)",
            "muallif": "Jim Collins",
            "tavsif": "Oddiy kompaniyalar qanday qilib uzoq muddatli buyuk kompaniyalarga aylanishi tahlili.",
        },
    ],
    "🌍 Jahon adabiyoti": [
        {
            "nom": "Graf Monte-Kristo",
            "muallif": "Alexandre Dumas",
            "tavsif": "Hiyonat, adolat, intiqom va sabr haqidagi jahon sarguzasht adabiyotining shoh asari.",
        },
        {
            "nom": "Alkimyogar (The Alchemist)",
            "muallif": "Paulo Coelho",
            "tavsif": "O'z orzusini izlab sayohatga chiqqan cho'pon yigitning hikmati va taqdir yo'li.",
        },
        {
            "nom": "Kichkina shahzoda (Le Petit Prince)",
            "muallif": "Antoine de Saint-Exupéry",
            "tavsif": "Kattalar va bolalar uchun qalb ko'zi bilan ko'rish va mehr-oqibat qissasi.",
        },
        {
            "nom": "Jinoyat va jazo",
            "muallif": "Fyodor Dostoyevskiy",
            "tavsif": "Inson vijdoni, axloqiy kurashlar va ruhiy poklanish haqidagi psixologik durdona.",
        },
        {
            "nom": "Usta va Margarita",
            "muallif": "Mixail Bulgakov",
            "tavsif": "Ezgu va yovuz kuchlar kurashi, sof sevgi va Moskvadagi sirli sarguzashtlar.",
        },
        {
            "nom": "Martin Iden",
            "muallif": "Jack London",
            "tavsif": "Oddiy dengizchining yozuvchi bo'lish yo'lidagi matonati va insoniy fojiasi.",
        },
    ],
}


# ============================================================
# MOTIVATSIYA IQTIBORLARI
# ============================================================

MOTIVATSIYA_QUOTES = [
    {"quote": "The only way to do great work is to love what you do.", "muallif": "Steve Jobs", "tarjima": "Ajoyib ish qilishning yagona yo'li — sevgan ishingizni qilish."},
    {"quote": "Believe you can and you're halfway there.", "muallif": "Theodore Roosevelt", "tarjima": "Qila olaman deb ishoning — yarim yo'lni bosib o'tgan bo'lasiz."},
    {"quote": "Success is not final, failure is not fatal.", "muallif": "Winston Churchill", "tarjima": "Muvaffaqiyat oxirgi emas, mag'lubiyat halokatli emas."},
    {"quote": "It does not matter how slowly you go as long as you do not stop.", "muallif": "Confucius", "tarjima": "Qanchalik sekin borsangiz ham muhim emas, asosiysi to'xtamang."},
    {"quote": "The future belongs to those who believe in the beauty of their dreams.", "muallif": "Eleanor Roosevelt", "tarjima": "Kelajak o'z orzularining go'zalligiga ishonganlarniki."},
    {"quote": "Education is the most powerful weapon which you can use to change the world.", "muallif": "Nelson Mandela", "tarjima": "Ta'lim — dunyoni o'zgartirish uchun ishlatishingiz mumkin bo'lgan eng kuchli qurol."},
    {"quote": "In the middle of difficulty lies opportunity.", "muallif": "Albert Einstein", "tarjima": "Qiyinchilikning o'rtasida imkoniyat yashiringan."},
    {"quote": "Don't watch the clock; do what it does. Keep going.", "muallif": "Sam Levenson", "tarjima": "Soatga qaramang; u nima qilsa, siz ham shuni qiling. Davom eting."},
    {"quote": "Your time is limited, don't waste it living someone else's life.", "muallif": "Steve Jobs", "tarjima": "Vaqtingiz cheklangan, uni boshqaning hayotini yashab sarflamang."},
    {"quote": "Hard work beats talent when talent doesn't work hard.", "muallif": "Tim Notke", "tarjima": "Iste'dod mehnat qilmasa, mehnat iste'doddan ustun keladi."},
    {"quote": "The best time to plant a tree was 20 years ago. The second best time is now.", "muallif": "Xitoy maqoli", "tarjima": "Daraxt ekishning eng yaxshi vaqti 20 yil oldin edi. Ikkinchi eng yaxshi vaqt — hozir."},
    {"quote": "Be the change that you wish to see in the world.", "muallif": "Mahatma Gandhi", "tarjima": "Dunyoda ko'rmoqchi bo'lgan o'zgarishning o'zi bo'ling."},
]


# ============================================================
# QIZIQARLI FAKTLAR
# ============================================================

FAKTLAR = [
    "🐙 Sakkizoyoqning 3 ta yuragi va ko'k qoni bor.",
    "🍯 Asal hech qachon buzilmaydi. 3000 yillik asal ham iste'mol qilinishi mumkin.",
    "🌍 Yerning 71% suv bilan qoplangan, lekin faqat 1% ichimlik suv.",
    "🧠 Inson miyasi 2% og'irlikka ega, lekin 20% energiyani sarflaydi.",
    "🐬 Delfinlar uxlayotganda miyasining faqat yarmi uxlaydi.",
    "⚡ Chaqmoq Quyosh yuzasidan 5 baravar issiq — 30,000°C gacha.",
    "🦷 Akula umri davomida 30,000 dan ortiq tish almashtirad.",
    "🌙 Oy har yili Yerdan 3.8 sm uzoqlashib bormoqda.",
    "🐜 Chumolilar o'z og'irligidan 50 baravar og'ir yuk ko'tara oladi.",
    "🎵 Musiqa tinglash miyada dopamin ishlab chiqaradi — shokolad yegandek.",
    "📱 Birinchi SMS 1992-yilda yuborilgan. Matni: 'Merry Christmas' edi.",
    "🌳 Bitta daraxt yiliga taxminan 22 kg CO2 yutadi.",
    "🐋 Ko'k kit yuragi Volkswagen Beetle avtomobili kattaligida.",
    "🔭 Koinotda Yerdagi qumdonadek ko'proq yulduz bor.",
    "🧬 Insonning DNK si 99.9% boshqa odamlar bilan bir xil.",
    "🦑 Ulkan kalmar ko'zi futbol to'pi kattaligida.",
    "🌋 Venera sayyorasida kunlar yillardan uzun.",
    "🐝 Asalarilar matematik hisob-kitob qila oladi.",
    "🏔 Everest tog'i har yili 4 mm balandlashmoqda.",
    "💧 Suv — yagona modda bo'lib, tabiiy ravishda 3 holatda mavjud: suyuq, qattiq va gaz.",
]


# ============================================================
# MATEMATIK MASALALAR (A, B, C VARIANTLARI BILAN)
# ============================================================

def generate_math_problem_with_options():
    problem_type = random.choice(["add", "sub", "mul", "div", "square", "cube", "sqrt", "equation", "percent", "geometry"])

    if problem_type == "add":
        a, b = random.randint(10, 999), random.randint(10, 999)
        ans = a + b
        problem_str = f"{a} + {b} = ?"
    elif problem_type == "sub":
        a = random.randint(100, 999)
        b = random.randint(10, a)
        ans = a - b
        problem_str = f"{a} - {b} = ?"
    elif problem_type == "mul":
        a, b = random.randint(2, 25), random.randint(2, 25)
        ans = a * b
        problem_str = f"{a} × {b} = ?"
    elif problem_type == "div":
        b = random.randint(2, 20)
        ans = random.randint(2, 50)
        a = b * ans
        problem_str = f"{a} ÷ {b} = ?"
    elif problem_type == "square":
        a = random.randint(2, 25)
        ans = a ** 2
        problem_str = f"{a}² = ?"
    elif problem_type == "cube":
        a = random.randint(2, 10)
        ans = a ** 3
        problem_str = f"{a}³ = ?"
    elif problem_type == "sqrt":
        ans = random.randint(2, 25)
        a = ans ** 2
        problem_str = f"√{a} = ?"
    elif problem_type == "equation":
        a = random.randint(2, 9)
        ans = random.randint(2, 15)
        b = random.randint(1, 30)
        c = a * ans + b
        problem_str = f"{a}x + {b} = {c}  (x = ?)"
    elif problem_type == "geometry":
        a = random.randint(3, 20)
        b = random.randint(3, 20)
        ans = 2 * (a + b)
        problem_str = f"Tomonlari {a} va {b} bo'lgan to'rtburchak perimetri = ?"
    else:  # percent
        a = random.randint(1, 20) * 10
        p = random.choice([10, 20, 25, 50, 75])
        ans = int(a * p / 100)
        problem_str = f"{a} ning {p}% = ?"

    # 2 ta chalg'ituvchi variant hosil qilish (A, B, C jami 3 ta variant)
    offsets = [-10, 10, -1, 1, -2, 2, -5, 5, -3, 3, -20, 20, 15, -15]
    random.shuffle(offsets)
    wrong = set()
    for off in offsets:
        cand = ans + off
        if cand != ans and cand >= 0:
            wrong.add(cand)
        if len(wrong) >= 2:
            break

    options = [ans] + list(wrong)[:2]
    random.shuffle(options)
    correct_idx = options.index(ans)

    return {
        "problem": problem_str,
        "options": [str(x) for x in options],
        "correct_idx": correct_idx,
        "answer": str(ans),
    }


def generate_math_problem():
    """Moslik uchun eski funksiya."""
    data = generate_math_problem_with_options()
    return data["problem"], data["answer"]


# ============================================================
# QUIZ SAVOLLARI (20 ta — EN/UZ/RU)
# ============================================================

QUIZ_QUESTIONS = [
    {
        "savol": "🇬🇧 'Apple' so'zining o'zbekcha tarjimasi nima?",
        "variantlar": ["🍎 Olma", "🍊 Apelsin", "🍌 Banan", "🍇 Uzum"],
        "javob": 0,
        "tushuntirish": "🇬🇧 Apple = 🇺🇿 Olma = 🇷🇺 Яблоко"
    },
    {
        "savol": "🇷🇺 'Книга' so'zining inglizcha tarjimasi nima?",
        "variantlar": ["Pen", "Book", "Table", "Chair"],
        "javob": 1,
        "tushuntirish": "🇷🇺 Книга = 🇬🇧 Book = 🇺🇿 Kitob"
    },
    {
        "savol": "🇺🇿 'Suv' so'zining inglizcha tarjimasi nima?",
        "variantlar": ["Fire", "Earth", "Water", "Air"],
        "javob": 2,
        "tushuntirish": "🇺🇿 Suv = 🇬🇧 Water = 🇷🇺 Вода"
    },
    {
        "savol": "🇬🇧 'Beautiful' so'zining o'zbekcha tarjimasi nima?",
        "variantlar": ["Kuchli", "Tez", "Chiroyli", "Katta"],
        "javob": 2,
        "tushuntirish": "🇬🇧 Beautiful = 🇺🇿 Chiroyli = 🇷🇺 Красивый"
    },
    {
        "savol": "🇷🇺 'Солнце' so'zining o'zbekcha tarjimasi nima?",
        "variantlar": ["Oy", "Yulduz", "Bulut", "Quyosh"],
        "javob": 3,
        "tushuntirish": "🇷🇺 Солнце = 🇺🇿 Quyosh = 🇬🇧 Sun"
    },
    {
        "savol": "🇬🇧 'Friend' so'zining o'zbekcha ma'nosi nima?",
        "variantlar": ["Do'st", "Qo'shni", "Dushman", "Aka"],
        "javob": 0,
        "tushuntirish": "🇬🇧 Friend = 🇺🇿 Do'st = 🇷🇺 Друг"
    },
    {
        "savol": "🇹🇷 'Teşekkür ederim' iborasi o'zbekchada nima degani?",
        "variantlar": ["Salom", "Rahmat / Tashakkur", "Xayr", "Kechirasiz"],
        "javob": 1,
        "tushuntirish": "🇹🇷 Teşekkür ederim = 🇺🇿 Rahmat, minnatdorman"
    },
    {
        "savol": "🇷🇺 'Работа' so'zining inglizcha tarjimasi nima?",
        "variantlar": ["Rest", "Play", "Work", "Sleep"],
        "javob": 2,
        "tushuntirish": "🇷🇺 Работа = 🇬🇧 Work = 🇺🇿 Ish"
    },
    {
        "savol": "🇺🇿 'Vatan' so'zining inglizcha tarjimasi nima?",
        "variantlar": ["City", "Country", "Village", "Homeland"],
        "javob": 3,
        "tushuntirish": "🇺🇿 Vatan = 🇬🇧 Homeland = 🇷🇺 Родина"
    },
    {
        "savol": "🇬🇧 'Knowledge' so'zining o'zbekcha tarjimasi qaysi?",
        "variantlar": ["Bilim", "Kuch", "Do'st", "Vaqt"],
        "javob": 0,
        "tushuntirish": "🇬🇧 Knowledge = 🇺🇿 Bilim = 🇷🇺 Знание"
    },
    {
        "savol": "🇷🇺 'Время' so'zining inglizcha tarjimasi nima?",
        "variantlar": ["Money", "Time", "Watch", "Hour"],
        "javob": 1,
        "tushuntirish": "🇷🇺 Время = 🇬🇧 Time = 🇺🇿 Vaqt"
    },
    {
        "savol": "🇺🇿 'Oila' so'zining inglizchasi nima?",
        "variantlar": ["Friends", "People", "Family", "Children"],
        "javob": 2,
        "tushuntirish": "🇺🇿 Oila = 🇬🇧 Family = 🇷🇺 Семья"
    },
    {
        "savol": "🇬🇧 'She ___ to school every day.' — to'g'ri fe'lni tanlang:",
        "variantlar": ["goes", "go", "going", "gone"],
        "javob": 0,
        "tushuntirish": "3-shaxs birlikda (Present Simple) fe'lga -es qo'shiladi: She goes."
    },
    {
        "savol": "🇬🇧 'I ___ from Uzbekistan.' — to'g'ri 'to be' shakli:",
        "variantlar": ["is", "am", "are", "be"],
        "javob": 1,
        "tushuntirish": "I uchun 'am' ishlatiladi: I am."
    },
    {
        "savol": "🇬🇧 'Go' fe'lining o'tgan zamon (Past Simple) shakli qaysi?",
        "variantlar": ["Gone", "Going", "Went", "Goes"],
        "javob": 2,
        "tushuntirish": "Go -> Went -> Gone (Noto'g'ri fe'l)."
    },
    {
        "savol": "🇷🇺 'Я ___ книгу' — to'g'ri fe'lni tanlang:",
        "variantlar": ["читает", "читаем", "читаете", "читаю"],
        "javob": 3,
        "tushuntirish": "Я читаю (1-shaxs birlik) = Men kitob o'qiyapman."
    },
    {
        "savol": "🇬🇧 'There ___ many students in the library.'",
        "variantlar": ["are", "is", "was", "am"],
        "javob": 0,
        "tushuntirish": "Many students ko'plik bo'lgani uchun 'are' ishlatiladi."
    },
    {
        "savol": "🇬🇧 Qaysi gap to'g'ri tuzilgan?",
        "variantlar": ["He can swims", "He can swim", "He can to swim", "He can swimming"],
        "javob": 1,
        "tushuntirish": "Modal fe'llardan (can, must) keyin fe'lning sof shakli (bare infinitive) keladi."
    },
    {
        "savol": "🇬🇧 'The book is ___ the table' — (ustida) ma'nosida:",
        "variantlar": ["under", "in", "on", "at"],
        "javob": 2,
        "tushuntirish": "On = ustida, Under = tagida, In = ichida."
    },
    {
        "savol": "🇬🇧 'I have been living here ___ 2020.'",
        "variantlar": ["for", "in", "from", "since"],
        "javob": 3,
        "tushuntirish": "Aniq boshlanish vaqti (yil, sana) bilan 'since' ishlatiladi."
    },
    {
        "savol": "🇬🇧 'Good' sifatining qiyosiy darajasi (Comparative):",
        "variantlar": ["Better", "Gooder", "More good", "Best"],
        "javob": 0,
        "tushuntirish": "Good -> Better -> Best."
    },
    {
        "savol": "🇷🇺 'Мы ___ в Ташкенте.' — to'g'ri shakl:",
        "variantlar": ["живу", "живём", "живёт", "живут"],
        "javob": 1,
        "tushuntirish": "Мы живём (1-shaxs ko'plik)."
    },
    {
        "savol": "🇬🇧 'If it rains, we ___ at home.'",
        "variantlar": ["stayed", "would stay", "will stay", "had stayed"],
        "javob": 2,
        "tushuntirish": "First Conditional: If + Present Simple, will + verb."
    },
    {
        "savol": "🇬🇧 'She is interested ___ art.' — to'g'ri predlogni tanlang:",
        "variantlar": ["at", "on", "for", "in"],
        "javob": 3,
        "tushuntirish": "To be interested in — biror narsaga qiziqmoq."
    },
    {
        "savol": "🇬🇧 'Enormous' so'zining ma'nosi nima?",
        "variantlar": ["Juda katta / Ulkan", "Juda kichik", "Tezkor", "Qorong'i"],
        "javob": 0,
        "tushuntirish": "🇬🇧 Enormous = Ulkan, behad katta = 🇷🇺 Огромный"
    },
    {
        "savol": "🇬🇧 'Brave' (jasur) so'zining antonimi qaysi?",
        "variantlar": ["Strong", "Cowardly", "Smart", "Kind"],
        "javob": 1,
        "tushuntirish": "Brave (jasur) <-> Cowardly (qo'rqoq)."
    },
    {
        "savol": "🇬🇧 'Piece of cake' idiomasining asl ma'nosi nima?",
        "variantlar": ["Shirin tort", "Qimmat taom", "Juda oson ish", "Tug'ilgan kun"],
        "javob": 2,
        "tushuntirish": "'A piece of cake' — juda oson, xamir uchidan patir degan ma'noda."
    },
    {
        "savol": "🇬🇧 'Break a leg' iborasi qachon ishlatiladi?",
        "variantlar": ["Xavf bo'lganda", "Urushda", "Kasalxonada", "Omad tilaganda"],
        "javob": 3,
        "tushuntirish": "'Break a leg' — san'atkorlarga yoki imtihon oldidan omad tilash iborasi."
    },
    {
        "savol": "🇬🇧 'Difficult' so'zining sinonimi qaysi?",
        "variantlar": ["Hard", "Easy", "Simple", "Light"],
        "javob": 0,
        "tushuntirish": "Difficult = Hard (Qiyin, murakkab)."
    },
    {
        "savol": "🇬🇧 'Under the weather' iborasi nimani bildiradi?",
        "variantlar": ["Yomg'ir ostida", "O'zini betob his qilish", "Quyoshli kun", "Ob-havo ma'lumoti"],
        "javob": 1,
        "tushuntirish": "'Under the weather' — biroz tobi qochgan, o'zini betob sezish."
    },
    {
        "savol": "🇬🇧 'Generous' so'zining ma'nosi nima?",
        "variantlar": ["Xasis", "Qaysar", "Saxiy / Qo'li ochiq", "Jahldor"],
        "javob": 2,
        "tushuntirish": "Generous = Saxiy, ochiqko'ngil."
    },
    {
        "savol": "🇬🇧 'Bilingual' so'zi nimani anglatadi?",
        "variantlar": ["Tilsiz", "Bitta til biluvchi", "Uch tilli", "Ikki til biluvchi"],
        "javob": 3,
        "tushuntirish": "Bi- (ikki) + lingual (til) = Ikki tilni mukammal biluvchi."
    },
    {
        "savol": "🇬🇧 'Ancient' so'zining ma'nosi qaysi?",
        "variantlar": ["Qadimiy / Qari", "Zamonaviy", "Kelajakdagi", "Yangi"],
        "javob": 0,
        "tushuntirish": "Ancient = Qadimiy, antik."
    },
    {
        "savol": "🇬🇧 'Patience' so'zining o'zbekcha tarjimasi:",
        "variantlar": ["Shoshqaloqlik", "Sabr-toqat", "Jasorat", "G'alaba"],
        "javob": 1,
        "tushuntirish": "Patience = Sabr, toqat."
    },
    {
        "savol": "🇬🇧 'Once in a blue moon' iborasining ma'nosi:",
        "variantlar": ["Har kecha", "To'lin oyda", "Juda kamdan-kam hollarda", "Hech qachon"],
        "javob": 2,
        "tushuntirish": "'Once in a blue moon' — amalda deyarli yuz bermaydigan, juda kamdan-kam bo'ladigan voqea."
    },
    {
        "savol": "🇬🇧 'Proud of' birikmasi nimani bildiradi?",
        "variantlar": ["Qo'rqmoq", "Uyalmoq", "Xafa bo'lmoq", "Faxrlanmoq"],
        "javob": 3,
        "tushuntirish": "Proud of = Bilan faxrlanmoq."
    },
    {
        "savol": "🧠 Bir poyezdda 10 ta vagon bor. 5-vagon boshidan nechanchi va oxiridan nechanchi?",
        "variantlar": ["Boshidan 5, oxiridan 6", "Boshidan 5, oxiridan 5", "Boshidan 4, oxiridan 6", "Boshidan 6, oxiridan 5"],
        "javob": 0,
        "tushuntirish": "Boshidan: 1, 2, 3, 4, 5. Oxiridan: 10, 9, 8, 7, 6 (demak 6-bo'ladi)."
    },
    {
        "savol": "🧠 Qaysi oyda 28 kun bor?",
        "variantlar": ["Faqat Fevralda", "Barcha 12 ta oyda", "Faqat kabisa yilida", "Aprel va Iyun"],
        "javob": 1,
        "tushuntirish": "Barcha 12 ta oyning hammasida kamida 28 kun bor!"
    },
    {
        "savol": "🧠 Otasi va o'g'lining yoshlari yig'indisi 66 yosh. Otasining yoshi o'g'linikining teskari yozilgani. Ular necha yoshda?",
        "variantlar": ["40 va 26", "52 va 14", "60 va 6 (yoki 51 va 15, 42 va 24)", "45 va 21"],
        "javob": 2,
        "tushuntirish": "Masalan, 51 + 15 = 66, 42 + 24 = 66 yoki 60 + 06 = 66."
    },
    {
        "savol": "🧠 Shifokor bemorga 3 ta dori berdi va har yarim soatda bittadan ichishni buyurdi. Dorilar qancha vaqtga yetadi?",
        "variantlar": ["1.5 soat", "2 soat", "30 minut", "1 soat"],
        "javob": 3,
        "tushuntirish": "1-dori darhol (0-daqiqa), 2-dori 30-daqiqada, 3-dori 60-daqiqada (1 soat)."
    },
    {
        "savol": "🧠 Bir kishi yomg'irda soyabonsiz qoldi, lekin uning birorta ham sochi ho'l bo'lmadi. Nega?",
        "variantlar": ["U kal edi", "Yomg'ir to'xtagan edi", "U daraxt ostida edi", "Bosh kiyimi bor edi"],
        "javob": 0,
        "tushuntirish": "Uning umuman sochi yo'q edi (kal edi)."
    },
    {
        "savol": "🧠 Qancha ko'p olsangiz, shuncha kattalashadigan narsa nima?",
        "variantlar": ["Tog'", "O'ra (chuqur)", "Qarz", "Daryo"],
        "javob": 1,
        "tushuntirish": "Chuqurdan tuproqni qancha ko'p olsangiz, u shuncha kattalashadi."
    },
    {
        "savol": "🧠 Men gapirmayman, lekin dunyo yangiliklarini aytaman. Men kimman?",
        "variantlar": ["Telefon", "Radio", "Kitob / Gazeta", "Ko'zgu"],
        "javob": 2,
        "tushuntirish": "Kitob yoki gazeta ovozsiz, lekin bilimlarni yetkazadi."
    },
    {
        "savol": "🧠 1 kg temir og'irmi yoki 1 kg paxtami?",
        "variantlar": ["Temir og'ir", "Paxta og'ir", "Sharoitga bog'liq", "Ikkalasi teng"],
        "javob": 3,
        "tushuntirish": "Ikkalasining ham vazni 1 kg, demak teng."
    },
    {
        "savol": "🧠 Xonada 4 ta burchak bor. Har bir burchakda bittadan mushuk o'tiribdi. Har bir mushuk qarshisida 3 tadan mushuk bor. Jami nechta mushuk?",
        "variantlar": ["4 ta mushuk", "12 ta mushuk", "16 ta mushuk", "8 ta mushuk"],
        "javob": 0,
        "tushuntirish": "Xonada jami 4 ta mushuk bor, har biri qolgan 3 tasini ko'rib turibdi."
    },
    {
        "savol": "🧠 Bir tuxum 4 daqiqada pishsa, 4 ta tuxum necha daqiqada pishadi?",
        "variantlar": ["16 daqiqa", "4 daqiqa", "8 daqiqa", "1 daqiqa"],
        "javob": 1,
        "tushuntirish": "Barcha 4 ta tuxum bitta qozonda bir vaqtda 4 daqiqada pishadi."
    },
    {
        "savol": "🧠 Qaysi so'z doimo xato yoziladi?",
        "variantlar": ["Grammatika", "Lug'at", "'Xato' so'zining o'zi", "Alifbo"],
        "javob": 2,
        "tushuntirish": "'Xato' so'zi qanday yozilsa ham aynan 'xato' deb yoziladi."
    },
    {
        "savol": "🧠 Ot, tovuq va sigirning birgalikda nechta oyog'i bor?",
        "variantlar": ["8 ta", "12 ta", "14 ta", "10 ta"],
        "javob": 3,
        "tushuntirish": "Ot (4) + tovuq (2) + sigir (4) = 10 ta oyoq."
    },
    {
        "savol": "🌍 Dunyodagi eng baland cho'qqi qaysi?",
        "variantlar": ["Everest (Jomolungma)", "K2", "Monblan", "Elbrus"],
        "javob": 0,
        "tushuntirish": "Everest cho'qqisi dengiz sathidan 8,848 metr balandlikda joylashgan."
    },
    {
        "savol": "🌍 Dunyodagi eng uzun daryo qaysi?",
        "variantlar": ["Amazonka", "Nil", "Yangszzi", "Missisipi"],
        "javob": 1,
        "tushuntirish": "Nil daryosi (Afrika) uzunligi taxminan 6,650 km ni tashkil qiladi."
    },
    {
        "savol": "🔬 Quyosh tizimidagi eng katta sayyora qaysi?",
        "variantlar": ["Mars", "Saturn", "Yupiter", "Neptun"],
        "javob": 2,
        "tushuntirish": "Yupiter Quyosh tizimidagi eng ulkan gigant gaz sayyorasidir."
    },
    {
        "savol": "🔬 Inson tanasidagi eng katta a'zo qaysi?",
        "variantlar": ["Jigar", "Yurak", "O'pka", "Teri"],
        "javob": 3,
        "tushuntirish": "Inson terisi tana yuzasi va og'irligi bo'yicha eng katta a'zo hisoblanadi."
    },
    {
        "savol": "🌍 O'zbekiston Respublikasi mustaqillikka erishgan sana:",
        "variantlar": ["1991-yil 1-sentyabr", "1992-yil 8-dekabr", "1989-yil 21-oktyabr", "1993-yil 1-sentyabr"],
        "javob": 0,
        "tushuntirish": "O'zbekiston 1991-yil 1-sentyabrda o'z mustaqilligini e'lon qilgan."
    },
    {
        "savol": "📚 'Al-Qonun fit-tibb' (Tibbiyot qonunlari) asarining muallifi kim?",
        "variantlar": ["Al-Xorazmiy", "Abu Ali ibn Sino", "Al-Beruniy", "Mirzo Ulug'bek"],
        "javob": 1,
        "tushuntirish": "Buyuk alloma Abu Ali ibn Sino (Avitsenna) tibbiyot ensiklopediyasining muallifidir."
    },
    {
        "savol": "🔬 Suvning kimyoviy formulasi qanday?",
        "variantlar": ["CO2", "NaCl", "H2O", "O2"],
        "javob": 2,
        "tushuntirish": "Suv vodorod va kisloroddan iborat: H₂O."
    },
    {
        "savol": "🌍 Dunyodagi eng katta okean qaysi?",
        "variantlar": ["Atlantika okeani", "Hind okeani", "Shimoliy Muz okeani", "Tinch okeani"],
        "javob": 3,
        "tushuntirish": "Tinch okeani (Tinch/Tinch okean) yer yuzasining uchdan bir qismini egallaydi."
    },
    {
        "savol": "🔬 Yorug'lik tezligi sekundiga taxminan necha km?",
        "variantlar": ["300,000 km/s", "150,000 km/s", "1,000 km/s", "30,000 km/s"],
        "javob": 0,
        "tushuntirish": "Vakuumda yorug'lik tezligi taxminan 300,000 km/soniya."
    },
    {
        "savol": "🌍 Alifbedagi 'Nol' (0) raqami va algebra asoschisi bo'lgan buyuk alloma kim?",
        "variantlar": ["Pifagor", "Muhammad al-Xorazmiy", "Evklid", "Arximed"],
        "javob": 1,
        "tushuntirish": "Al-Xorazmiy algebra fanining asoschisi bo'lib, 'algoritm' so'zi ham uning nomidan kelib chiqqan."
    },
    {
        "savol": "🔬 Havoning asosiy qismini (taxminan 78%) qaysi gaz tashkil etadi?",
        "variantlar": ["Kislorod", "Karbonat angidrid", "Azot", "Vodorod"],
        "javob": 2,
        "tushuntirish": "Atmosfera havosining taxminan 78% qismi Azot (N₂) gazidan iborat."
    },
    {
        "savol": "🌍 BMT (Birlashgan Millatlar Tashkiloti) bosh qarorgohi qaysi shaharda joylashgan?",
        "variantlar": ["Jeneva", "London", "Parij", "Nyu-York"],
        "javob": 3,
        "tushuntirish": "BMTning bosh qarorgohi AQShning Nyu-York shahrida joylashgan."
    },
]


# ============================================================
# DATABASE
# ============================================================

def init_database():

    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            searches INTEGER DEFAULT 0,
            target_lang TEXT DEFAULT 'auto',
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            result TEXT,
            created_at TEXT
        )
    """)

    # Agar eski jadvalda target_lang ustuni bo'lmasa, qo'shamiz
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN target_lang TEXT DEFAULT 'auto'")
    except sqlite3.OperationalError:
        pass  # Ustun allaqachon mavjud

    connection.commit()
    connection.close()


def register_user(
    user_id: int,
    username: str,
    full_name: str
):

    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO users
        (
            user_id,
            username,
            full_name,
            searches,
            target_lang,
            created_at
        )
        VALUES (?, ?, ?, 0, 'auto', ?)
        """,
        (
            user_id,
            username,
            full_name,
            datetime.now().isoformat()
        )
    )

    connection.commit()
    connection.close()


def set_user_lang(user_id: int, lang: str):

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE users SET target_lang = ? WHERE user_id = ?",
        (lang, user_id)
    )

    connection.commit()
    connection.close()

    user_target_lang[user_id] = lang


def get_user_lang(user_id: int) -> str:

    if user_id in user_target_lang:
        return user_target_lang[user_id]

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT target_lang FROM users WHERE user_id = ?",
        (user_id,)
    )

    row = cursor.fetchone()
    connection.close()

    lang = row[0] if row and row[0] else "auto"
    user_target_lang[user_id] = lang

    return lang


def increment_search(user_id: int):

    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        UPDATE users
        SET searches = searches + 1
        WHERE user_id = ?
        """,
        (user_id,)
    )

    connection.commit()
    connection.close()


def save_history(
    user_id: int,
    text: str,
    result: str
):

    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO history
        (
            user_id,
            text,
            result,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            text,
            result,
            datetime.now().isoformat()
        )
    )

    connection.commit()
    connection.close()


def get_user_stats(user_id: int):

    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT searches
        FROM users
        WHERE user_id = ?
        """,
        (user_id,)
    )

    row = cursor.fetchone()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM history
        WHERE user_id = ?
        """,
        (user_id,)
    )

    history_count = cursor.fetchone()[0]

    connection.close()

    searches = row[0] if row else 0

    return searches, history_count


def get_history(user_id: int, limit=10):

    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT text, result
        FROM history
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit)
    )

    rows = cursor.fetchall()

    connection.close()

    return rows


def clear_history(user_id: int):

    connection = sqlite3.connect(DB_NAME)

    cursor = connection.cursor()

    cursor.execute(
        """
        DELETE FROM history
        WHERE user_id = ?
        """,
        (user_id,)
    )

    connection.commit()
    connection.close()


# ============================================================
# MULTI-ENGINE TRANSLATOR (googletrans + deep_translator + MyMemory)
# ============================================================

try:
    from googletrans import Translator as GoogleTrans
    _gt_translator = GoogleTrans()
except Exception:
    _gt_translator = None

try:
    from deep_translator import GoogleTranslator as DeepGoogleTranslator, MyMemoryTranslator
except Exception:
    DeepGoogleTranslator = None
    MyMemoryTranslator = None

try:
    from langdetect import detect as langdetect_detect
except Exception:
    langdetect_detect = None


def _detect_script_heuristic(text: str) -> str | None:
    """Belgilar to'plami bo'yicha tezkor tilni aniqlash."""
    import re
    # Koreyscha
    if re.search(r"[\uac00-\ud7a3]", text):
        return "ko"
    # Arabcha
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
    # Yaponcha
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    # Kirillcha (Ruscha yoki O'zbek kirillcha)
    if re.search(r"[\u0400-\u04ff]", text):
        return "ru"
    # O'zbekcha lotiniga xos belgilar/so'zlar
    uz_markers = ["o‘", "o'", "g‘", "g'", "sh", "ch", " emas", " va ", " uchun", " bilan", " bu ", " men ", " siz "]
    lower_text = " " + text.lower() + " "
    if any(m in lower_text for m in uz_markers):
        return "uz"
    return None


def _google_direct_translate_sync(text: str, sl: str = "auto", tl: str = "uz") -> tuple[str | None, str | None]:
    """Google Translate API orqali (client=it / dict-chrome-ex) to'g'ridan-to'g'ri so'rov yuborish.
    Bu googletrans 302/429 xatolarini chetlab o'tadi."""
    clients = ["it", "dict-chrome-ex", "t"]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*",
    }
    for client in clients:
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": client,
                "sl": sl,
                "tl": tl,
                "dt": "t",
                "q": text,
                "ie": "UTF-8",
                "oe": "UTF-8",
            }
            r = requests.get(url, params=params, headers=headers, timeout=6)
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                    translated = "".join(part[0] for part in data[0] if part and part[0])
                    detected = data[2] if len(data) > 2 and isinstance(data[2], str) else None
                    if translated and translated.strip():
                        return translated.strip(), detected
        except Exception as err:
            logger.debug("Google direct (%s) xatosi: %s", client, err)
    return None, None


def _mymemory_direct_sync(text: str, sl: str = "uz", tl: str = "ru") -> str | None:
    """MyMemory API orqali bepul tarjima zaxirasi."""
    lang_map = {
        "uz": "uz-UZ", "en": "en-GB", "ru": "ru-RU", "tr": "tr-TR",
        "ko": "ko-KR", "de": "de-DE", "fr": "fr-FR", "ar": "ar-SA",
        "ja": "ja-JP", "es": "es-ES", "zh": "zh-CN", "it": "it-IT"
    }
    src_code = lang_map.get(sl, sl)
    dst_code = lang_map.get(tl, tl)
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {"q": text, "langpair": f"{src_code}|{dst_code}"}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        r = requests.get(url, params=params, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            if data.get("responseStatus") == 200:
                res = data.get("responseData", {}).get("translatedText")
                if res and "INVALID" not in res.upper() and res.strip() != text.strip():
                    return res.strip()
    except Exception as err:
        logger.debug("MyMemory direct xatosi: %s", err)
    return None


async def translator_detect(text: str):
    """Matn tilini aniqlash (ko'p bosqichli ishonchli tizim)."""
    clean_text = text.strip()[:200]
    if not clean_text:
        class DummyDetected:
            lang = "en"
        return DummyDetected()

    # 1. Tezkor script/belgi tahlili
    heuristic_lang = _detect_script_heuristic(clean_text)
    if heuristic_lang:
        class HeuristicDetected:
            lang = heuristic_lang
        return HeuristicDetected()

    # 2. Google Direct API orqali aniqlash
    try:
        _, detected = await asyncio.to_thread(_google_direct_translate_sync, clean_text, "auto", "en")
        if detected:
            class DetectedResult:
                lang = str(detected).lower()
            return DetectedResult()
    except Exception as e:
        logger.debug("Google direct detect xatosi: %s", e)

    # 3. langdetect
    if langdetect_detect:
        try:
            detected = await asyncio.to_thread(langdetect_detect, clean_text)
            if detected:
                class DetectedResult:
                    lang = str(detected).lower()
                return DetectedResult()
        except Exception as e:
            logger.debug("langdetect xatosi: %s", e)

    # 4. googletrans fallback
    if _gt_translator:
        try:
            def _detect_gt():
                res = _gt_translator.detect(clean_text)
                return getattr(res, "lang", None)
            detected = await asyncio.to_thread(_detect_gt)
            if detected:
                class DetectedResult:
                    lang = str(detected).lower()
                return DetectedResult()
        except Exception as e:
            logger.debug("googletrans detect xatosi: %s", e)

    class DummyDetected:
        lang = "en"
    return DummyDetected()


async def translator_translate(
    text: str,
    destination: str
):
    """Matnni belgilangan tilga tarjima qilish (Multi-Engine ishonchli tizim)."""
    clean_text = text.strip()
    if not clean_text:
        class DummyTranslated:
            def __init__(self, t):
                self.text = t
        return DummyTranslated(text)

    # 1-Urinish: Google Direct API (client=it / dict-chrome-ex)
    try:
        translated, _ = await asyncio.to_thread(_google_direct_translate_sync, clean_text, "auto", destination)
        if translated:
            class TranslatedResult:
                def __init__(self, t):
                    self.text = t
            return TranslatedResult(translated)
    except Exception as e:
        logger.warning("Google Direct translate xatosi: %s", e)

    # 2-Urinish: deep_translator (GoogleTranslator)
    if DeepGoogleTranslator:
        try:
            def _run_dt():
                return DeepGoogleTranslator(source='auto', target=destination).translate(clean_text)
            translated = await asyncio.to_thread(_run_dt)
            if translated and translated.strip() and (destination == "auto" or translated.strip() != clean_text):
                class TranslatedResult:
                    def __init__(self, t):
                        self.text = t
                return TranslatedResult(translated)
        except Exception as e:
            logger.warning("deep_translator translate xatosi: %s", e)

    # 3-Urinish: MyMemory Direct API fallback
    try:
        detected_res = await translator_detect(clean_text)
        src_lang = getattr(detected_res, "lang", "uz") or "uz"
        if src_lang == destination:
            src_lang = "en" if destination == "uz" else "uz"

        translated = await asyncio.to_thread(_mymemory_direct_sync, clean_text, src_lang, destination)
        if translated:
            class TranslatedResult:
                def __init__(self, t):
                    self.text = t
            return TranslatedResult(translated)
    except Exception as e:
        logger.warning("MyMemory Direct translate xatosi: %s", e)

    # 4-Urinish: googletrans fallback
    if _gt_translator:
        try:
            def _run_gt():
                res = _gt_translator.translate(clean_text, dest=destination)
                return getattr(res, "text", None)
            translated = await asyncio.to_thread(_run_gt)
            if translated and translated.strip() != clean_text:
                class TranslatedResult:
                    def __init__(self, t):
                        self.text = t
                return TranslatedResult(translated)
        except Exception as e:
            logger.warning("googletrans translate xatosi: %s", e)

    class DummyTranslated:
        def __init__(self, t):
            self.text = t
    return DummyTranslated(text)


# ============================================================
# INLINE KEYBOARDS
# ============================================================

def get_main_menu_keyboard():
    """Asosiy menyu Reply Keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🌐 Tarjima tili"),
                KeyboardButton(text="📚 Kutubxona"),
            ],
            [
                KeyboardButton(text="📝 Test topshirish"),
                KeyboardButton(text="🎲 Quiz / Savol"),
            ],
            [
                KeyboardButton(text="🧮 Matematik"),
                KeyboardButton(text="🔤 Alifbo"),
            ],
            [
                KeyboardButton(text="💡 Fakt"),
                KeyboardButton(text="🔥 Motivatsiya"),
            ],
            [
                KeyboardButton(text="🌤 Ob-havo"),
                KeyboardButton(text="❓ Yordam"),
            ],
            [
                KeyboardButton(text="📷 Rasm tarjima"),
                KeyboardButton(text="🎥 Video tarjima"),
            ],
            [
                KeyboardButton(text="📊 Statistika"),
                KeyboardButton(text="🕘 Tarix"),
            ],
        ],
        resize_keyboard=True,
    )


def get_alphabet_keyboard():
    """Alifbo tillarini tanlash Reply Keyboard (9 ta til)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🇬🇧 Ingliz alifbosi"),
                KeyboardButton(text="🇷🇺 Rus alifbosi"),
            ],
            [
                KeyboardButton(text="🇰🇷 Koreys alifbosi (Hangul)"),
                KeyboardButton(text="🇹🇷 Turk alifbosi"),
            ],
            [
                KeyboardButton(text="🇺🇿 O'zbek alifbosi"),
                KeyboardButton(text="🇸🇦 Arab alifbosi"),
            ],
            [
                KeyboardButton(text="🇩🇪 Nemis alifbosi"),
                KeyboardButton(text="🇫🇷 Fransuz alifbosi"),
            ],
            [
                KeyboardButton(text="🇯🇵 Yapon alifbosi"),
                KeyboardButton(text="⬅️ Asosiy menyu"),
            ],
        ],
        resize_keyboard=True,
    )


def get_test_lang_keyboard():
    """Test tilini va fanini tanlash Reply Keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🇬🇧 Ingliz tili testi"),
                KeyboardButton(text="🇷🇺 Rus tili testi"),
            ],
            [
                KeyboardButton(text="🇰🇷 Koreys tili testi"),
                KeyboardButton(text="🇹🇷 Turk tili testi"),
            ],
            [
                KeyboardButton(text="🧮 Matematika testi"),
                KeyboardButton(text="⬅️ Asosiy menyu"),
            ],
        ],
        resize_keyboard=True,
    )


def get_test_count_keyboard():
    """Test savollari sonini tanlash Reply Keyboard (20, 40, 60, 80, 100)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="20 ta savol"),
                KeyboardButton(text="40 ta savol"),
            ],
            [
                KeyboardButton(text="60 ta savol"),
                KeyboardButton(text="80 ta savol"),
            ],
            [
                KeyboardButton(text="100 ta savol"),
            ],
            [
                KeyboardButton(text="⬅️ Asosiy menyu"),
            ],
        ],
        resize_keyboard=True,
    )


def get_test_answer_keyboard(options):
    """Test variantlari Reply Keyboard (A, B, C, D)."""
    rows = []
    if len(options) == 3:
        rows.append([
            KeyboardButton(text=f"A) {options[0]}"),
            KeyboardButton(text=f"B) {options[1]}"),
        ])
        rows.append([
            KeyboardButton(text=f"C) {options[2]}"),
            KeyboardButton(text="❌ Testni to'xtatish"),
        ])
    else:
        rows.append([
            KeyboardButton(text=f"A) {options[0]}"),
            KeyboardButton(text=f"B) {options[1]}"),
        ])
        rows.append([
            KeyboardButton(text=f"C) {options[2]}"),
            KeyboardButton(text=f"D) {options[3]}"),
        ])
        rows.append([
            KeyboardButton(text="❌ Testni to'xtatish"),
        ])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def get_quiz_keyboard():
    """Quiz kategoriyalari Reply Keyboard (60 ta savol)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎲 Tasodifiy savol"),
            ],
            [
                KeyboardButton(text="🔤 So'z tarjimasi (1-12)"),
                KeyboardButton(text="📖 Grammatika (13-24)"),
            ],
            [
                KeyboardButton(text="📚 So'z boyligi (25-36)"),
                KeyboardButton(text="🧠 Mantiqiy savollar (37-48)"),
            ],
            [
                KeyboardButton(text="🌍 Dunyoqarash & Fan (49-60)"),
                KeyboardButton(text="⬅️ Asosiy menyu"),
            ],
        ],
        resize_keyboard=True,
    )


def get_lang_keyboard():
    """Til tanlash Reply Keyboard (UZ, EN, RU, KO, TR)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔄 Avtomatik"),
            ],
            [
                KeyboardButton(text="🇺🇿 O'zbekcha"),
                KeyboardButton(text="🇬🇧 English"),
            ],
            [
                KeyboardButton(text="🇷🇺 Русский"),
                KeyboardButton(text="🇰🇷 한국어 (Koreys)"),
            ],
            [
                KeyboardButton(text="🇹🇷 Türkçe (Turk)"),
            ],
            [
                KeyboardButton(text="⬅️ Asosiy menyu"),
            ],
        ],
        resize_keyboard=True,
    )


def get_lang_inline_keyboard():
    """Til tanlash Inline Keyboard (edit_text / inline xabarlar uchun)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Avtomatik", callback_data="lang_auto"),
            ],
            [
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            ],
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton(text="🇰🇷 한국어 (Koreys)", callback_data="lang_ko"),
            ],
            [
                InlineKeyboardButton(text="🇹🇷 Türkçe (Turk)", callback_data="lang_tr"),
            ],
            [
                InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_main"),
            ],
        ]
    )



def get_kutubxona_keyboard():
    """Kutubxona kategoriyalari Reply Keyboard."""
    buttons = []
    cats = list(KUTUBXONA.keys())
    for i in range(0, len(cats), 2):
        row = [KeyboardButton(text=c) for c in cats[i:i+2]]
        buttons.append(row)
    buttons.append([KeyboardButton(text="⬅️ Asosiy menyu")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)



WEATHER_CITY_MAP = {
    "🏙 Toshkent": "Tashkent",
    "🕌 Samarqand": "Samarkand",
    "🏛 Buxoro": "Bukhara",
    "🏔 Andijon": "Andijan",
    "🍇 Farg'ona": "Fergana",
    "🌸 Namangan": "Namangan",
    "🌾 Qashqadaryo": "Karshi",
    "☀️ Surxondaryo": "Termez",
    "🌲 Jizzax": "Jizzakh",
    "🌊 Sirdaryo": "Gulistan",
    "🏰 Xorazm": "Urgench",
    "⛏ Navoiy": "Navoi",
    "🏜 Qoraqalpog'iston": "Nukus",
    "🏰 Xiva": "Khiva",
    "🌆 Moskva": "Moscow",
    "🗼 London": "London",
}


def get_weather_keyboard():
    """Ob-havo viloyatlari (12 ta viloyat + Nukus) Reply Keyboard."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🏙 Toshkent"),
                KeyboardButton(text="🕌 Samarqand"),
            ],
            [
                KeyboardButton(text="🏛 Buxoro"),
                KeyboardButton(text="🏔 Andijon"),
            ],
            [
                KeyboardButton(text="🍇 Farg'ona"),
                KeyboardButton(text="🌸 Namangan"),
            ],
            [
                KeyboardButton(text="🌾 Qashqadaryo"),
                KeyboardButton(text="☀️ Surxondaryo"),
            ],
            [
                KeyboardButton(text="🌲 Jizzax"),
                KeyboardButton(text="🌊 Sirdaryo"),
            ],
            [
                KeyboardButton(text="🏰 Xorazm"),
                KeyboardButton(text="⛏ Navoiy"),
            ],
            [
                KeyboardButton(text="🏜 Qoraqalpog'iston"),
                KeyboardButton(text="⬅️ Asosiy menyu"),
            ],
        ],
        resize_keyboard=True,
    )


def get_back_button(callback_data="back_main"):
    """Orqaga tugmasi (Reply)."""
    return get_main_menu_keyboard()


# ============================================================
# /start
# ============================================================

@dp.message(Command("start"))
async def start_command(
    message: types.Message
):

    register_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name
    )

    await message.answer(
        f"👋 Assalomu alaykum, "
        f"<b>{html.escape(message.from_user.full_name)}</b>!\n\n"

        "🤖 <b>Super Tarjimon & Test Bot</b>\n\n"

        "Men sizga quyidagilarda yordam beraman:\n\n"

        "🌐 <b>Ko'p tilli tarjima:</b>\n"
        "🇬🇧 English | 🇺🇿 Uzbek | 🇷🇺 Русский\n"
        "🇰🇷 한국어 (Koreys) | 🇹🇷 Türkçe (Turk)\n\n"

        "📝 <b>Test topshirish</b> — 5 ta yo'nalishda: Ingliz, Rus, Koreys, Turk, Matematika (20-100 savol)\n"
        "🔤 <b>Alifbo</b> — 9 ta til alifbosi (EN, RU, KO, TR, UZ, AR, DE, FR, JA)\n"
        "🧮 <b>Matematik</b> — A, B, C variantli masalalar\n"
        "🌤 <b>Ob-havo</b> — O'zbekistonning barcha 12 ta viloyati\n"
        "📷 <b>Rasm tarjima</b> — Rasmdagi matnni tarjima\n"
        "🎥 <b>Video tarjima</b> — Video izohlarini tarjima\n"
        "🎲 <b>Quiz</b> — Til o'rganish savollari\n"
        "📚 <b>Kutubxona</b> — Eng yaxshi kitoblar\n"
        "💡 <b>Faktlar</b> — Qiziqarli ma'lumotlar\n"
        "🔥 <b>Motivatsiya</b> — Ruhlantiruvchi so'zlar\n\n"

        "📖 So'z yoki gap yuboring — tarjima qilaman!\n"
        "📷 Rasm yuboring — rasmdagi matnni tarjima qilaman!\n\n"
        "👇 Quyidagi menyu tugmalaridan foydalaning:",

        reply_markup=get_main_menu_keyboard()
    )


# ============================================================
# /menu
# ============================================================

@dp.message(Command("menu"))
async def menu_command(message: types.Message):

    await message.answer(
        "📋 <b>ASOSIY MENYU</b>\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=get_main_menu_keyboard()
    )


# ============================================================
# /help
# ============================================================

@dp.message(Command("help"))
async def help_command(
    message: types.Message
):

    await message.answer(
        "📚 <b>BOTDAN FOYDALANISH</b>\n\n"

        "1️⃣ <b>Tarjima</b>\n"
        "Istalgan gap yoki so'z yuboring:\n"
        "<code>I am learning English</code>\n"
        "→ Men ingliz tilini o'rganyapman\n\n"

        "2️⃣ <b>Til tanlash</b>\n"
        "/lang — maqsad tilini tanlang\n"
        "🔄 Auto | 🇺🇿 UZ | 🇬🇧 EN | 🇷🇺 RU | 🇰🇷 KO | 🇹🇷 TR\n\n"

        "3️⃣ <b>Test topshirish</b>\n"
        "/test — 🇬🇧 Ingliz, 🇷🇺 Rus, 🇰🇷 Koreys, 🇹🇷 Turk tillari va 🧮 Matematika bo'yicha 20, 40, 60, 80, 100 ta savolli testlar!\n\n"

        "4️⃣ <b>Matematik</b>\n"
        "/matematik — A, B, C variantlari bilan hisob-kitob masalalari\n\n"

        "5️⃣ <b>Ob-havo</b>\n"
        "/obhavo — 12 ta viloyat va boshqa shaharlar ob-havosi\n\n"

        "6️⃣ <b>Alifbo</b>\n"
        "/alfabit — 9 ta til alifbosi (Ingliz, Rus, Koreys, Turk, O'zbek, Arab, Nemis, Fransuz, Yapon) va o'qilishi\n\n"

        "━━━━━━ <b>BUYRUQLAR</b> ━━━━━━\n\n"

        "📋 /menu — Asosiy menyu\n"
        "🌐 /lang — Til tanlash\n"
        "🔤 /alfabit — Tillar alifbosi\n"
        "📝 /test — Til testlari (20/40/60/80/100)\n"
        "🎲 /quiz — Til o'rganish savollari\n"
        "🧮 /matematik — Matematik masala\n"
        "🌤 /obhavo — Ob-havo (12 ta viloyat)\n"
        "📚 /kutubxona — Kitoblar\n"
        "💡 /fakt — Qiziqarli fakt\n"
        "🔥 /motivatsiya — Motivatsion iqtibos\n"
        "📊 /stats — Statistika\n"
        "🕘 /history — Tarix\n"
        "🗑 /clear — Tarixni tozalash"
    )


# ============================================================
# /lang — TIL TANLASH
# ============================================================

@dp.message(Command("lang"))
async def lang_command(message: types.Message):

    current = get_user_lang(message.from_user.id)
    lang_names = {
        "auto": "🔄 Avtomatik",
        "uz": "🇺🇿 O'zbekcha",
        "en": "🇬🇧 English",
        "ru": "🇷🇺 Русский",
        "ko": "🇰🇷 한국어 (Koreys)",
        "tr": "🇹🇷 Türkçe (Turk)",
    }
    current_name = lang_names.get(current, "🔄 Avtomatik")

    await message.answer(
        "🌐 <b>TIL SOZLAMALARI</b>\n\n"
        f"Hozirgi maqsad til: <b>{current_name}</b>\n\n"
        "Tarjima qilish tilini tanlang:\n"
        "• <b>Avtomatik</b> — til avtomatik aniqlanadi\n"
        "• <b>O'zbekcha</b> — hammasi o'zbekchaga tarjima qilinadi\n"
        "• <b>English</b> — hammasi inglizchaga tarjima qilinadi\n"
        "• <b>Русский</b> — hammasi ruschaga tarjima qilinadi\n"
        "• <b>한국어</b> — hammasi koreyschaga tarjima qilinadi\n"
        "• <b>Türkçe</b> — hammasi turkchaga tarjima qilinadi",
        reply_markup=get_lang_keyboard()
    )


# ============================================================
# /stats
# ============================================================

@dp.message(Command("stats"))
async def stats_command(
    message: types.Message
):

    searches, history_count = get_user_stats(
        message.from_user.id
    )

    current = get_user_lang(message.from_user.id)
    lang_names = {
        "auto": "🔄 Avtomatik",
        "uz": "🇺🇿 O'zbekcha",
        "en": "🇬🇧 English",
        "ru": "🇷🇺 Русский",
    }

    await message.answer(
        "📊 <b>SIZNING STATISTIKANGIZ</b>\n\n"

        f"🔎 Qidiruvlar: <b>{searches}</b>\n"
        f"🕘 Tarixdagi yozuvlar: <b>{history_count}</b>\n"
        f"🌐 Tarjima tili: <b>{lang_names.get(current, 'Avtomatik')}</b>"
    )


# ============================================================
# /history
# ============================================================

@dp.message(Command("history"))
async def history_command(
    message: types.Message
):

    rows = get_history(
        message.from_user.id
    )

    if not rows:

        await message.answer(
            "🕘 Hozircha qidiruv tarixingiz bo'sh."
        )

        return

    text = "🕘 <b>OXIRGI QIDIRUVLAR</b>\n\n"

    for index, (query, result) in enumerate(
        rows,
        start=1
    ):

        text += (
            f"<b>{index}.</b> "
            f"{html.escape(query)}\n"
            f"→ {html.escape(result[:100])}\n\n"
        )

    await message.answer(text)


# ============================================================
# /clear
# ============================================================

@dp.message(Command("clear"))
async def clear_command(
    message: types.Message
):

    clear_history(
        message.from_user.id
    )

    await message.answer(
        "🗑 <b>Tarix tozalandi.</b>"
    )


# ============================================================
# /kutubxona
# ============================================================

@dp.message(Command("kutubxona"))
async def kutubxona_command(message: types.Message):

    await message.answer(
        "📚 <b>KUTUBXONA</b>\n\n"
        "Kategoriyani tanlang:",
        reply_markup=get_kutubxona_keyboard()
    )


# ====
# /fakt
# ============================================================

@dp.message(Command("fakt"))
async def fakt_command(message: types.Message):

    fakt = random.choice(FAKTLAR)

    await message.answer(
        "💡 <b>QIZIQARLI FAKT</b>\n\n"
        f"{fakt}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💡 Yana fakt!", callback_data="menu_fakt")],
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )


# ============================================================
# /motivatsiya
# ============================================================

@dp.message(Command("motivatsiya"))
async def motivatsiya_command(message: types.Message):

    quote = random.choice(MOTIVATSIYA_QUOTES)

    await message.answer(
        "🔥 <b>MOTIVATSIYA</b>\n\n"
        f"💬 <i>\"{html.escape(quote['quote'])}\"</i>\n\n"
        f"— <b>{html.escape(quote['muallif'])}</b>\n\n"
        "━━━━━━━━━━━━━━\n\n"
        f"🇺🇿 {html.escape(quote['tarjima'])}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Yana motivatsiya!", callback_data="menu_motivatsiya")],
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )


# ============================================================
# /matematik (A, B, C VARIANTLARI BILAN)
# ============================================================

@dp.message(Command("matematik"))
async def matematik_command(message: types.Message):
    data = generate_math_problem_with_options()
    user_math_sessions[message.from_user.id] = data

    await message.answer(
        "🧮 <b>MATEMATIK MASALA</b>\n\n"
        f"❓ <code>{data['problem']}</code>\n\n"
        f"A) {data['options'][0]}\n"
        f"B) {data['options'][1]}\n"
        f"C) {data['options'][2]}\n\n"
        "👇 <i>To'g'ri javobni tanlang:</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"A) {data['options'][0]}", callback_data=f"math_choice_0_{data['correct_idx']}"),
                InlineKeyboardButton(text=f"B) {data['options'][1]}", callback_data=f"math_choice_1_{data['correct_idx']}"),
            ],
            [
                InlineKeyboardButton(text=f"C) {data['options'][2]}", callback_data=f"math_choice_2_{data['correct_idx']}"),
            ],
            [
                InlineKeyboardButton(text="🧮 Yangi masala", callback_data="menu_matematik"),
                InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main"),
            ],
        ])
    )


# ============================================================
# /obhavo
# ============================================================

@dp.message(Command("obhavo"))
async def obhavo_command(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌤 @Obb_hovo_Bot ga o'tish", url="https://t.me/Obb_hovo_Bot")
        ]
    ])
    await message.answer(
        "🌤 <b>OB-HAVO MA'LUMOTLARI</b>\n\n"
        "O'zbekiston viloyatlari va dunyo shaharlari bo'yicha aniq ob-havoni bilish uchun rasmiy botimizga o'ting:\n\n"
        "👉 @Obb_hovo_Bot",
        reply_markup=markup
    )


async def send_weather(message_or_callback, city: str):
    """Ob-havo ma'lumotini yuboradi."""
    try:
        response = await asyncio.to_thread(
            requests.get,
            f"https://wttr.in/{city}?format=j1",
            timeout=10
        )

        if response.status_code != 200:
            text = (
                f"⚠️ <b>{html.escape(city)}</b> shahari topilmadi.\n"
                "Qaytadan urinib ko'ring."
            )
            if isinstance(message_or_callback, CallbackQuery):
                await message_or_callback.message.answer(text)
            else:
                await message_or_callback.answer(text)
            return

        data = response.json()
        current = data.get("current_condition", [{}])[0]
        area = data.get("nearest_area", [{}])[0]

        city_name = area.get("areaName", [{}])[0].get("value", city)
        country = area.get("country", [{}])[0].get("value", "")
        temp_c = current.get("temp_C", "?")
        feels_like = current.get("FeelsLikeC", "?")
        humidity = current.get("humidity", "?")
        wind_speed = current.get("windspeedKmph", "?")
        wind_dir = current.get("winddir16Point", "?")
        weather_desc = current.get("weatherDesc", [{}])[0].get("value", "?")
        visibility = current.get("visibility", "?")
        pressure = current.get("pressure", "?")
        uv_index = current.get("uvIndex", "?")

        # Haroratga qarab emoji
        try:
            temp_num = int(temp_c)
            if temp_num >= 35:
                temp_emoji = "🔥"
            elif temp_num >= 25:
                temp_emoji = "☀️"
            elif temp_num >= 15:
                temp_emoji = "🌤"
            elif temp_num >= 5:
                temp_emoji = "🌥"
            elif temp_num >= 0:
                temp_emoji = "❄️"
            else:
                temp_emoji = "🥶"
        except ValueError:
            temp_emoji = "🌡"

        weather_text = (
            f"{temp_emoji} <b>OB-HAVO: {html.escape(city_name)}</b>\n"
            f"🏳 {html.escape(country)}\n\n"
            f"━━━━━━━━━━━━━━\n\n"
            f"🌡 Harorat: <b>{temp_c}°C</b>\n"
            f"🤔 His qilinishi: <b>{feels_like}°C</b>\n"
            f"☁️ Holat: <b>{html.escape(weather_desc)}</b>\n"
            f"💧 Namlik: <b>{humidity}%</b>\n"
            f"💨 Shamol: <b>{wind_speed} km/s</b> ({wind_dir})\n"
            f"👁 Ko'rinish: <b>{visibility} km</b>\n"
            f"🔵 Bosim: <b>{pressure} hPa</b>\n"
            f"☀️ UV indeks: <b>{uv_index}</b>"
        )

        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(weather_text)
        else:
            await message_or_callback.answer(weather_text)

    except Exception as e:
        logger.error("Ob-havo xatosi: %s", e)
        error_text = "⚠️ Ob-havo ma'lumotini olishda xatolik yuz berdi."
        if isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(error_text)
        else:
            await message_or_callback.answer(error_text)


# ============================================================
# CALLBACK QUERY HANDLERS
# ============================================================

@dp.callback_query(F.data == "back_main")
async def callback_back_main(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(
        "📋 <b>ASOSIY MENYU</b>\n\nKerakli bo'limni quyidagi tugmalardan tanlang:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


# --- Lang callbacks ---

@dp.callback_query(F.data == "menu_lang")
async def callback_menu_lang(callback: CallbackQuery):

    current = get_user_lang(callback.from_user.id)
    lang_names = {
        "auto": "🔄 Avtomatik",
        "uz": "🇺🇿 O'zbekcha",
        "en": "🇬🇧 English",
        "ru": "🇷🇺 Русский",
        "ko": "🇰🇷 한국어 (Koreys)",
        "tr": "🇹🇷 Türkçe (Turk)",
    }

    await callback.message.edit_text(
        "🌐 <b>TIL SOZLAMALARI</b>\n\n"
        f"Hozirgi til: <b>{lang_names.get(current, 'Avtomatik')}</b>\n\n"
        "Tarjima maqsad tilini tanlang:",
        reply_markup=get_lang_inline_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("lang_"))
async def callback_lang_select(callback: CallbackQuery):

    lang = callback.data.replace("lang_", "")
    set_user_lang(callback.from_user.id, lang)

    lang_names = {
        "auto": "🔄 Avtomatik",
        "uz": "🇺🇿 O'zbekcha",
        "en": "🇬🇧 English",
        "ru": "🇷🇺 Русский",
        "ko": "🇰🇷 한국어 (Koreys)",
        "tr": "🇹🇷 Türkçe (Turk)",
    }

    await callback.message.edit_text(
        "✅ <b>Tarjima tili o'zgartirildi!</b>\n\n"
        f"Yangi maqsad til: <b>{lang_names.get(lang, lang)}</b>\n\n"
        "Endi yuborganingiz shu tilga tarjima qilinadi.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Boshqa tilni tanlash", callback_data="menu_lang")],
            [InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_main")],
        ])
    )
    await callback.answer(f"Til: {lang_names.get(lang, lang)}")



def get_kutubxona_inline_keyboard():
    """Kutubxona kategoriyalari Inline Keyboard (edit_text uchun)."""
    keyboard = []
    cats = list(KUTUBXONA.keys())
    for i in range(0, len(cats), 2):
        row = [InlineKeyboardButton(text=cats[i], callback_data=f"lib_{cats[i]}")]
        if i + 1 < len(cats):
            row.append(InlineKeyboardButton(text=cats[i + 1], callback_data=f"lib_{cats[i + 1]}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🏠 Menyu", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# --- Kutubxona callbacks ---

@dp.callback_query(F.data == "menu_kutubxona")
async def callback_menu_kutubxona(callback: CallbackQuery):

    await callback.message.edit_text(
        "📚 <b>KUTUBXONA</b>\n\n"
        "Kategoriyani tanlang:",
        reply_markup=get_kutubxona_inline_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("lib_"))
async def callback_lib_category(callback: CallbackQuery):

    category = callback.data.replace("lib_", "")
    books = KUTUBXONA.get(category, [])

    if not books:
        await callback.answer("Kitoblar topilmadi.")
        return

    text = f"📚 <b>{html.escape(category)}</b>\n\n"

    for i, book in enumerate(books, 1):
        text += (
            f"<b>{i}. {html.escape(book['nom'])}</b>\n"
            f"✍️ {html.escape(book['muallif'])}\n"
            f"📝 <i>{html.escape(book['tavsif'])}</i>\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Kategoriyalar", callback_data="menu_kutubxona")],
            [InlineKeyboardButton(text="🏠 Menyu", callback_data="back_main")],
        ])
    )
    await callback.answer()


# --- Fakt callback ---

@dp.callback_query(F.data == "menu_fakt")
async def callback_menu_fakt(callback: CallbackQuery):

    fakt = random.choice(FAKTLAR)

    await callback.message.edit_text(
        "💡 <b>QIZIQARLI FAKT</b>\n\n"
        f"{fakt}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💡 Yana fakt!", callback_data="menu_fakt")],
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )
    await callback.answer()


# --- Motivatsiya callback ---

@dp.callback_query(F.data == "menu_motivatsiya")
async def callback_menu_motivatsiya(callback: CallbackQuery):

    quote = random.choice(MOTIVATSIYA_QUOTES)

    await callback.message.edit_text(
        "🔥 <b>MOTIVATSIYA</b>\n\n"
        f"💬 <i>\"{html.escape(quote['quote'])}\"</i>\n\n"
        f"— <b>{html.escape(quote['muallif'])}</b>\n\n"
        "━━━━━━━━━━━━━━\n\n"
        f"🇺🇿 {html.escape(quote['tarjima'])}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Yana!", callback_data="menu_motivatsiya")],
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )
    await callback.answer()


# --- Matematik callbacks (A, B, C Variantlari) ---

@dp.callback_query(F.data == "menu_matematik")
async def callback_menu_matematik(callback: CallbackQuery):

    data = generate_math_problem_with_options()
    user_math_sessions[callback.from_user.id] = data

    await callback.message.edit_text(
        "🧮 <b>MATEMATIK MASALA</b>\n\n"
        f"❓ <code>{data['problem']}</code>\n\n"
        f"A) {data['options'][0]}\n"
        f"B) {data['options'][1]}\n"
        f"C) {data['options'][2]}\n\n"
        "👇 <i>To'g'ri javobni tanlang:</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"A) {data['options'][0]}", callback_data=f"math_choice_0_{data['correct_idx']}"),
                InlineKeyboardButton(text=f"B) {data['options'][1]}", callback_data=f"math_choice_1_{data['correct_idx']}"),
            ],
            [
                InlineKeyboardButton(text=f"C) {data['options'][2]}", callback_data=f"math_choice_2_{data['correct_idx']}"),
            ],
            [
                InlineKeyboardButton(text="🧮 Yangi masala", callback_data="menu_matematik"),
                InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main"),
            ],
        ])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("math_choice_"))
async def callback_math_choice(callback: CallbackQuery):
    parts = callback.data.replace("math_choice_", "").split("_")
    choice_idx = int(parts[0])
    correct_idx = int(parts[1])
    session = user_math_sessions.get(callback.from_user.id)
    letters = ["A", "B", "C"]
    chosen_letter = letters[choice_idx] if choice_idx < len(letters) else "?"
    correct_letter = letters[correct_idx] if correct_idx < len(letters) else "?"

    if choice_idx == correct_idx:
        await callback.answer("✅ To'g'ri javob! Barakalla! 🎉", show_alert=True)
        msg_text = (
            "🎉 <b>A'LO! TO'G'RI JAVOB!</b>\n\n"
            f"Siz tanlagan javob: <b>{chosen_letter}</b> ✅\n\n"
            "Yana masala yechish uchun quyidagi tugmani bosing:"
        )
    else:
        correct_ans = session["options"][correct_idx] if session else ""
        await callback.answer("❌ Noto'g'ri javob!", show_alert=True)
        msg_text = (
            "❌ <b>NOTO'G'RI JAVOB!</b>\n\n"
            f"Siz tanlagan javob: <b>{chosen_letter}</b>\n"
            f"To'g'ri javob: <b>{correct_letter}) {correct_ans}</b>\n\n"
            "Keyingi masalada omad tilaymiz!"
        )

    await callback.message.edit_text(
        msg_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧮 Yana masala", callback_data="menu_matematik")],
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )


# --- Ob-havo callback (12 ta viloyat) ---

@dp.callback_query(F.data == "menu_obhavo")
async def callback_menu_obhavo(callback: CallbackQuery):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌤 @Obb_hovo_Bot ga o'tish", url="https://t.me/Obb_hovo_Bot")
        ],
        [
            InlineKeyboardButton(text="⬅️ Asosiy menyu", callback_data="back_main")
        ]
    ])
    await callback.message.edit_text(
        "🌤 <b>OB-HAVO MA'LUMOTLARI</b>\n\n"
        "O'zbekistonning barcha 12 ta viloyati va dunyo shaharlari ob-havosini bilish uchun maxsus botimizga o'ting:\n\n"
        "👉 @Obb_hovo_Bot",
        reply_markup=markup
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("weather_"))
async def callback_weather(callback: CallbackQuery):

    city = callback.data.replace("weather_", "").replace("+", " ")
    await callback.answer(f"🌤 {city}...")
    await send_weather(callback, city)


# --- Stats callback ---

@dp.callback_query(F.data == "menu_stats")
async def callback_menu_stats(callback: CallbackQuery):

    searches, history_count = get_user_stats(callback.from_user.id)
    current = get_user_lang(callback.from_user.id)
    lang_names = {
        "auto": "🔄 Avtomatik",
        "uz": "🇺🇿 O'zbekcha",
        "en": "🇬🇧 English",
        "ru": "🇷🇺 Русский",
        "ko": "🇰🇷 한국어 (Koreys)",
        "tr": "🇹🇷 Türkçe (Turk)",
    }

    await callback.message.edit_text(
        "📊 <b>SIZNING STATISTIKANGIZ</b>\n\n"
        f"🔎 Qidiruvlar: <b>{searches}</b>\n"
        f"🕘 Tarixdagi yozuvlar: <b>{history_count}</b>\n"
        f"🌐 Tarjima tili: <b>{lang_names.get(current, 'Avtomatik')}</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )
    await callback.answer()


# --- History callback ---

@dp.callback_query(F.data == "menu_history")
async def callback_menu_history(callback: CallbackQuery):

    rows = get_history(callback.from_user.id)

    if not rows:
        await callback.message.edit_text(
            "🕘 Hozircha qidiruv tarixingiz bo'sh.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
            ])
        )
        await callback.answer()
        return

    text = "🕘 <b>OXIRGI QIDIRUVLAR</b>\n\n"
    for index, (query, result) in enumerate(rows, start=1):
        text += (
            f"<b>{index}.</b> "
            f"{html.escape(query)}\n"
            f"→ {html.escape(result[:100])}\n\n"
        )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Tozalash", callback_data="menu_clear")],
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "menu_clear")
async def callback_menu_clear(callback: CallbackQuery):

    clear_history(callback.from_user.id)

    await callback.message.edit_text(
        "🗑 <b>Tarix tozalandi.</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )
    await callback.answer("Tozalandi!")


# --- Help callback ---

@dp.callback_query(F.data == "menu_help")
async def callback_menu_help(callback: CallbackQuery):

    await callback.message.edit_text(
        "📚 <b>BOTDAN FOYDALANISH</b>\n\n"

        "1️⃣ <b>Tarjima</b> — So'z yoki gap yuboring (UZ/EN/RU/KO/TR)\n"
        "2️⃣ <b>/lang</b> — Maqsad tilini tanlang\n"
        "3️⃣ <b>/test</b> — Til testlari (20/40/60/80/100 savol)\n"
        "4️⃣ <b>/matematik</b> — A, B, C variantli masala\n"
        "5️⃣ <b>/obhavo</b> — 12 ta viloyat ob-havosi\n"
        "6️⃣ <b>/kutubxona</b> — Kitoblar\n"
        "8️⃣ <b>/fakt</b> — Qiziqarli fakt\n"
        "9️⃣ <b>/motivatsiya</b> — Ruhlantiruvchi so'zlar\n"
        "🔟 <b>/stats</b> — Qidiruvlar statistikasi\n",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )
    await callback.answer()


# ============================================================
# /quiz — SAVOLLAR
# ============================================================

@dp.message(Command("quiz"))
async def quiz_command(message: types.Message):

    await message.answer(
        "📝 <b>QUIZ — TIL O'RGANISH SAVOLLARI</b>\n\n"
        "20 ta savol: 🇬🇧 English, 🇺🇿 O'zbekcha, 🇷🇺 Русский\n\n"
        "Kategoriyani tanlang:",
        reply_markup=get_quiz_keyboard()
    )


@dp.message(Command("savol"))
async def savol_command(message: types.Message):
    """Alias for /quiz."""
    await quiz_command(message)


def build_quiz_message(q_index: int):
    """Quiz savoli uchun matn va keyboard yaratadi."""
    q = QUIZ_QUESTIONS[q_index]
    text = (
        f"📝 <b>SAVOL {q_index + 1}/20</b>\n\n"
        f"{q['savol']}\n\n"
    )
    for i, variant in enumerate(q['variantlar']):
        letter = chr(65 + i)  # A, B, C, D
        text += f"<b>{letter})</b> {variant}\n"

    buttons = []
    row = []
    for i, variant in enumerate(q['variantlar']):
        letter = chr(65 + i)
        row.append(InlineKeyboardButton(
            text=f"{letter}) {variant}",
            callback_data=f"quiza_{q_index}_{i}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Navigation
    nav_row = []
    if q_index > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"quizn_{q_index - 1}"))
    if q_index < len(QUIZ_QUESTIONS) - 1:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"quizn_{q_index + 1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton(text="📝 Quiz menyu", callback_data="menu_quiz")])
    buttons.append([InlineKeyboardButton(text="🏠 Menyu", callback_data="back_main")])

    return text, InlineKeyboardMarkup(inline_keyboard=buttons)


# --- Quiz callbacks ---

@dp.callback_query(F.data == "menu_quiz")
async def callback_menu_quiz(callback: CallbackQuery):

    await callback.message.edit_text(
        "📝 <b>QUIZ — TIL O'RGANISH SAVOLLARI</b>\n\n"
        "20 ta savol: 🇬🇧 English, 🇺🇿 O'zbekcha, 🇷🇺 Русский\n\n"
        "Kategoriyani tanlang:",
        reply_markup=get_quiz_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "quiz_random")
async def callback_quiz_random(callback: CallbackQuery):

    q_index = random.randint(0, len(QUIZ_QUESTIONS) - 1)
    text, keyboard = build_quiz_message(q_index)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("quiz_cat_"))
async def callback_quiz_category(callback: CallbackQuery):

    cat = callback.data.replace("quiz_cat_", "")
    ranges = {
        "words": (0, 12),
        "grammar": (12, 24),
        "vocab": (24, 36),
        "logic": (36, 48),
        "world": (48, 60),
        "mixed": (0, 60),
    }
    start, end = ranges.get(cat, (0, 5))
    q_index = start  # Birinchi savoldan boshlaymiz
    text, keyboard = build_quiz_message(q_index)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("quizn_"))
async def callback_quiz_navigate(callback: CallbackQuery):
    """Quiz savollar orasida navigatsiya."""
    q_index = int(callback.data.replace("quizn_", ""))
    if 0 <= q_index < len(QUIZ_QUESTIONS):
        text, keyboard = build_quiz_message(q_index)
        await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data.startswith("quiza_"))
async def callback_quiz_answer(callback: CallbackQuery):
    """Quiz javobini tekshirish."""
    parts = callback.data.replace("quiza_", "").split("_")
    q_index = int(parts[0])
    selected = int(parts[1])

    q = QUIZ_QUESTIONS[q_index]
    correct = q['javob']

    if selected == correct:
        result_emoji = "✅"
        result_text = "TO'G'RI!"
    else:
        result_emoji = "❌"
        result_text = f"NOTO'G'RI! To'g'ri javob: <b>{chr(65 + correct)}) {q['variantlar'][correct]}</b>"

    text = (
        f"📝 <b>SAVOL {q_index + 1}/20</b>\n\n"
        f"{q['savol']}\n\n"
    )
    for i, variant in enumerate(q['variantlar']):
        letter = chr(65 + i)
        if i == correct:
            text += f"✅ <b>{letter}) {variant}</b>\n"
        elif i == selected and selected != correct:
            text += f"❌ <s>{letter}) {variant}</s>\n"
        else:
            text += f"{letter}) {variant}\n"

    text += f"\n{result_emoji} <b>{result_text}</b>\n"
    text += f"\n💡 {q['tushuntirish']}"

    # Navigation buttons
    nav_buttons = []
    if q_index < len(QUIZ_QUESTIONS) - 1:
        nav_buttons.append([
            InlineKeyboardButton(text="➡️ Keyingi savol", callback_data=f"quizn_{q_index + 1}")
        ])
    nav_buttons.append([
        InlineKeyboardButton(text="🎲 Tasodifiy savol", callback_data="quiz_random")
    ])
    nav_buttons.append([
        InlineKeyboardButton(text="📝 Quiz menyu", callback_data="menu_quiz"),
        InlineKeyboardButton(text="🏠 Menyu", callback_data="back_main"),
    ])

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=nav_buttons)
    )
    await callback.answer(f"{result_emoji} {result_text.split('!')[0]}!")


# ============================================================
# MULTI-ENGINE OCR & RASM TARJIMA TIZIMI
# ============================================================

GLOBAL_LANG_FLAGS = {
    "uz": "🇺🇿", "en": "🇬🇧", "ru": "🇷🇺", "tr": "🇹🇷", "ko": "🇰🇷",
    "ar": "🇸🇦", "de": "🇩🇪", "fr": "🇫🇷", "ja": "🇯🇵", "es": "🇪🇸",
    "it": "🇮🇹", "zh-cn": "🇨🇳", "zh": "🇨🇳", "fa": "🇮🇷", "kk": "🇰🇿",
    "tg": "🇹🇯", "ky": "🇰🇬",
}

GLOBAL_LANG_NAMES = {
    "uz": "O'zbekcha", "en": "English", "ru": "Русский",
    "tr": "Türkçe", "ko": "한국어", "ar": "العربية",
    "de": "Deutsch", "fr": "Français", "ja": "日本語",
    "es": "Español", "it": "Italiano", "zh-cn": "中文",
    "zh": "中文", "fa": "فارسی", "kk": "Қазақша",
    "tg": "Тоҷикӣ", "ky": "Кыргызча", "auto": "Avtomatik",
}

def get_photo_translate_keyboard(msg_id: int, current_dest: str = "uz"):
    """Rasm tarjimasi uchun boshqa tillarga o'tish tugmalari."""
    buttons = [
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data=f"ptrans_uz_{msg_id}"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data=f"ptrans_en_{msg_id}"),
        ],
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"ptrans_ru_{msg_id}"),
            InlineKeyboardButton(text="🇹🇷 Türkçe", callback_data=f"ptrans_tr_{msg_id}"),
            InlineKeyboardButton(text="🇰🇷 한국어", callback_data=f"ptrans_ko_{msg_id}"),
        ],
        [
            InlineKeyboardButton(text="🏠 Asosiy menyu", callback_data="back_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def extract_text_from_image_bytes(image_bytes: bytes) -> str:
    """
    Rasmdan matnni aniqlash va o'qish (Multi-Engine OCR):
    1. RapidOCR (onnx neural network - tezkor va aniq, oflayn)
    2. OCR.space (bepul onlayn OCR bulut API)
    3. Pytesseract (agar tizimda tesseract o'rnatilgan bo'lsa)
    """
    # 1. RapidOCR (Asosiy neyron tarmoq)
    if RAPID_OCR_AVAILABLE and rapid_ocr_engine and Image:
        try:
            def _run_rapid():
                img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                res, _ = rapid_ocr_engine(np.array(img))
                if res:
                    lines = [line[1].strip() for line in res if len(line) > 1 and line[1].strip()]
                    return "\n".join(lines)
                return ""
            extracted = await asyncio.to_thread(_run_rapid)
            if extracted and len(extracted.strip()) > 0:
                logger.info("RapidOCR matn topdi: %d belgilar", len(extracted))
                return extracted.strip()
        except Exception as e:
            logger.warning("RapidOCR xatosi: %s", e)

    # 2. OCR.space Online Cloud API fallback (API key kerak)
    ocr_space_api_key = os.getenv("OCR_SPACE_API_KEY")
    if ocr_space_api_key:
        try:
            def _run_ocr_space():
                payload = {
                    "apikey": ocr_space_api_key,
                    "OCREngine": "2",
                }
                r = requests.post(
                    "https://api.ocr.space/parse/image",
                    files={"file.png": image_bytes},
                    data=payload,
                    timeout=12
                )
                if r.status_code == 200:
                    data = r.json()
                    parsed = data.get("ParsedResults", [])
                    if parsed:
                        text = parsed[0].get("ParsedText", "").strip()
                        if text:
                            return text
                return ""
            extracted = await asyncio.to_thread(_run_ocr_space)
            if extracted and len(extracted.strip()) > 0:
                logger.info("OCR.space matn topdi: %d belgilar", len(extracted))
                return extracted.strip()
        except Exception as e:
            logger.warning("OCR.space xatosi: %s", e)
    else:
        logger.debug("OCR_SPACE_API_KEY topilmadi, OCR.space o'tkazib yuborilmoqda")

    # 3. Pytesseract fallback
    if PYTESSERACT_AVAILABLE and Image:
        try:
            def _run_tesseract():
                img = Image.open(io.BytesIO(image_bytes))
                return pytesseract.image_to_string(img, lang="eng+rus+uzb").strip()
            extracted = await asyncio.to_thread(_run_tesseract)
            if extracted:
                return extracted
        except Exception as e:
            logger.warning("Pytesseract xatosi: %s", e)

    return ""


async def process_image_translation(
    message: types.Message,
    image_bytes: bytes,
    caption_text: str = ""
):
    """Rasmni tahlil qilib, matnini va tarjimasini yuboradi."""
    register_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name
    )

    # 1. Agar rasmga caption (izoh) yozilgan bo'lsa, uni ham tarjima qilamiz
    if caption_text:
        try:
            detected = await translator_detect(caption_text)
            lang = detected.lang
            user_pref = get_user_lang(message.from_user.id)
            if user_pref != "auto":
                destination = user_pref
                if lang == destination:
                    destination = "uz" if lang != "uz" else "en"
            else:
                destination = "en" if lang == "uz" else "uz"

            result = await translator_translate(caption_text, destination)
            src_flag = GLOBAL_LANG_FLAGS.get(lang, "🌐")
            dst_flag = GLOBAL_LANG_FLAGS.get(destination, "🌐")

            increment_search(message.from_user.id)
            save_history(message.from_user.id, caption_text[:100], result.text[:100])

            await message.answer(
                f"📷 <b>RASM CAPTION TARJIMASI</b> {src_flag} → {dst_flag}\n\n"
                f"📝 <b>Original izoh:</b>\n{html.escape(caption_text)}\n\n"
                "━━━━━━━━━━━━━━\n\n"
                f"🔄 <b>Tarjima:</b>\n{html.escape(result.text)}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        except Exception as e:
            logger.error("Caption tarjima xatosi: %s", e)

    # 2. Rasmdan matn o'qish (OCR)
    wait_msg = await message.answer("⏳ <b>Rasm tahlil qilinmoqda...</b> Matn o'qilmoqda...")

    try:
        extracted_text = await extract_text_from_image_bytes(image_bytes)

        if not extracted_text:
            await wait_msg.edit_text(
                "📷 <b>Rasmda matn topilmadi.</b>\n\n"
                "💡 <b>Maslahat:</b>\n"
                "• Matni aniqroq, yorug' va sifatli rasm yuboring.\n"
                "• Yoki rasm bilan birga izoh (caption) yozib yuboring — bot uni bir zumda tarjima qiladi!"
            )
            return

        # Matn tilini aniqlash
        detected = await translator_detect(extracted_text)
        src_lang = getattr(detected, "lang", "en") or "en"

        # Maqsad tili
        user_pref = get_user_lang(message.from_user.id)
        if user_pref != "auto":
            dest_lang = user_pref
            if src_lang == dest_lang:
                dest_lang = "uz" if src_lang != "uz" else "en"
        else:
            dest_lang = "en" if src_lang == "uz" else "uz"

        # Google Translate orqali tarjima qilish
        result = await translator_translate(extracted_text, dest_lang)
        translated_text = result.text

        src_flag = GLOBAL_LANG_FLAGS.get(src_lang, "🌐")
        dst_flag = GLOBAL_LANG_FLAGS.get(dest_lang, "🌐")
        src_name = GLOBAL_LANG_NAMES.get(src_lang, src_lang.upper())
        dst_name = GLOBAL_LANG_NAMES.get(dest_lang, dest_lang.upper())

        increment_search(message.from_user.id)
        save_history(message.from_user.id, extracted_text[:100], translated_text[:100])

        # Keshga saqlash
        cache_id = wait_msg.message_id
        photo_text_cache[cache_id] = extracted_text
        if len(photo_text_cache) > 500:
            photo_text_cache.pop(next(iter(photo_text_cache)))

        response_text = (
            f"📷 <b>RASM TARJIMASI</b> {src_flag} → {dst_flag}\n"
            f"<i>{src_name} → {dst_name}</i>\n\n"
            f"📝 <b>Rasmdagi matn:</b>\n<code>{html.escape(extracted_text[:1200])}</code>\n\n"
            "━━━━━━━━━━━━━━\n\n"
            f"🔄 <b>Google Tarjimasi:</b>\n{html.escape(translated_text[:1500])}"
        )

        await wait_msg.edit_text(
            response_text,
            reply_markup=get_photo_translate_keyboard(cache_id, dest_lang)
        )

    except Exception as e:
        logger.error("Rasm tarjima xatosi: %s", e)
        await wait_msg.edit_text(
            "⚠️ <b>Rasmni tarjima qilishda xatolik yuz berdi.</b>\n"
            "Iltimos, qaytadan urinib ko'ring yoki rasmga caption (izoh) yozib yuboring."
        )


# --- Photo translation callback ---

@dp.callback_query(F.data == "menu_photo")
async def callback_menu_photo(callback: CallbackQuery):

    await callback.message.edit_text(
        "📷 <b>RASM TARJIMA XIZMATI</b>\n\n"
        "Rasmda matn bormi? Menga yuboring!\n\n"
        "📌 <b>Qanday ishlaydi:</b>\n"
        "1. Matni bor istalgan rasmni yuboring\n"
        "2. Bot rasmdagi matnni sun'iy intellekt (OCR) orqali o'qiydi\n"
        "3. Matnni Google Translate orqali avtomatik tarjima qilib beradi!\n\n"
        "✅ <b>OCR tizimi to'liq faol!</b>\n\n"
        "💡 <i>Istalgan tildagi (Ingliz, Rus, Turk, Koreys va h.k.) rasmlarni yuborishingiz mumkin.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main")],
        ])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("ptrans_"))
async def callback_photo_retranslate(callback: CallbackQuery):
    """Rasmdagi matnni boshqa tilga qayta tarjima qilish."""
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer()
        return

    dest_lang = parts[1]
    msg_id = int(parts[2])

    extracted_text = photo_text_cache.get(msg_id)
    if not extracted_text:
        await callback.answer("Rasm matni eskirgan, iltimos rasmni qayta yuboring.", show_alert=True)
        return

    await callback.answer("Tarjima qilinmoqda...")

    try:
        detected = await translator_detect(extracted_text)
        src_lang = getattr(detected, "lang", "en") or "en"

        result = await translator_translate(extracted_text, dest_lang)
        translated_text = result.text

        src_flag = GLOBAL_LANG_FLAGS.get(src_lang, "🌐")
        dst_flag = GLOBAL_LANG_FLAGS.get(dest_lang, "🌐")
        src_name = GLOBAL_LANG_NAMES.get(src_lang, src_lang.upper())
        dst_name = GLOBAL_LANG_NAMES.get(dest_lang, dest_lang.upper())

        response_text = (
            f"📷 <b>RASM TARJIMASI</b> {src_flag} → {dst_flag}\n"
            f"<i>{src_name} → {dst_name}</i>\n\n"
            f"📝 <b>Rasmdagi matn:</b>\n<code>{html.escape(extracted_text[:1200])}</code>\n\n"
            "━━━━━━━━━━━━━━\n\n"
            f"🔄 <b>Google Tarjimasi ({dst_name}):</b>\n{html.escape(translated_text[:1500])}"
        )

        await callback.message.edit_text(
            response_text,
            reply_markup=get_photo_translate_keyboard(msg_id, dest_lang)
        )
    except Exception as e:
        logger.error("Rasm qayta tarjima xatosi: %s", e)
        await callback.answer("Tarjima qilishda xatolik yuz berdi.", show_alert=True)


# ============================================================
# PHOTO HANDLER — RASM TARJIMA
# ============================================================

@dp.message(F.photo)
async def photo_handler(message: types.Message):
    """Rasmni qabul qilib, matnini aniqlaydi va tarjima qiladi."""
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    file_bytes_io = await bot.download_file(file_info.file_path)
    caption = message.caption.strip() if message.caption else ""
    await process_image_translation(message, file_bytes_io.getvalue(), caption)


@dp.message(F.document)
async def document_image_handler(message: types.Message):
    """Hujjat sifatida yuborilgan rasmlarni qabul qilib tarjima qiladi."""
    doc = message.document
    if doc.mime_type and doc.mime_type.startswith("image/"):
        file_info = await bot.get_file(doc.file_id)
        file_bytes_io = await bot.download_file(file_info.file_path)
        caption = message.caption.strip() if message.caption else ""
        await process_image_translation(message, file_bytes_io.getvalue(), caption)


# ============================================================
# VIDEO HANDLER — VIDEO TARJIMA
# ============================================================

@dp.message(F.video | F.video_note | F.animation)
async def video_handler(message: types.Message):
    """Videoni qabul qilib, caption bo'lsa tarjima qiladi."""

    register_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name
    )

    # 1. Agar video bilan birga caption (matn) yuborilgan bo'lsa
    if message.caption and message.caption.strip():
        caption_text = message.caption.strip()
        try:
            detected = await translator_detect(caption_text)
            lang = detected.lang

            user_pref = get_user_lang(message.from_user.id)
            if user_pref != "auto":
                destination = user_pref
                if lang == destination:
                    destination = "uz" if lang != "uz" else "en"
            else:
                if lang == "en":
                    destination = "uz"
                elif lang == "uz":
                    destination = "en"
                elif lang == "ru":
                    destination = "uz"
                else:
                    destination = "en"

            result = await translator_translate(caption_text, destination)

            lang_flags = {"en": "🇬🇧", "uz": "🇺🇿", "ru": "🇷🇺"}
            src_flag = lang_flags.get(lang, "🌐")
            dst_flag = lang_flags.get(destination, "🌐")

            increment_search(message.from_user.id)
            save_history(message.from_user.id, caption_text[:100], result.text[:100])

            await message.answer(
                f"🎥 <b>VIDEO MATNI TARJIMASI</b> {src_flag} → {dst_flag}\n\n"
                f"📝 <b>Original:</b>\n{html.escape(caption_text)}\n\n"
                "━━━━━━━━━━━━━━\n\n"
                f"🔄 <b>Tarjima:</b>\n{html.escape(result.text)}",
                reply_markup=get_main_menu_keyboard()
            )
            return
        except Exception as e:
            logger.error("Video caption tarjima xatosi: %s", e)

    # 2. Agar caption bo'lmasa, ma'lumot va yo'riqnoma beramiz
    video_obj = message.video or message.video_note or message.animation
    duration = getattr(video_obj, "duration", 0)
    file_size = getattr(video_obj, "file_size", 0) or 0
    file_size_mb = file_size / (1024 * 1024)

    await message.answer(
        f"🎥 <b>VIDEO QABUL QILINDI!</b>\n\n"
        f"⏱ <b>Davomiyligi:</b> {duration} soniya\n"
        f"📦 <b>Hajmi:</b> {file_size_mb:.1f} MB\n\n"
        "💡 <b>Videoni tarjima qilish uchun:</b>\n"
        "Videoni yuborayotganda unga <b>izoh (caption)</b> sifatida inglizcha, ruscha yoki o'zbekcha matn yozing.\n"
        "Bot uni darhol kerakli tilga tarjima qilib beradi!\n\n"
        "Masalan:\n"
        "Videoni yuborib tagiga: <i>\"Amazing electric vehicle features\"</i> deb yozsangiz, bot uni o'zbekchaga tarjima qiladi.",
        reply_markup=get_main_menu_keyboard()
    )


# ============================================================
# TEST TOPSHIRISH FUNKSIYALARI
# ============================================================

async def send_test_question(message: types.Message, user_id: int):
    """Foydalanuvchiga navbatdagi test savolini yuboradi."""
    session = user_test_sessions.get(user_id)
    if not session:
        return

    idx = session["index"]
    questions = session["questions"]
    lang_code = session.get("lang", "en")
    lang_title = TEST_LANG_NAMES.get(lang_code, "")

    if idx >= len(questions):
        # Test yakunlandi!
        score = session["score"]
        total = len(questions)
        percent = int((score / total) * 100) if total > 0 else 0

        if percent >= 90:
            grade = "🏆 A'lo! (Excellent)"
        elif percent >= 70:
            grade = "🥇 Yaxshi! (Good)"
        elif percent >= 50:
            grade = "🥈 Qoniqarli! (Satisfactory)"
        else:
            grade = "📚 Yana o'rganing! (Keep learning)"

        del user_test_sessions[user_id]
        if user_id in user_test_setup:
            del user_test_setup[user_id]

        await message.answer(
            f"🎉 <b>TEST YAKUNLANDI!</b>\n\n"
            f"📌 Til: <b>{lang_title}</b>\n"
            f"━━━━━━━━━━━━━━\n"
            f"📊 <b>Natijangiz:</b> {score}/{total} ({percent}%)\n"
            f"✅ <b>To'g'ri:</b> {score} ta\n"
            f"❌ <b>Xatolar:</b> {total - score} ta\n"
            f"🌟 <b>Baho:</b> {grade}\n"
            f"━━━━━━━━━━━━━━\n\n"
            "Yana test topshirish uchun <b>📝 Test topshirish</b> tugmasini bosing!",
            reply_markup=get_main_menu_keyboard()
        )
        return

    q = questions[idx]
    letters = ["A", "B", "C", "D"]
    var_text = ""
    for i, opt in enumerate(q["variantlar"]):
        var_text += f"<b>{letters[i]})</b> {opt}\n"

    text = (
        f"📝 <b>TEST: {lang_title} ({idx + 1}/{len(questions)})</b>\n\n"
        f"<b>{q['savol']}</b>\n\n"
        f"{var_text}\n"
        "👇 <i>To'g'ri javobni tanlang:</i>"
    )

    await message.answer(text, reply_markup=get_test_answer_keyboard(q["variantlar"]))


# ============================================================
# REPLY KEYBOARD MENU HANDLERS
# ============================================================

@dp.message(F.text.in_({"⬅️ Asosiy menyu", "🏠 Menyu", "📋 Asosiy menyu", "Menyu"}))
async def btn_main_menu(message: types.Message):
    # Agar test jarayonida bo'lsa to'xtatamiz
    if message.from_user.id in user_test_sessions:
        del user_test_sessions[message.from_user.id]
    if message.from_user.id in user_test_setup:
        del user_test_setup[message.from_user.id]
    await message.answer(
        "📋 <b>ASOSIY MENYU</b>\n\nKerakli bo'limni tanlang:",
        reply_markup=get_main_menu_keyboard()
    )


@dp.message(F.text == "🎥 Video tarjima")
async def btn_video_menu(message: types.Message):
    await message.answer(
        "🎥 <b>VIDEO TARJIMA XIZMATI</b>\n\n"
        "Istalgan video yoki video-xabarni menga yuboring!\n\n"
        "📌 <b>Qanday ishlaydi:</b>\n"
        "1. Video tanlang va unga <b>izoh (caption)</b> yozing\n"
        "2. Bot video tilini avtomatik aniqlaydi\n"
        "3. Kerakli tilga darhol tarjima qiladi!\n\n"
        "🌐 Qo'llab-quvvatlanadigan tillar: 🇬🇧 English, 🇺🇿 Uzbek, 🇷🇺 Russian, 🇰🇷 한국어, 🇹🇷 Türkçe",
        reply_markup=get_main_menu_keyboard()
    )


@dp.message(F.text.in_({"📝 Test topshirish", "/test"}))
async def btn_start_test(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_test_sessions:
        del user_test_sessions[user_id]
    if user_id in user_test_setup:
        del user_test_setup[user_id]

    await message.answer(
        "📝 <b>TEST TOPSHIRISH — QAYSI YO'NALISHDA TEST TOPSHIRMOQCHISIZ?</b>\n\n"
        "Quyidagi fan/tillardan birini tanlang:\n"
        "• 🇬🇧 <b>Ingliz tili</b>\n"
        "• 🇷🇺 <b>Rus tili</b>\n"
        "• 🇰🇷 <b>Koreys tili</b>\n"
        "• 🇹🇷 <b>Turk tili</b>\n"
        "• 🧮 <b>Matematika</b>",
        reply_markup=get_test_lang_keyboard()
    )


@dp.message(F.text.in_({
    "🇬🇧 Ingliz tili testi",
    "🇷🇺 Rus tili testi",
    "🇰🇷 Koreys tili testi",
    "🇹🇷 Turk tili testi",
    "🧮 Matematika testi",
}))
async def btn_select_test_lang(message: types.Message):
    lang_map = {
        "🇬🇧 Ingliz tili testi": "en",
        "🇷🇺 Rus tili testi": "ru",
        "🇰🇷 Koreys tili testi": "ko",
        "🇹🇷 Turk tili testi": "tr",
        "🧮 Matematika testi": "math",
    }
    chosen_lang = lang_map.get(message.text, "en")
    user_test_setup[message.from_user.id] = {"lang": chosen_lang}
    lang_title = TEST_LANG_NAMES.get(chosen_lang, chosen_lang)

    await message.answer(
        f"🎯 <b>{lang_title} tanlandi!</b>\n\n"
        "Nechta savoldan iborat test topshirmoqchisiz?\n"
        "Quyidagi variantlardan birini tanlang:",
        reply_markup=get_test_count_keyboard()
    )


@dp.message(F.text.in_({
    "20 ta savol",
    "40 ta savol",
    "60 ta savol",
    "80 ta savol",
    "100 ta savol",
}))
async def btn_select_test_count(message: types.Message):
    user_id = message.from_user.id
    setup = user_test_setup.get(user_id)
    if not setup:
        await message.answer(
            "Iltimos, avval test tilini tanlang:",
            reply_markup=get_test_lang_keyboard()
        )
        return

    lang_code = setup["lang"]
    count_map = {
        "20 ta savol": 20,
        "40 ta savol": 40,
        "60 ta savol": 60,
        "80 ta savol": 80,
        "100 ta savol": 100,
    }
    count = count_map.get(message.text, 20)
    pool = TEST_QUESTIONS.get(lang_code, [])

    if not pool:
        pool = QUIZ_QUESTIONS

    sample_count = min(count, len(pool))
    selected_questions = random.sample(pool, sample_count)

    user_test_sessions[user_id] = {
        "lang": lang_code,
        "questions": selected_questions,
        "index": 0,
        "score": 0,
        "total": sample_count
    }

    lang_title = TEST_LANG_NAMES.get(lang_code, lang_code)
    await message.answer(
        f"🚀 <b>{lang_title} TESTI BOSHLANDI!</b>\n\n"
        f"📌 Jami: <b>{sample_count} ta savol</b>\n"
        "Har bir savolga to'g'ri variantni (A, B, C, D) tanlang.\n"
        "Omad tilaymiz! 🍀"
    )

    await send_test_question(message, user_id)


@dp.message(F.text == "❌ Testni to'xtatish")
async def btn_cancel_test(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_test_sessions:
        del user_test_sessions[user_id]
    if user_id in user_test_setup:
        del user_test_setup[user_id]
    await message.answer("❌ Test to'xtatildi.", reply_markup=get_main_menu_keyboard())


user_test_locks = {}


@dp.message(F.text.regexp(r"^[ABCDabcd]\)\s|^([ABCDabcd]\)?)$"))
async def btn_test_answer(message: types.Message):
    user_id = message.from_user.id
    session = user_test_sessions.get(user_id)
    if not session:
        return

    # Foydalanuvchi tez-tez yoki ikki marta bosganda race condition bo'lmasligi uchun lock
    if user_id not in user_test_locks:
        user_test_locks[user_id] = asyncio.Lock()

    async with user_test_locks[user_id]:
        session = user_test_sessions.get(user_id)
        if not session:
            return

        idx = session["index"]
        questions = session.get("questions", [])
        if idx >= len(questions):
            return

        q = questions[idx]
        user_text = message.text.strip()
        letter_map = {"A": 0, "B": 1, "C": 2, "D": 3}

        choice = None
        first_letter = user_text[0].upper()

        # Faqat qisqa harf yuborilgan bo'lsa: "A", "B", "C", "D" yoki "A)", "B)", etc.
        clean_short = user_text.rstrip(")").strip().upper()
        if clean_short in letter_map and len(user_text) <= 2:
            choice = letter_map[clean_short]
        elif len(user_text) >= 2 and first_letter in letter_map and user_text[1] == ")":
            # Tugma to'liq matn bilan bosilgan (masalan: "A) Kasal bo'lganda")
            # Bu matn AYNAN joriy savolning biror variantiga to'g'ri kelishi SHART!
            for i, opt in enumerate(q["variantlar"]):
                expected = f"{chr(65 + i)}) {opt}".strip()
                if user_text.lower() == expected.lower():
                    choice = i
                    break

            # Agar joriy savol variantlariga to'g'ri kelmasa:
            # Bu oldingi savoldan qolib ketgan dublikat tugma! E'tiborsiz qoldiramiz.
            if choice is None:
                logger.info(
                    "Eskirgan yoki dublikat test javobi e'tiborsiz qoldirildi: user=%s, text=%s",
                    user_id, user_text
                )
                return

        if choice is None or choice >= len(q["variantlar"]):
            return

        correct = q["javob"]

        if choice == correct:
            session["score"] += 1
            res = "✅ <b>To'g'ri javob!</b> 🎉"
        else:
            correct_letter = chr(65 + correct)
            res = (
                f"❌ <b>Noto'g'ri!</b>\n"
                f"To'g'ri javob: <b>{correct_letter}) {q['variantlar'][correct]}</b>\n\n"
                f"💡 <i>{q.get('tushuntirish', '')}</i>"
            )

        await message.answer(res)
        session["index"] += 1
        await send_test_question(message, user_id)


@dp.message(F.text == "🌐 Tarjima tili")
async def btn_lang_menu(message: types.Message):
    current = get_user_lang(message.from_user.id)
    lang_names = {
        "auto": "🔄 Avtomatik",
        "uz": "🇺🇿 O'zbekcha",
        "en": "🇬🇧 English",
        "ru": "🇷🇺 Русский",
        "ko": "🇰🇷 한국어 (Koreys)",
        "tr": "🇹🇷 Türkçe (Turk)",
    }
    await message.answer(
        "🌐 <b>TIL SOZLAMALARI</b>\n\n"
        f"Hozirgi maqsad til: <b>{lang_names.get(current, '🔄 Avtomatik')}</b>\n\n"
        "Tarjima qilish tilini tanlang:\n"
        "• <b>Avtomatik</b> — til avtomatik aniqlanadi\n"
        "• <b>O'zbekcha</b> — hammasi o'zbekchaga tarjima qilinadi\n"
        "• <b>English</b> — hammasi inglizchaga tarjima qilinadi\n"
        "• <b>Русский</b> — hammasi ruschaga tarjima qilinadi\n"
        "• <b>한국어</b> — hammasi koreyschaga tarjima qilinadi\n"
        "• <b>Türkçe</b> — hammasi turkchaga tarjima qilinadi",
        reply_markup=get_lang_keyboard()
    )


@dp.message(F.text.in_({"🔄 Avtomatik", "🇺🇿 O'zbekcha", "🇬🇧 English", "🇷🇺 Русский", "🇰🇷 한국어 (Koreys)", "🇹🇷 Türkçe (Turk)"}))
async def btn_set_lang(message: types.Message):
    lang_map = {
        "🔄 Avtomatik": "auto",
        "🇺🇿 O'zbekcha": "uz",
        "🇬🇧 English": "en",
        "🇷🇺 Русский": "ru",
        "🇰🇷 한국어 (Koreys)": "ko",
        "🇹🇷 Türkçe (Turk)": "tr"
    }
    lang = lang_map.get(message.text, "auto")
    set_user_lang(message.from_user.id, lang)
    await message.answer(
        f"✅ <b>Tarjima tili o'zgartirildi:</b> {message.text}\n\n"
        "Endi yuborganingiz shu tilga tarjima qilinadi.",
        reply_markup=get_main_menu_keyboard()
    )


@dp.message(F.text == "📚 Kutubxona")
async def btn_kutubxona(message: types.Message):
    await message.answer(
        "📚 <b>KUTUBXONA</b>\n\nKategoriyani tanlang:",
        reply_markup=get_kutubxona_keyboard()
    )


@dp.message(F.text.in_(set(KUTUBXONA.keys())))
async def btn_kutubxona_category(message: types.Message):
    category = message.text
    books = KUTUBXONA.get(category, [])
    if not books:
        await message.answer("Kitoblar topilmadi.")
        return

    text = f"📚 <b>{html.escape(category)}</b>\n\n"
    for i, book in enumerate(books, 1):
        text += (
            f"<b>{i}. {html.escape(book['nom'])}</b>\n"
            f"✍️ {html.escape(book['muallif'])}\n"
            f"📝 <i>{html.escape(book['tavsif'])}</i>\n\n"
        )
    await message.answer(text, reply_markup=get_kutubxona_keyboard())


@dp.message(F.text == "💡 Fakt")
async def btn_fakt_info(message: types.Message):
    fakt = random.choice(FAKTLAR)
    await message.answer(
        f"💡 <b>QIZIQARLI FAKT</b>\n\n{fakt}",
        reply_markup=get_main_menu_keyboard()
    )


@dp.message(F.text == "🔥 Motivatsiya")
async def btn_motivatsiya_quote(message: types.Message):
    quote = random.choice(MOTIVATSIYA_QUOTES)
    await message.answer(
        f"🔥 <b>MOTIVATSIYA</b>\n\n"
        f"💬 <i>\"{html.escape(quote['quote'])}\"</i>\n\n"
        f"— <b>{html.escape(quote['muallif'])}</b>\n\n"
        "━━━━━━━━━━━━━━\n\n"
        f"🇺🇿 {html.escape(quote['tarjima'])}",
        reply_markup=get_main_menu_keyboard()
    )


@dp.message(F.text == "🧮 Matematik")
async def btn_matematik_problem(message: types.Message):
    data = generate_math_problem_with_options()
    user_math_sessions[message.from_user.id] = data

    await message.answer(
        "🧮 <b>MATEMATIK MASALA</b>\n\n"
        f"❓ <code>{data['problem']}</code>\n\n"
        f"A) {data['options'][0]}\n"
        f"B) {data['options'][1]}\n"
        f"C) {data['options'][2]}\n\n"
        "👇 <i>To'g'ri javobni tanlang:</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=f"A) {data['options'][0]}", callback_data=f"math_choice_0_{data['correct_idx']}"),
                InlineKeyboardButton(text=f"B) {data['options'][1]}", callback_data=f"math_choice_1_{data['correct_idx']}"),
            ],
            [
                InlineKeyboardButton(text=f"C) {data['options'][2]}", callback_data=f"math_choice_2_{data['correct_idx']}"),
            ],
            [
                InlineKeyboardButton(text="🧮 Yangi masala", callback_data="menu_matematik"),
                InlineKeyboardButton(text="⬅️ Menyu", callback_data="back_main"),
            ],
        ])
    )


@dp.message(F.text == "🌤 Ob-havo")
async def btn_weather_menu(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌤 @Obb_hovo_Bot ga o'tish", url="https://t.me/Obb_hovo_Bot")
        ]
    ])
    await message.answer(
        "🌤 <b>OB-HAVO MA'LUMOTLARI</b>\n\n"
        "O'zbekistonning barcha 12 ta viloyati va dunyo shaharlari bo'yicha eng aniq ob-havo ma'lumotlarini olish uchun quyidagi tugma orqali rasmiy botimizga o'ting:\n\n"
        "👉 @Obb_hovo_Bot",
        reply_markup=markup
    )


@dp.message(F.text.in_(set(WEATHER_CITY_MAP.keys())))
async def btn_weather_city_select(message: types.Message):
    city = WEATHER_CITY_MAP.get(message.text, "Tashkent")
    await send_weather(message, city)


@dp.message(F.text == "📊 Statistika")
async def btn_stats_info(message: types.Message):
    await stats_command(message)


@dp.message(F.text == "🕘 Tarix")
async def btn_history_info(message: types.Message):
    await history_command(message)


@dp.message(F.text == "❓ Yordam")
async def btn_help_info(message: types.Message):
    await help_command(message)


@dp.message(F.text == "📷 Rasm tarjima")
async def btn_photo_info(message: types.Message):
    await message.answer(
        "📷 <b>RASM TARJIMA TIZIMI</b>\n\n"
        "Rasmda matn bormi? Menga yuboring!\n\n"
        "📌 <b>Qanday foydalaniladi:</b>\n"
        "1️⃣ Matni bor istalgan rasmni to'g'ridan-to'g'ri botga yuboring.\n"
        "2️⃣ Bot rasmdagi matnni sun'iy intellekt (OCR) orqali o'qiydi.\n"
        "3️⃣ So'ngra Google Translate orqali uni o'zbek yoki boshqa tilga tarjima qiladi!\n\n"
        "✅ <b>OCR tizimi faol va tayyor!</b>\n"
        "💡 <i>Shuningdek, rasmni yuborib tagiga izoh (caption) yozsangiz, bot izohni ham bir zumda tarjima qiladi.</i>",
        reply_markup=get_main_menu_keyboard()
    )


@dp.message(Command("alfabit"))
@dp.message(Command("alifbo"))
@dp.message(F.text == "🔤 Alifbo")
async def alfabit_command(message: types.Message):
    await message.answer(
        "🔤 <b>TILLAR ALIFBOSI VA TALAFFUZI (9 TA TIL)</b>\n\n"
        "O'rganmoqchi bo'lgan til alifbosini tanlang:\n\n"
        "• 🇬🇧 <b>Ingliz alifbosi</b> — 26 ta harf, transkripsiya va o'qilish qoidalari\n"
        "• 🇷🇺 <b>Rus alifbosi</b> — 33 ta harf, qattiq/yumshoq tovushlar va qoidalar\n"
        "• 🇰🇷 <b>Koreys alifbosi (Hangul)</b> — unlilar, undoshlar va Batchim qoidasi\n"
        "• 🇹🇷 <b>Turk alifbosi</b> — 29 ta harf va unlilar uyg'unligi qoidalari\n"
        "• 🇺🇿 <b>O'zbek alifbosi</b> — Lotin va Kirill yozuvlari, qoidalar\n"
        "• 🇸🇦 <b>Arab alifbosi</b> — 28 ta harf, harakatlar va mahrajlar\n"
        "• 🇩🇪 <b>Nemis alifbosi</b> — Umlaute, Eszett va asosiy tovush birikmalari\n"
        "• 🇫🇷 <b>Fransuz alifbosi</b> — Aksentlar, o'qilmaydigan harflar va qoidalar\n"
        "• 🇯🇵 <b>Yapon alifbosi</b> — Hiragana va Katakana bo'g'inlari",
        reply_markup=get_alphabet_keyboard()
    )


@dp.message(F.text.in_({
    "🇬🇧 Ingliz alifbosi",
    "🇷🇺 Rus alifbosi",
    "🇰🇷 Koreys alifbosi (Hangul)",
    "🇹🇷 Turk alifbosi",
    "🇺🇿 O'zbek alifbosi",
    "🇸🇦 Arab alifbosi",
    "🇩🇪 Nemis alifbosi",
    "🇫🇷 Fransuz alifbosi",
    "🇯🇵 Yapon alifbosi",
}))
async def btn_alphabet_selected(message: types.Message):
    lang_map = {
        "🇬🇧 Ingliz alifbosi": "en",
        "🇷🇺 Rus alifbosi": "ru",
        "🇰🇷 Koreys alifbosi (Hangul)": "ko",
        "🇹🇷 Turk alifbosi": "tr",
        "🇺🇿 O'zbek alifbosi": "uz",
        "🇸🇦 Arab alifbosi": "ar",
        "🇩🇪 Nemis alifbosi": "de",
        "🇫🇷 Fransuz alifbosi": "fr",
        "🇯🇵 Yapon alifbosi": "ja",
    }
    code = lang_map.get(message.text, "en")
    info = ALPHABET_DATA.get(code)
    if not info:
        await message.answer("Alifbo ma'lumoti topilmadi.", reply_markup=get_alphabet_keyboard())
        return

    await message.answer(info, reply_markup=get_alphabet_keyboard())


@dp.message(F.text.in_({"📝 Quiz / Savol", "🎲 Quiz / Savol"}))
async def btn_quiz_menu_open(message: types.Message):
    await message.answer(
        "📝 <b>QUIZ — TIL VA BILIM VIKTORINASI</b>\n\n"
        "Jami 60 ta qiziqarli savol:\n"
        "• 🔤 So'z tarjimasi (1-12)\n"
        "• 📖 Grammatika (13-24)\n"
        "• 📚 So'z boyligi (25-36)\n"
        "• 🧠 Mantiqiy savollar (37-48)\n"
        "• 🌍 Dunyoqarash & Fan (49-60)\n\n"
        "Kategoriyani tanlang:",
        reply_markup=get_quiz_keyboard()
    )


@dp.message(F.text.in_({
    "🎲 Tasodifiy savol",
    "🔤 So'z tarjimasi (1-12)",
    "📖 Grammatika (13-24)",
    "📚 So'z boyligi (25-36)",
    "🧠 Mantiqiy savollar (37-48)",
    "🌍 Dunyoqarash & Fan (49-60)",
}))
async def btn_quiz_question_show(message: types.Message):
    cat = message.text
    if cat == "🎲 Tasodifiy savol":
        q_index = random.randint(0, len(QUIZ_QUESTIONS) - 1)
    elif "1-12" in cat:
        q_index = random.randint(0, 11)
    elif "13-24" in cat:
        q_index = random.randint(12, 23)
    elif "25-36" in cat:
        q_index = random.randint(24, 35)
    elif "37-48" in cat:
        q_index = random.randint(36, 47)
    elif "49-60" in cat:
        q_index = random.randint(48, 59)
    else:
        q_index = random.randint(0, len(QUIZ_QUESTIONS) - 1)

    q = QUIZ_QUESTIONS[q_index]
    correct = q['javob']
    text = (
        f"📝 <b>SAVOL {q_index + 1}/{len(QUIZ_QUESTIONS)}</b>\n\n"
        f"{q['savol']}\n\n"
    )
    for i, variant in enumerate(q['variantlar']):
        letter = chr(65 + i)
        text += f"<b>{letter})</b> {variant}\n"

    text += (
        f"\n💡 <b>To'g'ri javob:</b> <b>{chr(65 + correct)}) {q['variantlar'][correct]}</b>\n\n"
        f"📖 <i>{q['tushuntirish']}</i>"
    )
    await message.answer(text, reply_markup=get_quiz_keyboard())


# ============================================================
# MAIN MESSAGE — TARJIMA (EN/UZ/RU)
# ============================================================

@dp.message()
async def translate_message(
    message: types.Message
):

    text = message.text

    if not text:

        return

    text = text.strip()

    if not text:

        return

    register_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name
    )

    try:

        # ==================================================
        # LANGUAGE DETECTION
        # ==================================================

        detected = await translator_detect(text)
        detected_raw = getattr(detected, "lang", "auto") or "auto"
        if isinstance(detected_raw, list):
            detected_raw = detected_raw[0]
        detected_raw = str(detected_raw).lower().strip()
        lang = detected_raw.split("-")[0] if "-" in detected_raw and detected_raw not in ("zh-cn", "zh-tw") else detected_raw

        logger.info(
            "User=%s | text=%s | language=%s",
            message.from_user.id,
            text,
            lang
        )

        # ==================================================
        # DETERMINE TARGET LANGUAGE
        # ==================================================

        user_pref = get_user_lang(message.from_user.id)

        if user_pref != "auto":
            # Foydalanuvchi o'zi tanlagan tilga tarjima
            destination = user_pref
            # Agar manba va maqsad tili bir xil bo'lsa
            if lang == destination:
                destination = "en" if destination == "uz" else "uz"
        else:
            # Avtomatik rejim
            if lang == "uz":
                destination = "en"
            elif lang == "en":
                destination = "uz"
            elif lang in ("ru", "ko", "tr", "de", "fr", "ar", "ja", "zh", "es"):
                destination = "uz"
            else:
                destination = "uz"

        src_flag = GLOBAL_LANG_FLAGS.get(lang, "🌐")
        dst_flag = GLOBAL_LANG_FLAGS.get(destination, "🌐")
        src_name = GLOBAL_LANG_NAMES.get(lang, lang.upper())
        dst_name = GLOBAL_LANG_NAMES.get(destination, destination.upper())

        # ==================================================
        # DIRECT TRANSLATION (user_pref != auto, gap yoki inglizcha bo'lmagan so'z)
        # ==================================================

        if user_pref != "auto" or len(text.split()) > 2 or lang != "en":
            result = await translator_translate(text, destination)
            translated_text = getattr(result, "text", str(result))

            increment_search(message.from_user.id)
            save_history(message.from_user.id, text, translated_text)

            await message.answer(
                f"🌐 <b>TARJIMA</b> {src_flag} → {dst_flag}\n"
                f"<i>{src_name} → {dst_name}</i>\n\n"
                f"📝 <b>Original:</b>\n"
                f"{html.escape(text)}\n\n"
                "━━━━━━━━━━━━━━\n\n"
                f"🔄 <b>Tarjima:</b>\n"
                f"{html.escape(translated_text)}"
            )
            return

        # ==================================================
        # SINGLE ENGLISH WORD — OXFORD DICTIONARY LOOKUP
        # ==================================================

        word = text.strip()
        lookup = await asyncio.to_thread(getDefinitions, word)

        if not lookup:
            # So'z lug'atda topilmasa oddiy tarjima
            result = await translator_translate(text, destination)
            translated_text = getattr(result, "text", str(result))

            increment_search(message.from_user.id)
            save_history(message.from_user.id, text, translated_text)

            await message.answer(
                f"🌐 <b>TARJIMA</b> {src_flag} → {dst_flag}\n"
                f"<i>{src_name} → {dst_name}</i>\n\n"
                f"📝 <b>Original:</b>\n"
                f"{html.escape(text)}\n\n"
                "━━━━━━━━━━━━━━\n\n"
                f"🔄 <b>Tarjima:</b>\n"
                f"{html.escape(translated_text)}"
            )
            return

        # Oxford lug'at topildi
        increment_search(message.from_user.id)
        real_word = lookup.get("word", word)
        phonetic = lookup.get("phonetic")
        definitions = lookup.get("getDefinitions")
        examples = lookup.get("examples", [])
        synonyms = lookup.get("synonyms", [])
        antonyms = lookup.get("antonyms", [])
        audio = lookup.get("audio")

        uz_translation = await translator_translate(real_word, "uz")
        ru_translation = await translator_translate(real_word, "ru")
        uz_text = getattr(uz_translation, "text", "")
        ru_text = getattr(ru_translation, "text", "")

        response = f"📖 <b>{html.escape(real_word)}</b>\n"
        response += (
            f"🇺🇿 <b>O'zbekcha:</b> {html.escape(uz_text)}\n"
            f"🇷🇺 <b>Русский:</b> {html.escape(ru_text)}\n"
        )
        if destination not in ("uz", "ru", "en"):
            dst_translation = await translator_translate(real_word, destination)
            dst_text = getattr(dst_translation, "text", "")
            response += f"{dst_flag} <b>{dst_name}:</b> {html.escape(dst_text)}\n"

        if phonetic:
            response += f"🔤 <b>Pronunciation:</b> <code>{html.escape(phonetic)}</code>\n"

        response += "\n"
        if definitions:
            response += f"📚 <b>DEFINITIONS</b>\n\n{definitions}\n"

        if examples:
            response += "\n📝 <b>EXAMPLES</b>\n\n"
            for example in examples[:5]:
                response += f"• <i>{example}</i>\n"

        if synonyms:
            response += f"\n🔄 <b>SYNONYMS</b>\n\n{', '.join(map(html.escape, synonyms[:15]))}\n"

        if antonyms:
            response += f"\n🚫 <b>ANTONYMS</b>\n\n{', '.join(map(html.escape, antonyms[:15]))}\n"

        await message.answer(response)

        if audio:
            try:
                audio_file = URLInputFile(audio, filename=f"{real_word}.mp3")
                await message.answer_voice(voice=audio_file)
            except Exception as audio_error:
                logger.warning("Audio yuborilmadi: %s", audio_error)

        save_history(message.from_user.id, text, real_word)


    except Exception as error:

        logger.exception(
            "Message processing error: %s",
            error
        )

        await message.answer(
            "⚠️ <b>Kutilmagan xatolik yuz berdi.</b>\n\n"
            "Internet aloqangizni tekshiring "
            "va qaytadan urinib ko'ring."
        )


# ============================================================
# START BOT
# ============================================================

async def main():

    init_database()

    logger.info(
        "======================================"
    )

    logger.info(
        "🤖 SUPER TARJIMON BOT ISHGA TUSHMOQDA..."
    )

    logger.info(
        "======================================"
    )

    try:

        await bot.delete_webhook(
            drop_pending_updates=True
        )

        # Telegram buyruqlar menyusini o'rnatish
        commands = [
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="menu", description="Asosiy menyuni ochish"),
            BotCommand(command="lang", description="Tarjima tilini sozlash"),
            BotCommand(command="alfabit", description="9ta til alifbosi EN,RU,KO,TR,UZ,AR,DE,FR,JA"),
            BotCommand(command="test", description="Fan va til testlari 20-100"),
            BotCommand(command="matematik", description="Matematik masalalar A,B,C"),
            BotCommand(command="obhavo", description="12 ta viloyat ob-havosi"),
            BotCommand(command="quiz", description="Til o'rganish viktorinasi"),
            BotCommand(command="kutubxona", description="Foydali kitoblar 9ta kategoriya"),
            BotCommand(command="fakt", description="Qiziqarli faktlar"),
            BotCommand(command="motivatsiya", description="Motivatsion iqtiboslar"),
            BotCommand(command="stats", description="Foydalanish statistikasi"),
            BotCommand(command="history", description="Tarjimalar tarixi"),
            BotCommand(command="clear", description="Tarixni tozalash"),
            BotCommand(command="help", description="Yordam va qo'llanma"),
        ]
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        await bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
        logger.info("✅ Telegram buyruqlar menyusi o'rnatildi.")

        retry_delay = 3
        while True:
            try:
                await dp.start_polling(bot)
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Polling vaqtinchalik uzildi: %s. %s soniyadan so'ng qayta ulanmoqda...", e, retry_delay)
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)
    finally:

        await bot.session.close()
# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi.")