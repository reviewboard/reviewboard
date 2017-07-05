from __future__ import unicode_literals

from django.conf.urls import url
from django.contrib.auth import views as auth_views

from reviewboard.accounts.forms.auth import AuthenticationForm
from reviewboard.accounts import views as accounts_views


urlpatterns = [
    url(r'^login/$',
        auth_views.login,
        kwargs={
            'template_name': 'accounts/login.html',
            'authentication_form': AuthenticationForm,
        },
        name='login'),
    url(r'^logout/$',
        auth_views.logout_then_login,
        name='logout'),
    url(r'^preferences/$',
        accounts_views.MyAccountView.as_view(),
        name='user-preferences'),
    url(r'^preferences/preview-email/password-changed/'
        r'(?P<message_format>(text|html))/$',
        'preview_password_changed_email',
        name='preview-password-change-email'),
    url(r'^register/$',
        accounts_views.account_register,
        kwargs={
            'next_url': 'dashboard',
        },
        name='register'),
    url(r'^recover/$',
        auth_views.password_reset,
        kwargs={
            'template_name': 'accounts/password_reset.html',
            'email_template_name': 'accounts/password_reset_email.txt'
        },
        name='recover'),
    url(r'^recover/done/$',
        auth_views.password_reset_done,
        kwargs={
            'template_name': 'accounts/password_reset_done.html',
        },
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        auth_views.password_reset_confirm,
        kwargs={
            'template_name': 'accounts/password_reset_confirm.html',
        },
        name='password_reset_confirm'),
    url(r'^reset/done/$',
        auth_views.password_reset_complete,
        kwargs={
            'template_name': 'accounts/password_reset_complete.html',
        },
        name='password_reset_complete'),
    url(r'^preferences/oauth2-application/(?:(?P<app_id>[0-9]+)/)?$',
        accounts_views.edit_oauth_app,
        name='edit-oauth-app'),
    url(r'^preferences/preview-email/password-changed/$',
        accounts_views.preview_password_changed_email,
        name='preview-password-change-email'),
]
