from django_evolution.mutations import RenameField


MUTATIONS = [
    RenameField('Profile', 'show_submitted', 'show_closed'),
]
