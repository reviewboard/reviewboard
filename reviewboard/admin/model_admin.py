"""Administration UI customization for models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.admin import ModelAdmin as DjangoModelAdmin
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

if TYPE_CHECKING:
    from django.db.models import Model
    from django.http import HttpRequest, HttpResponse


class ModelAdmin(DjangoModelAdmin):
    """Base class for administration UI representations of models.

    This should be used instead of :py:class:`django.contrib.admin.ModelAdmin`
    for any new model registrations. It provides additional options for
    Review Board's administration UI.

    Version Added:
        4.0
    """

    #: The template used for any fieldsets on the model's Change Form.
    #:
    #: If not explicitly overridden, ``admin/includes/fieldset.html`` will
    #: be used.
    fieldset_template_name = None

    def response_add(
        self,
        request: HttpRequest,
        obj: Model,
        post_url_continue: (str | None) = None,
    ) -> HttpResponse:
        """Return the response after an object is added.

        If the form was opened with a ``next`` URL, a plain "Save" returns
        there. This lets other pages link to an add form and get the user
        back afterward. "Save and continue editing" and "Save and add
        another" keep their normal behavior.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj (django.db.models.Model):
                The object that was added.

            post_url_continue (str, optional):
                The URL to use for "Save and continue editing".

        Returns:
            django.http.HttpResponse:
            The response to send.
        """
        next_url = request.POST.get('next')

        if (next_url and
            '_continue' not in request.POST and
            '_addanother' not in request.POST and
            '_popup' not in request.POST and
            url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure())):
            # Run the default handling for its success message, then
            # replace the redirect target.
            super().response_add(request, obj, post_url_continue)

            return HttpResponseRedirect(next_url)

        return super().response_add(request, obj, post_url_continue)
