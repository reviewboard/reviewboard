from django.conf.urls.defaults import patterns, url


urlpatterns = patterns("reviewboard.accounts.views",
    url(r'^register/$', 'account_register',
        { 'next_url': 'dashboard' }, name="register"),
    url(r'^preferences/$', 'user_preferences', name="user-preferences"),
)

urlpatterns += patterns("django.contrib.auth.views",
    url(r'^login/$', 'login',
        {
            'template_name': 'accounts/login.html',
            'redirect_field_name': 'next_page',
        },
        name='login'),
    url(r'^recover/$',
        'password_reset',
        {'template_name': 'accounts/password_reset.html',
         'email_template_name': 'accounts/password_reset_email.txt'},
        name='recover'),
    url(r'^recover/done/$',
        'password_reset_done',
        {'template_name': 'accounts/password_reset_done.html'}),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        'password_reset_confirm',
        {'template_name': 'accounts/password_reset_confirm.html'},
        name='password-reset-confirm'),
    url(r'^reset/done/$',
        'password_reset_complete',
        {'template_name': 'accounts/password_reset_complete.html'}),
)
