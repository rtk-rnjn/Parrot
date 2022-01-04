from __future__ import annotations

import itertools
import random
from abc import ABCMeta, abstractmethod
from collections.abc import Collection
from functools import cached_property
from typing import Any, Generic, Literal, NoReturn, Optional, TypeVar, Union

from discord.enums import Enum
from discord.utils import MISSING


def format_list(
    string: str,
    *list: Any,
    singular: str = "has",
    plural: str = "have",
    oxford_comma: bool = True
) -> str:
    if len(list) == 0:
        return string.format("no-one", singular)
    if len(list) == 1:
        return string.format(list[0], singular)

    *rest, last = list
    rest_str = ", ".join(str(item) for item in rest)
    return string.format(rest_str + "," * oxford_comma + " and " + str(last), plural)


T = TypeVar("T")
U = TypeVar("U")

PlayerCount = Literal[5, 6, 7, 8, 9, 10]

PLAYER_COUNTS: list[PlayerCount] = [5, 6, 7, 8, 9, 10]


class _Skip:
    def __repr__(self) -> str:
        return "True"

    def __eq__(self, other: Any) -> bool:
        return other is True

    def __bool__(self):
        return True


Skip: Any = _Skip()

# fmt: off


class Party(Enum):
    Liberal = 0
    Fascist = 1


class Role(Enum):
    Liberal = 0
    Fascist = 1
    Hitler = 2


class Power(Enum):
    Peek = 0
    Investigate = 1
    Election = 2
    Execution = 3


ROLES: dict[PlayerCount, list[Role]] = {
    5: [Role.Liberal] * 3 + [Role.Fascist] * 1,
    6: [Role.Liberal] * 4 + [Role.Fascist] * 1,
    7: [Role.Liberal] * 4 + [Role.Fascist] * 2,
    8: [Role.Liberal] * 5 + [Role.Fascist] * 2,
    9: [Role.Liberal] * 5 + [Role.Fascist] * 3,
    10: [Role.Liberal] * 6 + [Role.Fascist] * 3,
}


def _r():  # Pyright breaks if this doesn't exist. T.T (1/06/2021)
    for player_count in PLAYER_COUNTS:
        ROLES[player_count].append(Role.Hitler)


_r()

# fmt: on

SECRET_MESSAGES: dict[PlayerCount, dict[Role, str]] = {
    5: {
        Role.Liberal: "You are a Liberal.",
        Role.Fascist: "You are a Fascist, {0} is Hitler.",
        Role.Hitler: "You are Hitler.",
    },
    6: {},
    7: {
        Role.Fascist: "You are a Fascist, {1} is also a Fascist, {0} is Hitler.",
    },
    8: {},
    9: {
        Role.Fascist: "You are a Fascist, {1} and {2} are also Fascists, {0} is Hitler.",
    },
    10: {},
}

SECRET_MESSAGES[6][Role.Fascist] = SECRET_MESSAGES[5][Role.Fascist]
SECRET_MESSAGES[8][Role.Fascist] = SECRET_MESSAGES[7][Role.Fascist]
SECRET_MESSAGES[10][Role.Fascist] = SECRET_MESSAGES[9][Role.Fascist]

BOARD = """
Liberal policies: {0.liberal_policies}/5
Fascist policies: {0.fascist_policies}/6
"""


def _s():  # See above
    for player_count in PLAYER_COUNTS:
        SECRET_MESSAGES[player_count][Role.Liberal] = SECRET_MESSAGES[5][Role.Liberal]
        SECRET_MESSAGES[player_count][Role.Hitler] = SECRET_MESSAGES[5][Role.Hitler]


_s()

PARTIES: dict[Role, Party] = {
    Role.Liberal: Party.Liberal,
    Role.Fascist: Party.Fascist,
    Role.Hitler: Party.Fascist,
}

POLICIES: dict[Party, int] = {
    Party.Liberal: 6,
    Party.Fascist: 11,
}

POWERS: dict[PlayerCount, list[Optional[Power]]] = {
    5: [None, None, None, Power.Peek],
    7: [None, None, Power.Investigate, Power.Election],
    9: [None, Power.Investigate, Power.Investigate, Power.Election],
}

[POWERS[k].extend([Power.Execution] * 2) for k in POWERS]

POWERS[6] = POWERS[5]
POWERS[8] = POWERS[7]
POWERS[10] = POWERS[9]


class Player(Generic[T]):
    def __init__(self, identifier: T, role: Role) -> None:
        self.identifier = identifier
        self.role: Role = role
        self.dead: bool = False

    def __str__(self) -> str:
        return str(self.identifier)

    @property
    def party(self) -> Party:
        return PARTIES[self.role]


# region: game states


class GameState(Generic[T], metaclass=ABCMeta):
    def __init__(self, game: Game[T]) -> None:
        self.game: Game[T] = game

    @property
    @abstractmethod
    def message(self) -> str:
        raise NotImplementedError

    @property
    def ready(self) -> bool:
        return Skip

    @abstractmethod
    def next_state(self) -> GameState[T]:
        raise NotImplementedError


class UserInputGameState(GameState[T], metaclass=ABCMeta):
    @property
    @abstractmethod
    def tooltip(self) -> str:
        raise NotImplementedError


class AfterVoteGameState(GameState[T], metaclass=ABCMeta):
    votes: dict[Player[T], bool]

    def __init__(self, game: Game[T], votes: dict[Player[T], bool]) -> None:
        self.votes: dict[Player[T], bool] = votes
        super().__init__(game)

    @property
    @abstractmethod
    def _message(self) -> str:
        raise NotImplementedError

    @cached_property
    def message(self) -> str:
        return self._message + "\n" + self.vote_summary

    @cached_property
    def vote_summary(self) -> str:
        ja = [player.identifier for player, vote in self.votes.items() if vote is True]
        nein = [
            player.identifier for player, vote in self.votes.items() if vote is False
        ]
        return format_list("Ja: {0}", *ja) + "\n" + format_list("Nein: {0}", *nein)


class SelectGameState(UserInputGameState[T], Generic[T, U], metaclass=ABCMeta):
    def __init__(self, game: Game[T]) -> None:
        super().__init__(game)
        self.item: U = MISSING

    @property
    @abstractmethod
    def selectable(self) -> list[U]:
        raise NotImplementedError

    @property
    def ready(self) -> bool:
        return self.item is not MISSING


class VoteGameState(UserInputGameState[T], metaclass=ABCMeta):
    def __init__(self, game: Game[T]) -> None:
        super().__init__(game)
        self.votes: dict[Player[T], bool] = {}

    @property
    @abstractmethod
    def voters(self) -> list[Player[T]]:
        raise NotImplementedError

    @property
    def ready(self) -> bool:
        return len(self.votes) == len(self.voters)


class PlayerToBeChancellor(SelectGameState[T, Player[T]]):
    message = "{0.president}, is the President, choose a Chancellor!"
    tooltip = "Select the next Chancellor."

    def __init__(self, game: Game[T], president: Player[T]) -> None:
        self.president: Player[T] = president
        super().__init__(game)

        if len(self.game.draw_pile) < 3:
            self.game.shuffle_policies()

    @property
    def selectable(self) -> list[Player[T]]:
        players = []

        for player in self.game.players:
            if player == self.president:
                continue
            if player in self.game.previously_elected:
                continue
            if player.dead:
                continue
            players.append(player)

        return players

    def next_state(self) -> GameState[T]:
        return VoteOnGovernment[T](self.game, self.president, self.item)


class VoteOnGovernment(VoteGameState[T]):
    message = (
        "{0.president} has chosen {0.chancellor} as their chancellor, vote ja! or nein!"
    )
    tooltip = "Vote ja! or nein!"

    def __init__(
        self, game: Game[T], president: Player[T], chancellor: Player[T]
    ) -> None:
        self.president: Player[T] = president
        self.chancellor: Player[T] = chancellor
        super().__init__(game)

    @property
    def voters(self) -> list[Player[T]]:
        return [player for player in self.game.players if not player.dead]

    # region private properties

    @cached_property
    def ya_count(self):
        return len([vote for vote in self.votes.values() if vote])

    @cached_property
    def nein_count(self):
        return len([vote for vote in self.votes.values() if not vote])

    @cached_property
    def vote_passed(self):
        return self.ya_count > self.nein_count

    # endregion

    def next_state(self) -> GameState[T]:
        if self.vote_passed:
            return VotePassed[T](self.game, self.votes, self.president, self.chancellor)
        return VoteFailed[T](self.game, self.votes)


class VotePassed(AfterVoteGameState[T]):
    _message = "The vote passed, {0.game.president} is the President and {0.game.chancellor} is the Chancellor!"

    def __init__(
        self,
        game: Game[T],
        votes: dict[Player[T], bool],
        president: Player[T],
        chancellor: Player[T],
    ) -> None:
        self.president: Player[T] = president
        self.chancellor: Player[T] = chancellor
        super().__init__(game, votes)

        self.game.election_tracker = 0
        self.game.previously_elected = [self.game.president, self.game.chancellor]
        self.game.president = self.president
        self.game.chancellor = self.chancellor

    def next_state(self) -> GameState[T]:
        if self.chancellor.role is Role.Hitler and self.game.fascist_policies >= 3:
            return HitlerIsChancellor(self.game, self.chancellor)
        return PresidentDiscardsPolicy[T](self.game)


class PresidentDiscardsPolicy(SelectGameState[T, Party]):
    message = "The President will select a policy to be discarded."
    tooltip = "Select a policy to discard, the remaining two policies will be sent to the Chancellor."

    def __init__(self, game: Game[T]) -> None:
        super().__init__(game)

        self.policies: list[Party] = self.game.draw_policies()

    @property
    def selectable(self) -> list[Party]:
        return self.policies

    def next_state(self) -> GameState[T]:
        self.game.discard_pile.append(self.item)
        self.policies.remove(self.item)

        return ChancellorDiscardsPolicy[T](self.game, self.policies)


class ChancellorDiscardsPolicy(SelectGameState[T, Party]):
    message = "The Chancellor will select a policy to be discarded."
    tooltip = "Select a policy to discard, the remaining policy will be enacted."

    def __init__(self, game: Game[T], policies: list[Party]) -> None:
        self.policies: list[Party] = policies
        super().__init__(game)

    @property
    def selectable(self) -> list[Party]:
        return self.policies

    def next_state(self) -> GameState[T]:
        self.game.discard_pile.append(self.item)
        self.policies.remove(self.item)

        policy = self.policies[0]

        if self.game.veto_enabled:  # and policy is Party.Fascist:  # ???
            return GovernmentCanVeto[T](self.game, policy)
        return PolicyEnacted[T](self.game, policy)


class PolicyEnacted(GameState[T]):
    message = "A {0.policy.name} policy has been enacted."

    def __init__(self, game: Game[T], policy: Party, *, top_deck: bool = False) -> None:
        self.policy: Party = policy
        self.top_deck: bool = top_deck
        super().__init__(game)

        if self.policy is Party.Liberal:
            self.game.liberal_policies += 1
        else:
            self.game.fascist_policies += 1
            if self.game.fascist_policies == 5:  # and not self.top_deck:  # ???
                self.game.veto_enabled = True

    # region private properties

    @cached_property
    def sufficient_policies(self) -> bool:
        if self.policy is Party.Liberal:
            return self.game.liberal_policies == 5
        return self.game.fascist_policies == 6

    @cached_property
    def vote_power(self) -> Optional[Power]:
        if self.sufficient_policies or self.top_deck or self.policy is Party.Liberal:
            return None
        return POWERS[self.game.player_count][self.game.fascist_policies]

    # endregion

    def next_state(self) -> GameState[T]:
        if self.sufficient_policies:
            return SufficientPoliciesPlayed[T](self.game, self.policy)
        if self.vote_power is Power.Peek:
            return PolicyListPeek[T](self.game)
        if self.vote_power is Power.Investigate:
            return PlayerToBeInvesitgated[T](self.game)
        if self.vote_power is Power.Election:
            return PlayerToBePresident[T](self.game)
        if self.vote_power is Power.Execution:
            return PlayerToBeExecuted[T](self.game)
        return PresidencyRotates[T](self.game)


class VoteFailed(AfterVoteGameState[T]):
    _message = "The vote failed. The Election Tracker moves to position {0.game.election_tracker}."

    def __init__(self, game: Game[T], votes: dict[Player[T], bool]) -> None:
        super().__init__(game, votes)

        self.game.election_tracker += 1

    def next_state(self) -> GameState[T]:
        if self.game.election_tracker == 3:
            self.game.election_tracker = 0
            return ElectionTrackerMax[T](self.game)
        return PresidencyRotates[T](self.game)


class ElectionTrackerMax(GameState[T]):
    message = "The Election Tracker reached position 3, a policy will be enacted!"

    def __init__(self, game: Game[T]) -> None:
        super().__init__(game)

        self.policy: Party = self.game.draw_policy()

    def next_state(self) -> GameState[T]:
        return PolicyEnacted[T](self.game, self.policy, top_deck=True)


class PresidencyRotates(GameState[T]):
    def __init__(self, game: Game[T], *, start: bool = False) -> None:
        self.start = start
        super().__init__(game)

        self.president = next(self.game.cycle)

    @cached_property
    def message(self) -> str:
        if self.start:
            return "Secret Hitler game starting."
        return "The Presidency will rotate to the next player."

    def next_state(self) -> GameState[T]:
        return PlayerToBeChancellor[T](self.game, self.president)


class PolicyListPeek(UserInputGameState[T]):
    message = "The Fascist policy mandates the President peek at the next 3 policies."
    tooltip = "These are the next three policies in the deck."

    def __init__(self, game: Game[T]) -> None:
        super().__init__(game)

        self.policies: list[Party] = self.game.draw_pile[:3]

    def next_state(self) -> GameState[T]:
        return PresidencyRotates[T](self.game)


class PlayerToBePresident(SelectGameState[T, Player[T]]):
    message = "The Fascist policy mandates the President select a new President."
    tooltip = "Select the next president."

    @property
    def selectable(self) -> list[Player[T]]:
        players = []

        for player in self.game.players:
            if player == self.game.president:
                continue
            if player.dead:
                continue
            players.append(player)

        return players

    def next_state(self) -> GameState[T]:
        return PlayerToBeChancellor[T](self.game, self.item)


class PlayerToBeInvesitgated(SelectGameState[T, Player[T]]):
    message = "The Fascist policy mandates the President investigate a player."
    tooltip = "Select a player to investigate."

    @property
    def selectable(self) -> list[Player[T]]:
        players = []

        for player in self.game.players:
            if player == self.game.president:
                continue
            if player.dead:
                continue
            players.append(player)

        return players

    def next_state(self) -> GameState[T]:
        return PlayerWasInvestigated[T](self.game, self.item)


class PlayerWasInvestigated(GameState[T]):
    message = "{0.player} was investigated by the President."

    def __init__(self, game: Game[T], player: Player[T]) -> None:
        self.player: Player[T] = player
        super().__init__(game)

    def next_state(self) -> GameState[T]:
        return PresidencyRotates[T](self.game)


class PlayerToBeExecuted(SelectGameState[T, Player[T]]):
    message = "The Fascist policy mandates the President execute a player."
    tooltip = "Select a player to execute."

    @property
    def selectable(self) -> list[Player[T]]:
        players = []

        for player in self.game.players:
            if player.dead:
                continue
            players.append(player)

        return players

    def next_state(self) -> GameState[T]:
        return PlayerWasExecuted[T](self.game, self.item)


class PlayerWasExecuted(GameState[T]):
    message = "{0.player} was executed at the President's orders."

    def __init__(self, game: Game[T], player: Player[T]) -> None:
        self.player: Player[T] = player
        super().__init__(game)

    def next_state(self) -> GameState[T]:
        if self.player.role is Role.Hitler:
            return HitlerWasExecuted[T](self.game, self.player)
        return PresidencyRotates[T](self.game)


class GovernmentCanVeto(VoteGameState[T]):
    message = "The President and Chancellor can agree to veto this policy."
    tooltip = "Vote on whether to veto this policy."

    def __init__(self, game: Game[T], policy: Party) -> None:
        self.policy: Party = policy
        super().__init__(game)

    @property
    def voters(self) -> list[Player[T]]:
        return [self.game.president, self.game.chancellor]

    # region private properties

    @property
    def vote_passed(self) -> bool:
        return all(self.votes.values())

    # endregion

    def next_state(self) -> GameState[T]:
        if self.vote_passed:
            self.game.discard_pile.append(self.policy)
            return VetoPassed[T](self.game)
        return VetoFailed[T](self.game, self.policy)


class VetoPassed(GameState[T]):
    message = "The policy was vetoed."

    def next_state(self) -> GameState[T]:
        return PresidencyRotates[T](self.game)


class VetoFailed(GameState[T]):
    message = "The policy was not vetoed."

    def __init__(self, game: Game[T], policy: Party) -> None:
        self.policy: Party = policy
        super().__init__(game)

    def next_state(self) -> GameState[T]:
        return PolicyEnacted[T](self.game, self.policy)


class SufficientPoliciesPlayed(GameState[T]):
    message = "Sufficient {0.party.name} policies have been played."

    def __init__(self, game: Game[T], party: Party) -> None:
        self.party: Party = party
        super().__init__(game)

        self.game.winners = party

    def next_state(self) -> GameState[T]:
        return GameOver[T](self.game)


class HitlerWasExecuted(GameState[T]):
    message = "{0.player} was Hitler."

    def __init__(self, game: Game[T], player: Player[T]) -> None:
        self.player: Player[T] = player
        super().__init__(game)

        self.game.winners = Party.Liberal

    def next_state(self) -> GameState[T]:
        return GameOver[T](self.game)


class HitlerIsChancellor(GameState[T]):
    message = "{0.player} is Hitler."

    def __init__(self, game: Game[T], player: Player[T]) -> None:
        self.player: Player = player
        super().__init__(game)

        self.game.winners = Party.Fascist

    def next_state(self) -> GameState[T]:
        return GameOver[T](self.game)


class GameCancelled(GameState[T]):
    message = "The game has been cancelled."

    def __init__(self, game: Game[T]) -> None:
        super().__init__(game)

        self.game.game_over = True

    def next_state(self) -> NoReturn:
        raise StopIteration()


class GameOver(GameState[T]):
    message = "Game Over, the {0.game.winners.name} party wins!"

    def __init__(self, game: Game[T]) -> None:
        super().__init__(game)

        self.game.game_over = True

    def next_state(self) -> NoReturn:
        raise StopIteration()


# endregion


class Game(Generic[T]):
    def __init__(self, identifiers: Collection[T]) -> None:
        self._summary: list[str] = []

        # Players
        self.players: list[Player[T]] = [
            Player[T](identifier, role)
            for identifier, role in zip(identifiers, ROLES[len(identifiers)])
        ]  # type: ignore
        self.player_count: PlayerCount = len(self.players)  # type: ignore
        random.shuffle(self.players)
        self.cycle = itertools.cycle(self.players)

        # Policies
        liberal_policies = POLICIES[Party.Liberal]
        fascsit_policies = POLICIES[Party.Fascist]
        self.draw_pile: list[Party] = [Party.Liberal] * liberal_policies + [
            Party.Fascist
        ] * fascsit_policies
        self.discard_pile: list[Party] = []
        random.shuffle(self.draw_pile)

        self.liberal_policies: int = 0
        self.fascist_policies: int = 0

        # Election tracking
        self.previously_elected: list[Player] = []
        self.president: Player = MISSING
        self.chancellor: Player = MISSING
        self.election_tracker: int = 0
        self.veto_enabled: bool = False

        self.state: GameState[T] = PresidencyRotates(self, start=True)
        self._message: str = self.state.message.format(self.state)
        self.game_over: bool = False
        self.winners: Party = MISSING

    @property
    def message(self) -> str:
        return self._message + "\n\n" + BOARD.format(self)

    @property
    def summary(self) -> str:
        return "\n\n".join(self._summary)

    @cached_property
    def hitler(self) -> Player:
        return self.get_players(Role.Hitler)[0]

    @cached_property
    def liberals(self) -> list[Player]:
        return self.get_players(Party.Liberal)

    @cached_property
    def fascists(self) -> list[Player]:
        return self.get_players(Party.Fascist)

    def get_player(self, identifier: Optional[T]) -> Optional[Player[T]]:
        for player in self.players:
            if player.identifier == identifier:
                return player
        return None

    def get_players(self, identifier: Union[Party, Role]) -> list[Player[T]]:
        if isinstance(identifier, Role):
            return [player for player in self.players if player.role is identifier]
        return [player for player in self.players if player.party is identifier]

    def draw_policy(self) -> Party:
        return self.draw_pile.pop(0)

    def draw_policies(self) -> list[Party]:
        return [self.draw_policy() for _ in range(3)]

    def shuffle_policies(self):
        self.draw_pile.extend(self.discard_pile)
        self.discard_pile = []
        random.shuffle(self.draw_pile)

    def next_state(self):
        try:
            self.state = self.state.next_state()
            self._message = self.state.message.format(self.state)
            self._summary.append(self._message)
        except StopIteration:
            pass
