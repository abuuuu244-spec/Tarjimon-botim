"""
JSON asosidagi ma'lumotlar ombori.

Ilgari bot ma'lumotlarni SQLite (bot.db) da saqlardi. Endi hamma narsa
oddiy JSON fayllarda turadi:

    data/users.json    — foydalanuvchilar va ularning sozlamalari
    data/history.json  — har bir foydalanuvchining tarjimalar tarixi

Nima uchun JSON:
  • hech qanday tashqi baza/drayver kerak emas;
  • faylni ochib, ko'z bilan o'qish va tahrirlash mumkin;
  • zaxira nusxa olish = faylni ko'chirish.

Yozuv xavfsizligi:
  • har bir yozish avval vaqtinchalik faylga tushadi, keyin os.replace()
    orqali almashtiriladi — ya'ni yozish o'rtasida bot to'xtasa ham
    fayl buzilmaydi;
  • barcha o'zgarishlar threading.RLock bilan himoyalangan, chunki
    funksiyalar asyncio.to_thread ichidan ham chaqirilishi mumkin.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("TarjimonBot.storage")


# ============================================================
# KONFIGURATSIYA
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.getenv("DATA_DIR") or (BASE_DIR / "data"))

USERS_FILE = DATA_DIR / "users.json"
HISTORY_FILE = DATA_DIR / "history.json"

# Bitta foydalanuvchi uchun saqlanadigan maksimal tarix yozuvlari soni.
# Bu chegara fayl cheksiz o'sib ketmasligi uchun kerak.
MAX_HISTORY_PER_USER = int(os.getenv("MAX_HISTORY_PER_USER") or 200)

# Tarixda saqlanadigan matn uzunligi chegarasi.
MAX_TEXT_LENGTH = 500

DEFAULT_LANG = "auto"

# O'zgarishlar necha soniyada bir diskka yoziladi.
# 0 => har bir o'zgarish darhol yoziladi (sekinroq, lekin eng xavfsiz).
AUTOSAVE_INTERVAL = float(os.getenv("AUTOSAVE_INTERVAL") or 5)


# ============================================================
# XOTIRADAGI KESH
# ============================================================

_lock = threading.RLock()

_users: dict[str, dict[str, Any]] = {}
_history: dict[str, list[dict[str, Any]]] = {}
_initialized = False

# Qaysi fayllar o'zgargan va hali diskka yozilmagan
_dirty: set[str] = set()


# ============================================================
# QUYI DARAJADAGI FAYL AMALLARI
# ============================================================

def _now() -> str:
    return datetime.now().isoformat()


def _read_json(path: Path, default: Any) -> Any:
    """JSON faylni o'qiydi. Fayl buzilgan bo'lsa zaxira qilib, bo'sh boshlaydi."""
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        broken = path.with_suffix(path.suffix + ".broken")
        logger.error(
            "%s fayli buzilgan (%s). %s nomi bilan saqlab, yangidan boshlanmoqda.",
            path.name, error, broken.name
        )
        try:
            shutil.copy2(path, broken)
        except OSError:
            pass
        return default
    except OSError as error:
        logger.error("%s faylini o'qib bo'lmadi: %s", path.name, error)
        return default

    if not isinstance(data, type(default)):
        logger.error("%s fayli kutilmagan formatda, e'tiborsiz qoldirildi.", path.name)
        return default

    return data


def _write_json(path: Path, data: Any) -> None:
    """Faylni atomik tarzda yozadi (avval .tmp, keyin os.replace)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )

    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())

        os.replace(tmp_name, path)
    except OSError as error:
        logger.error("%s fayliga yozib bo'lmadi: %s", path.name, error)
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


def _save_users() -> None:
    """Foydalanuvchilar o'zgardi deb belgilaydi (yoki darhol yozadi)."""
    _mark_dirty("users")


def _save_history() -> None:
    """Tarix o'zgardi deb belgilaydi (yoki darhol yozadi)."""
    _mark_dirty("history")


def _mark_dirty(what: str) -> None:
    """
    O'zgarishni ro'yxatga oladi.

    AUTOSAVE_INTERVAL > 0 bo'lsa, fayl darhol emas, fonda ishlaydigan
    autosave sikli orqali yoziladi — shunda har bir xabarda butun JSON
    qayta yozilmaydi. Aks holda darhol yoziladi.
    """
    with _lock:
        _dirty.add(what)

        if AUTOSAVE_INTERVAL <= 0:
            flush()


def flush() -> bool:
    """
    Kutayotgan o'zgarishlarni diskka yozadi.

    Returns:
        Biror narsa yozilgan bo'lsa True.
    """
    with _lock:
        if not _dirty:
            return False

        if "users" in _dirty:
            _write_json(USERS_FILE, _users)
        if "history" in _dirty:
            _write_json(HISTORY_FILE, _history)

        _dirty.clear()
        return True


async def autosave_loop(interval: float | None = None) -> None:
    """
    Fonda ishlaydigan avtosaqlash sikli.

    Bot ishga tushganda asyncio.create_task() bilan ishga tushiriladi va
    bekor qilinganda (bot to'xtaganda) oxirgi marta saqlab qo'yadi.
    """
    period = AUTOSAVE_INTERVAL if interval is None else interval

    if period <= 0:
        return

    try:
        while True:
            await asyncio.sleep(period)
            if await asyncio.to_thread(flush):
                logger.debug("💾 Ma'lumotlar saqlandi.")
    except asyncio.CancelledError:
        flush()
        raise


def _key(user_id: int) -> str:
    """JSON kalitlari faqat matn bo'lishi mumkin, shuning uchun str() qilamiz."""
    return str(user_id)


# ============================================================
# INITSIALIZATSIYA
# ============================================================

def init_storage() -> None:
    """Ma'lumotlarni fayldan xotiraga yuklaydi. Bot ishga tushganda bir marta chaqiriladi."""
    global _initialized

    with _lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        _users.clear()
        _users.update(_read_json(USERS_FILE, {}))

        _history.clear()
        _history.update(_read_json(HISTORY_FILE, {}))

        _dirty.clear()

        # Fayllar hali mavjud bo'lmasa, darhol yaratib qo'yamiz.
        if not USERS_FILE.exists():
            _dirty.add("users")
        if not HISTORY_FILE.exists():
            _dirty.add("history")
        flush()

        _initialized = True

        logger.info(
            "💾 JSON ombor tayyor: %d foydalanuvchi, %d tarix yozuvi (%s) | autosave: %s",
            len(_users),
            sum(len(items) for items in _history.values()),
            DATA_DIR,
            f"{AUTOSAVE_INTERVAL:g}s" if AUTOSAVE_INTERVAL > 0 else "darhol",
        )


def _ensure_initialized() -> None:
    if not _initialized:
        init_storage()


# ============================================================
# FOYDALANUVCHILAR
# ============================================================

def register_user(user_id: int, username: str, full_name: str) -> dict[str, Any]:
    """
    Foydalanuvchini ro'yxatga oladi.

    Agar foydalanuvchi allaqachon bor bo'lsa, username/full_name o'zgargan
    bo'lsa yangilaydi (Telegramda ism va username o'zgarishi mumkin).
    """
    _ensure_initialized()

    key = _key(user_id)
    username = (username or "").strip()
    full_name = (full_name or "").strip()

    with _lock:
        user = _users.get(key)

        if user is None:
            _users[key] = {
                "user_id": user_id,
                "username": username,
                "full_name": full_name,
                "searches": 0,
                "target_lang": DEFAULT_LANG,
                "created_at": _now(),
                "updated_at": _now(),
            }
            _save_users()
            logger.info("🆕 Yangi foydalanuvchi: %s (%s)", full_name or user_id, user_id)
            return _users[key]

        if user.get("username") != username or user.get("full_name") != full_name:
            user["username"] = username
            user["full_name"] = full_name
            user["updated_at"] = _now()
            _save_users()

        return user


def _get_or_create(user_id: int) -> dict[str, Any]:
    """Ichki yordamchi: yozuvni topadi, bo'lmasa bo'sh yozuv yaratadi."""
    key = _key(user_id)
    user = _users.get(key)

    if user is None:
        user = {
            "user_id": user_id,
            "username": "",
            "full_name": "",
            "searches": 0,
            "target_lang": DEFAULT_LANG,
            "created_at": _now(),
            "updated_at": _now(),
        }
        _users[key] = user

    return user


def set_user_lang(user_id: int, lang: str) -> None:
    """Foydalanuvchining tarjima maqsad tilini saqlaydi."""
    _ensure_initialized()

    with _lock:
        user = _get_or_create(user_id)
        user["target_lang"] = lang or DEFAULT_LANG
        user["updated_at"] = _now()
        _save_users()


def get_user_lang(user_id: int) -> str:
    """Foydalanuvchining maqsad tilini qaytaradi ('auto' — avtomatik rejim)."""
    _ensure_initialized()

    with _lock:
        user = _users.get(_key(user_id))
        if not user:
            return DEFAULT_LANG
        return user.get("target_lang") or DEFAULT_LANG


def increment_search(user_id: int) -> None:
    """Qidiruvlar hisoblagichini bittaga oshiradi."""
    _ensure_initialized()

    with _lock:
        user = _get_or_create(user_id)
        user["searches"] = int(user.get("searches") or 0) + 1
        user["updated_at"] = _now()
        _save_users()


def get_user_stats(user_id: int) -> tuple[int, int]:
    """(qidiruvlar soni, tarixdagi yozuvlar soni) juftligini qaytaradi."""
    _ensure_initialized()

    with _lock:
        user = _users.get(_key(user_id)) or {}
        searches = int(user.get("searches") or 0)
        history_count = len(_history.get(_key(user_id), []))
        return searches, history_count


def get_user(user_id: int) -> dict[str, Any] | None:
    """Foydalanuvchining to'liq yozuvini (nusxasini) qaytaradi."""
    _ensure_initialized()

    with _lock:
        user = _users.get(_key(user_id))
        return dict(user) if user else None


def count_users() -> int:
    """Botdagi jami foydalanuvchilar soni."""
    _ensure_initialized()

    with _lock:
        return len(_users)


# ============================================================
# TARIX
# ============================================================

def save_history(user_id: int, text: str, result: str) -> None:
    """Tarjima yozuvini tarixga qo'shadi (eng eskilari avtomatik o'chiriladi)."""
    _ensure_initialized()

    text = (text or "").strip()[:MAX_TEXT_LENGTH]
    result = (result or "").strip()[:MAX_TEXT_LENGTH]

    if not text:
        return

    key = _key(user_id)

    with _lock:
        items = _history.setdefault(key, [])
        items.append({
            "text": text,
            "result": result,
            "created_at": _now(),
        })

        if len(items) > MAX_HISTORY_PER_USER:
            del items[:len(items) - MAX_HISTORY_PER_USER]

        _save_history()


def get_history(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Oxirgi `limit` ta tarix yozuvini yangisidan eskisiga qarab qaytaradi."""
    _ensure_initialized()

    with _lock:
        items = _history.get(_key(user_id), [])
        if not items:
            return []
        selected = items[-limit:] if limit > 0 else list(items)
        return [dict(item) for item in reversed(selected)]


def clear_history(user_id: int) -> int:
    """Foydalanuvchi tarixini tozalaydi va o'chirilgan yozuvlar sonini qaytaradi."""
    _ensure_initialized()

    key = _key(user_id)

    with _lock:
        removed = len(_history.pop(key, []))
        if removed:
            _save_history()
        return removed


# ============================================================
# ZAXIRA NUSXA
# ============================================================

def backup(directory: str | Path | None = None) -> Path:
    """Joriy JSON fayllarning zaxira nusxasini yaratadi va papkani qaytaradi."""
    _ensure_initialized()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = Path(directory) if directory else (DATA_DIR / "backups" / stamp)
    target.mkdir(parents=True, exist_ok=True)

    with _lock:
        _write_json(target / USERS_FILE.name, _users)
        _write_json(target / HISTORY_FILE.name, _history)

    logger.info("🗂 Zaxira nusxa yaratildi: %s", target)
    return target
