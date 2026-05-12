# bot/modules/quiz/keyboards/inline.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def build_quiz_kb(question_id: int, answers: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру с вариантами ответа. Ожидает [(id, text), ...]"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=f"ans:{question_id}:{ans_id}")]
        for ans_id, text in answers
    ])

def build_session_prompt_kb() -> InlineKeyboardMarkup:
    """Клавиатура для возобновления или отмены активной сессии."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="▶️ Продолжить", callback_data="quiz_resume")],
        [InlineKeyboardButton(text="🔙 В меню", callback_data="quiz_cancel")]
    ])

def build_main_menu_kb(locations: list[dict]) -> InlineKeyboardMarkup:
    """
    Динамическое меню локаций с индикатором прогресса.
    locations: [{"id": int, "name": str, "status": "new"|"in_progress"|"completed"}]
    """
    rows = []
    for loc in locations:
        icon = "✅" if loc["status"] == "completed" else "🔘"
        rows.append([InlineKeyboardButton(
            text=f"{icon} {loc['name']}",
            callback_data=f"start_loc:{loc['id']}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_main_menu_kb(locations: list[dict]) -> InlineKeyboardMarkup:
    emoji_map = {"new": "🔵", "in_progress": "🕔", "completed": "✅"}
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for loc in locations:
        icon = emoji_map.get(loc.get("status", "new"), "🔵")
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"{icon} {loc['name']}", callback_data=f"loc_info:{loc['id']}")
        ])
    return kb

def build_back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")]
    ])

def build_back_to_menu_without_del_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu_without_delete")]
    ])