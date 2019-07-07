from __future__ import unicode_literals

import re
import warnings

from django.utils import six
from django.utils.translation import ugettext_lazy as _
from djblets.registries.registry import (ALREADY_REGISTERED,
                                         AlreadyRegisteredError,
                                         ATTRIBUTE_REGISTERED,
                                         DEFAULT_ERRORS,
                                         ItemLookupError,
                                         NOT_REGISTERED,
                                         Registry,
                                         UNREGISTER)
from djblets.urls.staticfiles import static_lazy
from djblets.util.decorators import augment_method_from


class TrophyType(object):
    """Base class for a type of trophy.

    Trophies are achievements that can be awarded to users based on some
    aspect of a review request. When a review request is filed, each registered
    trophy type (managed by the :py:data:`trophies` registry) will be checked
    using :py:meth:`qualifies` to see if the trophy can be awarded. If so, the
    trophy will be recorded and shown on the review request page.

    A trophy should include a displayable name, a category (essentially the
    ID of the trophy), and details for the trophy image.
    """

    #: The category of the trophy.
    #:
    #: This is the string ID of the trophy. For historical reasons, it's
    #: referred to as a category and not an ID.
    category = None

    #: The name of the trophy.
    name = None

    #: URLs for the trophy images.
    #:
    #: This is a dictionary of images, where each key is a resolution
    #: specifier (``1x``, ``2x``, etc.), and the value is a URL.
    #:
    #: Each must have widths/heights that are multipliers on the base
    #: width/height for the ``1x`` specifier.
    image_urls = {}

    #: The width of the base image.
    image_width = None

    #: The height of the base image.
    #:
    #: It is recommended to use a height of 48px max.
    image_height = None

    def get_display_text(self, trophy):
        """Return the text to display in the trophy banner.

        Args:
            trophy (reviewboard.accounts.models.Trophy):
                The stored trophy information.

        Returns:
            unicode:
            The display text for the trophy banner.
        """
        raise NotImplementedError

    def qualifies(self, review_request):
        """Return whether this trophy should be given to this review request.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request to check for the trophy.

        Returns:
            bool:
            ``True`` if the trophy should be given, or ``False`` if not.
        """
        raise NotImplementedError

    def format_display_text(self, request, trophy, **kwargs):
        """Format the display text for the trophy.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            trophy (reviewboard.accounts.models.Trophy):
                The trophy instance.

            **kwargs (dict):
                Additional keyword arguments to use for formatting.

        Returns:
            unicode:
            The rendered text.
        """
        if self.display_format_str is None:
            raise NotImplementedError(
                '%s does not define the format_display_str attribute.'
                % type(self).__name__
            )

        return self.display_format_str % dict(kwargs, **{
            'recipient': trophy.user.get_profile().get_display_name(
                getattr(request, 'user', None)),
            'review_request_id': trophy.review_request.display_id,
        })


class MilestoneTrophy(TrophyType):
    """A milestone trophy.

    It is awarded if review request ID is greater than 1000 and is a non-zero
    digit followed by only zeroes (e.g. 1000, 5000, 10000).
    """

    category = 'milestone'
    title = _('Milestone Trophy')

    image_urls = {
        '1x': static_lazy('rb/images/trophies/sparkly.png'),
        '2x': static_lazy('rb/images/trophies/sparkly@2x.png'),
    }

    image_width = 33
    image_height = 35

    display_format_str = _(
        '%(recipient)s got review request #%(review_request_id)d!'
    )

    def qualifies(self, review_request):
        """Return whether this trophy should be given to this review request.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request to check for the trophy.

        Returns:
            bool:
            ``True`` if the trophy should be given, or ``False`` if not.
        """
        return (
            review_request.display_id >= 1000 and
            re.match(r'^[1-9]0+$', six.text_type(review_request.display_id))
        )


class FishTrophy(TrophyType):
    """A fish trophy.

    Give a man a fish, he'll waste hours trying to figure out why.
    """

    category = 'fish'
    name = _('Fish Trophy')

    image_urls = {
        '1x': static_lazy('rb/images/trophies/fish.png'),
        '2x': static_lazy('rb/images/trophies/fish@2x.png'),
    }

    image_width = 33
    image_height = 37

    display_format_str = _('%(recipient)s got a fish trophy!')

    def qualifies(self, review_request):
        """Return whether this trophy should be given to this review request.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request to check for the trophy.

        Returns:
            bool:
            ``True`` if the trophy should be given, or ``False`` if not.
        """
        id_str = six.text_type(review_request.display_id)

        return (review_request.display_id >= 1000 and
                id_str == ''.join(reversed(id_str)))


class UnknownTrophy(TrophyType):
    """A trophy with an unknown category.

    The data for this trophy exists in the database but its category does not
    match the category of any registered trophy types.
    """

    name = 'Unknown Trophy'


class TrophyRegistry(Registry):
    lookup_attrs = ('category',)

    default_errors = dict(DEFAULT_ERRORS, **{
        ALREADY_REGISTERED: _(
            'Could not register trophy type %(item)s. This trophy type is '
            'already registered or its category conficts with another trophy.'
        ),
        ATTRIBUTE_REGISTERED: _(
            'Could not register trophy type %(item)s: Another trophy type '
            '(%(duplicate)s) is already registered with the same category.'
        ),
        NOT_REGISTERED: _(
            'No trophy type was found matching "%(attr_value)s".'
        ),
        UNREGISTER: _(
            'Could not unregister trophy type %(item)s: This trophy type '
            'was not yet registered.'
        ),
    })

    @augment_method_from(Registry)
    def register(self, trophy_type):
        """Register a new trophy type.

        Args:
            trophy_type (type):
                The trophy type (subclass of :py:class:`TrophyType`) to
                register.

        Raises:
            djblets.registries.errors.RegistrationError:
                The :py:attr:`TrophyType.category` value is missing on the
                trophy.

            djblets.registries.errors.AlreadyRegisteredError:
                This trophy type, or another with the same category, was
                already registered.
        """
        pass

    @augment_method_from(Registry)
    def unregister(self, trophy_type):
        """Unregister a trophy type.

        Args:
            trophy_type (type):
                The trophy type (subclass of :py:class:`TrophyType`) to
                unregister.

        Raises:
            djblets.registries.errors.ItemLookupError:
                This trophy type was not registered.
        """
        pass

    def get_for_category(self, category):
        """Return the TrophyType instance matching a given trophy category.

        If there's no registered trophy for the category,
        :py:class:`UnknownTrophy` will be returned.

        Args:
            category (unicode):
                The stored category for the trophy.

        Returns:
            TrophyType:
            The trophy matching the given category.
        """
        try:
            return self.get('category', category)
        except self.lookup_error_class:
            return UnknownTrophy

    def get_defaults(self):
        """Return the default trophies for the registry.

        This is used internally by the parent registry class to populate the
        list of default, buit-in trophies available to review requests.

        Returns:
            list of TrophyType:
            The list of default trophies.
        """
        return [
            MilestoneTrophy,
            FishTrophy,
        ]


#: The registry of available trophies.
trophies_registry = TrophyRegistry()
