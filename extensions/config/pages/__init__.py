from __future__ import annotations

from .base import Page
from .birthday import BirthdayPage
from .events import EventsPage
from .general import GeneralPage
from .giveaway import GiveawayPage
from .global_chat import GlobalChatPage
from .hub import HubPage
from .leveling import LevelingPage
from .moderation import ModerationPage
from .overview import OverviewPage
from .starboard import StarboardPage
from .suggestion import SuggestionPage
from .telephone import TelephonePage
from .ticket import TicketPage
from .welcome import WelcomePage

__all__ = ("PAGES", "OverviewPage", "Page")

PAGES: tuple[type[Page], ...] = (
    OverviewPage,
    GeneralPage,
    ModerationPage,
    WelcomePage,
    LevelingPage,
    StarboardPage,
    GiveawayPage,
    TicketPage,
    SuggestionPage,
    BirthdayPage,
    HubPage,
    TelephonePage,
    GlobalChatPage,
    EventsPage,
)
