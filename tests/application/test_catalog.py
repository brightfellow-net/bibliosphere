import pytest

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.add_item import AddItem
from bibliosphere.application.use_cases.delete_bibliography import DeleteBibliography
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.application.use_cases.remove_item import RemoveItem
from bibliosphere.application.use_cases.search_catalog import SearchCatalog
from bibliosphere.application.use_cases.set_bibliography_authors import SetBibliographyAuthors
from bibliosphere.domain.exceptions import (
    BibliographyHasItems,
    BibliographyNotFound,
    DuplicateCallNumber,
    DuplicateIsbn,
    InvalidBibliographyDetails,
    ItemNotAvailable,
    ItemNotFound,
)


def test_add_bibliography(bibliography_repo, author_repo, unit_of_work):
    use_case = AddBibliography(bibliography_repo, author_repo, unit_of_work)
    result = use_case.execute(
        title="Clean Architecture", authors=["Robert C. Martin"], call_number="QA76.76 M37", isbn_issn="978-0-13-468599-1"
    )
    assert result.id is not None
    assert bibliography_repo.get_by_isbn("978-0-13-468599-1") == result
    assert bibliography_repo.get_by_call_number("QA76.76 M37") == result
    assert [c.author.name for c in bibliography_repo.list_authors(result.id)] == ["Robert C. Martin"]


def test_add_bibliography_rejects_duplicate_isbn(bibliography_repo, author_repo, unit_of_work):
    use_case = AddBibliography(bibliography_repo, author_repo, unit_of_work)
    use_case.execute(title="A", authors=["X"], call_number="CN-A", isbn_issn="123")
    with pytest.raises(DuplicateIsbn):
        use_case.execute(title="B", authors=["Y"], call_number="CN-B", isbn_issn="123")


def test_add_bibliography_rejects_blank_call_number(bibliography_repo, author_repo, unit_of_work):
    use_case = AddBibliography(bibliography_repo, author_repo, unit_of_work)
    with pytest.raises(InvalidBibliographyDetails):
        use_case.execute(title="A", authors=["X"], call_number="  ")


def test_add_bibliography_rejects_duplicate_call_number(bibliography_repo, author_repo, unit_of_work):
    use_case = AddBibliography(bibliography_repo, author_repo, unit_of_work)
    use_case.execute(title="A", authors=["X"], call_number="CN-1")
    with pytest.raises(DuplicateCallNumber):
        use_case.execute(title="B", authors=["Y"], call_number="CN-1")


def test_edit_bibliography(bibliography_repo, author_repo, unit_of_work):
    added = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="A", authors=["X"], call_number="CN-1", isbn_issn="123"
    )
    use_case = EditBibliography(bibliography_repo, author_repo, unit_of_work)
    updated = use_case.execute(added.id, title="A2", authors=["X"], call_number="CN-1", isbn_issn="123")
    assert updated.title == "A2"


def test_edit_bibliography_missing_raises(bibliography_repo, author_repo, unit_of_work):
    use_case = EditBibliography(bibliography_repo, author_repo, unit_of_work)
    with pytest.raises(BibliographyNotFound):
        use_case.execute(999, title="A", authors=["X"], call_number="CN-X", isbn_issn="123")


def test_edit_bibliography_rejects_duplicate_call_number(bibliography_repo, author_repo, unit_of_work):
    AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="A", authors=["X"], call_number="CN-1"
    )
    other = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="B", authors=["Y"], call_number="CN-2"
    )
    use_case = EditBibliography(bibliography_repo, author_repo, unit_of_work)
    with pytest.raises(DuplicateCallNumber):
        use_case.execute(other.id, title="B", authors=["Y"], call_number="CN-1")


def test_set_bibliography_authors(bibliography_repo, author_repo, unit_of_work):
    bibliography = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="Dune", authors=[], call_number="CN-2", isbn_issn="123"
    )
    use_case = SetBibliographyAuthors(bibliography_repo, author_repo, unit_of_work)

    use_case.execute(bibliography.id, ["Frank Herbert", "Brian Herbert"])
    assert [c.author.name for c in bibliography_repo.list_authors(bibliography.id)] == [
        "Frank Herbert",
        "Brian Herbert",
    ]

    # Reordering and dropping an author should be reflected exactly, independent of
    # the bibliography's other fields.
    use_case.execute(bibliography.id, ["Brian Herbert"])
    assert [c.author.name for c in bibliography_repo.list_authors(bibliography.id)] == ["Brian Herbert"]


def test_set_bibliography_authors_missing_raises(bibliography_repo, author_repo, unit_of_work):
    use_case = SetBibliographyAuthors(bibliography_repo, author_repo, unit_of_work)
    with pytest.raises(BibliographyNotFound):
        use_case.execute(999, ["X"])


def test_add_and_remove_item(bibliography_repo, author_repo, unit_of_work, loan_repo):
    bibliography = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="A", authors=["X"], call_number="CN-3", isbn_issn="123"
    )
    item = AddItem(bibliography_repo).execute(bibliography.id)
    assert item.bibliography_id == bibliography.id

    RemoveItem(bibliography_repo, loan_repo).execute(item.id)
    assert bibliography_repo.get_item(item.id) is None


def test_remove_missing_item_raises(bibliography_repo, loan_repo):
    with pytest.raises(ItemNotFound):
        RemoveItem(bibliography_repo, loan_repo).execute(999)


def test_delete_bibliography(bibliography_repo, author_repo, unit_of_work):
    bibliography = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="A", authors=["X"], call_number="CN-7", isbn_issn="123"
    )
    DeleteBibliography(bibliography_repo).execute(bibliography.id)
    assert bibliography_repo.get_by_id(bibliography.id) is None


def test_delete_bibliography_missing_raises(bibliography_repo):
    with pytest.raises(BibliographyNotFound):
        DeleteBibliography(bibliography_repo).execute(999)


def test_delete_bibliography_rejects_when_items_exist(bibliography_repo, author_repo, unit_of_work):
    bibliography = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="A", authors=["X"], call_number="CN-8", isbn_issn="123"
    )
    AddItem(bibliography_repo).execute(bibliography.id)
    with pytest.raises(BibliographyHasItems):
        DeleteBibliography(bibliography_repo).execute(bibliography.id)
    assert bibliography_repo.get_by_id(bibliography.id) is not None


def test_search_catalog_reports_availability(bibliography_repo, author_repo, unit_of_work, loan_repo):
    bibliography = AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="Dune", authors=["Herbert"], call_number="CN-4", isbn_issn="123"
    )
    AddItem(bibliography_repo).execute(bibliography.id)
    AddItem(bibliography_repo).execute(bibliography.id)

    [entry] = SearchCatalog(bibliography_repo, loan_repo).execute("Dune")
    assert entry.total_items == 2
    assert entry.available_items == 2


def test_search_catalog_empty_query_lists_all(bibliography_repo, author_repo, unit_of_work, loan_repo):
    AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="A", authors=["X"], call_number="CN-5", isbn_issn="1"
    )
    AddBibliography(bibliography_repo, author_repo, unit_of_work).execute(
        title="B", authors=["Y"], call_number="CN-6", isbn_issn="2"
    )
    assert len(SearchCatalog(bibliography_repo, loan_repo).execute("")) == 2
