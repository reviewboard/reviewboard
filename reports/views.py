from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template.context import RequestContext

from reviewboard.reviews.models import ReviewRequest, Review


reports = {
    'review_request': {
        'name': 'Review Requests',
        'templates': {
            'text': {
                'name': 'Plain Text',
                'template': 'reports/review_request-text.txt',
                'content-type': 'text/plain',
            },
            'moinmoin': {
                'name': 'Wiki (MoinMoin)',
                'template': 'reports/review_request-moinmoin.txt',
                'content-type': 'text/plain',
            },
        },
    },
    'review': {
        'name': 'Reviews Given',
        'templates': {
            'text': {
                'name': 'Plain Text',
                'template': 'reports/review-text.txt',
                'content-type': 'text/plain',
            },
            'moinmoin': {
                'name': 'Wiki (MoinMoin)',
                'template': 'reports/review-moinmoin.txt',
                'content-type': 'text/plain',
            }
        },
    },
    'status_report': {
        'name': 'Combined Status Report',
        'templates': {
            'text': {
                'name': 'Plain Text',
                'template': 'reports/status_report-text.txt',
                'content-type': 'text/plain',
            },
            'moinmoin': {
                'name': 'Wiki (MoinMoin)',
                'template': 'reports/status_report-moinmoin.txt',
                'content-type': 'text/plain',
            },
        },
    }
}


def report(request, username, format, report, get_context):
    # FIXME - error checking?
    period = int(request.GET.get('period', 7))

    user = User.objects.get(username=username)

    try:
        template = report['templates'][format]
    except KeyError:
        raise Http404

    since = datetime.now() - timedelta(days=period)

    context = get_context(user, since)
    context.update({
        'domain': Site.objects.get(pk=settings.SITE_ID).domain,
        'domain_method': settings.DOMAIN_METHOD,
    })

    return HttpResponse(
        render_to_response(template['template'],
                           RequestContext(request, context)),
        content_type=template['content-type'] + ";charset=UTF-8")


def review_request(request, username, format):
    return report(request, username, format,
                  reports['review_request'],
                  lambda user, since: {
                      'review_requests' : ReviewRequest.objects.filter(
                          submitter=user,
                          time_added__gt=since)
                  })


def review(request, username, format):
    return report(request, username, format,
                  reports['review'],
                  lambda user, since: {
                      'reviews' : Review.objects.filter(
                          user=user,
                          timestamp__gt=since)
                  })


def status_report(request, username, format):
    return report(request, username, format,
                  reports['status_report'],
                  lambda user, since: {
                      'review_requests' : ReviewRequest.objects.filter(
                          submitter=user,
                          time_added__gt=since),
                      'reviews' : Review.objects.filter(
                          user=user,
                          timestamp__gt=since)
                  })


def report_list(request,
                template_name='reports/report_list.html'):

    return render_to_response(template_name, RequestContext(request, {
        'reports': reports,
    }))
