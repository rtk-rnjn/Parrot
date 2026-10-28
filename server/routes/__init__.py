from fastapi import APIRouter

from .api import router as api_router
from .site import router as site_router

router = APIRouter()
router.include_router(site_router, tags=["site"])
router.include_router(api_router, tags=["api"])
