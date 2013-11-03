def localsite(request):
    return {
        'local_site_name': getattr(request, '_local_site_name', None),
    }
