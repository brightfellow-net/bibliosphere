import pytest

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.add_item import AddItem
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.application.use_cases.remove_item import RemoveItem
from bibliosphere.application.use_cases.search_catalog import SearchCatalog
from bibliosphere.domain.exceptions import BibliographyNotFound, DuplicateIsbn, ItemNotAvailable, ItemNotFound


def test_add_bibliography(bibliography_repo, author_repo):
    use_case = AddBibliography(bibliography_repo, author_repo)
    result = use_case.execute(title="Clean Architecture", authors=["Robert C. Martin"], isbn_issn="978-0-13-468599-1")
    assert result.id is not None
    assert bibliography_repo.get_by_isbn("978-0-13-468599-1") == result
    assert [a.name for a in bibliography_repo.list_authors(result.id)] == ["Robert C. Martin"]


def test_add_bibliography_rejects_duplicate_isbn(bibliography_repo, author_repo):
    use_case = AddBibliography(bibliography_repo, author_repo)
    use_case.execute(title="A", authors=["X"], isbn_issn="123")
    with pytest.raises(DuplicateIsbn):
        use_case.execute(title="B", authors=["Y"], isbn_issn="123")


def test_edit_bibliography(bibliography_repo, author_repo):
    added = AddBibliography(bibliography_repo, author_repo).execute(title="A", authors=["X"], isbn_issn="123")
    use_case = EditBibliography(bibliography_repo, author_repo)
    updated = use_case.execute(added.id, title="A2", authors=["X"], isbn_issn="123")
    assert updated.title == "A2"


def test_edit_bibliography_missing_raises(bibliography_repo, author_repo):
    use_case = EditBibliography(bibliography_repo, author_repo)
    with pytest.raises(BibliographyNotFound):
        use_case.execute(999, title="A", authors=["X"], isbn_issn="123")


def test_add_and_remove_item(bibliography_repo, author_repo, loan_repo):
    bibliography = AddBibliography(bibliography_repo, author_repo).execute(
        title="A", authors=["X"], isbn_issn="123"
    )
    item = AddItem(bibliography_repo).execute(bibliography.id)
    assert item.bibliography_id == bibliography.id

    RemoveItem(bibliography_repo, loan_repo).execute(item.id)
    assert bibliography_repo.get_item(item.id) is None


def test_remove_missing_item_raises(bibliography_repo, loan_repo):
    with pytest.raises(ItemNotFound):
        RemoveItem(bibliography_repo, loan_repo).execute(999)


def test_search_catalog_reports_availability(bibliography_repo, author_repo, loan_repo):
    bibliography = AddBibliography(bibliography_repo, author_repo).execute(
        title="Dune", authors=["Herbert"], isbn_issn="123"
    )
    AddItem(bibliography_repo).execute(bibliography.id)
    AddItem(bibliography_repo).execute(bibliography.id)

    [entry] = SearchCatalog(bibliography_repo, loan_repo).execute("Dune")
    assert entry.total_items == 2
    assert entry.available_items == 2


def test_search_catalog_empty_query_lists_all(bibliography_repo, author_repo, loan_repo):
    AddBibliography(bibliography_repo, author_repo).execute(title="A", authors=["X"], isbn_issn="1")
    AddBibliography(bibliography_repo, author_repo).execute(title="B", authors=["Y"], isbn_issn="2")
    assert len(SearchCatalog(bibliography_repo, loan_repo).execute("")) == 2
