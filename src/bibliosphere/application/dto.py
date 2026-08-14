from dataclasses import dataclass

from bibliosphere.domain.entities import Author, Bibliography, Item, Loan


@dataclass
class ItemStatus:
    item: Item
    available: bool


@dataclass
class CatalogEntry:
    """A bibliography plus its authors and items' derived availability, for display."""

    bibliography: Bibliography
    authors: list[Author]
    items: list[ItemStatus]

    @property
    def author_names(self) -> str:
        return ", ".join(author.name for author in self.authors)

    @property
    def total_items(self) -> int:
        return len(self.items)

    @property
    def available_items(self) -> int:
        return sum(1 for status in self.items if status.available)


@dataclass
class LoanView:
    """A loan resolved to display-friendly fields, for presentation use."""

    loan: Loan
    bibliography_title: str
    member_name: str
