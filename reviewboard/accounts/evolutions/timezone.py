from django_evolution.mutations import AddField
from djblets.util.fields import TimeZoneField

MUTATIONS = [
    AddField('Profile', 'timezone', TimeZoneField, initial=u'UTC', max_length=20)
]
