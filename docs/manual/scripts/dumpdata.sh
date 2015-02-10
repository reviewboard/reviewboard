#!/bin/sh

./docsmanage.py dumpdata --indent=4 \
	auth accounts attachments changedescs diffviewer extensions hostingsvcs \
	reviews scmtools site webapi \
	> fixtures/initial_data.json
