# TODO: I'd like to make these .conf.in, and then process them with autoconf to
# embed the prefix into them so that a user can just point their web server at
# the desired config file and it'll all work.
rbdir = $(pyexecdir)/reviewboard/contrib
nobase_rb_DATA =			\
	conf/apache-fastcgi.conf	\
	conf/apache-modpython.conf	\
	conf/lighttpd.conf

# I decided, for now, *not* to include "development" scripts such as db2wiki.py
# or django profiling tools.  We may change this later.
nobase_rb_SCRIPTS =			\
	db/backup-db.py			\
	db/load-db.py			\
	i18n/compile-messages.py	\
	i18n/make-messages.py		\
	i18n/unique-messages.py		\
	tools/post-review

EXTRA_DIST =			\
	$(nobase_rb_DATA)	\
	$(nobase_rb_SCRIPTS)
