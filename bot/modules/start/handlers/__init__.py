from .command import router as command_router
from aiogram import Router


router = Router()
router.include_router(command_router)


__all__ = ["router"]