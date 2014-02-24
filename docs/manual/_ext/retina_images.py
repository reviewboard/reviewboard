"""Sphinx extension for Retina images.

This extension goes through all the images Sphinx will provide in _images and
checks if Retina versions are available. If there are any, they will be copied
as well.
"""
import os


def add_retina_images(app, env):
    retina_images = []

    for full_path, (docnames, filename) in env.images.iteritems():
        base, ext = os.path.splitext(full_path)
        retina_path = base + '@2x' + ext

        if os.path.exists(retina_path):
            retina_images += [
                (docname, retina_path)
                for docname in docnames
            ]

    for docname, path in retina_images:
        env.images.add_file(docname, path)


def collect_pages(app):
    new_images = {}

    for full_path, basename in app.builder.images.iteritems():
        base, ext = os.path.splitext(full_path)
        retina_path = base + '@2x' + ext

        if retina_path in app.env.images:
            new_images[retina_path] = app.env.images[retina_path][1]

    app.builder.images.update(new_images)

    return []


def setup(app):
    app.connect('env-updated', add_retina_images)
    app.connect('html-collect-pages', collect_pages)
