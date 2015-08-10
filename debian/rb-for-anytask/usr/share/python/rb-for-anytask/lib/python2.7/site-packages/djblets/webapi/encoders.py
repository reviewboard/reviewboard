from __future__ import unicode_literals

import json
from xml.sax.saxutils import XMLGenerator

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.db.models.query import QuerySet
from django.utils import six
from django.utils.six.moves import cStringIO as StringIO

from djblets.util.serializers import DjbletsJSONEncoder


class WebAPIEncoder(object):
    """Encodes an object into a dictionary of fields and values.

    This object is used for both JSON and XML API formats.

    Projects can subclass this to provide representations of their objects.
    To make use of a encoder, add the path to the encoder class to
    the project's settings.WEB_API_ENCODERS list.

    For example:

    WEB_API_ENCODERS = (
        'myproject.webapi.MyEncoder',
    )
    """

    def encode(self, o, *args, **kwargs):
        """Encodes an object.

        This is expected to return either a dictionary or a list. If the
        object being encoded is not supported, return None, or call
        the superclass's encode method.
        """
        return None


class BasicAPIEncoder(WebAPIEncoder):
    """A basic encoder that encodes standard types.

    This supports encoding of dates, times, QuerySets, Users, and Groups.
    """
    def encode(self, o, *args, **kwargs):
        if isinstance(o, QuerySet):
            return list(o)
        elif isinstance(o, User):
            return {
                'id': o.id,
                'username': o.username,
                'first_name': o.first_name,
                'last_name': o.last_name,
                'fullname': o.get_full_name(),
                'email': o.email,
                'url': o.get_absolute_url(),
            }
        elif isinstance(o, Group):
            return {
                'id': o.id,
                'name': o.name,
            }
        else:
            try:
                return DjbletsJSONEncoder().default(o)
            except TypeError:
                return None


class ResourceAPIEncoder(WebAPIEncoder):
    """An encoder that encodes objects based on registered resources."""
    def encode(self, o, *args, **kwargs):
        if isinstance(o, QuerySet):
            return list(o)
        else:
            calling_resource = kwargs.pop('calling_resource', None)

            if calling_resource:
                serializer = calling_resource.get_serializer_for_object(o)
            else:
                from djblets.webapi.resources import get_resource_for_object

                serializer = get_resource_for_object(o)

            if serializer:
                return serializer.serialize_object(o, *args, **kwargs)
            else:
                try:
                    return DjbletsJSONEncoder().default(o)
                except TypeError:
                    return None


class JSONEncoderAdapter(json.JSONEncoder):
    """Adapts a WebAPIEncoder to be used with json.

    This takes an existing encoder and makes it available to use as a
    json.JSONEncoder. This is used internally when generating JSON from a
    WebAPIEncoder, but can be used in other projects for more specific
    purposes as well.
    """
    def __init__(self, encoder, *args, **kwargs):
        json.JSONEncoder.__init__(self, *args, **kwargs)
        self.encoder = encoder

    def encode(self, o, *args, **kwargs):
        self.encode_args = args
        self.encode_kwargs = kwargs
        return super(JSONEncoderAdapter, self).encode(o)

    def default(self, o):
        """Encodes an object using the supplied WebAPIEncoder.

        If the encoder is unable to encode this object, a TypeError is raised.
        """
        result = self.encoder.encode(o, *self.encode_args,
                                     **self.encode_kwargs)

        if result is None:
            raise TypeError("%r is not JSON serializable" % (o,))

        return result


class XMLEncoderAdapter(object):
    """Adapts a WebAPIEncoder to output XML.

    This takes an existing encoder and adapts it to output a simple XML format.
    """
    def __init__(self, encoder, *args, **kwargs):
        self.encoder = encoder

    def encode(self, o, *args, **kwargs):
        self.level = 0
        self.doIndent = False

        stream = StringIO()
        self.xml = XMLGenerator(stream, settings.DEFAULT_CHARSET)
        self.xml.startDocument()
        self.startElement("rsp")
        self.__encode(o, *args, **kwargs)
        self.endElement("rsp")
        self.xml.endDocument()
        self.xml = None

        return stream.getvalue()

    def __encode(self, o, *args, **kwargs):
        if isinstance(o, dict):
            for key, value in six.iteritems(o):
                attrs = {}

                if isinstance(key, six.integer_types):
                    attrs['value'] = str(key)
                    key = 'int'

                self.startElement(key, attrs)
                self.__encode(value, *args, **kwargs)
                self.endElement(key)
        elif isinstance(o, (tuple, list)):
            self.startElement("array")

            for i in o:
                self.startElement("item")
                self.__encode(i, *args, **kwargs)
                self.endElement("item")

            self.endElement("array")
        elif isinstance(o, six.string_types):
            self.text(o)
        elif isinstance(o, six.integer_types):
            self.text("%d" % o)
        elif isinstance(o, bool):
            if o:
                self.text("True")
            else:
                self.text("False")
        elif o is None:
            pass
        else:
            result = self.encoder.encode(o, *args, **kwargs)

            if result is None:
                raise TypeError("%r is not XML serializable" % (o,))

            return self.__encode(result, *args, **kwargs)

    def startElement(self, name, attrs={}):
        self.addIndent()
        self.xml.startElement(name, attrs)
        self.level += 1
        self.doIndent = True

    def endElement(self, name):
        self.level -= 1
        self.addIndent()
        self.xml.endElement(name)
        self.doIndent = True

    def text(self, value):
        self.xml.characters(value)
        self.doIndent = False

    def addIndent(self):
        if self.doIndent:
            self.xml.ignorableWhitespace('\n' + ' ' * self.level)


_registered_encoders = None


def get_registered_encoders():
    """
    Returns a list of registered Web API encoders.
    """
    global _registered_encoders

    if _registered_encoders is None:
        _registered_encoders = []

        encoders = getattr(settings, 'WEB_API_ENCODERS',
                           ['djblets.webapi.encoders.BasicAPIEncoder'])

        for encoder in encoders:
            encoder_path = encoder.split('.')
            if len(encoder_path) > 1:
                encoder_module_name = '.'.join(encoder_path[:-1])
            else:
                encoder_module_name = '.'

            encoder_module = __import__(encoder_module_name, {}, {},
                                        encoder_path[-1])
            encoder_class = getattr(encoder_module, encoder_path[-1])
            _registered_encoders.append(encoder_class())

    return _registered_encoders
