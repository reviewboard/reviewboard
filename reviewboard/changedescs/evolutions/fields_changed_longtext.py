"""Change ChangeDescription.fields_changed to a longtext type on MySQL.

Version Added:
    1.5.6
"""

from django_evolution.mutations import SQLMutation


MUTATIONS = [
    SQLMutation('mysql_fields_changed_longtext', ["""
        ALTER TABLE changedescs_changedescription
             MODIFY fields_changed LONGTEXT;
"""])
]
