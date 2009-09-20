#!/bin/sh

if [ ! -e "reviewboard/manage.py" ]; then
	echo "This must be ran from the top-level source tree."
	exit 1
fi

if [ ! -e "settings_local.py" ]; then
	echo "You must create a settings_local.py in the top-level source"
	echo "directory. You can use contrib/conf/settings_local.py.tmpl"
	echo "as a basis."
	exit 1
fi

if [ ! -e "reviewboard/htdocs/media/djblets" ]; then
	echo "You must set up the Djblets media path. Create a symlink pointing"
	echo "to a development djblets/media directory and name it"
	echo "reviewboard/htdocs/media/djblets"
	echo
	echo "For example:"
	echo "$ ln -s /path/to/djblets/djblets/media reviewboard/htdocs/media/djblets"
	exit 1
fi

if [ ! -e "ReviewBoard.egg-info" ]; then
	./setup.py egg_info
fi

./reviewboard/manage.py \
	runserver 0.0.0.0:8080 \
	--adminmedia=reviewboard/htdocs/media/admin/
