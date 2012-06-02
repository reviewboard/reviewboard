from django import forms


class HostingServiceForm(forms.Form):
    def load(self, repository):
        for field in self.fields:
            if self.prefix:
                key = self.prefix + '-' + field
            else:
                key = field

            value = repository.extra_data.get(key, None)

            if isinstance(value, bool) or value:
                self.fields[field].initial = value

    def save(self, repository, *args, **kwargs):
        if not self.errors:
            for key, value in self.cleaned_data.iteritems():
                if self.prefix:
                    key = self.prefix + '-' + key

                repository.extra_data[key] = value
