from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect
from djblets.auth.views import register
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.accounts.backends import get_enabled_auth_backends
from reviewboard.accounts.forms.registration import RegistrationForm
from reviewboard.accounts.models import Profile
from reviewboard.accounts.pages import get_page_classes
from reviewboard.accounts.signals import user_registered


@csrf_protect
def account_register(request, next_url='dashboard'):
    """
    Handles redirection to the appropriate registration page, depending
    on the authentication type the user has configured.
    """
    siteconfig = SiteConfiguration.objects.get_current()
    auth_backends = get_enabled_auth_backends()

    if (auth_backends[0].supports_registration and
            siteconfig.get("auth_enable_registration")):
        response = register(request, next_page=reverse(next_url),
                            form_class=RegistrationForm)

        if request.user.is_authenticated():
            # This will trigger sending an e-mail notification for
            # user registration, if enabled.
            user_registered.send(sender=None, user=request.user)

        return response

    return HttpResponseRedirect(reverse("login"))


@csrf_protect
@login_required
def user_preferences(request, template_name='accounts/prefs.html'):
    """Displays the My Account page containing user preferences.

    The page will be built based on registered pages and forms. This makes
    it easy to plug in new bits of UI for the page, which is handy for
    extensions that want to offer customization for users.
    """
    profile, is_new = Profile.objects.get_or_create(user=request.user)

    pages = [
        page_cls(request, request.user)
        for page_cls in get_page_classes()
    ]

    forms = {}

    # Store a mapping of form IDs to form instances, and check for duplicates.
    for page in pages:
        for form in page.forms:
            # This should already be handled during form registration.
            assert form.form_id not in forms, \
                'Duplicate form ID %s (on page %s)' % (
                    form.form_id, page.page_id)

            forms[form.form_id] = form

    if request.POST:
        form_id = request.POST.get('form_target')

        if form_id is None:
            return HttpResponseBadRequest()

        if form_id not in forms:
            return Http404

        # Replace the form in the list with a new instantiation containing
        # the form data. If we fail to save, this will ensure the error is
        # shown on the page.
        old_form = forms[form_id]
        form_cls = old_form.__class__
        form = form_cls(old_form.page, request, request.user, request.POST)
        forms[form_id] = form

        if form.is_valid():
            form.save()

            return HttpResponseRedirect(request.path)

    return render(request, template_name, {
        'pages': pages,
        'forms': forms.values(),
    })
