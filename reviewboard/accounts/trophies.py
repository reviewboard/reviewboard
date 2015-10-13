from __future__ import unicode_literals

import logging
import re

from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.translation import ugettext_lazy as _


_trophy_types = {}


class TrophyType(object):
    """An abstract trophy.

    Represents a type of trophy, with logic to see if it qualifies as a
    trophy for a given review request.

    Contains methods to visually display itself.
    """

    def __init__(self, title, image_url, image_width=32, image_height=48):
        """Initialize the trophy."""
        self.title = title
        self.image_url = image_url
        self.image_width = image_width
        self.image_height = image_height

    def get_display_text(self, trophy):
        """Get the text to display in the trophy banner."""
        raise NotImplementedError

    @staticmethod
    def for_category(category):
        """Get the TrophyType instance matching a given trophy category."""
        if not _trophy_types:
            _register_trophies()

        return _trophy_types.get(category, UnknownTrophy)


class MilestoneTrophy(TrophyType):
    """A milestone trophy.

    It is awarded if review request ID is greater than 1000 and is a non-zero
    digit followed by only zeroes (e.g. 1000, 5000, 10000).
    """

    category = 'milestone'

    def __init__(self):
        """Initialize the trophy."""
        super(MilestoneTrophy, self).__init__(
            title=_('Milestone Trophy'),
            image_url=static('rb/images/trophy.png'))

    def get_display_text(self, trophy):
        """Get the text to display in the trophy banner."""
        return _('%(user)s got review request #%(rid)s!') % {
            'user': trophy.user.get_full_name() or trophy.user.username,
            'rid': trophy.review_request.display_id
        }

    def qualifies(self, review_request):
        """Get whether or not the given review request deserves this trophy."""
        id_str = unicode(review_request.display_id)
        return (review_request.display_id >= 1000
                and re.match(r'^[1-9]0+$', id_str))


class FishTrophy(TrophyType):
    """A fish trophy.

    Give a man a fish, he'll waste hours trying to figure out why.
    """

    category = 'fish'

    def __init__(self):
        """Initialize the trophy."""
        super(FishTrophy, self).__init__(
            title=_('Fish Trophy'),
            image_url=static('rb/images/fish-trophy.png'))

    def qualifies(self, review_request):
        """Get whether or not the given review request deserves this trophy."""
        id_str = unicode(review_request.display_id)
        return (review_request.display_id >= 1000
                and id_str == ''.join(reversed(id_str)))

    def get_display_text(self, trophy):
        """Get the text to display in the trophy banner."""
        return _('%(user)s got a fish trophy!') % {
            'user': trophy.user.get_full_name() or trophy.user.username,
        }


class UnknownTrophy(TrophyType):
    """A trophy with an unknown category.

    The data for this trophy exists in the database but its category does not
    match the category of any registered trophy types.
    """

    def __init__(self):
        """Initialize the trophy."""
        super(UnknownTrophy, self).__init__(
            title=_('Unknown Trophy'),
            image_url=None)


def register_trophy(trophy):
    """Register a TrophyType subclass.

    This will register a type of trophy. Review Board will use it to calculate
    and display possible trophies.

    Only TrophyType subclasses are supported.
    """
    _register_trophies()

    if not issubclass(trophy, TrophyType):
        raise TypeError('Only TrophyType subclasses can be registered')

    if trophy in _trophy_types:
        raise KeyError(unicode(trophy.category) +
                       'is already a registered TrophyType subclass')

    _trophy_types[trophy.category] = trophy


def unregister_trophy(trophy):
    """Unregister a TrophyType subclass.

    This will unregister a previously registered type of trophy.

    Only TrophyType subclasses are supported. The class must have been
    registered beforehand or a ValueError will be thrown.
    """
    _register_trophies()

    if not issubclass(trophy, TrophyType):
        raise TypeError('Only TrophyType subclasses can be unregistered')

    try:
        del _trophy_types[trophy.category]
    except ValueError:
        logging.error('Failed to unregister missing TrophyType: %r',
                      trophy)
        raise ValueError('The TrophyType "%r" was not previously registered'
                         % trophy)


def get_registered_trophy_types():
    """Get all registered trophy types."""
    _register_trophies()

    return _trophy_types


def _register_trophies():
    """Register all bundled TrophyTypes."""
    if not _trophy_types:
        for type in (MilestoneTrophy, FishTrophy):
            _trophy_types[type.category] = type
