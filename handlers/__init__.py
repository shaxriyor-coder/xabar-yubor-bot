"""Botning barcha handlerlarini bitta routerga birlashtiradi."""

from aiogram import Router

from . import admin, common, login, messaging, premium

router = Router()
router.include_router(common.router)
router.include_router(premium.router)
router.include_router(login.router)
router.include_router(messaging.router)
router.include_router(admin.router)
