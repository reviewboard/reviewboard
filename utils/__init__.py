from django.core.serializers import serialize
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.utils import simplejson

class JsonResponse(HttpResponse):
    def __init__(self, request, obj):
        json = obj
        json['stat'] = 'ok'

        if isinstance(obj, QuerySet):
            content = serialize('json', json)
        else:
            content = simplejson.dumps(json, cls=DateTimeAwareJSONEncoder)

        callback = request.GET.get('callback', None)

        if callback != None:
            content = callback + "(" + content + ");"

        super(JsonResponse, self).__init__(content, mimetype='text/plain')
        #super(JsonResponse, self).__init__(content, mimetype='application/json')
