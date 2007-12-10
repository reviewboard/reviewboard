# TODO: locale isn't distributed yet, since we don't have any localizations
# right now.  Once those are added, we should add it to here
SUBDIRS =		\
	accounts	\
	contrib		\
	datagrid	\
	diffviewer	\
	htdocs		\
	iphone		\
	reports		\
	reviews		\
	scmtools	\
	templates	\
	utils

rbdir = $(pyexecdir)/reviewboard
rb_PYTHON =		\
	__init__.py	\
	settings.py	\
	test.py		\
	urls.py

rb_SCRIPTS =		\
	devserver.sh	\
	manage.py	\
	server.sh

djbletsdir = $(pyexecdir)
nobase_djblets_PYTHON =			\
	djblets/__init__.py		\
	djblets/auth/__init__.py	\
	djblets/auth/forms.py		\
	djblets/auth/util.py		\
	djblets/auth/views.py		\
	djblets/util/__init__.py	\
	djblets/util/db.py		\
	djblets/util/decorators.py	\
	djblets/util/misc.py		\
	djblets/util/testing.py

EXTRA_DIST = $(rb_SCRIPTS)
