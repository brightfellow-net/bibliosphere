from dataclasses import dataclass

from bibliosphere.application.use_cases.add_bibliography import AddBibliography
from bibliosphere.application.use_cases.add_item import AddItem
from bibliosphere.application.use_cases.authenticate_user import AuthenticateUser
from bibliosphere.application.use_cases.checkout_item import CheckoutItem
from bibliosphere.application.use_cases.create_member import CreateMember
from bibliosphere.application.use_cases.delete_bibliography import DeleteBibliography
from bibliosphere.application.use_cases.edit_bibliography import EditBibliography
from bibliosphere.application.use_cases.edit_member import EditMember
from bibliosphere.application.use_cases.generate_member_id import GenerateMemberId
from bibliosphere.application.use_cases.list_authors import ListAuthors
from bibliosphere.application.use_cases.list_loan_history import ListLoanHistory
from bibliosphere.application.use_cases.list_member_loans import ListMemberLoans
from bibliosphere.application.use_cases.list_members import ListMembers
from bibliosphere.application.use_cases.list_open_loans import ListOpenLoans
from bibliosphere.application.use_cases.remove_item import RemoveItem
from bibliosphere.application.use_cases.return_item import ReturnItem
from bibliosphere.application.use_cases.search_catalog import SearchCatalog
from bibliosphere.application.use_cases.set_bibliography_authors import SetBibliographyAuthors


@dataclass
class UseCases:
    """Groups all use case instances for injection into the presentation layer.

    Built once by the composition root (main.py); the GUI only ever calls .execute()
    on these members, never touching infrastructure directly.
    """

    authenticate_user: AuthenticateUser
    search_catalog: SearchCatalog
    add_bibliography: AddBibliography
    edit_bibliography: EditBibliography
    delete_bibliography: DeleteBibliography
    set_bibliography_authors: SetBibliographyAuthors
    list_authors: ListAuthors
    add_item: AddItem
    remove_item: RemoveItem
    list_members: ListMembers
    generate_member_id: GenerateMemberId
    create_member: CreateMember
    edit_member: EditMember
    checkout_item: CheckoutItem
    return_item: ReturnItem
    list_member_loans: ListMemberLoans
    list_open_loans: ListOpenLoans
    list_loan_history: ListLoanHistory
