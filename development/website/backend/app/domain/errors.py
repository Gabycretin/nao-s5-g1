class DomainError(Exception):
    """Base class for domain-level errors, translated to HTTP responses by the API layer."""


class GameNotFoundError(DomainError):
    pass


class PlayerNotFoundError(DomainError):
    pass


class PseudoTakenError(DomainError):
    pass


class InvalidPseudoError(DomainError):
    pass


class NotHostError(DomainError):
    pass


class InvalidGameStateError(DomainError):
    pass


class InvalidRolesConfigError(DomainError):
    pass
