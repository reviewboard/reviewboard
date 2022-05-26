"""Rename Repository.password to Repository.encrypted_password.

Version Added:
    2.0.9
"""

from django_evolution.mutations import RenameField


MUTATIONS = [
    RenameField('Repository', 'password', 'encrypted_password',
                db_column='password'),
]
