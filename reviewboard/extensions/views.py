from __future__ import unicode_literals

import djblets.extensions.views as djblets_ext_views
from django.views.decorators.csrf import csrf_protect

from reviewboard.extensions.base import get_extension_manager


@csrf_protect
def configure_extension(request, ext_class, form_class,
                        template_name='extensions/configure_extension.html'):
    return djblets_ext_views.configure_extension(request, ext_class,
                                                 form_class,
                                                 get_extension_manager(),
                                                 template_name)
