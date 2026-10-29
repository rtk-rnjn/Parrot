from __future__ import annotations

from fastapi import APIRouter

from .auth import router as auth_router
from .info import router as info_router
from .me import router as me_router
from .ping import router as ping_router

router = APIRouter(prefix="/v1")

router.include_router(auth_router, tags=["auth"])
router.include_router(info_router, tags=["info"])
router.include_router(me_router, tags=["me"])
router.include_router(ping_router, tags=["ping"])
