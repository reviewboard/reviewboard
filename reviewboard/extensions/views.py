import djblets.extensions.views as djblets_ext_views

from reviewboard.extensions.base import get_extension_manager


def configure_extension(request, ext_class, form_class):
    return djblets_ext_views.configure_extension(request, ext_class,
                                                 form_class,
                                                 get_extension_manager())
