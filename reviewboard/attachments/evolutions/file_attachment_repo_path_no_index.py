"""Remove index from FileAttachment.repo_path.

Version Added:
    2.0
"""

from django_evolution.mutations import ChangeField


MUTATIONS = [
    ChangeField('FileAttachment', 'repo_path', initial=None, db_index=False)
]
