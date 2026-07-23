"""Admin panelning barcha bo'limlarini bitta routerga birlashtiradi."""

from aiogram import Router

from . import broadcast, channels, users

router = Router()
router.include_router(users.router)
router.include_router(channels.router)
router.include_router(broadcast.router)
