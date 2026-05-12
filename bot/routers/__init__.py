from aiogram import Router
# from bot.modules.start import router as start_router
from bot.modules.quiz import router as quiz_router


router = Router()
router.include_routers(
                       quiz_router
                    )


__all__ = ["router"]