import logging

from django.db.models.signals import post_init

from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


def _migrate_scmtool_ids(instance, **kwargs):
    """Migrate SCMTool IDs on repositories, if missing.

    Starting in Review Board 5.0, SCMTools began to be tracked by a
    :py:attr:`~reviewboard.scmtools.models.Repository.scmtool_id` attribute.
    This is efficiently set when upgrading the database, but if any fail to
    migrate (such as if a package-provided SCMTool can't be loaded during
    upgrade) or if data is injected/imported into the database after upgrade,
    this may be NULL.

    This handler will detect this whenever a repository is instantiated, and
    will try to perform a migration automatically.

    This will only attempt the SCMTool ID migration if working with a full
    repository without any deferred fields, in order to avoid any unwanted
    database access.

    Args:
        instance (reviewboard.scmtools.models.Repository):
            The repository instance being initialized.

        **kwargs (dict, unused):
            Additional keyword arguments.
    """
    if instance.get_deferred_fields():
        # We don't want to risk any extra queries here. This can be called
        # during the pre-upgrade steps, and an unwanted query can be fatal
        # to the upgrade process. So if there are deferred fields, just
        # skip this handler.
        return

    if (instance.scmtool_id is None and
        instance.tool_id is not None):
        # This wasn't set during upgrade. The package/extension may have
        # been missing at that time. We'll attempt to find it now and
        # upgrade the repository.
        try:
            tool = instance.tool
            scmtool_id = tool.scmtool_id
        except Exception as e:
            logger.error('Attempted to upgrade the SCMTool state for '
                         'repository ID %s, but the SCMTool "%s" could '
                         'not be loaded: %s',
                         instance.pk, tool.name, e)
            return

        if scmtool_id:
            instance.scmtool_id = scmtool_id

            if instance.pk:
                try:
                    instance.save(update_fields=('scmtool_id',))
                except Exception as e:
                    logging.error('Unable to save migrated scmtool_id "%s" '
                                  'for repository ID %s: %s',
                                  scmtool_id, instance.pk, e)


def connect_signal_handlers():
    """Connect SCMTool-related signal handlers.

    Version Added:
        5.0
    """
    post_init.connect(_migrate_scmtool_ids, sender=Repository)
