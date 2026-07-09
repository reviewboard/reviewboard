"""Admin definitions for the hostingsvcs app."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from reviewboard.admin import ModelAdmin, admin_site
from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.models import HostingServiceAccount

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from django.db.models import QuerySet
    from django.http import HttpRequest


class HostingServiceAccountAdmin(ModelAdmin):
    """Admin definitions for the HostingServiceAccount model."""

    list_display = ('username', 'service_name', 'visible', 'local_site')
    raw_id_fields = ('local_site',)

    def get_deleted_objects(
        self,
        objs: (
            Sequence[HostingServiceAccount] |
            QuerySet[HostingServiceAccount]
        ),
        request: HttpRequest,
    ) -> tuple[list[Any], dict[str, int], set[str], list[str]]:
        """Return the objects that would be deleted, and what blocks it.

        This asks each account's hosting service for state that depends on the
        accounts but that the database does not protect. A service can store
        such a reference in JSON data rather than as a foreign key, in which
        case nothing at the database level reports the dependency.

        Reporting it here means the admin UI refuses the deletion up front and
        names what is in the way, the same as it does for a protected foreign
        key.

        Version Added:
            9.0

        Args:
            objs (list of reviewboard.hostingsvcs.models.
                  HostingServiceAccount):
                The accounts being deleted.

            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            tuple:
            A 4-tuple of:

            Tuple:
                0 (list):
                    The nested list of objects to delete.

                1 (dict):
                    A mapping of model name to the number of objects to delete.

                2 (set of str):
                    The set of permissions needed to perform the deletion.

                3 (list of str):
                    The list of objects blocking the deletion.
        """
        deleted_objects, model_count, perms_needed, protected = \
            super().get_deleted_objects(objs, request)

        accounts_by_service: dict[str, list[HostingServiceAccount]] = \
            defaultdict(list)

        for account in objs:
            accounts_by_service[account.service_name].append(account)

        blocking: list[str] = []

        for service_id, accounts in accounts_by_service.items():
            service = hosting_service_registry.get_hosting_service(service_id)

            if service is not None:
                blockers = service.get_protected_objects_for_account_deletion(
                    accounts)

                blocking += [
                    str(blocker)
                    for blocker in blockers
                ]

        return (
            deleted_objects,
            model_count,
            perms_needed,
            list(protected) + blocking,
        )


admin_site.register(HostingServiceAccount, HostingServiceAccountAdmin)
