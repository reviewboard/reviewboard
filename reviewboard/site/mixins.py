"""Mixins for LocalSite-related views and forms."""

from __future__ import unicode_literals

import logging

import django
from django.contrib.auth.models import User
from django.db import models
from django.utils import six
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from djblets.db.query import get_object_or_none
from djblets.forms.fields import ConditionsField

from reviewboard.admin.form_widgets import RelatedObjectWidget
from reviewboard.site.decorators import check_local_site_access
from reviewboard.site.models import LocalSite


logger = logging.getLogger(__name__)


class CheckLocalSiteAccessViewMixin(object):
    """Generic view mixin to check if a user has access to the Local Site.

    It's important to note that this does not check for login access.
    This is just a convenience around using the
    :py:func:`@check_local_site_access
    <reviewboard.site.decorators.check_local_site_access>` decorator for
    generic views.

    The :py:attr:`local_site` attribute will be set on the class for use in
    the view.

    Attributes:
        local_site (reviewboard.site.models.LocalSite):
            The Local Site being accessed, or ``None``.
    """

    @method_decorator(check_local_site_access)
    def dispatch(self, request, local_site=None, *args, **kwargs):
        """Dispatch a HTTP request to the right handler.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site being accessed, if any.

            *args (tuple):
                Positional arguments to pass to the handler.

            **kwargs (tuple):
                Keyword arguments to pass to the handler.

                These will be arguments provided by the URL pattern.

        Returns:
            django.http.HttpResponse:
            The resulting HTTP response to send to the client.
        """
        self.local_site = local_site

        return super(CheckLocalSiteAccessViewMixin, self).dispatch(
            request, *args, **kwargs)


class LocalSiteAwareModelFormMixin(object):
    """Mixin for model forms that associate with Local Sites.

    This mixin allows model forms to be bound to a Local Site, which will
    then limit all relation fields to objects bound to the same site. This
    allows the construction of forms that could be modified by a Local Site
    administrator without risk of data outside the Local Site being used. The
    bound Local Site will always be forced, and the field will not appear on
    the form.

    When not bound to a Local Site, relations across all Local Sites (and
    those not associated with a Local Site) are allowed, but if a Local Site
    is being assigned when posting to the form, all related objects will be
    validated against that Local Site.

    Attributes:
        cur_local_site (reviewboard.site.models.LocalSite):
            The Local Site that's either been bound to the form or provided
            in posted data. This will be ``None`` if no Local Site is being
            used.

        limited_to_local_site (reviewboard.site.models.LocalSite):
            The Local Site bound to the form. This will be ``None`` if no
            Local Site is bound.

        request (django.http.HttpRequest):
            The HTTP request provided to the form. This may be ``None`` if no
            request was provided.
    """

    #: The name of the Local Site field on the form.
    local_site_field_name = 'local_site'

    #: Whether the form needs the 'request' argument.
    form_needs_request = False

    def __init__(self, data=None, initial={}, request=None, *args, **kwargs):
        """Initialize the form.

        Args:
            data (dict, optional):
                Posted data for the form.

            initial (dict, optional):
                Initial data for the form.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client. This is used for logging
                of access errors, and will be passed to the underlying form
                if :py:attr:`form_needs_request` is ``True``.

            *args (tuple):
                Positional arguments to pass to the parent form.

            **kwargs (dict):
                Keyword arguments to pass to the parent form.

        Keyword Args:
            limit_to_local_site (reviewboard.site.models.LocalSite, optional):
                A specific Local Site to bind the form to.

            request (django.http.HttpRequest, optional):
                The HTTP request from the client.

        Raises:
            ValueError:
                An object instance was provided to the form that isn't
                compatible with the
                :py:class:`~reviewboard.site.models.LocalSite` provided in
                ``limit_to_local_site``.
        """
        local_site = kwargs.pop('limit_to_local_site', None)

        if self.form_needs_request:
            kwargs['request'] = request

        self.limited_to_local_site = local_site

        local_site_field_name = self.local_site_field_name

        if local_site is None:
            local_site_id = None

            if data and data.get(local_site_field_name):
                try:
                    local_site_id = int(data[local_site_field_name])
                except ValueError:
                    local_site_id = None

            if local_site_id is not None:
                local_site = get_object_or_none(LocalSite, pk=local_site_id)
            elif initial and initial.get(local_site_field_name):
                local_site = initial[local_site_field_name]

        if data is not None and local_site:
            # Always use the assigned Local Site in the model data. We
            # don't want to allow this to ever be overridden. We'll delete
            # here and then assign after the constructor does its thing.
            data = data.copy()
            data[local_site_field_name] = local_site.pk

        self.cur_local_site = local_site

        super(LocalSiteAwareModelFormMixin, self).__init__(
            data=data,
            initial=initial,
            *args,
            **kwargs)

        # Prepare to patch up some fields. We have a few special types we'll
        # be dealing with.
        self._conditions_fields = []
        self._related_obj_fields = []
        self._queryset_fields = []
        self._patched_local_sites = False

        for field_name, field in six.iteritems(self.fields):
            if isinstance(field.widget, RelatedObjectWidget):
                self._related_obj_fields.append(field)
            elif isinstance(field, ConditionsField):
                self._conditions_fields.append(field)
                field.choice_kwargs['request'] = request

            if getattr(field, 'queryset', None) is not None:
                self._queryset_fields.append(field)

        if self.limited_to_local_site is not None:
            if self.instance is not None:
                if self.instance.pk is None:
                    # This is a new instance, so force its Local Site now.
                    self.instance.local_site = local_site
                elif self.instance.local_site != local_site:
                    # Something went very wrong, and an instance is now in our
                    # form that isn't part of this Local Site. Log this and
                    # bail out now.
                    logger.error('Attempted to pass instance %r with '
                                 'LocalSite "%s" to form %r. Only LocalSite '
                                 '"%s" is permitted.',
                                 self.instance,
                                 self.instance.local_site,
                                 self.__class__,
                                 local_site,
                                 request=request)

                    raise ValueError(
                        _('The provided instance is not associated with a '
                          'LocalSite compatible with this form. Please '
                          'contact support.'))

            # We never want to show a "Local Site" field, so let's get rid of
            # it.
            del self.fields[local_site_field_name]

            # Go through the fields and widgets and start limiting querysets
            # and other choices.
            local_site_name = local_site.name

            for field in self._related_obj_fields:
                field.widget.local_site_name = local_site_name

            for field in self._conditions_fields:
                field.choice_kwargs['local_site'] = local_site

            for field in self._queryset_fields:
                self._patch_field_local_site_queryset(field, local_site)

            self._patched_local_sites = True

    def full_clean(self):
        """Perform a full clean the form.

        This wraps the typical form cleaning process by first ensuring that
        all relation fields limit their choices to objects on the bound
        Local Site (if one is set), allowing validation to work naturally on
        each field. It then invokes the standard form cleaning logic, and
        then restores the choices.

        Returns:
            dict:
            The cleaned data from the form.

        Raises:
            django.core.exceptions.ValidationError:
                The form failed to validate.
        """
        local_site = self.cur_local_site

        assert (self.limited_to_local_site is None or
                self.limited_to_local_site == local_site)

        if local_site is None:
            local_site_name = None
        else:
            local_site_name = local_site.name

        # Go through the fields and widgets and start limiting querysets
        # and other choices.
        old_values = {}

        # Only perform this work if we didn't do it during construction.
        if not self._patched_local_sites:
            for field in self._related_obj_fields:
                old_values[field.widget] = ('local_site_name',
                                            field.widget.local_site_name)
                field.widget.local_site_name = local_site_name

            for field in self._conditions_fields:
                old_values[field] = ('choice_kwargs',
                                     field.choice_kwargs.copy())
                field.choice_kwargs['local_site'] = local_site

            for field in self._queryset_fields:
                old_queryset = self._patch_field_local_site_queryset(
                    field, local_site)

                if old_queryset is not None:
                    old_values[field] = ('queryset', old_queryset)

        try:
            return super(LocalSiteAwareModelFormMixin, self).full_clean()
        finally:
            # Restore the values so that the original options are available
            # if the form is shown again (due to errors).
            for obj, (attr, value) in six.iteritems(old_values):
                setattr(obj, attr, value)

    def _clean_fields(self):
        """Clean the fields on the form.

        This overrides the standard form field cleaning logic to ensure that
        a Local Site is available in the cleaned data if binding to a Local
        Site. This is required because in this situation, the field will not
        be present on the form, even though other clean methods may require
        it.
        """
        if self.limited_to_local_site is not None:
            self.cleaned_data[self.local_site_field_name] = \
                self.limited_to_local_site

        super(LocalSiteAwareModelFormMixin, self)._clean_fields()

    def _patch_field_local_site_queryset(self, field, local_site):
        """Patch the queryset on a field to be bound to a Local Site.

        The field will only be patched if it contains a ``queryset`` attribute
        and its related model type contains a known attribute for associating
        with a :py:class:`~reviewboard.site.models.LocalSite`.

        Note that if the queryset matches users, then we only perform the
        patching if the model instance will have an associated
        :py:class:`~reviewboard.site.models.LocalSite`. This allows any user
        (whether or not they're on a Local Site) to be associated with
        instances not on a Local Site, preserving the behavior we've had for
        many years.

        If the queryset matches any other type of model, then we're more
        strict, requiring the object's Local Site value to be the same as
        what's being passed in to this method.

        Args:
            field (django.forms.Field):
                The field to patch.

            local_site (reviewboard.site.models.LocalSite):
                The Local Site to bind the queryset to.

        Returns:
            django.db.models.query.QuerySet:
            The old queryset for the field. This will be ``None`` if the
            queryset was not patched.
        """
        queryset = getattr(field, 'queryset', None)
        old_queryset = None

        if (queryset is not None and
            (local_site is not None or
             not issubclass(queryset.model, User))):
            local_site_field_name = \
                self._get_rel_local_site_field_name(queryset.model)

            if local_site_field_name:
                old_queryset = queryset
                field.queryset = queryset.filter(**{
                    local_site_field_name: local_site,
                })

        return old_queryset

    def _get_rel_local_site_field_name(self, model):
        """Return the Local Site field name on a model.

        This checks for the presence of a ``local_site`` or ``local_site_set``
        field.

        Args:
            model (django.db.models.Model):
                The model containing the field.

        Returns:
            unicode:
            The name of the Local Site field, if found. If a field with a
            supported name is not present, ``None`` will be returned.
        """
        meta = model._meta

        for local_site_field_name in ('local_site', 'local_site_set'):
            try:
                meta.get_field(local_site_field_name)

                return local_site_field_name
            except models.FieldDoesNotExist:
                continue

        return None
