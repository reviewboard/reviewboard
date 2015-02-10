from django_evolution.mutations import AddField, RenameField
from django.db import models
from djblets.db.fields import JSONField


MUTATIONS = [
    AddField('WebHookTarget', 'encoding', models.CharField,
             initial='application/json', max_length=40),
    AddField('WebHookTarget', 'repositories', models.ManyToManyField,
             null=True, related_model='scmtools.Repository'),
    AddField('WebHookTarget', 'custom_content', models.TextField, null=True),
    AddField('WebHookTarget', 'use_custom_content', models.BooleanField,
             initial=False),
    AddField('WebHookTarget', 'apply_to', models.CharField, initial='A',
             max_length=1),
    AddField('WebHookTarget', 'extra_data', JSONField, initial=None),
    RenameField('WebHookTarget', 'handlers', 'events'),
]
