"""Internal utilities to help with database installs and upgrades.

These functions should not be called outside of :command:`rb-site` or
:file:`manage.py`.

Version Added:
    5.0
"""

# NOTE: Imports for anything that touches Django/database functionality must
#       be done within the upgrade function. Importing at the module level
#       can cause problems with apps being loaded in the wrong order.

import sys

from django.db import DatabaseError


def pre_upgrade_reset_oauth2_provider(upgrade_state, console):
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

        console (reviewboard.cmdline.utils.console.Console, unused):
            The console output wrapper.
    """
    from django.db import connection
    from django_evolution.consts import UpgradeMethod
    from django_evolution.models import Evolution, Version
    from django_evolution.utils.migrations import unrecord_applied_migrations

    try:
        version = Version.objects.current_version()
    except (DatabaseError, Version.DoesNotExist):
        # There's no recorded versions, or no table. This is a brand-new
        # installation. We have nothing to do at this stage.
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


def post_upgrade_reset_oauth2_provider(upgrade_state, console):
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

        console (reviewboard.cmdline.utils.console.Console, unused):
            The console output wrapper.
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


def pre_upgrade_store_scmtool_data(upgrade_state, console):
    """Store the data for adding scmtool_id to the Repository object.

    Version Added:
        5.0

    Args:
        upgrade_state (dict):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.

        console (reviewboard.cmdline.utils.console.Console):
            The console output wrapper.
    """
    from django_evolution.models import Evolution
    from reviewboard.scmtools.models import Repository

    try:
        evolution = Evolution.objects.filter(
            app_label='scmtools', label='repository_scmtool_id')

        has_evolution = evolution.exists()
    except DatabaseError:
        # The evolution tables don't yet exist. This is a brand-new
        # installation. We have nothing to do at this stage.
        return

    # We'll need to store state for an upgrade if we haven't yet added the
    # Repository.scmtool_id field or if we have any repositories remaining
    # that haven't been updated yet.
    try:
        needs_upgrade = (
            not has_evolution or
            Repository.objects.filter(scmtool_id=None).exists()
        )
    except Exception as e:
        # Something went wrong trying to perform this query. The evolution
        # may be in the database but the table hasn't been upgraded. Assume
        # an upgrade is needed.
        console.error('Unexpected error trying to determine if an upgrade '
                      'is required. Proceeding with the upgrade. Contact '
                      'Beanbag Support and report the following error if '
                      'you encounter any problems: %s'
                      % e)
        needs_upgrade = True

    if needs_upgrade:
        # TODO: We do eventually want to delete the Tool model entirely. When
        # we do that, this will need to change to run some hand-written SQL
        # because we won't have the Python-side available, even when the
        # table is still present in the database.
        from django.db.models import Prefetch, Q
        from reviewboard.scmtools import scmtools_registry
        from reviewboard.scmtools.models import Tool

        # This will just be 2 queries in total, optimized only for the fields
        # we need, and leveraging the database as best as possible:
        repositories_queryset = Repository.objects.only('pk', 'tool_id')

        if has_evolution:
            repositories_queryset = repositories_queryset.filter(
                Q(scmtool_id=None) &
                Q(tool_id__isnull=False))

        tools = (
            Tool.objects
            .prefetch_related(Prefetch(
                'repositories',
                queryset=repositories_queryset))
            .order_by('pk')
        )

        upgrade_state['needs_scmtool_id_migration'] = True

        scmtool_id_data = {}
        missing_tools = []

        for tool in tools:
            try:
                scmtool_id = tool.scmtool_id
            except Exception as e:
                missing_tools.append((tool.name, e))
                continue

            # This is required instead of values_list() due to the prefetch,
            # but will be optimized due to what we chose to prefetch.
            scmtool_id_data[scmtool_id] = [
                repository.pk
                for repository in tool.repositories.all()
            ]

        errors = []

        if missing_tools:
            errors.append([
                'The following tools were registered in your database but '
                'could not be loaded due the following errors:',
            ] + [
                '* %s: %s' % (tool_name, e)
                for tool_name, e in missing_tools
            ] + [
                'For now, these tools are being skipped. Review requests '
                'using associated repositories may crash. Please ensure the '
                'proper packages are installed correctly, and then '
                're-upgrade the site directory.',
            ])

        if scmtools_registry.conflicting_tools:
            errors.append([
                'The following SCMTools in your database have been modified '
                'or renamed, and may no longer work correctly:',
            ] + [
                '* Your %s (%s) conflicts with our %s (%s)'
                % (conflict_tool.name,
                   conflict_tool.class_name,
                   scmtool_cls.name,
                   scmtool_cls.class_name)
                for (scmtool_cls,
                     conflict_tool) in scmtools_registry.conflicting_tools
            ] + [
                'If you are using custom SCMTools, you will '
                'need to register yours via an extension and update any '
                'repositories.',
            ])

        if errors:
            for error in errors:
                console.warning('\n'.join(error))

            console.note(
                'Contact Beanbag Support (support@beanbaginc.com) if you '
                'need help.',
            )

        upgrade_state['scmtool_id_data'] = scmtool_id_data
    else:
        upgrade_state['needs_scmtool_id_migration'] = False


def post_upgrade_apply_scmtool_data(upgrade_state, console):
    """Apply the scmtool_id migration data.

    Version Added:
        5.0

    Args:
        upgrade_state (dict):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.

        console (reviewboard.cmdline.utils.console.Console, unused):
            The console output wrapper.
    """
    if upgrade_state.get('needs_scmtool_id_migration'):
        from reviewboard.scmtools.models import Repository

        scmtool_id_data = upgrade_state['scmtool_id_data']

        for scmtool_id, repository_ids in scmtool_id_data.items():
            repositories = Repository.objects.filter(pk__in=repository_ids)
            repositories.update(scmtool_id=scmtool_id)


def pre_upgrade_store_condition_tool_info(upgrade_state, console):
    """Store the data for converting RepositoryTypeChoice data.

    The :py:class:`reviewboard.scmtools.conditions.RepositoryTypeChoice`
    traditionally used the Tool pk as its value. This upgrade sequence will
    convert those to use the SCMTool ID instead.

    This must run after :py:func:`pre_upgrade_store_scmtool_data`.

    Version Added:
        5.0

    Args:
        upgrade_state (dict):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.

        console (reviewboard.cmdline.utils.console.Console, unused):
            The console output wrapper.
    """
    if upgrade_state.get('needs_scmtool_id_migration'):
        from reviewboard.integrations.models import IntegrationConfig
        from reviewboard.scmtools.models import Tool

        tool_pks = set()
        affected_configs = set()

        configs = IntegrationConfig.objects.only('pk', 'settings')

        for config in configs:
            # We need to directly work with the underlying settings dictionary.
            # If we go through config.get(), and the setting doesn't exist, it
            # will result in looking up the integration instance, which may not
            # be available at this point (due to being part of an extension) or
            # may not even be installed, and that will crash the upgrade
            # process.
            conditions = config.settings.get('conditions')

            if conditions:
                for condition in conditions['conditions']:
                    if condition['choice'] == 'repository_type':
                        tool_pks.update(condition['value'])
                        affected_configs.add(config.pk)

        tools = Tool.objects.filter(pk__in=tool_pks).only('pk', 'class_name')

        upgrade_state['tool_pk_to_scmtool_id'] = {
            tool.pk: tool.scmtool_id
            for tool in tools
        }
        upgrade_state['conditions_for_scmtool_migration'] = affected_configs


def post_upgrade_apply_condition_tool_info(upgrade_state, console):
    """Convert RepositoryTypeChoice conditions to use SCMTool ID.

    The :py:class:`reviewboard.scmtools.conditions.RepositoryTypeChoice`
    traditionally used the Tool pk as its value. This upgrade sequence will
    convert those to use the SCMTool ID instead.

    Version Added:
        5.0

    Args:
        upgrade_state (dict):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.

        console (reviewboard.cmdline.utils.console.Console, unused):
            The console output wrapper.
    """
    if upgrade_state.get('needs_scmtool_id_migration'):
        from reviewboard.integrations.models import IntegrationConfig

        tool_pk_to_scmtool_id = upgrade_state['tool_pk_to_scmtool_id']
        config_pks = upgrade_state['conditions_for_scmtool_migration']

        configs = (
            IntegrationConfig.objects
            .filter(pk__in=config_pks)
            .only('pk', 'settings')
        )

        for config in configs:
            # See the note above about how we access the settings for
            # configurations.
            #
            # It should be safe to use .get(), since we've already determined
            # the correct integrations above, but as this is the upgrade
            # process we'll want to be extra careful.
            conditions = config.settings.get('conditions')

            if conditions:
                for condition in conditions['conditions']:
                    if condition['choice'] == 'repository_type':
                        condition['value'] = [
                            tool_pk_to_scmtool_id[pk]
                            for pk in condition['value']
                        ]

                config.set('conditions', conditions)
                config.save(update_fields=('settings',))


def run_pre_upgrade_tasks(upgrade_state, console):
    """Run any database pre-upgrade tasks.

    Version Added:
        5.0

    Args:
        upgrade_state (dict):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.
            Pre-upgrade steps can modify this to include any information
            needed.

        console (reviewboard.cmdline.utils.console.Console):
            The console output wrapper.
    """
    pre_upgrade_reset_oauth2_provider(upgrade_state, console)
    pre_upgrade_store_scmtool_data(upgrade_state, console)
    pre_upgrade_store_condition_tool_info(upgrade_state, console)


def run_post_upgrade_tasks(upgrade_state, console):
    """Run any database post-upgrade tasks.

    Version Added:
        5.0

    Args:
        upgrade_state (dict):
            Upgrade state that can be used by pre-upgrade/post-upgrade steps.

        console (reviewboard.cmdline.utils.console.Console):
            The console output wrapper.
    """
    post_upgrade_reset_oauth2_provider(upgrade_state, console)
    post_upgrade_apply_scmtool_data(upgrade_state, console)
    post_upgrade_apply_condition_tool_info(upgrade_state, console)
