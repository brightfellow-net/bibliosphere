import pytest

from tests.fakes import FakeAuthorRepository, FakeBibliographyRepository, FakeLoanRepository, FakeMemberRepository


@pytest.fixture
def author_repo():
    return FakeAuthorRepository()


@pytest.fixture
def bibliography_repo(author_repo):
    return FakeBibliographyRepository(author_repo)


@pytest.fixture
def member_repo():
    return FakeMemberRepository()


@pytest.fixture
def loan_repo():
    return FakeLoanRepository()
