PYTHON=python3
PIP=${PYTHON} -m pip


develop:
	${PIP} install -e .
	${PIP} install -r dev-requirements.txt


.PHONY: develop
