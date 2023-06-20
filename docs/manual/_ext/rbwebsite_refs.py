"""Sphinx extension for the Review Board documentation.

This provides general cross-reference roles/directives to help link related
content in the documentation.

Version Added:
    5.0.5
"""


def setup(app):
    app.add_crossref_type(directivename='rb-management-command',
                          rolename='rb-management-command',
                          indextemplate=('pair: %s; management command'))
