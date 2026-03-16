"""CRUD operations package - re-exports all domain modules for backward compatibility."""

from src.database.crud.users import (
    create_user,
    get_user_by_id,
    get_user_by_email,
    list_users,
    update_user,
    update_user_password,
)
from src.database.crud.projects import (
    create_project,
    get_project,
    get_project_by_code,
    get_all_projects,
    get_project_counts,
    get_document_req_counts,
    update_project,
    delete_project,
    get_documents_by_project,
)
from src.database.crud.documents import (
    create_document,
    get_document,
    get_all_documents,
    update_document_status,
)
from src.database.crud.sections import (
    create_section,
    get_sections_by_document,
)
from src.database.crud.requirements import (
    create_requirement,
    get_requirement,
    get_requirements_by_document,
    accept_requirement,
    reject_requirement,
    edit_requirement,
    assign_requirement,
    update_requirement_status,
    bulk_create_requirements,
)
from src.database.crud.metrics import (
    get_coverage_metrics,
    create_coverage_metrics,
)
from src.database.crud.requirement_history import (
    create_history_entry,
    get_requirement_history,
)
from src.database.crud.comments import (
    create_comment,
    get_comments,
    get_comment,
    delete_comment,
    delete_comment_by_id,
)
from src.database.crud.dashboard import get_dashboard_stats, get_my_dashboard_stats
from src.database.crud.dictionaries import (
    VALID_DICT_TYPES,
    get_dictionary_items,
    get_dictionary_item,
    create_dictionary_item,
    update_dictionary_item,
    delete_dictionary_item,
    seed_dictionary_defaults,
)
from src.database.crud.requirement_links import (
    get_links_for_requirement,
    get_outgoing_links,
    get_incoming_links,
    create_link,
    delete_link,
    get_link,
)

__all__ = [
    # users
    "create_user",
    "get_user_by_id",
    "get_user_by_email",
    "list_users",
    "update_user",
    "update_user_password",
    # projects
    "create_project",
    "get_project",
    "get_project_by_code",
    "get_all_projects",
    "get_project_counts",
    "get_document_req_counts",
    "update_project",
    "delete_project",
    "get_documents_by_project",
    # documents
    "create_document",
    "get_document",
    "get_all_documents",
    "update_document_status",
    # sections
    "create_section",
    "get_sections_by_document",
    # requirements
    "create_requirement",
    "get_requirement",
    "get_requirements_by_document",
    "accept_requirement",
    "reject_requirement",
    "edit_requirement",
    "assign_requirement",
    "update_requirement_status",
    "bulk_create_requirements",
    # metrics
    "get_coverage_metrics",
    "create_coverage_metrics",
    # comments
    "create_comment",
    "get_comments",
    "get_comment",
    "delete_comment",
    "delete_comment_by_id",
    # requirement_history
    "create_history_entry",
    "get_requirement_history",
    # dashboard
    "get_dashboard_stats",
    "get_my_dashboard_stats",
    # dictionaries
    "VALID_DICT_TYPES",
    "get_dictionary_items",
    "get_dictionary_item",
    "create_dictionary_item",
    "update_dictionary_item",
    "delete_dictionary_item",
    "seed_dictionary_defaults",
    # requirement_links
    "get_links_for_requirement",
    "get_outgoing_links",
    "get_incoming_links",
    "create_link",
    "delete_link",
    "get_link",
]
