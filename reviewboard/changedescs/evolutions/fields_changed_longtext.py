from __future__ import unicode_literals

from django_evolution.mutations import SQLMutation


MUTATIONS = [
    SQLMutation('mysql_fields_changed_longtext', ["""
        ALTER TABLE changedescs_changedescription
             MODIFY fields_changed LONGTEXT;
"""])
]
