from .exceptions import (
    AkiConnectionFailure,
    AkiNoQuestions,
    AkiServerDown,
    AkiTechnicalError,
    AkiTimedOut,
    InvalidAnswerError,
    InvalidLanguageError,
)


def ans_to_id(ans):
    """Convert an input answer string into an Answer ID for Akinator"""

    ans = str(ans).lower()
    if ans in {"yes", "y", "0"}:
        return "0"
    elif ans in {"no", "n", "1"}:
        return "1"
    elif ans in {"i", "idk", "i dont know", "i don't know", "2"}:
        return "2"
    elif ans in {"probably", "p", "3"}:
        return "3"
    elif ans in {"probably not", "pn", "4"}:
        return "4"
    else:
        raise InvalidAnswerError(
            """
        You put "{}", which is an invalid answer.
        The answer must be one of these:
            - "yes" OR "y" OR "0" for YES
            - "no" OR "n" OR "1" for NO
            - "i" OR "idk" OR "i dont know" OR "i don't know" OR "2" for I DON'T KNOW
            - "probably" OR "p" OR "3" for PROBABLY
            - "probably not" OR "pn" OR "4" for PROBABLY NOT
        """.format(
                ans
            )
        )


def get_lang_and_theme(lang=None):
    """Returns the language code and theme based on what is input"""

    if lang is None:
        return {"lang": "en", "theme": "c"}

    lang = str(lang).lower()
    if lang == "en":
        return {"lang": "en", "theme": "c"}
    elif lang == "english":
        return {"lang": "en", "theme": "c"}
    elif lang in {"en_animals", "english_animals"}:
        return {"lang": "en", "theme": "a"}
    elif lang in {"en_objects", "english_objects"}:
        return {"lang": "en", "theme": "o"}
    elif lang in {"ar", "arabic"}:
        return {"lang": "ar", "theme": "c"}
    elif lang in {"cn", "chinese"}:
        return {"lang": "cn", "theme": "c"}
    elif lang in {"de", "german"}:
        return {"lang": "de", "theme": "c"}
    elif lang in {"de_animals", "german_animals"}:
        return {"lang": "de", "theme": "a"}
    elif lang in {"es", "spanish"}:
        return {"lang": "es", "theme": "c"}
    elif lang in {"es_animals", "spanish_animals"}:
        return {"lang": "es", "theme": "a"}
    elif lang in {"fr", "french"}:
        return {"lang": "fr", "theme": "c"}
    elif lang in {"fr_animals", "french_animals"}:
        return {"lang": "fr", "theme": "a"}
    elif lang in {"fr_objects", "french_objects"}:
        return {"lang": "fr", "theme": "o"}
    elif lang in {"il", "hebrew"}:
        return {"lang": "il", "theme": "c"}
    elif lang in {"it", "italian"}:
        return {"lang": "it", "theme": "c"}
    elif lang in {"it_animals", "italian_animals"}:
        return {"lang": "it", "theme": "a"}
    elif lang in {"jp", "japanese"}:
        return {"lang": "jp", "theme": "c"}
    elif lang in {"jp_animals", "japanese_animals"}:
        return {"lang": "jp", "theme": "a"}
    elif lang in {"kr", "korean"}:
        return {"lang": "kr", "theme": "c"}
    elif lang in {"nl", "dutch"}:
        return {"lang": "nl", "theme": "c"}
    elif lang in {"pl", "polish"}:
        return {"lang": "pl", "theme": "c"}
    elif lang in {"pt", "portuguese"}:
        return {"lang": "pt", "theme": "c"}
    elif lang in {"ru", "russian"}:
        return {"lang": "ru", "theme": "c"}
    elif lang in {"tr", "turkish"}:
        return {"lang": "tr", "theme": "c"}
    elif lang in {"id", "indonesian"}:
        return {"lang": "id", "theme": "c"}
    else:
        raise InvalidLanguageError(f'You put "{lang}", which is an invalid language.')


def raise_connection_error(response):
    """Raise the proper error if the API failed to connect"""

    if response == "KO - SERVER DOWN":
        raise AkiServerDown(
            "Akinator's servers are down in this region. Try again later or use a different language"
        )
    elif response == "KO - TECHNICAL ERROR":
        raise AkiTechnicalError(
            "Akinator's servers have had a technical error. Try again later or use a different language"
        )
    elif response == "KO - TIMEOUT":
        raise AkiTimedOut("Your Akinator session has timed out")
    elif response in ["KO - ELEM LIST IS EMPTY", "WARN - NO QUESTION"]:
        raise AkiNoQuestions('"Akinator.step" reached 79. No more questions')
    else:
        raise AkiConnectionFailure(
            f"An unknown error has occured. Server response: {response}"
        )
