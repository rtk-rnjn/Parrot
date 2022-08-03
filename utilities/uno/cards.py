from .enums import Color, CardType
from typing import Optional, TypeVar

E = TypeVar('E', bound='Card')


class Emojis:
    class red:
        numbers = [
            '<:red_0:875131307586355212>',
            '<:red_1:875131309004054579>',
            '<:red_2:875131309578649701>',
            '<:red_3:875131310782435329>',
            '<:red_4:875131312074276904>',
            '<:red_5:875131312984453230>',
            '<:red_6:875131313848451092>',
            '<:red_7:875131314863480832>',
            '<:red_8:875131316318908446>',
            '<:red_9:875131317417836584>'
        ]

        plus_2 = '<:red_plus_2:875131318483185664>'
        reverse = '<:red_reverse:875131319389143090>'
        skip = '<:red_skip:875131320660029451>'

    class yellow:
        numbers = [
            '<:yellow_0:875131321914118174>',
            '<:yellow_1:875131322773942292>',
            '<:yellow_2:875131323738652762>',
            '<:yellow_3:875131324648808520>',
            '<:yellow_4:875131325529595945>',
            '<:yellow_5:875131327039537212>',
            '<:yellow_6:875131328222359582>',
            '<:yellow_7:875131329216393246>',
            '<:yellow_8:875131330147532830>',
            '<:yellow_9:875131331057704990>'
        ]

        plus_2 = '<:yellow_plus_2:875131331963666452>'
        reverse = '<:yellow_reverse:875131333045805076>'
        skip = '<:yellow_skip:875131334371184640>'

    class blue:
        numbers = [
            '<:blue_0:875131335088435232>',
            '<:blue_1:875131336346722374>',
            '<:blue_2:875131337240113192>',
            '<:blue_3:875131338213175317>',
            '<:blue_4:875131339022663720>',
            '<:blue_5:875131339769262101>',
            '<:blue_6:875131340650057769>',
            '<:blue_7:875131341761544213>',
            '<:blue_8:875131342730448946>',
            '<:blue_9:875131343523172382>'
        ]

        plus_2 = '<:blue_plus_2:875131344701779968>'
        reverse = '<:blue_reverse:875131345532252170>'
        skip = '<:blue_skip:875131346387869736>'

    class green:
        numbers = [
            '<:green_0:875131347155447818>',
            '<:green_1:875131348308885524>',
            '<:green_2:875131349235814490>',
            '<:green_3:875131350166953994>',
            '<:green_4:875131350842212383>',
            '<:green_5:875131351538487368>',
            '<:green_6:875131352914202684>',
            '<:green_7:875131353690161203>',
            '<:green_8:875131354302513213>',
            '<:green_9:875131355191709779>'
        ]

        plus_2 = '<:green_plus_2:875131356496150578>'
        reverse = '<a:green_reverse:875146408766881832>'
        skip = '<a:green_skip:875146409869971497>'

    wild = '<a:wild_wild:875146410985672744>'
    plus_4 = '<a:wild_plus_4:875146412084572181>'


class Card:
    def __init__(
        self,
        *,
        color: Color,
        type: CardType = CardType.number,
        value: Optional[int] = None,
    ) -> None:
        self.color: Color = color
        self.type: CardType = type
        self.value: Optional[int] = value

    def __hash__(self) -> int:
        return hash((self.color, self.type, self.value))

    def __repr__(self) -> str:
        return f'<Card color={self.color.name} type={self.type.name} value={self.value}>'

    def __eq__(self: E, other: E) -> bool:
        return (
            isinstance(other, self.__class__)
            and self.color is other.color
            and self.type is other.type
            and self.value == other.value
        )

    @property
    def emoji(self) -> str:
        if self.type is CardType.plus_4:
            return Emojis.plus_4
        elif self.type is CardType.wild:
            return Emojis.wild

        sink = getattr(Emojis, self.color.name)
        if self.type is CardType.number:
            return sink.numbers[self.value]
        elif self.type is CardType.plus_2:
            return sink.plus_2
        elif self.type is CardType.reverse:
            return sink.reverse
        elif self.type is CardType.skip:
            return sink.skip

    @property
    def image_url(self) -> str:
        _id = self.emoji.split(':')[-1].rstrip('>')
        return f'https://cdn.discordapp.com/emojis/{_id}.png?v=1'

    def is_wild(self) -> bool:
        return self.type in (
            CardType.wild,
            CardType.plus_4
        )

    def match(self: E, other: E, /) -> bool:
        return other.color is self.color or other.is_wild() or self.stackable_with(other)

    def stackable_with(self: E, other: E, /) -> bool:
        return (
            (other.type is self.type is CardType.number and other.value == self.value)
            or other.type is self.type is not CardType.number
        )


cards = [
    # Red 
    Card(color=Color.red, value=0),
    Card(color=Color.red, value=1),
    Card(color=Color.red, value=1),
    Card(color=Color.red, value=2),
    Card(color=Color.red, value=2),
    Card(color=Color.red, value=3),
    Card(color=Color.red, value=3),
    Card(color=Color.red, value=4),
    Card(color=Color.red, value=4),
    Card(color=Color.red, value=5),
    Card(color=Color.red, value=5),
    Card(color=Color.red, value=6),
    Card(color=Color.red, value=6),
    Card(color=Color.red, value=7),
    Card(color=Color.red, value=7),
    Card(color=Color.red, value=8),
    Card(color=Color.red, value=8),
    Card(color=Color.red, value=9),
    Card(color=Color.red, value=9),
    Card(color=Color.red, type=CardType.plus_2),
    Card(color=Color.red, type=CardType.plus_2),
    Card(color=Color.red, type=CardType.reverse),
    Card(color=Color.red, type=CardType.reverse),
    Card(color=Color.red, type=CardType.skip),
    Card(color=Color.red, type=CardType.skip),

    # Yellow
    Card(color=Color.yellow, value=0),
    Card(color=Color.yellow, value=1),
    Card(color=Color.yellow, value=1),
    Card(color=Color.yellow, value=2),
    Card(color=Color.yellow, value=2),
    Card(color=Color.yellow, value=3),
    Card(color=Color.yellow, value=3),
    Card(color=Color.yellow, value=4),
    Card(color=Color.yellow, value=4),
    Card(color=Color.yellow, value=5),
    Card(color=Color.yellow, value=5),
    Card(color=Color.yellow, value=6),
    Card(color=Color.yellow, value=6),
    Card(color=Color.yellow, value=7),
    Card(color=Color.yellow, value=7),
    Card(color=Color.yellow, value=8),
    Card(color=Color.yellow, value=8),
    Card(color=Color.yellow, value=9),
    Card(color=Color.yellow, value=9),
    Card(color=Color.yellow, type=CardType.plus_2),
    Card(color=Color.yellow, type=CardType.plus_2),
    Card(color=Color.yellow, type=CardType.reverse),
    Card(color=Color.yellow, type=CardType.reverse),
    Card(color=Color.yellow, type=CardType.skip),
    Card(color=Color.yellow, type=CardType.skip),

    # Blue
    Card(color=Color.blue, value=0),
    Card(color=Color.blue, value=1),
    Card(color=Color.blue, value=1),
    Card(color=Color.blue, value=2),
    Card(color=Color.blue, value=2),
    Card(color=Color.blue, value=3),
    Card(color=Color.blue, value=3),
    Card(color=Color.blue, value=4),
    Card(color=Color.blue, value=4),
    Card(color=Color.blue, value=5),
    Card(color=Color.blue, value=5),
    Card(color=Color.blue, value=6),
    Card(color=Color.blue, value=6),
    Card(color=Color.blue, value=7),
    Card(color=Color.blue, value=7),
    Card(color=Color.blue, value=8),
    Card(color=Color.blue, value=8),
    Card(color=Color.blue, value=9),
    Card(color=Color.blue, value=9),
    Card(color=Color.blue, type=CardType.plus_2),
    Card(color=Color.blue, type=CardType.plus_2),
    Card(color=Color.blue, type=CardType.reverse),
    Card(color=Color.blue, type=CardType.reverse),
    Card(color=Color.blue, type=CardType.skip),
    Card(color=Color.blue, type=CardType.skip),
    
    # Green
    Card(color=Color.green, value=0),
    Card(color=Color.green, value=1),
    Card(color=Color.green, value=1),
    Card(color=Color.green, value=2),
    Card(color=Color.green, value=2),
    Card(color=Color.green, value=3),
    Card(color=Color.green, value=3),
    Card(color=Color.green, value=4),
    Card(color=Color.green, value=4),
    Card(color=Color.green, value=5),
    Card(color=Color.green, value=5),
    Card(color=Color.green, value=6),
    Card(color=Color.green, value=6),
    Card(color=Color.green, value=7),
    Card(color=Color.green, value=7),
    Card(color=Color.green, value=8),
    Card(color=Color.green, value=8),
    Card(color=Color.green, value=9),
    Card(color=Color.green, value=9),
    Card(color=Color.green, type=CardType.plus_2),
    Card(color=Color.green, type=CardType.plus_2),
    Card(color=Color.green, type=CardType.reverse),
    Card(color=Color.green, type=CardType.reverse),
    Card(color=Color.green, type=CardType.skip),
    Card(color=Color.green, type=CardType.skip),

    # Wild cards
    Card(color=Color.wild, type=CardType.wild),
    Card(color=Color.wild, type=CardType.wild),
    Card(color=Color.wild, type=CardType.wild),
    Card(color=Color.wild, type=CardType.wild),
    Card(color=Color.wild, type=CardType.plus_4),
    Card(color=Color.wild, type=CardType.plus_4),
    Card(color=Color.wild, type=CardType.plus_4),
    Card(color=Color.wild, type=CardType.plus_4)
]


def create_deck():
    return cards[:]