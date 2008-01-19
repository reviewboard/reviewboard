rbdir = $(pyexecdir)/reviewboard/diffviewer
nobase_rb_PYTHON =			\
	__init__.py			\
	diffutils.py			\
	forms.py			\
	models.py			\
	myersdiff.py			\
	parser.py			\
	smdiff.py			\
	tests.py			\
	views.py			\
	templatetags/__init__.py	\
	templatetags/difftags.py

nobase_rb_DATA =				\
	testdata/foo				\
	testdata/orig_src/foo.c			\
	testdata/orig_src/nuke_me		\
	testdata/orig_src/README		\
	testdata/orig_src/README.crlf		\
	testdata/diffs/context/foo.c.diff	\
	testdata/diffs/context/nuke_me.diff	\
	testdata/diffs/context/README.diff	\
	testdata/diffs/context/README.crlf.diff	\
	testdata/diffs/unified/foo.c.diff	\
	testdata/diffs/unified/nuke_me.diff	\
	testdata/diffs/unified/README.diff	\
	testdata/diffs/unified/README.crlf.diff	\
	testdata/new_src/foo.c			\
	testdata/new_src/README

EXTRA_DIST = $(nobase_rb_DATA)
