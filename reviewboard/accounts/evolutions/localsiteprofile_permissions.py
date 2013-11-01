from django_evolution.mutations import AddField
from djblets.util.fields import JSONField


MUTATIONS = [
    AddField('LocalSiteProfile', 'permissions', JSONField, null=True)
]
