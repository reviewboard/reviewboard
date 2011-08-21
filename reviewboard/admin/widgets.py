import sys
from attachments.models import FileAttachment

import datetime

from diffviewer.models import DiffSet

from django.contrib.auth.models import User
from django.db.models.aggregates import Count
from django.utils.translation import ugettext as _
from djblets.util.misc import cache_memoize

from reviewboard.admin.cache_stats import get_cache_stats
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.scmtools.models import Repository
from reviewboard.reviews.models import ReviewRequest, Group, \
                                       Comment, Review, Screenshot, \
                                       ReviewRequestDraft

import time


DAYS_TOTAL = 30 # Set the number of days to display in date browsing widgets

def getUserActivityWidget(request):
    """ User Activity Widget
    A pie chart of active application users based on their last login date
    """

    def activityData():
        now = datetime.date.today()
        users = User.objects

        activity_list = {
            'now': users.filter(last_login__range=\
                (now - datetime.timedelta(days=7),
                 now + datetime.timedelta(days=1))).count(),
            'seven_days': users.filter(last_login__range=\
                (now - datetime.timedelta(days=30),
                 now - datetime.timedelta(days=7))).count(),
            'thirty_days': users.filter(last_login__range=\
                (now - datetime.timedelta(days=60),
                 now - datetime.timedelta(days=30))).count(),
            'sixty_days': users.filter(last_login__range=\
                (now - datetime.timedelta(days=90),
                 now - datetime.timedelta(days=60))).count(),
            'ninety_days': users.filter(last_login__lte=\
                now - datetime.timedelta(days=90)).count(),
            'total': users.count()
        }

        return activity_list

    widget_actions = [
        ('db/auth/user/add/', _("Add New")),
        ('db/auth/user/', _("Manage Users"), 'btn-right')
    ]

    key = "w-user-activity-" + str(datetime.date.today())
    widget_data = {
        'size': 'widget-large',
        'template': 'admin/widgets/w-user-activity.html',
        'data': cache_memoize(key,activityData),
        'actions': widget_actions
    }

    return widget_data


def getRequestStatuses(request):
    """ Request Statuses by Percentage Widget
    A pie chart showing review request by status """

    def statusData():
        request_objects = ReviewRequest.objects

        request_count = {
            'pending': request_objects.filter(status="P").count(),
            'draft': request_objects.filter(status="D").count(),
            'submit': request_objects.filter(status="S").count()
        }
        return request_count

    key = "w-request-statuses-" + str(datetime.date.today())
    widget_data = {
        'size': 'widget-small',
        'template': 'admin/widgets/w-request-statuses.html',
        'actions': '',
        'data': cache_memoize(key, statusData)
    }
    return widget_data


def getRepositories(request):
    """ Shows a list of repositories in the system

    This widget displays a table with the most recent repositories.
     """
    def repoData():
        repositories = Repository.objects.accessible(request.user)\
            .order_by('-id')[:3]
        return repositories

    key = "w-repositories-" + str(datetime.date.today())
    widget_data = {
        'size': 'widget-large',
        'template': 'admin/widgets/w-repositories.html',
        'actions': [
            ('db/scmtools/repository/add/', _("Add")),
            ('db/scmtools/repository/',  _("View All"), 'btn-right')
        ],
        'data': cache_memoize(key, repoData)
    }

    return widget_data


def getGroups(request):
    """ Review Group Listing

    Shows a list of recently created groups """
    def groupData():
        review_groups = Group.objects.all().order_by('-id')[:5]
        return review_groups

    key = "w-groups-"+ str(datetime.date.today())
    widget_data = {
        'size': 'widget-small',
        'template': 'admin/widgets/w-groups.html',
        'actions': [
            ('db/reviews/group/add/', _("Add")),
            ('db/reviews/group/', _("View All"))
        ],
        'data': cache_memoize(key, groupData)
    }
    return widget_data


def getServerCache(request):
    """ Cache Statistic Widget

    A list of memcached statistic if available to the application """
    cache_stats = get_cache_stats()
    uptime = {}

    for hosts, stats in cache_stats:
        if stats['uptime'] > 86400:
            uptime['value'] = stats['uptime'] / 60 / 60 / 24
            uptime['unit'] = _("days")
        elif stats['uptime'] > 3600:
            uptime['value'] = stats['uptime'] / 60 / 60
            uptime['unit'] = _("hours")
        else:
            uptime['value'] = stats['uptime'] / 60
            uptime['unit'] =  _("minutes")

    cache_data = {
        "cache_stats": cache_stats,
        "uptime": uptime
    }

    widget_data = {
        'size': 'widget-small',
        'template': 'admin/widgets/w-server-cache.html',
        'actions': '',
        'data': cache_data
    }
    return widget_data


def getNews(request):
    """ News Widget

    Latest Review Board news via RSS """

    widget_data = {
    'size': 'widget-small',
    'template': 'admin/widgets/w-news.html',
    'actions': [
            ('http://www.reviewboard.org/news/', _('More')),
            ('#', _('Reload'), 'reload-news')
    ],
        'data': ''
    }
    return widget_data


def getStats(request):
    """ Shows a list of totals for multiple database objects.

    Passes a count for Comments, Reviews and more to render a widget table
     """
    def statsData():
        stats_data = {
            'count_comments': Comment.objects.all().count(),
            'count_reviews': Review.objects.all().count(),
            'count_attachments': FileAttachment.objects.all().count(),
            'count_reviewdrafts': ReviewRequestDraft.objects.all().count(),
            'count_screenshots': Screenshot.objects.all().count(),
            'count_diffsets': DiffSet.objects.all().count()
        }
        return stats_data

    key = "w-stats-" + str(datetime.date.today())
    widget_data = {
        'size': 'widget-small',
        'template': 'admin/widgets/w-stats.html',
        'actions': '',
        'data': cache_memoize(key, statsData)
    }
    return widget_data


def getRecentActions(request):
    """ Shows a list of recent admin actions to the user.

    Based on the default Django admin widget.
     """

    widget_data = {
        'size': 'widget-small',
        'template': 'admin/widgets/w-recent-actions.html',
        'actions': '',
        'data': ''
    }

    return widget_data


def dynamicActivityData(request):
    """ Large Database Acitivity Widget Helper

     This method serves as a helper for the activity widget, it's used with for
     AJAX requests based on date ranges passed to it.
     """
    direction = request.GET.get('direction')
    range_end = request.GET.get('range_end')
    range_start = request.GET.get('range_start')
    days_total = DAYS_TOTAL

    """ Converting the date from the request

    This takes the date from the request in YYYY-MM-DD format and
    converts into a format suitable for QuerySet later on.
    """
    if range_end and range_start:
       range_end = datetime.datetime.fromtimestamp(time.mktime(time\
            .strptime(request.GET.get('range_end'), "%Y-%m-%d")))
       range_start = datetime.datetime.fromtimestamp(time.mktime(time\
            .strptime(request.GET.get('range_start'), "%Y-%m-%d")))

    if direction == "next":
        new_range_start = range_end
        new_range_end = \
            new_range_start + datetime.timedelta(days=days_total)
    elif direction == "prev":
        new_range_start = range_start - datetime.timedelta(days=days_total)
        new_range_end = range_start
    elif direction == "same":
        new_range_start = range_start
        new_range_end = range_end
    else:
        new_range_end = datetime.date.today()
        new_range_start = new_range_end - datetime.timedelta(days=days_total)

    response_data = {
        "range_start": new_range_start.strftime("%Y-%m-%d"),
        "range_end": new_range_end.strftime("%Y-%m-%d")
    }

    def largeStatsData(range_start, range_end):
        def getObjects(modelName, timestampField, dateField):
            """ Perform timestamp based queries

            This method receives a dynamic model name and performs a filter
            query. Later the results are grouped by day and prepared for the
            charting library.
            """
            args = '%s__%s' % (timestampField, 'range')
            unique_objects = \
                modelName.objects.filter(**{args: (range_start, range_end)})\
                    .extra({timestampField: dateField})\
                    .values(timestampField).annotate(created_count=Count('id'))\
                    .order_by(timestampField)

            data_array = []
            for object in unique_objects:
                inner_array = []
                made_time = time.mktime(time.strptime(\
                    object[timestampField], "%Y-%m-%d")) * 1000
                inner_array.append(made_time)
                inner_array.append(object['created_count'])
                data_array.append(inner_array)
            return data_array

        comment_array = getObjects(Comment, "timestamp", "date(timestamp)")
        change_desc_array = \
            getObjects(ChangeDescription, "timestamp", "date(timestamp)")
        review_array = getObjects(Review, "timestamp", "date(timestamp)")
        rr_array = getObjects(ReviewRequest, "time_added", "date(time_added)")

        # getting all widget_data together
        stat_data = {
            'change_descriptions': change_desc_array,
            'comments': comment_array,
            'reviews': review_array,
            'review_requests': rr_array
        }

        return stat_data

    stats_data  = largeStatsData(new_range_start, new_range_end)
    activity_data = {
        "range":response_data,
        "activity_data": stats_data
    }

    return activity_data


def getLargeStats(request):
    """ Shows latest database activity for multiple models

     This ajax powered widget shows a daily view of creation activity for a list of
     models. This construct doesn't send any widget data, all data comes from
     the ajax request on page load.
     """

    widget_data = {
        'size': 'widget-large',
        'template': 'admin/widgets/w-stats-large.html',
        'actions':  [
            ('#', _('<'), '', 'set-prev'),
            ('#', _('>'), '', 'set-next'),
            ('#', _('Reviews'), 'btn-s btn-s-checked', 'set-reviews'),
            ('#', _('Comments'), 'btn-s btn-s-checked', 'set-comments'),
            ('#', _('Review Requests'), 'btn-s btn-s-checked', 'set-requests'),
            ('#', _('Descriptions'), 'btn-s btn-s-checked', 'set-descriptions')
        ],
        'data': ["Loading..."]
    }
    return widget_data