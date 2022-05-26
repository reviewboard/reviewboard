"""Internal utilities to help with database installs and upgrades.

These functions should not be called outside of :command:`rb-site` or
:file:`manage.py`.

Version Added:
    5.0
"""

# NOTE: Imports for anything that touches Django/database functionality must
#       be done within the upgrade function. Importing at the module level
#       can cause problems with apps being loaded in the wrong order.


def pre_upgrade_reset_oauth2_provider(upgrade_state):
    """Reset the OAuth2 migration/evolution state pre-upgrade.

    This will remove any migration information regarding the
    :py:mod:`oauth2_provider` Django app from the list of migrations and the
    Django Evolution project signature. This allows Django Evolution to take
    control of the upgrade process again.

    Version Added:
        5.0

    Args:
        upgrade_state (dict, unused):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.

            This is not used by this pre-upgrade step.
    """
    from django.db import connection
    from django_evolution.consts import UpgradeMethod
    from django_evolution.models import Evolution, Version
    from django_evolution.utils.migrations import unrecord_applied_migrations

    try:
        version = Version.objects.current_version()
    except Version.DoesNotExist:
        return

    project_sig = version.signature
    app_sig = project_sig.get_app_sig('oauth2_provider')

    if app_sig is None or app_sig.upgrade_method != UpgradeMethod.MIGRATIONS:
        return

    # Patch the signature to reset this app back to Django Evolution, undoing
    # the MoveToMigrations introduced in Review Board 4.
    app_sig.upgrade_method = UpgradeMethod.EVOLUTIONS
    app_sig.applied_migrations = []
    version.save()

    # Remove any migrations. We'll later record the migrations we want to
    # simulate having applied in the post-upgrade step.
    unrecord_applied_migrations(connection=connection,
                                app_label='oauth2_provider')

    # Remove the "move_to_migrations" evolution.
    evolutions = Evolution.objects.filter(app_label='oauth2_provider',
                                          label='move_to_migrations')
    evolutions.delete()


def post_upgrade_reset_oauth2_provider(upgrade_state):
    """Mark oauth2_provider migrations as applied.

    Post-upgrade, this will mark all oauth2_provider migrations as applied,
    satisfying migration dependency checks and Django startup checks.

    These steps will be executed regardless of whether we changed any state
    in :py:func:`pre_upgrade_reset_oauth2_provider`, since we always need to
    mirror the current version's migrations regardless of whether we've
    altered the database signature.

    This list of migrations must be updated whenever we update oauth2_provider.

    Version Added:
        5.0

    Args:
        upgrade_state (dict, unused):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.

            This is not used by this post-upgrade step.
    """
    from django.db import connection
    from django_evolution.utils.migrations import (MigrationList,
                                                   record_applied_migrations,
                                                   unrecord_applied_migrations)

    unrecord_applied_migrations(connection=connection,
                                app_label='oauth2_provider')

    # This is current as of oauth2_provider 1.6.3.
    record_applied_migrations(
        connection=connection,
        migrations=MigrationList.from_names(
            app_label='oauth2_provider',
            migration_names=[
                '0001_initial',
                '0002_auto_20190406_1805',
                '0003_auto_20201211_1314',
                '0004_auto_20200902_2022',
                '0005_auto_20211222_2352',
            ]))


def run_pre_upgrade_tasks(upgrade_state):
    """Run any database pre-upgrade tasks.

    Version Added:
        5.0

    Args:
        upgrade_state (dict):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.
            Pre-upgrade steps can modify this to include any information
            needed.
    """
    pre_upgrade_reset_oauth2_provider(upgrade_state)


def run_post_upgrade_tasks(upgrade_state):
    """Run any database post-upgrade tasks.

    Version Added:
        5.0

    Args:
        upgrade_state (dict):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.
    """
    post_upgrade_reset_oauth2_provider(upgrade_state)
