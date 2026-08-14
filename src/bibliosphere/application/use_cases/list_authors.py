from bibliosphere.domain.entities import Author
from bibliosphere.domain.ports import AuthorRepository


class ListAuthors:
    def __init__(self, author_repository: AuthorRepository):
        self._authors = author_repository

    def execute(self) -> list[Author]:
        return self._authors.list_all()
