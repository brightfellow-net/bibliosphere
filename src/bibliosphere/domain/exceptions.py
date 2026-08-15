class BibliosphereError(Exception):
    """Base class for all domain errors."""


class ItemNotAvailable(BibliosphereError):
    """Raised when checkout is attempted but no item of the bibliography is available."""


class LoanLimitExceeded(BibliosphereError):
    """Raised when a member already has the maximum number of open loans."""


class DuplicateIsbn(BibliosphereError):
    """Raised when adding a bibliography whose ISBN is already in the catalog."""


class DuplicateCallNumber(BibliosphereError):
    """Raised when a bibliography's call number is already used by another one."""


class InvalidBibliographyDetails(BibliosphereError):
    """Raised when a bibliography's call number is blank."""


class BibliographyHasItems(BibliosphereError):
    """Raised when deleting a bibliography that still has one or more items."""


class ItemHasLoanHistory(BibliosphereError):
    """Raised when removing an item that has ever been loaned (open or returned).

    The `loans.item_id` foreign key would otherwise reject the delete outright once
    any loan references the item — this surfaces that as a clean, catchable error
    instead of an unhandled IntegrityError.
    """


class MemberHasLoanHistory(BibliosphereError):
    """Raised when deleting a member who has ever had a loan (open or returned).

    loans.member_id is a NOT NULL FK — this surfaces that as a clean, catchable
    error instead of an unhandled IntegrityError, mirroring ItemHasLoanHistory.
    """


class CannotDeleteLastLibrarian(BibliosphereError):
    """Raised when deleting the last remaining librarian account would leave the
    app with no one able to log in and manage it.
    """


class DuplicateUsername(BibliosphereError):
    """Raised when creating a member whose username is already taken."""


class DuplicateMemberId(BibliosphereError):
    """Raised when creating a member whose id is already in use."""


class InvalidMemberDetails(BibliosphereError):
    """Raised when a member's id, username, name, or password is blank."""


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
