from django.core.exceptions import ImproperlyConfigured
from django.db import models


class Tool(models.Model):
    name = models.CharField(max_length=32, unique=True)
    class_name = models.CharField(max_length=128, unique=True)

    supports_authentication = property(
        lambda x: x.get_scmtool_class().supports_authentication)

    def __unicode__(self):
        return self.name

    def get_scmtool_class(self):
        path = self.class_name
        i = path.rfind('.')
        module, attr = path[:i], path[i+1:]

        try:
            mod = __import__(module, {}, {}, [attr])
        except ImportError, e:
            raise ImproperlyConfigured, \
                'Error importing SCM Tool %s: "%s"' % (module, e)

        try:
            return getattr(mod, attr)
        except AttributeError:
            raise ImproperlyConfigured, \
                'Module "%s" does not define a "%s" SCM Tool' % (module, attr)

    class Meta:
        ordering = ("name",)


class Repository(models.Model):
    name = models.CharField(max_length=64, unique=True)
    path = models.CharField(max_length=128, unique=True)
    mirror_path = models.CharField(max_length=128, blank=True)
    username = models.CharField(max_length=32, blank=True)
    password = models.CharField(max_length=128, blank=True)
    tool = models.ForeignKey(Tool, related_name="repositories")
    bug_tracker = models.CharField(max_length=256, blank=True)
    encoding = models.CharField(max_length=32, blank=True)

    def get_scmtool(self):
        cls = self.tool.get_scmtool_class()
        return cls(self)


    def __unicode__(self):
        return self.name


    class Meta:
        verbose_name_plural = "Repositories"
