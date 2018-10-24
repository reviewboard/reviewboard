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

from reviewboard.deprecation import RemovedInReviewBoard40Warning


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

    def __init__(self, title=None, image_url=None, image_width=None,
                 image_height=None):
        """Initialize the trophy.

        This accepts deprecated arguments for the trophy information.
        Subclasses should instead define the appropriate attributes on the
        class body.

        Args:
            title (unicode, optional):
                The name of the trophy.

                Subclasses should instead set :py:attr:`name`.

                .. deprecated:: 3.0

            image_url (unicode, optional):
                The URL of the trophy.

                Subclasses should instead set :py:attr:`image_urls`.

                .. deprecated:: 3.0

            image_width (int, optional):
                The width of the image.

                Subclasses should instead set :py:attr:`image_width`.

                .. deprecated:: 3.0

            image_height (int, optional):
                The height of the image.

                Subclasses should instead set :py:attr:`image_height`.

                .. deprecated:: 3.0
        """
        if not self.name and title:
            warnings.warn('%r should define "name" as a class attribute '
                          'instead of passing "title" to the constructor.'
                          % self.__class__,
                          RemovedInReviewBoard40Warning)

            self.name = title

        if not self.image_urls and image_url:
            warnings.warn('%r should define "image_urls" as a class attribute '
                          'instead of passing "image_url" to the constructor.'
                          % self.__class__,
                          RemovedInReviewBoard40Warning)

            self.image_urls = {
                '1x': image_url,
            }

        if not self.image_width:
            warnings.warn('%r should define "image_width" as a class '
                          'attribute instead of passing "image_width" to '
                          'the constructor.'
                          % self.__class__,
                          RemovedInReviewBoard40Warning)

            self.image_width = image_width or 32

        if not self.image_height:
            warnings.warn('%r should define "image_height" as a class '
                          'attribute instead of passing "image_height" to '
                          'the constructor.'
                          % self.__class__,
                          RemovedInReviewBoard40Warning)

            self.image_height = image_height or 48

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
        if getattr(self, 'display_format_str', None) is None:
            # In this case we may be dealing with a custom old-style trophy
            # that has implemented get_display_text. We need to check if
            # that has been implemented and, if so, use that.
            try:
                text = self.get_display_text(trophy)
            except NotImplementedError:
                raise NotImplementedError(
                    '%s does not define the format_display_text attribute.'
                    % type(self).__name__
                )
            else:
                warnings.warn(
                    'TrophyType.get_display_text has been deprecated in favor '
                    'of TrophyType.format_display_text.',
                    RemovedInReviewBoard40Warning)
                return text

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


def register_trophy(trophy):
    """Register a TrophyType subclass.

    This will register a type of trophy. Review Board will use it to calculate
    and display possible trophies.

    Only :py:class:`TrophyType` subclasses are supported.

    .. deprecated:: 3.0

       This is deprecated in favor of calling ``trophies_registry.register``.

    Args:
        trophy (type):
            The trophy type (subclass of :py:class:`TrophyType`) to register.

    Raises:
        TypeError:
            The provided trophy to register is not a :py:class:`TrophyType`
            subclass.

        KeyError:
            The trophy could not be registered.
    """
    warnings.warn('register_trophy() is deprecated. Please use '
                  'reviewboard.accounts.trophies:trophies_registry.register() '
                  'instead.',
                  RemovedInReviewBoard40Warning)

    if not issubclass(trophy, TrophyType):
        raise TypeError('Only TrophyType subclasses can be registered')

    try:
        trophies_registry.register(trophy)
    except AlreadyRegisteredError as e:
        raise KeyError(six.text_type(e))


def unregister_trophy(trophy):
    """Unregister a TrophyType subclass.

    This will unregister a previously registered type of trophy.

    Only :py:class:`TrophyType` subclasses are supported. The class must have
    been registered beforehand or a :py:exc:`ValueError` will be thrown.

    .. deprecated:: 3.0

       This is deprecated in favor of calling ``trophies_registry.unregister``.

    Args:
        trophy (type):
            The trophy type (subclass of :py:class:`TrophyType`) to unregister.

    Raises:
        TypeError:
            The provided trophy to register is not a :py:class:`TrophyType`
            subclass.

        ValueError:
            The trophy could not be unregistered.
    """
    warnings.warn('unregister_trophy() is deprecated. Please use '
                  'reviewboard.accounts.trophies:trophies_registry'
                  '.unregister() instead.',
                  RemovedInReviewBoard40Warning)

    if not issubclass(trophy, TrophyType):
        raise TypeError('Only TrophyType subclasses can be unregistered')

    try:
        trophies_registry.unregister(trophy)
    except ItemLookupError as e:
        raise ValueError(six.text_type(e))


def get_registered_trophy_types():
    """Return all registered trophy types.

    .. deprecated:: 3.0

       This is deprecated in favor of iterating through
       :py:data:`trophies_registry`.

    Returns:
        list of TrophyType:
        The list of all registered trophies.
    """
    warnings.warn('get_registered_trophy_types() is deprecated. Please '
                  'iterate through '
                  'reviewboard.accounts.trophies:trophies_registry instead.',
                  RemovedInReviewBoard40Warning)

    return {
        trophy.category: trophy
        for trophy in trophies_registry
    }
