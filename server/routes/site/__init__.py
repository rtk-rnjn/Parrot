from fastapi import APIRouter

from .root import root_router

router = APIRouter()

router.include_router(root_router, tags=["root"])
