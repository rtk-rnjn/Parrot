from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, PositiveInt, field_validator

from .user import User


class Upload(BaseModel):
    file: str
    type: Literal["user_avatar", "poll_cover", "poll_option", "theme_logo"]


class Pagination(BaseModel):
    page: PositiveInt
    limit: PositiveInt
    total: PositiveInt


class Media(BaseModel):
    id: str | None = None
    type: str | None = None
    source: str | None = None
    url: str | None = None
    width: int | None = None
    height: int | None = None
    created_at: int | None = None
    updated_at: int | None = None


class Workspace(BaseModel):
    id: str | None = None
    name: str | None = None
    member_count: int | None = None
    poll_count: int | None = None
    created_at: int | None = None
    updated_at: int | None = None


class PollOption(BaseModel):
    id: str | None = None
    type: Literal["text", "image", "date", "time_range"] | None = None
    position: int | None = None
    vote_count: int | None = None
    max_votes: int | None = None
    description: str | None = None
    is_write_in: bool | None = None


class TextPollOption(PollOption):
    value: str | None = None
    type: Literal["text"] | None = "text"


class ImagePollOption(TextPollOption):
    media: Media | None = None
    type: Literal["image"] | None = "image"


class DatePollOption(PollOption):
    date: str | None = None
    type: Literal["date"] | None = "date"

    @field_validator("date")
    def validate_date(cls, date: str) -> datetime.datetime | None:
        return datetime.datetime.strptime(date, "%Y-%m-%d") if date else None


class TimeRangePollOption(PollOption):
    type: Literal["time_range"] | None = "time_range"
    start_time: int | None = None
    end_time: int | None = None


class PollConfig(BaseModel):
    is_private: bool | None = None
    vote_type: Literal["default", "box_small", "participant_grid"] | None = None
    allow_comments: bool | None = False
    allow_indeterminate: bool | None = False
    allow_other_option: bool | None = False
    custom_design_colors: str | None = "{}"
    deadline_at: int | None = None
    duplication_checking: Literal["ip", "session", "invite", "none"] | None = "none"
    allow_vpn_users: bool | None = False
    edit_vote_permissions: Literal["admin", "admin_voter", "voter", "nobody"] | None = "admin"
    force_appearance: Literal["auto", "dark", "light"] | None
    hide_participants: bool | None = False
    is_multiple_choice: bool | None = True
    multiple_choice_min: int | None = 1
    multiple_choice_max: int | None = 1
    number_of_winners: int | None = 1
    randomize_options: bool | None = False
    require_voter_names: bool | None = False
    results_visibility: Literal["always", "after_deadline", "after_vote", "never"] | None = "always"
    use_custom_design: bool | None = False


class PollMeta(BaseModel):
    description: str | None = None
    location: str | None = None
    vote_count: int | None = None
    participant_count: int | None = None
    view_count: int | None = None
    comment_count: int | None = None
    creator_country: str | None = None
    pin_code_expired_at: int | None = None
    last_vote_at: int | None = None
    timezone: str | None = None


PollOptions = TextPollOption | ImagePollOption | DatePollOption | TimeRangePollOption


class Poll(BaseModel):
    id: str | None = None
    title: str | None
    user: User | None = None
    media: Media | None = None
    workspace: Workspace | None = None
    poll_options: list[PollOptions]
    poll_config: PollConfig | None = None
    poll_meta: PollMeta | None = None
    type: Literal["multiple_choice", "image_poll", "meeting", "ranked_choice"] | None
    version: str | None = None
    updated_at: int | None = None
    reset_at: int | None = None


class PollParticipants(BaseModel):
    id: str | None = None
    name: str | None = None
    country_code: str | None = None
    is_edit_allowed: bool | None = None
    poll_votes: list[Literal[1] | Literal[0] | None] = []
    created_at: int | None = None


class PollResults(BaseModel):
    id: str | None = None
    version: str | None = None
    voteCount: int | None = None
    participantCount: int | None = None
    resultsKey: str | None = None
    poll_options: list[PollOptions]
    poll_participants: list[PollParticipants] = []
