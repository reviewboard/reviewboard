import datetime
import time

from django.contrib.auth.models import User
from django.db.models.aggregates import Count
from django.utils.translation import ugettext as _
from djblets.util.misc import cache_memoize

from reviewboard.admin.cache_stats import get_cache_stats
from reviewboard.attachments.models import FileAttachment
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.diffviewer.models import DiffSet
from reviewboard.reviews.models import ReviewRequest, Group, \
                                       Comment, Review, Screenshot, \
                                       ReviewRequestDraft
from reviewboard.scmtools.models import Repository


DAYS_TOTAL = 30 # Set the number of days to display in date browsing widgets


def get_user_activity_widget(request):
    """User activity widget.

    A pie chart of active application users based on their last login date.
    """
    def activity_data():
        now = datetime.date.today()
        users = User.objects

        week = datetime.timedelta(days=7)
        day = datetime.timedelta(days=1)
        month = datetime.timedelta(days=30)
        two_months = datetime.timedelta(days=60)
        three_months = datetime.timedelta(days=90)

        one_day = (now - week, now + day)
        seven_days = (now - month, now - week)
        thirty_days = (now - two_months, now - month)
        sixty_days = (now - three_months, now - two_months)
        ninety_days = now - three_months

        return {
            'now': users.filter(last_login__range=one_day).count(),
            'seven_days': users.filter(last_login__range=seven_days).count(),
            'thirty_days': users.filter(last_login__range=thirty_days).count(),
            'sixty_days': users.filter(last_login__range=sixty_days).count(),
            'ninety_days': users.filter(last_login__lte=ninety_days).count(),
            'total': users.count()
        }

    widget_actions = [
        ('db/auth/user/add/', _("Add New")),
        ('db/auth/user/', _("Manage Users"), 'btn-right')
    ]

    key = "w-user-activity-" + str(datetime.date.today())

    return {
        'size': 'widget-large',
        'template': 'admin/widgets/w-user-activity.html',
        'data': cache_memoize(key, activity_data),
        'actions': widget_actions
    }


def get_request_statuses(request):
    """Request statuses by percentage widget.

    A pie chart showing review request by status.
    """
    def status_data():
        request_objects = ReviewRequest.objects.all()

        return {
            'pending': request_objects.filter(status="P").count(),
            'draft': request_objects.filter(status="D").count(),
            'submit': request_objects.filter(status="S").count()
        }

    key = "w-request-statuses-" + str(datetime.date.today())

    return {
        'size': 'widget-small',
        'template': 'admin/widgets/w-request-statuses.html',
        'actions': '',
        'data': cache_memoize(key, status_data)
    }


def get_repositories(request):
    """Shows a list of repositories in the system.

    This widget displays a table with the most recent repositories.
    """
    def repo_data():
        return Repository.objects.accessible(request.user).order_by('-id')[:3]

    key = "w-repositories-" + str(datetime.date.today())

    return {
        'size': 'widget-large',
        'template': 'admin/widgets/w-repositories.html',
        'actions': [
            ('db/scmtools/repository/add/', _("Add")),
            ('db/scmtools/repository/',  _("View All"), 'btn-right')
        ],
        'data': cache_memoize(key, repo_data)
    }


def get_groups(request):
    """Review group listing.

    Shows a list of recently created groups.
    """
    return {
        'size': 'widget-small',
        'template': 'admin/widgets/w-groups.html',
        'actions': [
            ('db/reviews/group/add/', _("Add")),
            ('db/reviews/group/', _("View All"))
        ],
        'data': cache_memoize("w-groups-" + str(datetime.date.today()),
                              lambda: Group.objects.all().order_by('-id')[:5]),
    }


def get_server_cache(request):
    """Cache statistic widget.

    A list of memcached statistic if available to the application.
    """
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

    return {
        'size': 'widget-small',
        'template': 'admin/widgets/w-server-cache.html',
        'actions': '',
        'data': cache_data
    }


def get_news(request):
    """News widget.

    Latest Review Board news via RSS.
    """
    return {
        'size': 'widget-small',
        'template': 'admin/widgets/w-news.html',
        'actions': [
                ('http://www.reviewboard.org/news/', _('More')),
                ('#', _('Reload'), 'reload-news')
        ],
        'data': ''
    }


def get_stats(request):
    """Shows a list of totals for multiple database objects.

    Passes a count for Comments, Reviews and more to render a widget table.
    """
    def stats_data():
        return {
            'count_comments': Comment.objects.all().count(),
            'count_reviews': Review.objects.all().count(),
            'count_attachments': FileAttachment.objects.all().count(),
            'count_reviewdrafts': ReviewRequestDraft.objects.all().count(),
            'count_screenshots': Screenshot.objects.all().count(),
            'count_diffsets': DiffSet.objects.all().count()
        }

    key = "w-stats-" + str(datetime.date.today())

    return {
        'size': 'widget-small',
        'template': 'admin/widgets/w-stats.html',
        'actions': '',
        'data': cache_memoize(key, stats_data)
    }


def get_recent_actions(request):
    """Shows a list of recent admin actions to the user.

    Based on the default Django admin widget.
    """
    return {
        'size': 'widget-small',
        'template': 'admin/widgets/w-recent-actions.html',
        'actions': '',
        'data': ''
    }


def dynamic_activity_data(request):
    """Large database acitivity widget helper.

    This method serves as a helper for the activity widget, it's used with for
    AJAX requests based on date ranges passed to it.
    """
    direction = request.GET.get('direction')
    range_end = request.GET.get('range_end')
    range_start = request.GET.get('range_start')
    days_total = DAYS_TOTAL

    # Convert the date from the request.
    #
    # This takes the date from the request in YYYY-MM-DD format and
    # converts into a format suitable for QuerySet later on.
    if range_end and range_start:
        range_end = datetime.datetime.fromtimestamp(
            time.mktime(time.strptime(range_end, "%Y-%m-%d")))
        range_start = datetime.datetime.fromtimestamp(
            time.mktime(time.strptime(range_start, "%Y-%m-%d")))

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

    def large_stats_data(range_start, range_end):
        def get_objects(modelName, timestampField, dateField):
            """Perform timestamp based queries.

            This method receives a dynamic model name and performs a filter
            query. Later the results are grouped by day and prepared for the
            charting library.
            """
            args = '%s__range' % timestampField
            q = modelName.objects.filter(**{
                args: (range_start, range_end)
            })
            q = q.extra({timestampField: dateField})
            q = q.values(timestampField)
            q = q.annotate(created_count=Count('pk'))
            q = q.order_by(timestampField)

            data = []

            for obj in q:
                data.append([
                    time.mktime(time.strptime(obj[timestampField],
                                              "%Y-%m-%d")) * 1000,
                    obj['created_count']
                ])

            return data

        comment_array = get_objects(Comment, "timestamp", "date(timestamp)")
        change_desc_array = get_objects(ChangeDescription, "timestamp",
                                        "date(timestamp)")
        review_array = get_objects(Review, "timestamp", "date(timestamp)")
        rr_array = get_objects(ReviewRequest, "time_added", "date(time_added)")

        return {
            'change_descriptions': change_desc_array,
            'comments': comment_array,
            'reviews': review_array,
            'review_requests': rr_array
        }

    stats_data = large_stats_data(new_range_start, new_range_end)

    return {
        "range": response_data,
        "activity_data": stats_data
    }


def get_large_stats(request):
    """Shows the latest database activity for multiple models.

    This ajax powered widget shows a daily view of creation activity for a
    list of models. This construct doesn't send any widget data, all data
    comes from the ajax request on page load.
    """
    return {
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
