from django.conf import settings
from django.urls import include, path, re_path
from django.contrib.auth import views as auth_views
from djblets.urls.resolvers import DynamicURLResolver

from reviewboard.accounts.forms.auth import AuthenticationForm
from reviewboard.accounts.views import LoginView
from reviewboard.accounts import views as accounts_views


sso_dynamic_urls = DynamicURLResolver()


urlpatterns = [
    path('login/',
         LoginView.as_view(
             template_name='accounts/login.html',
             authentication_form=AuthenticationForm),
         name='login'),
    path('logout/',
         auth_views.logout_then_login,
         name='logout'),
    path('preferences/',
         accounts_views.MyAccountView.as_view(),
         name='user-preferences'),
    re_path(r'^preferences/preview-email/password-changed/'
            r'(?P<message_format>text|html)/$',
            accounts_views.preview_password_changed_email,
            name='preview-password-change-email'),
    path('register/',
         accounts_views.account_register,
         kwargs={
             'next_url': 'dashboard',
         },
         name='register'),
    path('recover/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset.html',
             email_template_name='accounts/password_reset_email.txt',
             extra_email_context={
                 'PRODUCT_NAME': settings.PRODUCT_NAME,
             }),
         name='recover'),
    path('recover/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html'),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html'),
         name='password_reset_complete'),
    re_path(r'^preferences/oauth2-application/(?:(?P<app_id>[0-9]+)/)?$',
            accounts_views.edit_oauth_app,
            name='edit-oauth-app'),
    path('preferences/preview-email/password-changed/',
         accounts_views.preview_password_changed_email,
         name='preview-password-change-email'),
    path('sso/', include(([sso_dynamic_urls], 'accounts'), namespace='sso')),
]
