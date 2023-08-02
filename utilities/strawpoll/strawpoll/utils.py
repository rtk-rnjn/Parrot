from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel


def flat_model_to_dict(model: BaseModel):
    data = {}
    for k, v in model:
        if not v:
            continue
        elif isinstance(v, BaseModel):
            data[k] = flat_model_to_dict(v)
        elif isinstance(v, list):
            data[k] = [flat_model_to_dict(i) for i in v]
        else:
            data[k] = v
    return data


def datetime_from_timestamp(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
