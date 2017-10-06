#!/bin/sh

./docsmanage.py dumpdata --indent=4 \
	auth \
	accounts \
	attachments \
	changedescs \
	diffviewer \
	extensions \
	hostingsvcs \
	notifications \
	oauth2_provider \
	oauth \
	reviews \
	scmtools \
	site \
	webapi \
	> fixtures/initial_data.json
