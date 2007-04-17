from django.core.serializers import serialize
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.utils import simplejson

class JsonResponse(HttpResponse):
    def __init__(self, obj):
        if isinstance(obj, QuerySet):
            content = serialize('json', obj)
        else:
            content = simplejson.dumps(obj, cls=DateTimeAwareJSONEncoder)

        super(JsonResponse, self).__init__(content, mimetype='text/plain')
        #super(JsonResponse, self).__init__(content, mimetype='application/json')
