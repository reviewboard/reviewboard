from __future__ import unicode_literals

from django import forms
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils import six
from django.utils.translation import ugettext_lazy as _


class ConfigPageForm(forms.Form):
    """Base class for a form on a ConfigPage.

    ConfigPageForms belong to ConfigPages, and will be displayed when
    navigating to that ConfigPage.

    A simple form presents fields that can be filled out and posted. More
    advanced forms can supply their own template or even their own
    JavaScript models and views.
    """
    form_id = None
    form_title = None

    save_label = _('Save')

    template_name = 'configforms/config_page_form.html'

    css_bundle_names = []
    js_bundle_names = []

    js_model_class = None
    js_view_class = None

    form_target = forms.CharField(
        required=False,
        widget=forms.HiddenInput)

    def __init__(self, page, request, user, *args, **kwargs):
        super(ConfigPageForm, self).__init__(*args, **kwargs)
        self.page = page
        self.request = request
        self.user = user
        self.profile = user.get_profile()

        self.fields['form_target'].initial = self.form_id
        self.load()

    def set_initial(self, field_values):
        """Sets the initial fields for the form based on provided data.

        This can be used during load() to fill in the fields based on
        data from the database or another source.
        """
        for field, value in six.iteritems(field_values):
            self.fields[field].initial = value

    def is_visible(self):
        """Returns whether the form should be visible.

        This can be overridden to hide forms based on certain criteria.
        """
        return True

    def get_js_model_data(self):
        """Returns data to pass to the JavaScript Model during instantiation.

        If js_model_class is provided, the data returned from this function
        will be provided to the model when constructued.
        """
        return {}

    def get_js_view_data(self):
        """Returns data to pass to the JavaScript View during instantiation.

        If js_view_class is provided, the data returned from this function
        will be provided to the view when constructued.
        """
        return {}

    def render(self):
        """Renders the form."""
        return render_to_string(
            self.template_name,
            RequestContext(self.request, {
                'form': self,
                'page': self.page,
            }))

    def load(self):
        """Loads data for the form.

        By default, this does nothing. Subclasses can override this to
        load data into the fields based on data from the database or
        from another source.
        """
        pass

    def save(self):
        """Saves the form data.

        Subclasses can override this to save data from the fields into
        the database.
        """
        raise NotImplementedError
