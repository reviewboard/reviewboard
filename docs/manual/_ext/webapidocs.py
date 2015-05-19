"""
Sphinx plugins for web API docs.
"""
import inspect
import logging
import re
import sys

try:
    import json
except ImportError:
    import simplejson as json

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.template.defaultfilters import title
from djblets.util.http import is_mimetype_a
from djblets.webapi.resources import get_resource_from_class, WebAPIResource
from djblets.webapi.responses import WebAPIResponseError
from docutils import nodes
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from reviewboard import initialize
from reviewboard.webapi.resources import resources
from sphinx import addnodes
from sphinx.util import docname_join
from sphinx.util.compat import Directive


# Mapping of mimetypes to language names for syntax highlighting.
MIMETYPE_LANGUAGES = [
    ('application/json', 'javascript'),
    ('application/xml', 'xml'),
    ('text/x-patch', 'diff'),
]


# Initialize Review Board
initialize()


# Build the list of parents.
resources.root.get_url_patterns()


class ResourceNotFound(Exception):
    def __init__(self, directive, classname):
        self.classname = classname
        self.error_node = [
            directive.state_machine.reporter.error(
                str(self),
                line=directive.lineno)
        ]

    def __str__(self):
        return ('Unable to import the web API resource class "%s"'
                % self.classname)


class ErrorNotFound(Exception):
    def __init__(self, directive, classname):
        self.error_node = [
            directive.state_machine.reporter.error(
                'Unable to import the web API error class "%s"' % classname,
                line=directive.lineno)
        ]


class DummyRequest(HttpRequest):
    def __init__(self, *args, **kwargs):
        super(DummyRequest, self).__init__(*args, **kwargs)
        self.method = 'GET'
        self.path = ''
        self.user = User.objects.all()[0]
        self.session = {}
        self._local_site_name = None

        # This is normally set internally by Djblets, but we don't
        # go through the standard __call__ flow.
        self._djblets_webapi_object_cache = {}

    def build_absolute_uri(self, location=None):
        if not self.path and not location:
            return '/api/'

        if not location:
            location = self.path

        if not location.startswith('http://'):
            location = 'http://reviews.example.com' + location

        return location


class ResourceDirective(Directive):
    has_content = True
    required_arguments = 0
    option_spec = {
        'classname': directives.unchanged_required,
        'is-list': directives.flag,
        'hide-links': directives.flag,
        'hide-examples': directives.flag,
    }

    item_http_methods = set(['GET', 'DELETE', 'PUT'])
    list_http_methods = set(['GET', 'POST'])

    FILTERED_MIMETYPES = [
        'application/json',
        'application/xml',
    ]

    type_mapping = {
        int: 'Integer',
        str: 'String',
        unicode: 'String',
        bool: 'Boolean',
        dict: 'Dictionary',
        file: 'Uploaded File',
    }

    def run(self):
        try:
            resource_class = self.get_resource_class(self.options['classname'])
        except ResourceNotFound, e:
            return e.error_node

        # Add the class's file and this extension to the dependencies.
        self.state.document.settings.env.note_dependency(__file__)
        self.state.document.settings.env.note_dependency(
            sys.modules[resource_class.__module__].__file__)

        resource = get_resource_from_class(resource_class)

        is_list = 'is-list' in self.options

        docname = 'webapi2.0-%s-resource' % \
            get_resource_docname(resource, is_list)
        resource_title = get_resource_title(resource, is_list)

        targetnode = nodes.target('', '', ids=[docname], names=[docname])
        self.state.document.note_explicit_target(targetnode)
        main_section = nodes.section(ids=[docname])

        # Main section
        main_section += nodes.title(text=resource_title)
        main_section += parse_text(
            self, inspect.getdoc(resource),
            where='%s class docstring' % self.options['classname'])

        # Details section
        details_section = nodes.section(ids=['details'])
        main_section += details_section

        details_section += nodes.title(text='Details')
        details_section += self.build_details_table(resource)

        # Fields section
        if (resource.fields and
            (not is_list or resource.singleton)):
            fields_section = nodes.section(ids=['fields'])
            main_section += fields_section

            fields_section += nodes.title(text='Fields')
            fields_section += self.build_fields_table(resource.fields)

        # Links section
        if 'hide-links' not in self.options:
            fields_section = nodes.section(ids=['links'])
            main_section += fields_section

            fields_section += nodes.title(text='Links')
            fields_section += self.build_links_table(resource)

        # HTTP method descriptions
        for http_method in self.get_http_methods(resource, is_list):
            method_section = nodes.section(ids=[http_method])
            main_section += method_section

            method_section += nodes.title(text='HTTP %s' % http_method)
            method_section += self.build_http_method_section(resource,
                                                             http_method)

        if 'hide-examples' not in self.options:
            examples_section = nodes.section(ids=['examples'])
            examples_section += nodes.title(text='Examples')

            has_examples = False

            if is_list:
                mimetype_key = 'list'
            else:
                mimetype_key = 'item'

            for mimetype in resource.allowed_mimetypes:
                try:
                    mimetype = mimetype[mimetype_key]
                except KeyError:
                    continue

                if mimetype in self.FILTERED_MIMETYPES:
                    # Resources have more specific mimetypes. We want to
                    # filter out the general ones (like application/json)
                    # so we don't show redundant examples.
                    continue

                if mimetype.endswith('xml'):
                    # JSON is preferred. While we support XML, let's not
                    # continue to advertise it.
                    continue

                url, headers, data = \
                    self.fetch_resource_data(resource, mimetype)
                example_node = build_example(headers, data, mimetype)

                if example_node:
                    example_section = \
                        nodes.section(ids=['example_' + mimetype],
                                      classes=['examples', 'requests-example'])
                    examples_section += example_section

                    example_section += nodes.title(text=mimetype)

                    accept_mimetype = mimetype

                    if (mimetype.startswith('application/') and
                        mimetype.endswith('+json')):
                        # Instead of telling the user to ask for a specific
                        # mimetype on the request, show them that asking for
                        # application/json works fine.
                        accept_mimetype = 'application/json'

                    curl_text = ('$ curl http://reviews.example.com%s -A %s'
                                 % (url, accept_mimetype))
                    example_section += nodes.literal_block(
                        curl_text, curl_text, classes=['cmdline'])

                    example_section += nodes.literal_block(
                        headers, headers, classes=['http-headers'])
                    example_section += example_node
                    has_examples = True

            if has_examples:
                main_section += examples_section

        return [targetnode, main_section]

    def build_details_table(self, resource):
        is_list = 'is-list' in self.options

        table = nodes.table(classes=['resource-info'])

        tgroup = nodes.tgroup(cols=2)
        table += tgroup

        tgroup += nodes.colspec(colwidth=30, classes=['field'])
        tgroup += nodes.colspec(colwidth=70, classes=['value'])

        tbody = nodes.tbody()
        tgroup += tbody

        # Name
        if is_list:
            resource_name = resource.name_plural
        else:
            resource_name = resource.name

        append_detail_row(tbody, "Name", nodes.literal(text=resource_name))

        # URI
        uri_template = get_resource_uri_template(resource, not is_list)
        append_detail_row(tbody, "URI", nodes.literal(text=uri_template))

        # Token Policy ID
        if hasattr(resource, 'policy_id'):
            append_detail_row(tbody, "Token Policy ID",
                              nodes.literal(text=resource.policy_id))

        # HTTP Methods
        allowed_http_methods = self.get_http_methods(resource, is_list)
        bullet_list = nodes.bullet_list()

        for http_method in allowed_http_methods:
            item = nodes.list_item()
            bullet_list += item

            paragraph = nodes.paragraph()
            item += paragraph

            ref = nodes.reference(text=http_method, refid=http_method)
            paragraph += ref

            doc_summary = self.get_doc_for_http_method(resource, http_method)
            i = doc_summary.find('.')

            if i != -1:
                doc_summary = doc_summary[:i + 1]

            paragraph += nodes.inline(text=" - ")
            paragraph += parse_text(
                self, doc_summary, nodes.inline,
                where='HTTP %s handler summary for %s'
                      % (http_method, self.options['classname']))

        append_detail_row(tbody, "HTTP Methods", bullet_list)

        # Parent Resource
        if is_list or resource.uri_object_key is None:
            parent_resource = resource._parent_resource
            is_parent_list = False
        else:
            parent_resource = resource
            is_parent_list = True

        if parent_resource:
            paragraph = nodes.paragraph()
            paragraph += get_ref_to_resource(parent_resource, is_parent_list)
        else:
            paragraph = 'None.'

        append_detail_row(tbody, "Parent Resource", paragraph)

        # Child Resources
        if is_list:
            child_resources = list(resource.list_child_resources)

            if resource.name != resource.name_plural:
                if resource.uri_object_key:
                    child_resources.append(resource)

                are_children_lists = False
            else:
                are_children_lists = True
        else:
            child_resources = resource.item_child_resources
            are_children_lists = True

        if child_resources:
            tocnode = addnodes.toctree()
            tocnode['glob'] = None
            tocnode['maxdepth'] = 1
            tocnode['hidden'] = False

            docnames = sorted([
                docname_join(self.state.document.settings.env.docname,
                             get_resource_docname(child_resource,
                                                  are_children_lists))
                for child_resource in child_resources
            ])

            tocnode['includefiles'] = docnames
            tocnode['entries'] = [(None, docname) for docname in docnames]
        else:
            tocnode = nodes.paragraph(text="None")

        append_detail_row(tbody, "Child Resources", tocnode)

        # Anonymous Access
        if is_list and not resource.singleton:
            getter = resource.get_list
        else:
            getter = resource.get

        if getattr(getter, 'login_required', False):
            anonymous_access = 'No'
        elif getattr(getter, 'checks_login_required', False):
            anonymous_access = 'Yes, if anonymous site access is enabled'
        else:
            anonymous_access = 'Yes'

        append_detail_row(tbody, "Anonymous Access", anonymous_access)

        return table

    def build_fields_table(self, fields, required_fields={},
                           show_requirement_labels=False):
        def get_type_name(field_type):
            # We may be dealing with a forward-declared class.
            if isinstance(field_type, basestring) and field_type is not str:
                field_type = self.get_resource_class(field_type)

            if type(field_type) is list:
                return ([nodes.inline(text='List of ')] +
                        get_type_name(field_type[0]))
            elif type(field_type) is tuple:
                value_nodes = []

                for value in field_type:
                    if value_nodes:
                        value_nodes.append(nodes.inline(text=', '))

                    value_nodes.append(nodes.literal(text=value))

                return [nodes.inline(text='One of ')] + value_nodes
            elif (inspect.isclass(field_type) and
                  issubclass(field_type, WebAPIResource)):
                return [get_ref_to_resource(field_type, False)]
            elif field_type in self.type_mapping:
                return [nodes.inline(text=self.type_mapping[field_type])]
            else:
                print "Unknown type %s" % (field_type,)
                assert False

        table = nodes.table(classes=['resource-fields'])

        tgroup = nodes.tgroup(cols=3)
        table += tgroup

        tgroup += nodes.colspec(colwidth=15, classes=['field'])
        tgroup += nodes.colspec(colwidth=25, classes=['type'])
        tgroup += nodes.colspec(colwidth=60, classes=['description'])

        thead = nodes.thead()
        tgroup += thead
        append_row(thead, ['Field', 'Type', 'Description'])

        tbody = nodes.tbody()
        tgroup += tbody

        if isinstance(fields, dict):
            for field in sorted(fields.iterkeys()):
                info = fields[field]

                name_node = nodes.inline()
                name_node += nodes.strong(text=field)

                if show_requirement_labels:
                    if field in required_fields:
                        name_node += nodes.inline(text=" (required)")
                    else:
                        name_node += nodes.inline(text=" (optional)")

                type_node = nodes.inline()

                if info.get('supports_text_types'):
                    type_node += get_ref_to_doc('webapi2.0-text-fields',
                                                'Rich Text')
                else:
                    type_node += get_type_name(info['type'])

                description_node = parse_text(
                    self, info['description'],
                    where='%s field description' % field)

                if 'added_in' in info:
                    paragraph = nodes.paragraph()
                    paragraph += nodes.emphasis(
                        text='Added in %s\n' % info['added_in'],
                        classes=['field-versioning'])
                    description_node += paragraph

                if 'deprecated_in' in info:
                    paragraph = nodes.paragraph()
                    paragraph += nodes.emphasis(
                        text='Deprecated in %s\n' % info['deprecated_in'],
                        classes=['field-versioning'])
                    description_node += paragraph

                if 'removed_in' in info:
                    paragraph = nodes.paragraph()
                    paragraph += nodes.emphasis(
                        text='Removed in %s\n' % info['removed_in'],
                        classes=['field-versioning'])
                    description_node += paragraph

                append_row(tbody, [name_node, type_node, description_node])
        else:
            for field in sorted(fields):
                name = field

                if show_requirement_labels:
                    if field in required_fields:
                        name += " (required)"
                    else:
                        name += " (optional)"

                append_row(tbody, [name, "", ""])

        return table

    def build_links_table(self, resource):
        is_list = 'is-list' in self.options

        table = nodes.table()

        tgroup = nodes.tgroup(cols=3)
        table += tgroup

        tgroup += nodes.colspec(colwidth=25)
        tgroup += nodes.colspec(colwidth=15)
        tgroup += nodes.colspec(colwidth=60)

        thead = nodes.thead()
        tgroup += thead
        append_row(thead, ['Name', 'Method', 'Resource'])

        tbody = nodes.tbody()
        tgroup += tbody

        request = DummyRequest()

        if is_list:
            child_resources = resource.list_child_resources
        else:
            child_resources = resource.item_child_resources

        names_to_resource = {}

        for child in child_resources:
            names_to_resource[child.name_plural] = (child, True)

        if not is_list and resource.model:
            child_keys = {}
            create_fake_resource_path(request, resource, child_keys, True)
            obj = resource.get_queryset(request, **child_keys)[0]
        else:
            obj = None

        related_links = resource.get_related_links(request=request, obj=obj)

        for key, info in related_links.iteritems():
            if 'resource' in info:
                names_to_resource[key] = \
                    (info['resource'], info.get('list-resource', False))

        links = resource.get_links(child_resources, request=DummyRequest(),
                                   obj=obj)

        for linkname in sorted(links.iterkeys()):
            info = links[linkname]
            child, is_child_link = \
                names_to_resource.get(linkname, (resource, is_list))

            paragraph = nodes.paragraph()
            paragraph += get_ref_to_resource(child, is_child_link)

            append_row(tbody,
                       [nodes.strong(text=linkname),
                        info['method'],
                        paragraph])

        return table

    def build_http_method_section(self, resource, http_method):
        doc = self.get_doc_for_http_method(resource, http_method)
        http_method_func = self.get_http_method_func(resource, http_method)

        # Description text
        returned_nodes = [
            parse_text(self, doc, where='HTTP %s doc' % http_method)
        ]

        # Request Parameters section
        required_fields = getattr(http_method_func, 'required_fields', [])
        optional_fields = getattr(http_method_func, 'optional_fields', [])

        if required_fields or optional_fields:
            all_fields = dict(required_fields)
            all_fields.update(optional_fields)

            fields_section = nodes.section(ids=['%s_params' % http_method])
            returned_nodes.append(fields_section)

            fields_section += nodes.title(text='Request Parameters')

            table = self.build_fields_table(all_fields,
                                            required_fields=required_fields,
                                            show_requirement_labels=True)
            fields_section += table

        # Errors section
        errors = getattr(http_method_func, 'response_errors', [])

        if errors:
            errors_section = nodes.section(ids=['%s_errors' % http_method])
            returned_nodes.append(errors_section)

            errors_section += nodes.title(text='Errors')

            bullet_list = nodes.bullet_list()
            errors_section += bullet_list

            for error in sorted(errors, key=lambda x: x.code):
                item = nodes.list_item()
                bullet_list += item

                paragraph = nodes.paragraph()
                item += paragraph

                paragraph += get_ref_to_error(error)

        return returned_nodes

    def fetch_resource_data(self, resource, mimetype):
        kwargs = {}
        request = DummyRequest()
        request.path = create_fake_resource_path(request, resource, kwargs,
                                                 'is-list' not in self.options)

        headers, data = fetch_response_data(resource, mimetype, request,
                                            **kwargs)

        return request.path, headers, data

    def get_resource_class(self, classname):
        try:
            return get_from_module(classname)
        except ImportError:
            raise ResourceNotFound(self, classname)

    def get_http_method_func(self, resource, http_method):
        if (http_method == 'GET' and 'is-list' in self.options and
            not resource.singleton):
            method_name = 'get_list'
        else:
            method_name = resource.method_mapping[http_method]

            # Change "put" and "post" to "update" and "create", respectively.
            # "put" and "post" are just wrappers and we don't want to show
            # their documentation.
            if method_name == 'put':
                method_name = 'update'
            elif method_name == 'post':
                method_name = 'create'

        return getattr(resource, method_name)

    def get_doc_for_http_method(self, resource, http_method):
        return inspect.getdoc(self.get_http_method_func(resource,
                                                        http_method)) or ''

    def get_http_methods(self, resource, is_list):
        if is_list:
            possible_http_methods = self.list_http_methods
        else:
            possible_http_methods = self.item_http_methods

        return sorted(
            set(resource.allowed_methods).intersection(possible_http_methods))


class ResourceTreeDirective(Directive):
    has_content = True

    def run(self):
        bullet_list = nodes.bullet_list()
        self._output_resource(resources.root, bullet_list, True)

        return [bullet_list]

    def _output_resource(self, resource, parent, is_list):
        item = nodes.list_item()
        parent += item

        paragraph = nodes.paragraph()
        item += paragraph

        paragraph += parse_text(
            self,
            ':ref:`%s <%s>`' %
            (get_resource_title(resource, is_list, False),
             'webapi2.0-%s-resource'
             % get_resource_docname(resource, is_list)))

        bullet_list = nodes.bullet_list()
        item += bullet_list

        if is_list:
            if resource.uri_object_key:
                self._output_resource(resource, bullet_list, False)

            for child in resource.list_child_resources:
                self._output_resource(child, bullet_list, True)
        else:
            for child in resource.item_child_resources:
                self._output_resource(child, bullet_list, True)


class ErrorDirective(Directive):
    has_content = True
    final_argument_whitespace = True
    option_spec = {
        'instance': directives.unchanged_required,
        'example-data': directives.unchanged,
        'title': directives.unchanged,
    }

    MIMETYPES = [
        'application/json',
        'application/xml',
    ]

    def run(self):
        try:
            error_obj = self.get_error_object(self.options['instance'])
        except ErrorNotFound, e:
            return e.error_node

        # Add the class's file and this extension to the dependencies.
        self.state.document.settings.env.note_dependency(__file__)
        self.state.document.settings.env.note_dependency(
            sys.modules[error_obj.__module__].__file__)

        docname = 'webapi2.0-error-%s' % error_obj.code
        error_title = self.get_error_title(error_obj)

        targetnode = nodes.target('', '', ids=[docname], names=[docname])
        self.state.document.note_explicit_target(targetnode)
        main_section = nodes.section(ids=[docname])

        # Details section
        main_section += nodes.title(text=error_title)
        main_section += self.build_details_table(error_obj)

        # Example section
        examples_section = nodes.section(ids=['examples'])
        examples_section += nodes.title(text='Examples')
        extra_params = {}

        if 'example-data' in self.options:
            extra_params = json.loads(self.options['example-data'])

        has_examples = False

        for mimetype in self.MIMETYPES:
            headers, data = \
                fetch_response_data(WebAPIResponseError, mimetype,
                                    err=error_obj,
                                    extra_params=extra_params)
            example_node = build_example(headers, data, mimetype)

            if example_node:
                example_section = nodes.section(ids=['example_' + mimetype])
                examples_section += example_section

                example_section += nodes.title(text=mimetype)
                example_section += example_node
                has_examples = True

        if has_examples:
            main_section += examples_section

        return [targetnode, main_section]

    def build_details_table(self, error_obj):
        table = nodes.table()

        tgroup = nodes.tgroup(cols=2)
        table += tgroup

        tgroup += nodes.colspec(colwidth=20)
        tgroup += nodes.colspec(colwidth=80)

        tbody = nodes.tbody()
        tgroup += tbody

        # API Error Code
        append_detail_row(tbody, 'API Error Code',
                          nodes.literal(text=error_obj.code))

        # HTTP Status Code
        ref = parse_text(self, ':http:`%s`' % error_obj.http_status)
        append_detail_row(tbody, 'HTTP Status Code', ref)

        # Error Text
        append_detail_row(tbody, 'Error Text',
                          nodes.literal(text=error_obj.msg))

        if error_obj.headers:
            if callable(error_obj.headers):
                headers = error_obj.headers(DummyRequest())

            # HTTP Headers
            if len(headers) == 1:
                content = nodes.literal(text=headers.keys()[0])
            else:
                content = nodes.bullet_list()

                for header in headers.iterkeys():
                    item = nodes.list_item()
                    content += item

                    literal = nodes.literal(text=header)
                    item += literal

            append_detail_row(tbody, 'HTTP Headers', content)

        # Description
        append_detail_row(
            tbody, 'Description',
            parse_text(self, '\n'.join(self.content),
                       where='API error %s description' % error_obj.code))

        return table

    def get_error_title(self, error_obj):
        if 'title' in self.options:
            error_title = self.options['title']
        else:
            name = self.options['instance'].split('.')[-1]
            error_title = name.replace('_', ' ').title()

        return '%s - %s' % (error_obj.code, error_title)

    def get_error_object(self, name):
        try:
            return get_from_module(name)
        except ImportError:
            raise ErrorNotFound(self, name)


def parse_text(directive, text, node_type=nodes.paragraph,
               where=None):
    """Parses text in ReST format and returns a node with the content."""
    assert text is not None, 'Missing text during parse_text in %s' % where

    vl = ViewList()

    for line in text.split('\n'):
        vl.append(line, line)

    node = node_type(rawsource=text)
    directive.state.nested_parse(vl, 0, node)
    return node


def get_from_module(name):
    i = name.rfind('.')
    module, attr = name[:i], name[i + 1:]

    try:
        mod = __import__(module, {}, {}, [attr])
        return getattr(mod, attr)
    except (ImportError, AttributeError):
        raise ImportError


def append_row(tbody, cells):
    row = nodes.row()
    tbody += row

    for cell in cells:
        entry = nodes.entry()
        row += entry

        if isinstance(cell, basestring):
            node = nodes.paragraph(text=cell)
        else:
            node = cell

        entry += node


def append_detail_row(tbody, header_text, detail):
    header_node = nodes.strong(text=header_text)

    if isinstance(detail, basestring):
        detail_node = [nodes.paragraph(text=text)
                       for text in detail.split('\n\n')]
    else:
        detail_node = detail

    append_row(tbody, [header_node, detail_node])


FIRST_CAP_RE = re.compile(r'(.)([A-Z][a-z]+)')
ALL_CAP_RE = re.compile(r'([a-z0-9])([A-Z])')


def uncamelcase(name, separator='_'):
    """
    Converts a string from CamelCase into a lowercase name separated by
    a provided separator.
    """
    s1 = FIRST_CAP_RE.sub(r'\1%s\2' % separator, name)
    return ALL_CAP_RE.sub(r'\1%s\2' % separator, s1).lower()


def get_resource_title(resource, is_list, append_resource=True):
    """Returns a human-readable name for the resource."""
    if hasattr(resource, 'verbose_name'):
        normalized_title = resource.verbose_name
    else:
        class_name = resource.__class__.__name__
        class_name = class_name.replace('Resource', '')
        normalized_title = title(uncamelcase(class_name, ' '))

    if is_list:
        s = '%s List' % normalized_title
    else:
        s = normalized_title

    if append_resource:
        s += ' Resource'

    return s


def get_resource_docname(resource, is_list):
    """Returns the name of the page used for a resource's documentation."""
    if inspect.isclass(resource):
        class_name = resource.__name__
    else:
        class_name = resource.__class__.__name__

    class_name = class_name.replace('Resource', '')
    docname = uncamelcase(class_name, '-')

    if is_list and resource.name != resource.name_plural:
        docname = '%s-list' % docname

    return docname


def get_ref_to_doc(refname, title=''):
    """Returns a node that links to a document with the given ref name."""
    ref = addnodes.pending_xref(reftype='ref', reftarget=refname,
                                refexplicit=(title != ''), refdomain='std')
    ref += nodes.literal(title, title, classes=['xref'])
    return ref


def get_ref_to_resource(resource, is_list):
    """Returns a node that links to a resource's documentation."""
    return get_ref_to_doc('webapi2.0-%s-resource' %
                          get_resource_docname(resource, is_list))


def get_ref_to_error(error):
    """Returns a node that links to an error's documentation."""
    return get_ref_to_doc('webapi2.0-error-%s' % error.code)


def get_resource_uri_template(resource, include_child):
    """Returns the URI template for a resource.

    This will go up the resource tree, building a URI based on the URIs
    of the parents.
    """
    if resource.name == 'root':
        path = '/api/'
    else:
        if resource._parent_resource:
            path = get_resource_uri_template(resource._parent_resource, True)

        path += '%s/' % resource.uri_name

        if not resource.singleton and include_child and resource.model:
            path += '{%s}/' % resource.uri_object_key

    return path


def create_fake_resource_path(request, resource, child_keys, include_child):
    """Creates a fake path to a resource.

    This will go up the resource tree, building a URI based on the URIs
    of the parents and based on objects sitting in the database.
    """
    if resource._parent_resource and resource._parent_resource.name != "root":
        path = create_fake_resource_path(request, resource._parent_resource,
                                         child_keys, True)
    else:
        path = '/api/'

    if resource.name != 'root':
        path += '%s/' % resource.uri_name

        if (not resource.singleton and
            include_child and
            resource.model and
            resource.uri_object_key):
                q = resource.get_queryset(request, **child_keys)

                if q.count() == 0:
                    logging.critical('Resource "%s" requires objects in the '
                                     'database', resource.__class__)

                    # Do the assert so it shows up in the logs.
                    assert q.count() > 0

                obj = q[0]
                value = getattr(obj, resource.model_object_key)
                child_keys[resource.uri_object_key] = value
                path += '%s/' % value

    return path


def build_example(headers, data, mimetype):
    if not data:
        return None

    language = None

    for base_mimetype, lang in MIMETYPE_LANGUAGES:
        if is_mimetype_a(mimetype, base_mimetype):
            language = lang
            break

    if language == 'javascript':
        code = json.dumps(json.loads(data), sort_keys=True, indent=2)
    else:
        code = data

    return nodes.literal_block(code, code, language=language or 'text',
                               classes=['example-payload'])


def fetch_response_data(response_class, mimetype, request=None, **kwargs):
    if not request:
        request = DummyRequest()

    request.META['HTTP_ACCEPT'] = mimetype

    result = unicode(response_class(request, **kwargs))
    return result.split('\r\n\r\n', 1)


def setup(app):
    app.add_directive('webapi-resource', ResourceDirective)
    app.add_directive('webapi-resource-tree', ResourceTreeDirective)
    app.add_directive('webapi-error', ErrorDirective)
    app.add_crossref_type('webapi2.0', 'webapi2.0', 'single: %s',
                          nodes.emphasis)
