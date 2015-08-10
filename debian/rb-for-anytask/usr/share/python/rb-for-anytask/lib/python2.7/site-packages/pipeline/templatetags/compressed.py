from __future__ import unicode_literals

from django.contrib.staticfiles.storage import staticfiles_storage

from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from pipeline.conf import settings
from pipeline.packager import Packager, PackageNotFound
from pipeline.utils import guess_type

register = template.Library()


class CompressedMixin(object):
    def package_for(self, package_name, package_type):
        package = {
            'js': getattr(settings, 'PIPELINE_JS', {}).get(package_name, {}),
            'css': getattr(settings, 'PIPELINE_CSS', {}).get(package_name, {}),
        }[package_type]

        if package:
            package = {package_name: package}

        packager = {
            'js': Packager(css_packages={}, js_packages=package),
            'css': Packager(css_packages=package, js_packages={}),
        }[package_type]

        return packager.package_for(package_type, package_name)

    def render_compressed(self, package, package_type):
        if settings.PIPELINE_ENABLED:
            method = getattr(self, "render_{0}".format(package_type))
            return method(package, package.output_filename)
        else:
            packager = Packager()
            method = getattr(self, "render_individual_{0}".format(package_type))
            paths = packager.compile(package.paths)
            templates = packager.pack_templates(package)
            return method(package, paths, templates=templates)


class CompressedCSSNode(CompressedMixin, template.Node):
    def __init__(self, name):
        self.name = name

    def render(self, context):
        package_name = template.Variable(self.name).resolve(context)
        try:
            package = self.package_for(package_name, 'css')
        except PackageNotFound:
            return ''  # fail silently, do not return anything if an invalid group is specified
        return self.render_compressed(package, 'css')

    def render_css(self, package, path):
        template_name = package.template_name or "pipeline/css.html"
        context = package.extra_context
        context.update({
            'type': guess_type(path, 'text/css'),
            'url': mark_safe(staticfiles_storage.url(path))
        })
        return render_to_string(template_name, context)

    def render_individual_css(self, package, paths, **kwargs):
        tags = [self.render_css(package, path) for path in paths]
        return '\n'.join(tags)


class CompressedJSNode(CompressedMixin, template.Node):
    def __init__(self, name):
        self.name = name

    def render(self, context):
        package_name = template.Variable(self.name).resolve(context)
        try:
            package = self.package_for(package_name, 'js')
        except PackageNotFound:
            return ''  # fail silently, do not return anything if an invalid group is specified
        return self.render_compressed(package, 'js')

    def render_js(self, package, path):
        template_name = package.template_name or "pipeline/js.html"
        context = package.extra_context
        context.update({
            'type': guess_type(path, 'text/javascript'),
            'url': mark_safe(staticfiles_storage.url(path))
        })
        return render_to_string(template_name, context)

    def render_inline(self, package, js):
        context = package.extra_context
        context.update({
            'source': js
        })
        return render_to_string("pipeline/inline_js.html", context)

    def render_individual_js(self, package, paths, templates=None):
        tags = [self.render_js(package, js) for js in paths]
        if templates:
            tags.append(self.render_inline(package, templates))
        return '\n'.join(tags)


@register.tag
def compressed_css(parser, token):
    try:
        tag_name, name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('%r requires exactly one argument: the name of a group in the PIPELINE_CSS setting' % token.split_contents()[0])
    return CompressedCSSNode(name)


@register.tag
def compressed_js(parser, token):
    try:
        tag_name, name = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError('%r requires exactly one argument: the name of a group in the PIPELINE_JS setting' % token.split_contents()[0])
    return CompressedJSNode(name)
