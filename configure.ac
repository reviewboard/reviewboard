AC_PREREQ(2.57)
AC_INIT([Review Board], [0.4], [http://code.google.com/p/reviewboard/issues/entry], [reviewboard])

AC_CONFIG_MACRO_DIR([m4])
AC_CONFIG_SRCDIR([__init__.py])
AC_CONFIG_HEADERS([config.h])

AM_INIT_AUTOMAKE([1.9 dist-bzip2])

AM_MAINTAINER_MODE
AC_PROG_INSTALL
AM_PATH_PYTHON
AM_PATH_DJANGO

AC_OUTPUT([
Makefile
accounts/Makefile
contrib/Makefile
diffviewer/Makefile
htdocs/Makefile
iphone/Makefile
reports/Makefile
reviews/Makefile
scmtools/Makefile
templates/Makefile
utils/Makefile
webapi/Makefile
])
