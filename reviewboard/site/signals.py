from django.dispatch import Signal


#: Emitted when a user is added to a local site.
#:
#: Args:
#:     user (django.contrib.auth.models.User):
#:         The user which was added.
#:
#:     localsite (reviewboard.site.models.LocalSite):
#:         The site the user was added to.
local_site_user_added = Signal()
