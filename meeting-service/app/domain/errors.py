"""Meeting-Service Domain-Fehler."""


class DomainError(Exception):
    pass


class MeetingNotFound(DomainError):
    pass


class NotAuthorized(DomainError):
    pass


class MeetingEnded(DomainError):
    pass


class MeetingFull(DomainError):
    pass


class RateLimitExceeded(DomainError):
    pass
