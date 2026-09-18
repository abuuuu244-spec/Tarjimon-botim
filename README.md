# 🤖 Tarjimon Bot

Telegram uchun ko'p tilli tarjimon va o'quv boti: tarjima, ingliz tili lug'ati,
testlar, viktorina, alifbolar, matematik masalalar, ob-havo, kutubxona, faktlar
va motivatsiya.

Ma'lumotlar **JSON fayllarda** saqlanadi — hech qanday ma'lumotlar bazasi
(SQLite/Postgres) o'rnatish shart emas.

---

## Mundarija

- [Imkoniyatlar](#imkoniyatlar)
- [Ishga tushirish ketma-ketligi](#ishga-tushirish-ketma-ketligi)
- [Loyiha tuzilishi](#loyiha-tuzilishi)
- [Savollarni tahrirlash va tekshirish](#savollarni-tahrirlash-va-tekshirish)
- [Ma'lumotlar ombori (JSON)](#malumotlar-ombori-json)
- [Muhit o'zgaruvchilari](#muhit-ozgaruvchilari)
- [Railway'ga deploy qilish](#railwayga-deploy-qilish)
- [Botning ishlash mantiqi](#botning-ishlash-mantiqi)
- [Buyruqlar](#buyruqlar)
- [Muammolarni hal qilish](#muammolarni-hal-qilish)

---

## Imkoniyatlar

| Bo'lim | Tavsif |
|---|---|
| 🌐 Tarjima | Matn tilini avtomatik aniqlab, kerakli tilga o'giradi (UZ, EN, RU, KO, TR va boshqalar) |
| 📖 Lug'at | Bitta inglizcha so'z uchun ta'rif, transkripsiya, misollar, sinonim/antonim va talaffuz audiosi |
| 📷 Rasm tarjima | Rasmdagi matnni OCR orqali o'qib tarjima qiladi (ixtiyoriy) |
| 🎥 Video tarjima | Videoga yozilgan izohni (caption) tarjima qiladi |
| 📝 Test | 5 yo'nalish (EN, RU, KO, TR, matematika), har birida 100 ta savol; 20–100 tadan test |
| 🎲 Quiz | 60 ta savol, 5 kategoriya, javob tugmalari va tushuntirish bilan |
| 🔤 Alifbo | 9 ta til alifbosi va o'qilish qoidalari |
| 🧮 Matematik | Variantli masalalar (qo'shish, ildiz, foiz, tenglama, geometriya…) |
| 🌤 Ob-havo | wttr.in orqali shaharlar ob-havosi |
| 📚 Kutubxona | Kategoriyalarga ajratilgan kitob tavsiyalari |
| 📊 Statistika / 🕘 Tarix | Qidiruvlar soni va oxirgi tarjimalar |

---

## Ishga tushirish ketma-ketligi

Quyidagi qadamlarni **shu tartibda** bajaring.

### 2-qadam — Virtual muhit yaratish

```bash
python -m venv .venv
```

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

### 3-qadam — Kutubxonalarni o'rnatish

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> 💡 Rasm tarjimasi kerak bo'lmasa, `requirements.txt` dagi OCR bo'limini
> (`pillow`, `numpy`, `rapidocr-onnxruntime`, `onnxruntime`) izohga oling —
> o'rnatish ~250 MB tejaladi va bot baribir ishlayveradi.

### 4-qadam — Tokenni sozlash

```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

`.env` faylini oching va [@BotFather](https://t.me/BotFather) dan olgan
tokeningizni yozing:

```env
BOT_TOKEN=123456789:AAExampleTokenReplaceMeWithYourOwnToken
```

### 5-qadam — Ishga tushirish

```bash
python main.py
```

Konsolda quyidagilarni ko'rsangiz — hammasi joyida:

```
💾 JSON ombor tayyor: 4 foydalanuvchi, 61 tarix yozuvi (...\data) | autosave: 5s
🤖 SUPER TARJIMON BOT ISHGA TUSHMOQDA...
📚 Savollar: 60 ta quiz, 5 ta test yo'nalishi
🖼 OCR: faol
✅ Telegram buyruqlar menyusi o'rnatildi.
```

### 6-qadam — Telegramda tekshirish

Botga `/start` yuboring → menyu chiqadi → biror so'z yuboring → tarjima keladi.

### 7-qadam — To'xtatish

`Ctrl + C` bosing. Bot saqlanmagan ma'lumotlarni diskka yozib, so'ng yopiladi.

---

## Loyiha tuzilishi

```
Tarjimon-botim/
│
├── main.py              # Bot mantiqi: handlerlar, klaviaturalar, tarjima oqimi
├── storage.py           # JSON ombor: foydalanuvchilar, tarix, avtosaqlash
├── oxfordLookup.py      # Inglizcha so'zlar lug'ati (dictionaryapi.dev API)
├── test_data.py         # 5 yo'nalish × 100 ta test savoli
├── alphabet_data.py     # 9 ta til alifbosi ma'lumotlari
├── validate_data.py     # Savol/kontent ma'lumotlarini tekshiruvchi vosita
│
├── data/                # Ma'lumotlar (repoga tushmaydi)
│   ├── users.json       #   foydalanuvchilar va sozlamalari
│   ├── history.json     #   tarjimalar tarixi
│   └── backups/         #   zaxira nusxalar
│
├── requirements.txt     # Kutubxonalar ro'yxati
├── .env.example         # Muhit o'zgaruvchilari namunasi
├── .gitignore
├── Procfile             # Railway/Heroku uchun ishga tushirish buyrug'i
├── railway.toml         # Railway konfiguratsiyasi
└── .python-version      # Python versiyasi (3.12)
```

### `main.py` ichki tartibi

Fayl yuqoridan pastga quyidagi bloklarga bo'lingan:

| Blok | Nima turadi |
|---|---|
| 1. Importlar va konfiguratsiya | `BOT_TOKEN`, OCR mavjudligini aniqlash, logging |
| 2. Yordamchilar | `split_long_text`, `answer_long`, `safe_edit_text`, `lang_title` |
| 3. Kontent ma'lumotlari | `KUTUBXONA`, `MOTIVATSIYA_QUOTES`, `FAKTLAR`, `QUIZ_QUESTIONS` |
| 4. Tarjima tizimi | Til aniqlash evristikasi, 4 bosqichli tarjima zanjiri |
| 5. Klaviaturalar | Reply va Inline klaviaturalar (`get_*_keyboard`) |
| 6. Matn generatorlari | `build_*_text`, `build_quiz_message`, `build_math_message` |
| 7. Buyruq handlerlari | `/start`, `/help`, `/lang`, `/test`, `/quiz`, … |
| 8. Callback handlerlari | Inline tugmalar (`menu_*`, `quiz*`, `math_choice_*`, …) |
| 9. Media handlerlari | Rasm, hujjat, video |
| 10. Matn handleri | Asosiy tarjima oqimi (eng oxirida — «catch-all») |
| 11. `main()` | Ishga tushirish, avtosaqlash, signal bilan to'xtatish |

> ⚠️ **Handlerlar tartibi muhim.** aiogram birinchi mos kelgan handlerni
> ishlatadi. Shuning uchun `@dp.message()` (filtrsiz, catch-all) tarjima
> handleri **eng oxirida** turishi shart — aks holda u boshqa barcha
> tugmalarni «yutib» yuboradi.

---

## Savollarni tahrirlash va tekshirish

Savol qo'shsangiz yoki alifbo matnini o'zgartirsangiz, **har doim** tekshiruvni
ishga tushiring:

```bash
python validate_data.py
```

```
[QUIZ] — 60 ta savol
[TEST:en] — 100 ta savol
...
✅ MUAMMO TOPILMADI — barcha ma'lumotlar to'g'ri
```

Tekshiruv nimani topadi:

| Tekshiruv | Nega muhim |
|---|---|
| `javob` indeksi variantlar sonidan kichikmi | Chegaradan chiqsa handler xato beradi |
| 4 tadan ko'p variant yo'qmi | Klaviatura A–D tugmalariga mo'ljallangan |
| Takrorlangan savol/variant | Foydalanuvchiga bir xil savol ikki marta tushmasin |
| Telegram HTML to'g'riligi | **Eng muhimi** — noto'g'ri teg bo'lsa xabar umuman yuborilmaydi |
| Tugma va xabar uzunligi | Telegram chegaralari (64 / 4096 belgi) |

### ⚠️ HTML haqida eslatma

Savol matnlari Telegram'ga **HTML** sifatida yuboriladi. Shuning uchun:

```python
# ❌ NOTO'G'RI — Telegram "<->" ni teg deb o'qiydi va xabar yuborilmaydi
"tushuntirish": "Fast (tez) <-> Slow (sekin)."

# ✅ TO'G'RI
"tushuntirish": "Fast (tez) ↔ Slow (sekin)."
```

Ruxsat etilgan teglar: `<b> <i> <u> <s> <a> <code> <pre> <blockquote> <tg-spoiler>`.
`<` va `&` belgilari `&lt;` va `&amp;` ko'rinishida yozilishi kerak.

> Himoya sifatida bot HTML xatosini ushlab qolsa, xabarni **oddiy matn**
> sifatida qayta yuboradi — foydalanuvchi baribir javob oladi. Lekin bunda
> qalin/kursiv formatlash yo'qoladi, shuning uchun `validate_data.py` bilan
> oldindan tekshirgan ma'qul.

---

## Ma'lumotlar ombori (JSON)

Loyiha ilgari SQLite (`bot.db`) ishlatgan. Endi ma'lumotlar oddiy JSON
fayllarda saqlanadi — ochib o'qish, tahrirlash va nusxalash oson.

### `data/users.json`

```json
{
  "123456789": {
    "user_id": 123456789,
    "username": "example",
    "full_name": "Ism Familiya",
    "searches": 47,
    "target_lang": "uz",
    "created_at": "2026-09-10T03:33:55.360762",
    "updated_at": "2026-09-17T21:10:02.120033"
  }
}
```

### `data/history.json`

```json
{
  "123456789": [
    {
      "text": "Men maktabga boraman",
      "result": "I go to school",
      "created_at": "2026-09-10T03:34:10.001122"
    }
  ]
}
```

### Qanday ishlaydi

| Xususiyat | Tavsif |
|---|---|
| **Xotirada kesh** | Barcha ma'lumot ishga tushganda RAM'ga yuklanadi — o'qish bir zumda |
| **Avtosaqlash** | O'zgarishlar `AUTOSAVE_INTERVAL` (default 5 s) da bir marta diskka yoziladi. Har bir xabarda butun faylni qayta yozish o'rniga — ancha tez |
| **Atomik yozuv** | Avval `.tmp` faylga yoziladi, keyin `os.replace()` — yozuv o'rtasida bot to'xtasa ham fayl buzilmaydi |
| **Thread-safe** | `threading.RLock` bilan himoyalangan |
| **Tarix chegarasi** | Har bir foydalanuvchi uchun oxirgi `MAX_HISTORY_PER_USER` (default 200) ta yozuv |
| **Buzilgan fayl** | JSON o'qilmasa, `.broken` nomi bilan saqlanadi va bot bo'sh holatdan davom etadi |
| **To'xtashda saqlash** | `Ctrl+C` yoki `SIGTERM` (Railway) kelganda saqlanmagan ma'lumot diskka yoziladi |

### Zaxira nusxa olish

Eng oddiy yo'l — `data/` papkasini nusxalash. Yoki kod orqali:

```python
import storage
storage.init_storage()
storage.backup()          # data/backups/20260917_221500/ ichiga yozadi
storage.backup("D:/zaxira")
```

---

## Muhit o'zgaruvchilari

| O'zgaruvchi | Majburiy | Default | Tavsif |
|---|---|---|---|
| `BOT_TOKEN` | ✅ ha | — | @BotFather dan olingan token |
| `OCR_SPACE_API_KEY` | yo'q | — | Rasmdan matn o'qish uchun onlayn zaxira ([ocr.space](https://ocr.space/ocrapi)) |
| `DATA_DIR` | yo'q | `./data` | JSON fayllar papkasi |
| `MAX_HISTORY_PER_USER` | yo'q | `200` | Bitta foydalanuvchi tarixi chegarasi |
| `AUTOSAVE_INTERVAL` | yo'q | `5` | Necha soniyada bir saqlansin. `0` — har o'zgarishda darhol |

---

## Railway'ga deploy qilish

[railway.com](https://railway.com) da bot **worker** (fon xizmati) sifatida
ishlaydi — HTTP port ochmaydi, Telegram'dan yangiliklarni o'zi so'rab turadi.

### 1-qadam — Kodni GitHub'ga yuklash

```bash
git add .
git commit -m "JSON ombor + Railway konfiguratsiyasi"
git push origin main
```

> ⚠️ `.env` va `data/*.json` `.gitignore` orqali chiqarib tashlangan —
> token va foydalanuvchi ma'lumotlari GitHub'ga tushmaydi.

### 2-qadam — Railway'da loyiha yaratish

1. [railway.com](https://railway.com) → **New Project**
2. **Deploy from GitHub repo** → `Tarjimon-botim` reposini tanlang
3. Railway `railway.toml` va `requirements.txt` ni o'zi topib, build qiladi

### 3-qadam — O'zgaruvchilarni kiritish

Service → **Variables** → **New Variable**:

| Nomi | Qiymati |
|---|---|
| `BOT_TOKEN` | `123456789:AAE...` (BotFather tokeni) |
| `DATA_DIR` | `/data` |
| `TZ` | `Asia/Tashkent` *(ixtiyoriy — loglardagi vaqt uchun)* |

### 4-qadam — Volume ulash (ENG MUHIM QADAM)

Railway konteynerining diski **vaqtinchalik**: har bir yangi deploydan keyin
fayllar o'chib ketadi. Foydalanuvchilar va tarix yo'qolmasligi uchun doimiy
disk (Volume) ulash **shart**:

1. Service → **Settings** → **Volumes** → **Add Volume**
2. **Mount path**: `/data`
3. `DATA_DIR=/data` o'zgaruvchisi allaqachon shu papkaga ishora qiladi

> Volume ulanmasa bot ishlaydi, lekin har deploydan keyin barcha
> foydalanuvchi sozlamalari va tarix nolga tushadi.

### 5-qadam — Mavjud ma'lumotni ko'chirish (ixtiyoriy)

Kompyuteringizdagi `data/users.json` va `data/history.json` ni Railway'ga
ko'chirish uchun:

```bash
railway login
railway link                       # loyihani tanlang
railway run bash                   # konteyner ichida terminal
# boshqa terminalda fayl yuborish uchun:
railway volume                     # volume ma'lumotlari
```

Eng oddiy yo'l — fayllarni vaqtincha private Gist/S3 ga qo'yib,
konteyner ichida `curl` bilan `/data` ga yuklab olish.

### 6-qadam — Tekshirish

Service → **Deployments** → **View Logs**. Quyidagi qatorlarni qidiring:

```
💾 JSON ombor tayyor: 0 foydalanuvchi, 0 tarix yozuvi (/data) | autosave: 5s
🤖 SUPER TARJIMON BOT ISHGA TUSHMOQDA...
✅ Telegram buyruqlar menyusi o'rnatildi.
```

Telegramda botga `/start` yuboring.

### Railway bo'yicha muhim eslatmalar

| Masala | Yechim |
|---|---|
| `Conflict: terminated by other getUpdates request` | Bot bir vaqtda ikki joyda ishlayapti. Kompyuterdagi nusxani to'xtating; Railway'da `numReplicas = 1` bo'lsin (`railway.toml` da yozilgan) |
| Build juda uzoq / hajm katta | `requirements.txt` dagi OCR bo'limini izohga oling |
| Har deploydan keyin ma'lumot yo'qoladi | Volume ulanmagan — 4-qadamga qarang |
| "No start command found" | `railway.toml` yoki `Procfile` repo ildizida turganiga ishonch hosil qiling |
| Deploy paytida ma'lumot yo'qolishi | Bot `SIGTERM` ni ushlab, to'xtashdan oldin saqlaydi — qo'shimcha sozlash kerak emas |

---

## Botning ishlash mantiqi

### Tarjima oqimi

```
Foydalanuvchi matni
        │
        ▼
1. Til aniqlash (_detect_script_heuristic)
   • Koreys / arab / yapon / kirill yozuvlari — belgilar bo'yicha
   • O'zbek kirill (ў, қ, ғ, ҳ) rus tilidan ajratiladi
   • O'zbek lotin: o', g' harflari yoki "va/bu/men/uchun…" so'zlari
   • Topilmasa → Google detect → langdetect → googletrans
        │
        ▼
2. Maqsad tilni tanlash (choose_destination)
   • Foydalanuvchi til tanlagan bo'lsa — o'sha til
   • Matn allaqachon shu tilda bo'lsa — teskari yo'nalish
   • "auto" rejimida: o'zbekcha → inglizcha, qolgani → o'zbekcha
        │
        ▼
3. Tarjima (translator_translate) — 4 bosqichli zanjir:
   Google Direct API → deep_translator → MyMemory → googletrans
        │
        ▼
4. Natija + tarixga yozish
```

Bitta inglizcha so'z yuborilsa (va til "auto" bo'lsa), bot tarjima o'rniga
**lug'at kartasini** qaytaradi: ta'riflar, misollar, sinonimlar va audio.

### Nega bir nechta tarjima motori?

Bepul (rasmiy bo'lmagan) Google endpointlari vaqti-vaqti bilan `429`/`302`
qaytaradi. Bot birinchi ishlagan motorni ishlatadi — shuning uchun bitta
xizmat yiqilsa ham tarjima to'xtamaydi.

---

## Buyruqlar

```
/start        Botni ishga tushirish
/menu         Asosiy menyu
/lang         Tarjima tilini tanlash
/alfabit      Tillar alifbosi (/alifbo ham ishlaydi)
/test         Testlar (20/40/60/80/100 savol)
/quiz         Viktorina savollari (/savol ham ishlaydi)
/matematik    Matematik masala
/obhavo       Ob-havo
/kutubxona    Kitoblar
/fakt         Qiziqarli fakt
/motivatsiya  Motivatsion iqtibos
/stats        Statistika
/history      Tarjimalar tarixi
/clear        Tarixni tozalash
/help         Yordam
```

---

## Muammolarni hal qilish

| Xato | Sabab va yechim |
|---|---|
| `BOT_TOKEN topilmadi!` | `.env` fayli yo'q yoki `BOT_TOKEN` bo'sh. 4-qadamga qarang |
| `TelegramUnauthorizedError` | Token noto'g'ri yoki bekor qilingan — BotFather'dan yangisini oling |
| `Conflict: terminated by other getUpdates` | Bot ikki joyda ishlayapti — bittasini to'xtating |
| Rasm tarjimasi ishlamayapti | OCR kutubxonalari o'rnatilmagan. `pip install rapidocr-onnxruntime pillow numpy` yoki `OCR_SPACE_API_KEY` qo'shing |
| Tarjima "⚠️ Kutilmagan xatolik" beradi | Internet yo'q yoki barcha tarjima xizmatlari cheklovga uchradi — bir necha daqiqadan keyin urinib ko'ring |
| `can't parse entities` | Savol matnida noto'g'ri HTML bor. `python validate_data.py` ni ishga tushiring |
| Konsolda emoji o'rniga `?` | Bot `stdout` ni UTF-8 ga o'tkazadi; eski konsollarda `chcp 65001` buyrug'ini bering |
| Ma'lumot saqlanmayapti | `data/` papkasiga yozish huquqi bormi? `DATA_DIR` to'g'ri ko'rsatilganmi? |

---

## Eslatmalar

- Tarjima bepul (rasmiy bo'lmagan) Google Translate va MyMemory endpointlari
  orqali ishlaydi — katta yuklamada so'rovlar cheklanishi mumkin.
- `data/` papkasidagi fayllar foydalanuvchi ma'lumotlarini saqlaydi va
  `.gitignore` orqali repoga tushmaydi.
- Test va viktorina sessiyalari **xotirada** saqlanadi: bot qayta ishga
  tushsa, tugallanmagan test bekor bo'ladi.
