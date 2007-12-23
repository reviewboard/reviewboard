AC_DEFUN([AM_PATH_DJANGO], [
AC_REQUIRE([AM_PATH_PYTHON])
AM_CHECK_PYMOD(django,, have_django="yes", have_django="no")
if test "x$have_django" = "xyes" ; then
    prog="
import django
print django.__path__[[0]]"

    DJANGO_PATH=`$PYTHON -c "$prog"`
else
    DJANGO_PATH="/path/to/django"
fi
AC_SUBST(DJANGO_PATH)
])
