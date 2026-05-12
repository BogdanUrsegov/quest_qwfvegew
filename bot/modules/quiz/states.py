# bot/modules/quiz/states.py
from aiogram.fsm.state import StatesGroup, State

class QuizState(StatesGroup):
    active = State()