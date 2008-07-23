# TODO: locale isn't distributed yet, since we don't have any localizations
# right now.  Once those are added, we should add it to here
SUBDIRS = \
	accounts \
	admin \
	contrib \
	diffviewer \
	htdocs \
	iphone \
	reports \
	reviews \
	scmtools \
	templates \
	webapi

rbdir = $(pyexecdir)/reviewboard
rb_PYTHON = \
	__init__.py \
	settings.py \
	test.py \
	urls.py

rb_SCRIPTS = \
	devserver.sh \
	manage.py \
	server.sh

rb_DATA = \
	settings_local.py.tmpl

djbletsdir = $(pyexecdir)
nobase_djblets_PYTHON = \
	djblets/__init__.py \
	djblets/auth/__init__.py \
	djblets/auth/forms.py \
	djblets/auth/util.py \
	djblets/auth/views.py \
	djblets/datagrid/__init__.py \
	djblets/datagrid/grids.py \
	djblets/datagrid/templatetags/__init__.py \
	djblets/datagrid/templatetags/datagrid.py \
	djblets/feedview/__init__.py \
	djblets/feedview/feedparser.py \
	djblets/feedview/views.py \
	djblets/feedview/templatetags/__init__.py \
	djblets/feedview/templatetags/feedtags.py \
	djblets/util/templatetags/__init__.py \
	djblets/util/templatetags/djblets_deco.py \
	djblets/util/templatetags/djblets_email.py \
	djblets/util/templatetags/djblets_images.py \
	djblets/util/templatetags/djblets_js.py \
	djblets/util/templatetags/djblets_utils.py \
	djblets/util/__init__.py \
	djblets/util/context_processors.py \
	djblets/util/db.py \
	djblets/util/dbevolution.py \
	djblets/util/decorators.py \
	djblets/util/fields.py \
	djblets/util/misc.py \
	djblets/util/rooturl.py \
	djblets/util/testing.py \
	djblets/util/tests.py \
	djblets/webapi/__init__.py \
	djblets/webapi/auth.py \
	djblets/webapi/core.py \
	djblets/webapi/decorators.py \
	djblets/webapi/errors.py

nobase_djblets_DATA = \
	djblets/datagrid/templates/datagrid/cell.html \
	djblets/datagrid/templates/datagrid/column_header.html \
	djblets/datagrid/templates/datagrid/listview.html \
	djblets/datagrid/templates/datagrid/paginator.html \
	djblets/media/images/datagrid/checkmark.png \
	djblets/media/images/datagrid/header_bg.png \
	djblets/media/images/datagrid/header_bg_primary.png \
	djblets/media/images/datagrid/sort_asc_primary.png \
	djblets/media/images/datagrid/sort_asc_secondary.png \
	djblets/media/images/datagrid/sort_desc_primary.png \
	djblets/media/images/datagrid/sort_desc_secondary.png \
	djblets/media/images/datagrid/unsort.png \
	djblets/media/js/datagrid.js \
	djblets/util/templates/deco/box.html \
	djblets/util/templates/deco/errorbox.html

EXTRA_DIST = \
	$(rb_SCRIPTS) \
	$(rb_DATA) \
	$(nobase_djblets_DATA)

install-data-local:
	mkdir -p -m 1777 ${DESTDIR}${rbdir}/search-index
