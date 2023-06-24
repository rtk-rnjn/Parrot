import operator
import random
from dataclasses import dataclass
from typing import List

THUMBNAIL_SIZE = (80, 80)

MAX_SQUARES = 10_000

IMAGES = {
    6: "https://cdn.discordapp.com/attachments/859123972884922418/888133201497837598/hangman0.png",
    5: "https://cdn.discordapp.com/attachments/859123972884922418/888133595259084800/hangman1.png",
    4: "https://cdn.discordapp.com/attachments/859123972884922418/888134194474139688/hangman2.png",
    3: "https://cdn.discordapp.com/attachments/859123972884922418/888133758069395466/hangman3.png",
    2: "https://cdn.discordapp.com/attachments/859123972884922418/888133786724859924/hangman4.png",
    1: "https://cdn.discordapp.com/attachments/859123972884922418/888133828831477791/hangman5.png",
    0: "https://cdn.discordapp.com/attachments/859123972884922418/888133845449338910/hangman6.png",
}


RESPONSES = [
    "All signs point to yes...",
    "Yes!",
    "My sources say nope.",
    "You may rely on it.",
    "Concentrate and ask again...",
    "Outlook not so good...",
    "It is decidedly so!",
    "Better not tell you.",
    "Very doubtful.",
    "Yes - Definitely!",
    "It is certain!",
    "Most likely.",
    "Ask again later.",
    "No!",
    "Outlook good.",
    "Don't count on it.",
    "Why not",
    "Probably",
    "Can't say",
    "Well well...",
]

UWU_WORDS = {
    "fi": "fwi",
    "l": "w",
    "r": "w",
    "some": "sum",
    "th": "d",
    "thing": "fing",
    "tho": "fo",
    "you're": "yuw'we",
    "your": "yur",
    "you": "yuw",
}

DEFAULT_QUESTION_LIMIT = 7
STANDARD_VARIATION_TOLERANCE = 88
DYNAMICALLY_GEN_VARIATION_TOLERANCE = 97
TIME_LIMIT = 60
MAX_ERROR_FETCH_TRIES = 3

WRONG_ANS_RESPONSE = [
    "No one answered correctly!",
    "Better luck next time...",
]

RULES = (
    "No cheating and have fun!",
    "Points for each question reduces by 25 after 10s or after a hint. Total time is 30s per question",
)

WIKI_FEED_API_URL = "https://en.wikipedia.org/api/rest_v1/feed/featured/{date}"
TRIVIA_QUIZ_ICON = "https://raw.githubusercontent.com/python-discord/branding/main/icons/trivia_quiz/trivia-quiz-dist.png"


@dataclass(frozen=True)
class QuizEntry:
    """Stores quiz entry (a question and a list of answers)."""

    question: str
    answers: List[str]
    var_tol: int


class DynamicQuestionGen:
    """Class that contains functions to generate math/science questions for TriviaQuiz Cog."""

    N_PREFIX_STARTS_AT = 5
    N_PREFIXES = [
        "penta",
        "hexa",
        "hepta",
        "octa",
        "nona",
        "deca",
        "hendeca",
        "dodeca",
        "trideca",
        "tetradeca",
    ]

    PLANETS = [
        ("1st", "Mercury"),
        ("2nd", "Venus"),
        ("3rd", "Earth"),
        ("4th", "Mars"),
        ("5th", "Jupiter"),
        ("6th", "Saturn"),
        ("7th", "Uranus"),
        ("8th", "Neptune"),
    ]

    TAXONOMIC_HIERARCHY = [
        "species",
        "genus",
        "family",
        "order",
        "class",
        "phylum",
        "kingdom",
        "domain",
    ]

    UNITS_TO_BASE_UNITS = {
        "hertz": ("(unit of frequency)", "s^-1"),
        "newton": ("(unit of force)", "m*kg*s^-2"),
        "pascal": ("(unit of pressure & stress)", "m^-1*kg*s^-2"),
        "joule": ("(unit of energy & quantity of heat)", "m^2*kg*s^-2"),
        "watt": ("(unit of power)", "m^2*kg*s^-3"),
        "coulomb": ("(unit of electric charge & quantity of electricity)", "s*A"),
        "volt": ("(unit of voltage & electromotive force)", "m^2*kg*s^-3*A^-1"),
        "farad": ("(unit of capacitance)", "m^-2*kg^-1*s^4*A^2"),
        "ohm": ("(unit of electric resistance)", "m^2*kg*s^-3*A^-2"),
        "weber": ("(unit of magnetic flux)", "m^2*kg*s^-2*A^-1"),
        "tesla": ("(unit of magnetic flux density)", "kg*s^-2*A^-1"),
    }

    @classmethod
    def linear_system(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a system of linear equations with two unknowns."""
        x, y = random.randint(2, 5), random.randint(2, 5)
        answer = a_format.format(x, y)

        coeffs = random.sample(range(1, 6), 4)

        question = q_format.format(
            coeffs[0],
            coeffs[1],
            coeffs[0] * x + coeffs[1] * y,
            coeffs[2],
            coeffs[3],
            coeffs[2] * x + coeffs[3] * y,
        )

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def mod_arith(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a basic modular arithmetic question."""
        quotient, m, b = (
            random.randint(30, 40),
            random.randint(10, 20),
            random.randint(200, 350),
        )
        ans = random.randint(0, 9)  # max remainder is 9, since the minimum modulus is 10
        a = quotient * m + ans - b

        question = q_format.format(a, b, m)
        answer = a_format.format(ans)

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def ngonal_prism(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a question regarding vertices on n-gonal prisms."""
        n = random.randint(0, len(cls.N_PREFIXES) - 1)

        question = q_format.format(cls.N_PREFIXES[n])
        answer = a_format.format((n + cls.N_PREFIX_STARTS_AT) * 2)

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def imag_sqrt(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a negative square root question."""
        ans_coeff = random.randint(3, 10)

        question = q_format.format(ans_coeff**2)
        answer = a_format.format(ans_coeff)

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def binary_calc(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a binary calculation question."""
        a = random.randint(15, 20)
        b = random.randint(10, a)
        oper = random.choice(
            (
                ("+", operator.add),
                ("-", operator.sub),
                ("*", operator.mul),
            )
        )

        # if the operator is multiplication, lower the values of the two operands to make it easier
        if oper[0] == "*":
            a -= 5
            b -= 5

        question = q_format.format(a, oper[0], b)
        answer = a_format.format(oper[1](a, b))

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def solar_system(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a question on the planets of the Solar System."""
        planet = random.choice(cls.PLANETS)

        question = q_format.format(planet[0])
        answer = a_format.format(planet[1])

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def taxonomic_rank(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a question on taxonomic classification."""
        level = random.randint(0, len(cls.TAXONOMIC_HIERARCHY) - 2)

        question = q_format.format(cls.TAXONOMIC_HIERARCHY[level])
        answer = a_format.format(cls.TAXONOMIC_HIERARCHY[level + 1])

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)

    @classmethod
    def base_units_convert(cls, q_format: str, a_format: str) -> QuizEntry:
        """Generate a SI base units conversion question."""
        unit = random.choice(list(cls.UNITS_TO_BASE_UNITS))

        question = q_format.format(f"{unit} {cls.UNITS_TO_BASE_UNITS[unit][0]}")
        answer = a_format.format(cls.UNITS_TO_BASE_UNITS[unit][1])

        return QuizEntry(question, [answer], DYNAMICALLY_GEN_VARIATION_TOLERANCE)


DYNAMIC_QUESTIONS_FORMAT_FUNCS = {
    201: DynamicQuestionGen.linear_system,
    202: DynamicQuestionGen.mod_arith,
    203: DynamicQuestionGen.ngonal_prism,
    204: DynamicQuestionGen.imag_sqrt,
    205: DynamicQuestionGen.binary_calc,
    301: DynamicQuestionGen.solar_system,
    302: DynamicQuestionGen.taxonomic_rank,
    303: DynamicQuestionGen.base_units_convert,
}
