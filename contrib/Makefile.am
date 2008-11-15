rbdir = $(pyexecdir)/reviewboard/contrib
data_in_files =				\
	conf/apache-fastcgi.conf.in	\
	conf/apache-modpython.conf.in	\
	conf/lighttpd.conf.in		\
	conf/search-cron.conf.in

# I decided, for now, *not* to include "development" scripts such as db2wiki.py
# or django profiling tools.  We may change this later.
nobase_rb_SCRIPTS =			\
	db/backup-db.py			\
	db/load-db.py			\
	i18n/compile-messages.py	\
	i18n/make-messages.py		\
	i18n/unique-messages.py		\
	tools/post-review		\
	tools/rb-site

EXTRA_DIST =			\
	$(data_in_files)	\
	$(nobase_rb_SCRIPTS)
