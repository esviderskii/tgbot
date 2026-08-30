"""Telegram command and callback handlers."""

from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router, html
from aiogram.filters import Command, CommandStart
from aiogram.filters import Filter
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from . import config
from .db import db
from .timeparser import parse_reminder

log = logging.getLogger(__name__)
router = Router()


class OwnerOnly(Filter):
    def __init__(self, owner_id: int | None) -> None:
        self.owner_id = owner_id

    async def __call__(self, obj) -> bool:
        if self.owner_id is None:
            return True
        user_id = getattr(obj, "from_user", None)
        return bool(user_id) and user_id.id == self.owner_id


def _fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return ""
    local = dt.astimezone(config.TZ)
    today = datetime.now(config.TZ).date()
    if local.date() == today:
        day = "сегодня"
    elif (local.date() - today).days == 1:
        day = "завтра"
    else:
        day = local.strftime("%d.%m")
    return f"{day} {local.strftime('%H:%M')}"


def _fmt_repeat(interval_minutes: int | None, repeat_tod: tuple[int, int] | None) -> str:
    if interval_minutes is None:
        return ""
    day_part = ""
    if repeat_tod is not None:
        day_part = f" в {repeat_tod[0]:02d}:{repeat_tod[1]:02d}"
        if interval_minutes == 1440:
            return f"ежедневно{day_part}"
        if interval_minutes == 10080:
            return f"еженедельно{day_part}"
    if interval_minutes == 60:
        return f"каждый час{day_part}"
    if interval_minutes == 1440:
        return f"ежедневно{day_part}"
    if interval_minutes == 10080:
        return f"еженедельно{day_part}"
    if interval_minutes % 1440 == 0:
        return f"каждые {interval_minutes // 1440} дн.{day_part}"
    if interval_minutes % 60 == 0:
        return f"каждые {interval_minutes // 60} ч."
    return f"каждые {interval_minutes} мин."


@router.message(CommandStart())
async def on_start(message: Message) -> None:
    await message.answer(
        "Привет! 📝 Я твой бот для заметок.\n\n"
        "Команды:\n"
        "/add <текст> — создать заметку (можно добавить напоминание: "
        "«купить хлеб завтра в 9:00», «позвонить через 30 минут»)\n"
        "Повтор: «каждый день в 9:00», «каждые 3 дня»\n"
        "/list — показать все заметки\n"
        "/delete — удалить заметку"
    )


@router.message(Command("add", "new"))
async def on_add(message: Message) -> None:
    args = message.text.split(maxsplit=1)[1].strip() if message.text and " " in message.text else ""
    if not args:
        await message.answer("Дай текст заметки: /add <текст>")
        return

    remind = parse_reminder(args, config.TZ)
    repeat_tod_min = (
        remind.repeat_tod[0] * 60 + remind.repeat_tod[1]
        if remind.repeat_tod is not None
        else None
    )
    note_id = await db.add_note(
        remind.text if remind.text else args,
        remind.remind_at,
        remind.interval_minutes,
        repeat_tod_min,
    )

    body = remind.text if remind.text else args
    reply = f"✅ Заметка добавлена (#{note_id}):\n{html.quote(body)}"
    if remind.is_recurring:
        repeat = _fmt_repeat(remind.interval_minutes, remind.repeat_tod)
        reply += f"\n\n🔁 Повтор: {repeat} (первый: {_fmt_dt(remind.remind_at)})"
    elif remind.remind_at:
        reply += f"\n\n⏰ Напомню: {_fmt_dt(remind.remind_at)}"
    await message.answer(reply)


@router.message(Command("list"))
async def on_list(message: Message) -> None:
    notes = await db.list_notes()
    if not notes:
        await message.answer("Заметок пока нет. Добавь первую через /add.")
        return

    lines = []
    for i, n in enumerate(notes, start=1):
        line = f"{i}. {html.quote(n['text'])}"
        if n["remind_at"]:
            if n["repeat_interval_minutes"]:
                rep = _fmt_repeat(
                    n["repeat_interval_minutes"],
                    ((n["repeat_tod"] // 60, n["repeat_tod"] % 60)
                     if n["repeat_tod"] is not None else None),
                )
                line += f"  [🔁 {rep}]"
            else:
                marker = "✓⏰" if n["reminder_sent"] else "⏰"
                line += f"  [{marker} {_fmt_dt(n['remind_at'])}]"
        lines.append(line)

    await message.answer("📋 Заметки:\n" + "\n".join(lines))


@router.message(Command("delete", "del"))
async def on_delete(message: Message) -> None:
    notes = await db.list_notes()
    if not notes:
        await message.answer("Удалять нечего — заметок нет.")
        return

    buttons = [
        [InlineKeyboardButton(
            text=f"{i}. {n['text'][:30]}",
            callback_data=f"del:{n['id']}",
        )]
        for i, n in enumerate(notes, start=1)
    ]
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="delno")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("Выбери заметку для удаления:", reply_markup=kb)


@router.callback_query(F.data.startswith("del:"))
async def on_del_pick(query: CallbackQuery) -> None:
    note_id = int(query.data.split(":", 1)[1])
    note = await db.get_note(note_id)
    if note is None:
        await query.message.edit_text("Заметки уже нет.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Да, удалить", callback_data=f"confirm:{note_id}"),
         InlineKeyboardButton(text="Нет", callback_data="delno")],
    ])
    await query.message.edit_text(
        f"Точно удалить?\n{html.quote(note['text'][:200])}",
        reply_markup=kb,
    )
    await query.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def on_del_confirm(query: CallbackQuery) -> None:
    note_id = int(query.data.split(":", 1)[1])
    await db.delete_note(note_id)
    await query.message.edit_text(f"🗑 Заметка #{note_id} удалена.")
    await query.answer()


@router.callback_query(F.data == "delno")
async def on_del_cancel(query: CallbackQuery) -> None:
    try:
        await query.message.delete()
    except Exception:  # noqa: BLE001
        await query.message.edit_text("Отменено.")
    await query.answer("Отменено")