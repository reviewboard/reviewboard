"""Validators for diffviewer components."""

from __future__ import unicode_literals

import re

from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _


#: The maximum length of a commit ID.
COMMIT_ID_LENGTH = 64

#: A regular expression for matching commit IDs.
COMMIT_ID_RE = re.compile(r'[A-Za-z0-9]{1,%s}' % COMMIT_ID_LENGTH)

#: A validator for commit IDs.
validate_commit_id = RegexValidator(COMMIT_ID_RE,
                                    _('Commits must be alphanumeric.'))
