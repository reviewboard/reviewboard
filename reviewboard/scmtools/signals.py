from django.dispatch import Signal


#: Emitted before a file existence check occurs.
#:
#: Args:
#:     path (unicode):
#:         The path of the file being checked.
#:
#:     revision (unicode):
#:         The revision of the file being checked.
#:
#:     request (django.http.HttpRequest):
#:         The current request.
checking_file_exists = Signal()


#: Emitted after a file existence check occurs.
#:
#: Args:
#:     path (unicode):
#:         The path of the file being checked.
#:
#:     revision (unicode):
#:         The revision of the file being checked.
#:
#:     request (django.http.HttpRequest):
#:         The current request.
checked_file_exists = Signal()


#: Emitted before a file is fetched.
#:
#: Args:
#:     path (unicode):
#:         The path of the file being checked.
#:
#:     revision (unicode):
#:         The revision of the file being checked.
#:
#:     request (django.http.HttpRequest):
#:         The current request.
fetching_file = Signal()


#: Emitted after a file is fetched.
#:
#: Args:
#:     path (unicode):
#:         The path of the file being checked.
#:
#:     revision (unicode):
#:         The revision of the file being checked.
#:
#:     request (django.http.HttpRequest):
#:         The current request.
fetched_file = Signal()
