from django.conf import settings
from django.conf.urls.defaults import patterns, url


urlpatterns = patterns("reviewboard.accounts.views",
    url(r'^register/$', 'account_register', name="register"),
    url(r'^preferences/$', 'user_preferences',
        name="user-preferences"),
)

urlpatterns += patterns("djblets.auth.views",
    url(r'^login/$', 'login',
        {'next_page': settings.SITE_ROOT + 'dashboard/'},
        name="login"),
)
