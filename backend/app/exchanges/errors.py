class ExchangeError(Exception):
    user_message = "Kraken kunde inte behandla begäran. Försök igen senare."


class InvalidCredentialsError(ExchangeError):
    user_message = "API-nyckeln eller den privata nyckeln är ogiltig."


class MissingPermissionsError(ExchangeError):
    user_message = "API-nyckeln saknar nödvändiga behörigheter."


class InsufficientBalanceError(ExchangeError):
    user_message = "Kontot saknar tillräckligt saldo för ordern."


class MinimumOrderError(ExchangeError):
    user_message = "Ordern understiger Krakens minsta tillåtna storlek."


class PrecisionError(ExchangeError):
    user_message = "Orderns pris eller mängd har för många decimaler."


class RateLimitError(ExchangeError):
    user_message = "Kraken tar emot för många anrop. Vänta och försök igen."


class ExchangeUnavailableError(ExchangeError):
    user_message = "Kraken är tillfälligt otillgängligt eller under underhåll."


class NonceError(ExchangeError):
    user_message = (
        "Kraken avvisade tidsstämpeln. Kontrollera datorns datum och tid innan du försöker igen."
    )


class UnknownOrderResultError(ExchangeError):
    user_message = (
        "Orderresultatet är osäkert. Odin kontrollerar orderstatus innan något nytt försök."
    )
