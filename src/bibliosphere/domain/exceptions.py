class BibliosphereError(Exception):
    """Base class for all domain errors."""


class ItemNotAvailable(BibliosphereError):
    """Raised when checkout is attempted but no item of the bibliography is available."""


class LoanLimitExceeded(BibliosphereError):
    """Raised when a member already has the maximum number of open loans."""


class DuplicateIsbn(BibliosphereError):
    """Raised when adding a bibliography whose ISBN is already in the catalog."""


class DuplicateUsername(BibliosphereError):
    """Raised when creating a member whose username is already taken."""


class InvalidMemberDetails(BibliosphereError):
    """Raised when a member's username, name, or password is blank."""


class InvalidCredentials(BibliosphereError):
    """Raised when a login attempt's username/password do not match."""


class BibliographyNotFound(BibliosphereError):
    """Raised when a referenced bibliography does not exist."""


class ItemNotFound(BibliosphereError):
    """Raised when a referenced item does not exist."""


class MemberNotFound(BibliosphereError):
    """Raised when a referenced member does not exist."""


class LoanNotFound(BibliosphereError):
    """Raised when a referenced loan does not exist."""


class LoanAlreadyReturned(BibliosphereError):
    """Raised when attempting to return a loan that has already been returned."""
