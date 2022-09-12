class InvalidAnswerError(ValueError):
    """Raised when the user inputs an invalid answer"""

    pass


class InvalidLanguageError(ValueError):
    """Raised when the user inputs an invalid language"""

    pass


class AkiConnectionFailure(Exception):
    """Raised if the Akinator API fails to connect for some reason. Base class for AkiTimedOut, AkiNoQuestions, AkiServerDown, and AkiTechnicalError"""

    pass


class AkiTimedOut(AkiConnectionFailure):
    """Raised if the Akinator session times out. Derived from AkiConnectionFailure"""

    pass


class AkiNoQuestions(AkiConnectionFailure):
    """Raised if the Akinator API runs out of questions to ask. This will happen if "Akinator.step" is at 79 and the "answer" function is called again. Derived from AkiConnectionFailure"""

    pass


class AkiServerDown(AkiConnectionFailure):
    """Raised if Akinator's servers are down for the region you're running on. If this happens, try again later or use a different language. Derived from AkiConnectionFailure"""

    pass


class AkiTechnicalError(AkiConnectionFailure):
    """Raised if Aki's servers had a technical error. If this happens, try again later or use a different language. Derived from AkiConnectionFailure"""

    pass


class CantGoBackAnyFurther(Exception):
    """Raised when the user is on the first question and tries to go back further"""

    pass
