from aiogram import BaseMiddleware, Bot
from aiogram.types import Update, Message, CallbackQuery
from aiogram.exceptions import TelegramAPIError
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

class ChannelLoggerMiddleware(BaseMiddleware):
    """Миддлварь для логирования действий в телеграм канал и ошибок"""
    
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        super().__init__()
    
    async def __call__(self, handler, event: Update, data: dict):
        bot: Bot = data['bot']
        
        try:
            # Логируем действие пользователя
            await self._log_action(event, bot)
            
            # Выполняем хендлер
            return await handler(event, data)
            
        except Exception as e:
            # Логируем ошибку
            await self._log_error(event, bot, e)
            raise
    
    async def _log_action(self, event: Update, bot: Bot):
        try:
            # Проверяем, есть ли пользователь в апдейте
            user = None
            if event.message and event.message.from_user:
                user = event.message.from_user
            elif event.callback_query and event.callback_query.from_user:
                user = event.callback_query.from_user
            elif event.my_chat_member and event.my_chat_member.from_user:
                user = event.my_chat_member.from_user

            if not user:
                return  # Пропускаем логирование, если нет пользователя

            action_text = ""
            if event.message:
                action_text = f"💬 {event.message.text or '[без текста]'}"
            elif event.callback_query:
                action_text = f"🔘 {event.callback_query.data}"

            log_message = (
                f"👤 <b>Пользователь:</b> {user.full_name} (@{user.username or '—'})\n"
                f"🆔 <b>ID:</b> {user.id}\n"
                f"📅 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                f"📝 <b>Действие:</b> {action_text}"
            )

            await bot.send_message(
                chat_id=self.channel_id,
                text=log_message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка логирования действия: {e}")
    
    async def _log_error(self, event: Update, bot: Bot, error: Exception):
        """Логирование ошибок с понятным сообщением"""
        try:
            user = event.from_user
            error_type = type(error).__name__
            error_message = str(error)
            
            # Формируем понятное сообщение об ошибке
            log_message = (
                f"❌ <b>Ошибка в боте</b>\n\n"
                f"👤 <b>Пользователь:</b> {user.full_name} (@{user.username})\n"
                f"🆔 <b>ID:</b> {user.id}\n"
                f"📅 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"⚠️ <b>Тип ошибки:</b> {error_type}\n"
                f"📝 <b>Сообщение:</b> {error_message}\n\n"
                f"📍 <b>Место:</b>\n"
                f"<code>{traceback.format_exc()[-500:]}</code>"
            )
            
            await bot.send_message(
                chat_id=self.channel_id,
                text=log_message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Ошибка логирования ошибки: {e}")


# Декоратор для красивого вывода ошибок пользователю
def error_handler(func):
    """Декоратор для обработки ошибок с понятным сообщением"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            
            user_message = (
                f"⚠️ <b>Произошла ошибка</b>\n\n"
                f"😔 Извините, произошла непредвиденная ошибка.\n"
                f"🔧 <b>Тип:</b> {error_type}\n"
                f"📝 <b>Описание:</b> {error_message}\n\n"
                f"💬 Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
            
            # Отправляем пользователю понятное сообщение
            from aiogram.types import Message, CallbackQuery
            event = args[0] if args else None
            
            if isinstance(event, Message):
                await event.answer(user_message, parse_mode='HTML')
            elif isinstance(event, CallbackQuery):
                await event.message.answer(user_message, parse_mode='HTML')
            
            # Логируем ошибку
            logger.error(f"Ошибка в {func.__name__}: {e}", exc_info=True)
            raise
    
    return wrapper