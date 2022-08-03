from enum import Enum


class Color(Enum):
    red    = 0
    yellow = 1
    blue   = 2
    green  = 3
    wild   = 4


class CardType(Enum):
    number  = 0
    plus_2  = 1
    reverse = 2
    skip    = 3
    wild    = 4
    plus_4  = 5