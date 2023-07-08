from __future__ import annotations

from typing import List, Literal, Optional, Type, Union

from .base_model import BaseModel
from .media import Media
from .user import User
from .workspace import Workspace


class PollMeta(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def description(self) -> Optional[str]:
        return self._raw.get("description")

    @description.setter
    def description(self, value: str):
        self._raw["description"] = value

    @property
    def location(self) -> Optional[str]:
        return self._raw.get("location")

    @location.setter
    def location(self, value: str):
        self._raw["location"] = value

    @property
    def vote_count(self) -> Optional[int]:
        return self._raw.get("vote_count")

    @property
    def participant_count(self) -> Optional[int]:
        return self._raw.get("participant_count")

    @property
    def comment_count(self) -> Optional[int]:
        return self._raw.get("comment_count")

    @property
    def view_count(self) -> Optional[int]:
        return self._raw.get("view_count")

    @property
    def creator_country(self) -> Optional[str]:
        return self._raw.get("creator_country")

    @property
    def pin_code_expired_at(self) -> Optional[int]:
        return self._raw.get("pin_code_expired_at")

    @property
    def last_vote_at(self) -> Optional[int]:
        return self._raw.get("last_vote_at")

    @property
    def timezone(self) -> Optional[str]:
        return self._raw.get("timezone")

    @timezone.setter
    def timezone(self, value: str):
        self._raw["timezone"] = value


class PollConfig(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def is_private(self) -> Optional[bool]:
        return self._raw.get("is_private")

    @is_private.setter
    def is_private(self, value: bool):
        self._raw["is_private"] = value

    @property
    def vote_type(self) -> Literal["default", "box_small", "participant_grid"]:
        return self._raw["vote_type"]

    @vote_type.setter
    def vote_type(self, value: Literal["default", "box_small", "participant_grid"]):
        self._raw["vote_type"] = value

    @property
    def allow_comments(self) -> Optional[bool]:
        return self._raw.get("allow_comments")

    @allow_comments.setter
    def allow_comments(self, value: bool):
        self._raw["allow_comments"] = value

    @property
    def allow_indeterminate(self) -> Optional[bool]:
        return self._raw.get("allow_indeterminate")

    @allow_indeterminate.setter
    def allow_indeterminate(self, value: bool):
        self._raw["allow_indeterminate"] = value

    @property
    def allow_other_options(self) -> Optional[bool]:
        return self._raw.get("allow_other_options")

    @allow_other_options.setter
    def allow_other_options(self, value: bool):
        self._raw["allow_other_options"] = value

    @property
    def custom_design_colors(self) -> Optional[str]:
        return self._raw.get("custom_design_colors")

    @custom_design_colors.setter
    def custom_design_colors(self, value: str):
        self._raw["custom_design_colors"] = value

    @property
    def deadline_at(self) -> Optional[int]:
        return self._raw.get("deadline_at")

    @deadline_at.setter
    def deadline_at(self, value: int):
        self._raw["deadline_at"] = value

    @property
    def duplication_checking(self) -> Literal["ip", "session", "invite", "none"]:
        return self._raw["duplication_checking"]

    @duplication_checking.setter
    def duplication_checking(self, value: Literal["ip", "session", "invite", "none"]):
        self._raw["duplication_checking"] = value

    @property
    def allow_vpn_users(self) -> Optional[bool]:
        return self._raw.get("allow_vpn_users")

    @allow_vpn_users.setter
    def allow_vpn_users(self, value: bool):
        self._raw["allow_vpn_users"] = value

    @property
    def edit_vote_permissions(self) -> Literal["admin", "admin_voter", "voter", "nobody"]:
        return self._raw["edit_vote_permissions"]

    @edit_vote_permissions.setter
    def edit_vote_permissions(self, value: Literal["admin", "admin_voter", "voter", "nobody"]):
        self._raw["edit_vote_permissions"] = value

    @property
    def force_appearance(self) -> Literal["auto", "dark", "light"]:
        return self._raw["force_appearance"]

    @force_appearance.setter
    def force_appearance(self, value: Literal["auto", "dark", "light"]):
        self._raw["force_appearance"] = value

    @property
    def hide_participants(self) -> Optional[bool]:
        return self._raw.get("hide_participants")

    @hide_participants.setter
    def hide_participants(self, value: bool):
        self._raw["hide_participants"] = value

    @property
    def is_multiple_choice(self) -> Optional[bool]:
        return self._raw.get("is_multiple_choice")

    @is_multiple_choice.setter
    def is_multiple_choice(self, value: bool):
        self._raw["is_multiple_choice"] = value

    @property
    def multiple_choice_min(self) -> Optional[int]:
        return self._raw.get("multiple_choice_min")

    @multiple_choice_min.setter
    def multiple_choice_min(self, value: int):
        self._raw["multiple_choice_min"] = value

    @property
    def multiple_choice_max(self) -> Optional[int]:
        return self._raw.get("multiple_choice_max")

    @multiple_choice_max.setter
    def multiple_choice_max(self, value: int):
        self._raw["multiple_choice_max"] = value

    @property
    def number_of_winners(self) -> Optional[int]:
        return self._raw.get("number_of_winners")

    @number_of_winners.setter
    def number_of_winners(self, value: int):
        self._raw["number_of_winners"] = value

    @property
    def randomize_options(self) -> Optional[bool]:
        return self._raw.get("randomize_options")

    @randomize_options.setter
    def randomize_options(self, value: bool):
        self._raw["randomize_options"] = value

    @property
    def require_voter_names(self) -> Optional[bool]:
        return self._raw.get("require_voter_names")

    @require_voter_names.setter
    def require_voter_names(self, value: bool):
        self._raw["require_voter_names"] = value

    @property
    def results_visibility(self) -> Literal["always", "after_deadline", "after_vote", "never"]:
        return self._raw["results_visibility"]

    @results_visibility.setter
    def results_visibility(self, value: Literal["always", "after_deadline", "after_vote", "never"]):
        self._raw["results_visibility"] = value

    @property
    def use_custom_design(self) -> Optional[bool]:
        return self._raw.get("use_custom_design")

    @use_custom_design.setter
    def use_custom_design(self, value: bool):
        self._raw["use_custom_design"] = value


class PollOption(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def id(self) -> Optional[int]:
        return self._raw.get("id")

    @id.setter
    def id(self, value: int):
        self._raw["id"] = value

    @property
    def type(self) -> Literal["text", "image", "date", "time_range"]:
        return self._raw["type"]

    @type.setter
    def type(self, value: Literal["text", "image", "date", "time_range"]):
        self._raw["type"] = value

    @property
    def position(self) -> Optional[int]:
        return self._raw.get("position")

    @position.setter
    def position(self, value: int):
        self._raw["position"] = value

    @property
    def vote_count(self) -> Optional[int]:
        return self._raw.get("vote_count")

    @vote_count.setter
    def vote_count(self, value: int):
        self._raw["vote_count"] = value

    @property
    def max_votes(self) -> Optional[int]:
        return self._raw.get("max_votes")

    @max_votes.setter
    def max_votes(self, value: int):
        self._raw["max_votes"] = value

    @property
    def description(self) -> Optional[str]:
        return self._raw.get("description")

    @description.setter
    def description(self, value: str):
        self._raw["description"] = value

    @property
    def is_write_in(self) -> Optional[bool]:
        return self._raw.get("is_write_in")

    @is_write_in.setter
    def is_write_in(self, value: bool):
        self._raw["is_write_in"] = value


class TextPollOption(PollOption):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def value(self) -> Optional[str]:
        return self._raw.get("value")

    @value.setter
    def value(self, value: str):
        self._raw["value"] = value


class ImagePollOption(TextPollOption):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def media(self) -> Optional[Media]:
        return Media._from_dict(self._raw.get("media", {}))

    @media.setter
    def media(self, value: Media):
        self._raw["media"] = value


class DatePollOption(PollConfig):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def date(self) -> Optional[str]:
        return self._raw.get("date")

    @date.setter
    def date(self, value: str):
        self._raw["date"] = value


class TimeRangePollOption(PollConfig):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def start_time(self) -> Optional[int]:
        return self._raw.get("start_time")

    @start_time.setter
    def start_time(self, value: int):
        self._raw["start_time"] = value

    @property
    def end_time(self) -> Optional[int]:
        return self._raw.get("end_time")

    @end_time.setter
    def end_time(self, value: int):
        self._raw["end_time"] = value


class Poll(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def title(self) -> str:
        return self._raw["title"]

    @title.setter
    def title(self, value: str):
        self._raw["title"] = value

    @property
    def user(self) -> Optional[User]:
        return User._from_dict(self._raw.get("user", {}))

    @property
    def media(self) -> Optional[Media]:
        return Media._from_dict(self._raw.get("media", {}))

    @media.setter
    def media(self, value: Media):
        self._raw["media"] = value

    @property
    def workspace(self) -> Optional[Workspace]:
        return Workspace._from_dict(self._raw.get("workspace", {}))

    @workspace.setter
    def workspace(self, value: Workspace):
        self._raw["workspace"] = value

    @property
    def poll_options(self) -> List[PollOption]:
        return [PollOption._from_dict(i) for i in self._raw["poll_options"]]

    @poll_options.setter
    def poll_options(self, value: List[PollOption]):
        self._raw["poll_options"] = value

    @property
    def poll_meta(self) -> Optional[PollMeta]:
        return PollMeta._from_dict(self._raw.get("poll_meta", {}))

    @poll_meta.setter
    def poll_meta(self, value: PollMeta):
        self._raw["poll_meta"] = value

    @property
    def poll_config(self) -> Optional[PollConfig]:
        return PollConfig._from_dict(self._raw.get("poll_config", {}))

    @poll_config.setter
    def poll_config(self, value: PollConfig):
        self._raw["poll_config"] = value

    @property
    def type(self) -> Literal["multiple_choice", "image_poll", "meeting", "ranked_choice"]:
        return self._raw["type"]

    @type.setter
    def type(self, value: Literal["multiple_choice", "image_poll", "meeting", "ranked_choice"]):
        self._raw["type"] = value

    @property
    def version(self) -> Optional[str]:
        return self._raw.get("version")

    @property
    def created_at(self) -> Optional[int]:
        return self._raw.get("created_at")

    @property
    def updated_at(self) -> Optional[int]:
        return self._raw.get("updated_at")

    @property
    def reset_at(self) -> Optional[int]:
        return self._raw.get("reset_at")


class PollParticipant(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def name(self) -> Optional[str]:
        return self._raw.get("name")

    @name.setter
    def name(self, value: str):
        self._raw["name"] = value

    @property
    def country_code(self) -> Optional[str]:
        return self._raw.get("country_code")

    @country_code.setter
    def country_code(self, value: str):
        self._raw["country_code"] = value

    @property
    def is_edit_allowed(self) -> Optional[bool]:
        return self._raw.get("is_edit_allowed")

    @property
    def poll_votes(self) -> Optional[List[Optional[int]]]:
        return list(self._raw["poll_votes"])

    @property
    def created_at(self) -> Optional[int]:
        return self._raw.get("created_at")


class PollResults(BaseModel):
    def __init__(self, **kw):
        super().__init__(**kw)

    @property
    def id(self) -> Optional[str]:
        return self._raw.get("id")

    @property
    def version(self) -> Optional[str]:
        return self._raw.get("version")

    @property
    def vote_count(self) -> Optional[int]:
        return self._raw.get("voteCount")

    @vote_count.setter
    def vote_count(self, value: int):
        self._raw["voteCount"] = value

    @property
    def participant_count(self) -> Optional[int]:
        return self._raw.get("participantCount")

    @participant_count.setter
    def participant_count(self, value: int):
        self._raw["participantCount"] = value

    @property
    def result_key(self) -> Optional[str]:
        return self._raw.get("resultKey")

    @result_key.setter
    def result_key(self, value: str):
        self._raw["resultKey"] = value

    @property
    def poll_options(self) -> Optional[List[PollOption]]:
        return [PollOption._from_dict(i) for i in self._raw["poll_options"]]

    @poll_options.setter
    def poll_options(self, value: List[PollOption]):
        self._raw["poll_options"] = value

    @property
    def poll_participants(self) -> List[PollParticipant]:
        return [PollParticipant._from_dict(i) for i in self._raw["poll_participants"]]
