# bot/database/utils/__init__.py
import logging
from sqlalchemy import select, update, func, delete
from bot.database.session import AsyncSessionLocal
from bot.database.models import User, Location, Question, Answer, UserLocationProgress

logger = logging.getLogger(__name__)

async def ensure_user(telegram_id: int) -> None:
    async with AsyncSessionLocal() as session:
        exists = await session.execute(select(User.id).where(User.telegram_id == telegram_id))
        if not exists.scalar_one_or_none():
            session.add(User(telegram_id=telegram_id, total_correct=0))
            await session.commit()

async def get_progress(user_id: int, loc_id: int) -> dict | None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(UserLocationProgress).where(
            UserLocationProgress.user_telegram_id == user_id,
            UserLocationProgress.location_id == loc_id
        ))
        p = res.scalar_one_or_none()
        return {"status": p.status, "last_question_id": p.last_question_id, "correct_count": p.correct_count} if p else None

async def create_progress(user_id: int, loc_id: int) -> None:
    async with AsyncSessionLocal() as session:
        session.add(UserLocationProgress(user_telegram_id=user_id, location_id=loc_id, status="in_progress"))
        await session.commit()

async def update_progress(user_id: int, loc_id: int, status: str = None, last_question_id: int = None, correct_count: int = None) -> None:
    values = {k: v for k, v in {"status": status, "last_question_id": last_question_id, "correct_count": correct_count}.items() if v is not None}
    if not values: return
    async with AsyncSessionLocal() as session:
        await session.execute(update(UserLocationProgress).where(
            UserLocationProgress.user_telegram_id == user_id,
            UserLocationProgress.location_id == loc_id
        ).values(**values))
        await session.commit()

async def get_next_question(loc_id: int, last_q_id: int) -> dict | None:
    q_id = last_q_id or 0
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Question).where(
            Question.location_id == loc_id,
            Question.id > q_id
        ).order_by(Question.id).limit(1))
        q = res.scalar_one_or_none()
        return {"id": q.id, "text": q.text} if q else None

async def check_answer(q_id: int, a_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Answer.is_correct).where(Answer.id == a_id, Answer.question_id == q_id))
        return bool(res.scalar_one_or_none())

async def get_correct_text(q_id: int) -> str:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Answer.text).where(Answer.question_id == q_id, Answer.is_correct == True).limit(1))
        return res.scalar_one() or ""

async def get_explanation(q_id: int) -> str | None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Question.explanation).where(Question.id == q_id))
        return res.scalar_one_or_none()

async def get_location_name(loc_id: int) -> str:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Location.name).where(Location.id == loc_id))
        return res.scalar_one() or "Локация"

async def get_location_total_q(loc_id: int) -> int:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(func.count(Question.id)).where(Question.location_id == loc_id))
        return res.scalar_one() or 0

async def add_to_user_total(user_id: int, count: int = 0, return_total: bool = False) -> int | None:
    async with AsyncSessionLocal() as session:
        if count > 0:
            await session.execute(update(User).where(User.telegram_id == user_id).values(total_correct=User.total_correct + count))
            await session.commit()
        if return_total:
            res = await session.execute(select(User.total_correct).where(User.telegram_id == user_id))
            return res.scalar_one() or 0
        return None

async def is_quest_completed(user_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        total = (await session.execute(select(func.count(Location.id)))).scalar_one()
        done = (await session.execute(select(func.count(UserLocationProgress.user_telegram_id)).where(
            UserLocationProgress.user_telegram_id == user_id,
            UserLocationProgress.status == "completed"
        ))).scalar_one()
        return done == total

async def get_answers_for_question(q_id: int) -> list[tuple[int, str]]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Answer.id, Answer.text).where(Answer.question_id == q_id))
        return [(row.id, row.text) for row in res.mappings().all()]
    
async def get_user_locations(user_id: int) -> list[dict]:
    async with AsyncSessionLocal() as s:
        res = await s.execute(
            select(Location.id, Location.name, UserLocationProgress.status)
            .outerjoin(UserLocationProgress, 
                       (Location.id == UserLocationProgress.location_id) & 
                       (UserLocationProgress.user_telegram_id == user_id))
        )
        return [{"id": r.id, "name": r.name, "status": r.status or "new"} for r in res.mappings()]

async def get_location_info(loc_id: int) -> dict | None:
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(Location.name, Location.description).where(Location.id == loc_id))
        row = res.mappings().first()
        return dict(row) if row else None
    
async def delete_user_and_progress(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        try:
            # 1. Удаляем прогресс (связанные записи)
            await session.execute(
                delete(UserLocationProgress).where(UserLocationProgress.user_telegram_id == telegram_id)
            )
            # 2. Удаляем пользователя
            await session.execute(
                delete(User).where(User.telegram_id == telegram_id)
            )
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка удаления пользователя {telegram_id}: {e}")
            return False