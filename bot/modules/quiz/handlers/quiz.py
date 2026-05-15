# bot/modules/quiz/handlers/quiz.py
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from bot.database.utils import (
    delete_user_and_progress, ensure_user, get_user_locations, get_location_info, 
    get_progress, create_progress, update_progress,
    get_next_question, check_answer, get_correct_text, get_explanation,
    get_location_name, get_location_total_q, add_to_user_total, is_quest_completed,
    get_answers_for_question
)
from ..states import QuizState
from ..keyboards.inline import build_quiz_kb, build_session_prompt_kb, build_main_menu_kb, build_back_to_menu_kb, build_back_to_menu_without_del_kb
import logging

router = Router()
logger = logging.getLogger(__name__)


def format_quiz_message(q_text: str, answers: list[tuple[int, str]], correct_text: str | None = None, wrong_text: str | None = None) -> str:
    """Форматирует вопрос + варианты. Подсвечивает правильный <b>жирным</b>, неверный <s>зачёркивает</s>."""
    lines = []
    for i, (_, text) in enumerate(answers, 1):
        prefix = f"{i}) "
        t_clean = text.strip()
        if t_clean == (correct_text or "").strip():
            lines.append(f"{prefix}<b>{text}</b>")
        elif t_clean == (wrong_text or "").strip():
            lines.append(f"{prefix}<s>{text}</s>")
        else:
            lines.append(f"{prefix}{text}")
    return f"📍 <b>Вопрос:</b>\n\n{q_text}\n\n🔹 <b>Варианты:</b>\n" + "\n".join(lines)

@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await ensure_user(user_id)

    parts = message.text.split(maxsplit=1)
    args = parts[1] if len(parts) > 1 else ""

    # 🔄 QR-код приоритетнее меню
    if args and args.isdigit():
        await _start_quiz(user_id, message, int(args), state)
        return

    if await state.get_state() == QuizState.active.state:
        await message.answer(
            "⏸ <b>У вас незаконченный тест!</b>\n\nПродолжить отвечать или вернуться в меню?",
            reply_markup=build_session_prompt_kb()
        )
        return

    locations = await get_user_locations(user_id)
    await message.answer(
        "🎓 <b>Квест «Наследие Мешкова»</b>\n\n"
        "🗺️ <b>Как играть:</b>\n"
        "1️⃣ Нажмите на локацию ниже — узнайте, где она находится.\n"
        "2️⃣ Найдите точку в кампусе и отсканируйте QR-код.\n"
        "3️⃣ Ответьте на вопросы и копите баллы!\n\n"
        "🏆 Пройдите все 5 точек — заберите приз! 🎁",
        reply_markup=build_main_menu_kb(locations)
    )

@router.callback_query(F.data.startswith("loc_info:"))
async def show_location_info(call: types.CallbackQuery):
    loc_id = int(call.data.split(":")[1])
    info = await get_location_info(loc_id)
    if info:
        await call.message.edit_text(
            f"📍 <b>{info['name']}</b>\n\n🗺️ {info['description']}\n\n📸 Найдите QR-код на этой точке и отсканируйте его для старта теста.",
            reply_markup=build_back_to_menu_kb()
        )
    await call.answer()

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(call: types.CallbackQuery):
    locations = await get_user_locations(call.from_user.id)
    await call.message.edit_text(
        "🎓 <b>Квест «Наследие Мешкова»</b>\n\n"
        "🗺️ <b>Как играть:</b>\n\n"
        "1️⃣ Нажмите на название локации в меню ниже — узнаете, где она находится\n"
        "2️⃣ Найдите эту точку в кампусе и отсканируйте QR-код на месте\n"
        "3️⃣ Ответьте на вопросы и получите баллы!\n\n"
        "🏆 Пройдите все 5 локаций — заберите приз в конце! 🎁",
        reply_markup=build_main_menu_kb(locations)
    )
    await call.answer()

@router.callback_query(F.data == "main_menu_without_delete")
async def back_to_main_menu(call: types.CallbackQuery):
    locations = await get_user_locations(call.from_user.id)
    await call.message.edit_reply_markup(None)
    await call.message.answer(
        "🎓 <b>Квест «Наследие Мешкова»</b>\n\n"
        "🗺️ <b>Как играть:</b>\n\n"
        "1️⃣ Нажмите на название локации в меню ниже — узнаете, где она находится\n"
        "2️⃣ Найдите эту точку в кампусе и отсканируйте QR-код на месте\n"
        "3️⃣ Ответьте на вопросы и получите баллы!\n\n"
        "🏆 Пройдите все 5 локаций — заберите приз в конце! 🎁",
        reply_markup=build_main_menu_kb(locations)
    )
    await call.answer()

@router.callback_query(F.data == "quiz_resume", QuizState.active)
async def resume_quiz(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await _start_quiz(call.from_user.id, call.message, data["loc_id"], state)
    await call.answer()

@router.callback_query(F.data == "quiz_cancel", QuizState.active)
async def cancel_quiz(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("✅ <i>Когда будете готовы, просто отсканируйте QR-код нужной локации, чтобы продолжить</i> 🔄", reply_markup=build_back_to_menu_kb())
    await call.answer()

async def _start_quiz(user_id: int, message: types.Message, loc_id: int, state: FSMContext):
    progress = await get_progress(user_id, loc_id)

    if progress and progress["status"] == "completed":
        await message.answer("✅ <b>Вы уже прошли этот этап!</b>\n\nТест для данной локации успешно завершён. Ищите следующую точку! 🗺️",
                             reply_markup=build_back_to_menu_kb())
        return

    # ID последнего ОТВЕЧЕННОГО вопроса
    last_answered_id = progress.get("last_question_id") if progress else 0

    q = await get_next_question(loc_id, last_answered_id)
    if not q:
        await message.answer("📦 <b>Вопросы не найдены.</b>\nВозможно, вы уже ответили на все вопросы или локация ещё не добавлена. 🔍")
        return

    # ⚠️ НЕ обновляем last_question_id в БД здесь! Это предотвратит "перескакивание".
    await state.set_state(QuizState.active)
    await state.update_data(loc_id=loc_id, correct_cnt=0, q_text=q['text'])

    if not progress:
        await create_progress(user_id, loc_id)

    answers = await get_answers_for_question(q["id"])
    await message.answer(
        format_quiz_message(q["text"], answers),
        reply_markup=build_quiz_kb(q["id"], answers)
    )
@router.callback_query(F.data.startswith("ans:"), QuizState.active)
async def handle_answer(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    _, q_id, a_id = call.data.split(":")
    q_id, a_id = int(q_id), int(a_id)

    data = await state.get_data()
    loc_id, cnt = data["loc_id"], data.get("correct_cnt", 0)

    # Получаем данные один раз
    answers_list = await get_answers_for_question(q_id)
    correct_txt = await get_correct_text(q_id)
    expl = await get_explanation(q_id)
    is_ok = await check_answer(q_id, a_id)

    # Находим текст, который выбрал пользователь
    selected_txt = next((t for aid, t in answers_list if aid == a_id), "")

    if is_ok:
        cnt += 1
        await state.update_data(correct_cnt=cnt)
        feedback = "\n\n✅ <b>Верно!</b>\n\nОтличная работа! Вы на правильном пути 🚀"
        # Подсвечиваем только правильный ответ
        formatted_msg = format_quiz_message(data.get("q_text", ""), answers_list, correct_text=correct_txt)
    else:
        feedback = f"\n\n❌ <b>Неверно</b>\n\n💡 <b>Правильный ответ:</b> {correct_txt}\n\n📖 <i>{expl or 'Пояснение отсутствует...'}</i>"
        # Правильный жирный, выбранный зачёркнут
        formatted_msg = format_quiz_message(data.get("q_text", ""), answers_list, correct_text=correct_txt, wrong_text=selected_txt)

    # Редактируем сообщение: форматируем текст + фидбек, убираем кнопки
    await call.message.edit_text(text=f"{formatted_msg}{feedback}")

    # Фиксируем прогресс только после ответа
    await update_progress(user_id, loc_id, last_question_id=q_id)

    next_q = await get_next_question(loc_id, q_id)
    if next_q:
        answers = await get_answers_for_question(next_q["id"])
        await call.message.answer(
            format_quiz_message(next_q["text"], answers),
            reply_markup=build_quiz_kb(next_q["id"], answers)
        )
    else:
        await update_progress(user_id, loc_id, status="completed")
        await add_to_user_total(user_id, cnt)
        await state.clear()

        loc_name = await get_location_name(loc_id)
        total = await get_location_total_q(loc_id)

        if await is_quest_completed(user_id):
            await call.message.answer(
                f"🎉 <b>Локация «{loc_name}» пройдена!</b>\n\n📊 <b>Ваш результат:</b> {cnt}/{total}"
            )
            total_correct = await add_to_user_total(user_id, 0, return_total=True)
            await call.message.answer(
                "🏆 <b>Поздравляем! Квест пройден!</b>\n\n"
                "✨ Вы завершили все этапы и раскрыли историю наследия Мешкова!\n\n"
                f"📈 <b>Ваш результат:</b> <b>{total_correct}</b> правильных ответов из <b>15</b>\n\n"
                "🎁 <b>Вечером определится победитель!</b>\n\n"
                "<i>Спасибо за участие! Ждём вас в новых квестах!</i> 🚀",
                reply_markup=build_back_to_menu_without_del_kb()
            )
        else:
            await call.message.answer(
                f"🎉 <b>Локация «{loc_name}» пройдена!</b>\n\n📊 <b>Ваш результат:</b> {cnt}/{total}\n\nПереходите к следующей точке, чтобы завершить квест! 🏃‍♂️",
                reply_markup=build_back_to_menu_without_del_kb()
            )

    await call.answer()
    
@router.message(Command("delete_me"))
async def cmd_delete_me(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    is_deleted = await delete_user_and_progress(user_id)
    
    await state.clear()
    
    if is_deleted:
        await message.answer(
            "🗑️ <b>Данные успешно удалены.</b>\n\n"
            "Ваш прогресс и статистика полностью сброшены. Для нового старта отправьте /start или отсканируйте QR-код. 🔄"
        )
    else:
        await message.answer(
            "⚠️ <b>Ошибка при удалении данных.</b>\n\n"
            "Попробуйте позже или обратитесь к администратору. 🛠️"
        )