from django.core.exceptions import ImproperlyConfigured
from django.db import models

class Tool(models.Model):
    name = models.CharField(max_length=32, unique=True)
    class_name = models.CharField(max_length=128, unique=True)

    def __unicode__(self):
        return self.name

    class Admin:
        list_display = ('__unicode__', 'class_name')


class Repository(models.Model):
    name = models.CharField(max_length=64, unique=True)
    path = models.CharField(max_length=128, unique=True)
    mirror_path = models.CharField(max_length=128, blank=True)
    username = models.CharField(max_length=32, blank=True)
    password = models.CharField(max_length=128, blank=True)
    tool = models.ForeignKey(Tool)
    bug_tracker = models.URLField(verify_exists=False, blank=True)
    encoding = models.CharField(max_length=32, blank=True)

    def get_scmtool(self):
        path = self.tool.class_name
        i = path.rfind('.')
        module, attr = path[:i], path[i+1:]

        try:
            mod = __import__(module, {}, {}, [attr])
        except ImportError, e:
            raise ImproperlyConfigured, \
                'Error importing SCM Tool %s: "%s"' % (module, e)

        try:
            cls = getattr(mod, attr)
        except AttributeError:
            raise ImproperlyConfigured, \
                'Module "%s" does not define a "%s" SCM Tool' % (module, attr)

        return cls(self)


    def __unicode__(self):
        return self.name


    class Meta:
        verbose_name_plural = "Repositories"

    class Admin:
        list_display = ('__unicode__', 'path')
