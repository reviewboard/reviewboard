from __future__ import unicode_literals

from django.conf.urls import patterns, url

from reviewboard.accounts.forms.auth import AuthenticationForm
from reviewboard.accounts.views import MyAccountView


urlpatterns = patterns(
    "reviewboard.accounts.views",

    url(r'^register/$', 'account_register',
        {'next_url': 'dashboard'}, name="register"),
    url(r'^preferences/$',
        MyAccountView.as_view(),
        name="user-preferences"),
)

urlpatterns += patterns(
    "django.contrib.auth.views",

    url(r'^login/$', 'login',
        {
            'template_name': 'accounts/login.html',
            'authentication_form': AuthenticationForm,
        },
        name='login'),
    url(r'^logout/$', 'logout_then_login', name='logout'),

    url(r'^recover/$',
        'password_reset',
        {
            'template_name': 'accounts/password_reset.html',
            'email_template_name': 'accounts/password_reset_email.txt'
        },
        name='recover'),
    url(r'^recover/done/$',
        'password_reset_done',
        {'template_name': 'accounts/password_reset_done.html'},
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/'
        '(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        'password_reset_confirm',
        {'template_name': 'accounts/password_reset_confirm.html'},
        name='password_reset_confirm'),
    url(r'^reset/done/$',
        'password_reset_complete',
        {'template_name': 'accounts/password_reset_complete.html'},
        name='password_reset_complete'),
)
