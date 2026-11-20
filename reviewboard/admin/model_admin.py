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
        next_url = self._get_next_url(request)

        if next_url:
            # Run the default handling for its success message, then
            # replace the redirect target.
            super().response_add(request, obj, post_url_continue)

            return HttpResponseRedirect(next_url)

        return super().response_add(request, obj, post_url_continue)

    def response_change(
        self,
        request: HttpRequest,
        obj: Model,
    ) -> HttpResponse:
        """Return the response after an object is changed.

        If the form was opened with a ``next`` URL, a plain "Save" returns
        there. This lets other pages link to a change form and get the user
        back afterward. The other save buttons keep their normal behavior.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj (django.db.models.Model):
                The object that was changed.

        Returns:
            django.http.HttpResponse:
            The response to send.
        """
        next_url = self._get_next_url(request)

        if next_url:
            # Run the default handling for its success message, then
            # replace the redirect target.
            super().response_change(request, obj)

            return HttpResponseRedirect(next_url)

        return super().response_change(request, obj)

    def response_delete(
        self,
        request: HttpRequest,
        obj_display: str,
        obj_id: int,
    ) -> HttpResponse:
        """Return the response after an object is deleted.

        If the delete was started from a form opened with a ``next`` URL,
        this returns there instead of the change list.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            obj_display (str):
                The display name of the deleted object.

            obj_id (int):
                The ID of the deleted object.

        Returns:
            django.http.HttpResponse:
            The response to send.
        """
        next_url = self._get_next_url(request)

        if next_url:
            # Run the default handling for its success message, then
            # replace the redirect target.
            super().response_delete(request, obj_display, obj_id)

            return HttpResponseRedirect(next_url)

        return super().response_delete(request, obj_display, obj_id)

    def _get_next_url(
        self,
        request: HttpRequest,
    ) -> str | None:
        """Return a safe ``next`` URL to redirect to after saving or deleting.

        Version Added:
            9.0

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

        Returns:
            str:
            The URL to redirect to, or ``None`` to use the default behavior.
        """
        post = request.POST
        next_url = post.get('next')

        if (next_url and
            '_continue' not in post and
            '_addanother' not in post and
            '_saveasnew' not in post and
            '_popup' not in post and
            url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure())):
            return next_url

        return None
