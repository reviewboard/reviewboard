import datetime
import re
import time

from django.contrib.auth.models import User
from django.db.models.aggregates import Count
from django.template.context import RequestContext
from django.template.loader import render_to_string
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

NAME_TRANSFORM_RE = re.compile('([A-Z])')


primary_widgets = []
secondary_widgets = []


class Widget(object):
    """The base class for an Administration Dashboard widget.

    Widgets appear in the Administration Dashboard and can display useful
    information on the system, links to other pages, or even fetch data
    from external sites.

    There are a number of built-in widgets, but extensions can provide their
    own.
    """
    # Constants
    SMALL = 'small'
    LARGE = 'large'

    # Configuration
    title = None
    icon = None
    size = SMALL
    template = None
    actions = []
    has_data = True
    cache_data = True

    def __init__(self):
        self.data = None
        self.name = NAME_TRANSFORM_RE.sub(
            lambda m: '-%s' % m.group(1).lower(),
            self.__class__.__name__)[1:]

    def render(self, request):
        """Renders a widget.

        This will render the HTML for a widget. It takes care of generating
        and caching the data, depending on the widget's needs.
        """
        if self.has_data and self.data is None:
            if self.cache_data:
                self.data = cache_memoize(self.generate_cache_key(request),
                                          lambda: self.generate_data(request))
            else:
                self.data = self.generate_data(request)

        return render_to_string('admin/admin_widget.html',
                                RequestContext(request, {
            'widget': self,
        }))

    def generate_data(self, request):
        """Generates data for the widget.

        Widgets should override this to provide extra data to pass to the
        template. This will be available in 'widget.data'.

        If cache_data is True, this data will be cached for the day.
        """
        return {}

    def generate_cache_key(self, request):
        """Generates a cache key for this widget's data.

        By default, the key takes into account the current day. If the
        widget is displaying specific to, for example, the user, this should
        be overridden to include that data in the key.
        """
        return "w-%s-%s" % (self.name, str(datetime.date.today()))


class UserActivityWidget(Widget):
    """User activity widget.

    Displays a pie chart of the active application users based on their last
    login dates.
    """
    title = 'User Activity'
    size = Widget.LARGE
    template = 'admin/widgets/w-user-activity.html'
    actions = [
        {
            'url': 'db/auth/user/add/',
            'label': _('Add'),
        },
        {
            'url': 'db/auth/user/',
            'label': _('Manage Users'),
            'classes': 'btn-right',
        },
    ]

    def generate_data(self, request):
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


class ReviewRequestStatusesWidget(Widget):
    """Review request statuses widget.

    Displays a pie chart showing review request by status.
    """
    title = 'Request Statuses'
    template = 'admin/widgets/w-request-statuses.html'

    def generate_data(self, request):
        request_objects = ReviewRequest.objects.all()

        return {
            'pending': request_objects.filter(status="P").count(),
            'draft': request_objects.filter(status="D").count(),
            'submit': request_objects.filter(status="S").count()
        }


class RepositoriesWidget(Widget):
    """Shows a list of repositories in the system.

    This widget displays a table with the most recent repositories,
    their types, and visibility.
    """
    MAX_REPOSITORIES = 3

    title = 'Repositories'
    size = Widget.LARGE
    template = 'admin/widgets/w-repositories.html'
    actions = [
        {
            'url': 'db/scmtools/repository/add/',
            'label': _('Add'),
        },
        {
            'url': 'db/scmtools/repository/',
            'label': _('View All'),
            'classes': 'btn-right',
        },
    ]

    def generate_data(self, request):
        repos = Repository.objects.accessible(request.user).order_by('-id')

        return {
            'repositories': repos[:self.MAX_REPOSITORIES]
        }

    def generate_cache_key(self, request):
        return "w-%s-%s-%s" % (self.name, request.user.username,
                               str(datetime.date.today()))


class ReviewGroupsWidget(Widget):
    """Review groups widget.

    Shows a list of recently created groups.
    """
    MAX_GROUPS = 5

    title = 'Review Groups'
    template = 'admin/widgets/w-groups.html'
    icon = 'rb/images/admin/set-auth.png'
    actions = [
        {
            'url': 'db/reviews/group/',
            'label': _('View All'),
            'classes': 'btn-right',
        },
        {
            'url': 'db/reviews/group/add/',
            'label': _('Add'),
        },
    ]

    def generate_data(self, request):
        return {
            'groups': Group.objects.all().order_by('-id')[:self.MAX_GROUPS]
        }


class ServerCacheWidget(Widget):
    """Cache statistics widget.

    Displays a list of memcached statistics, if available.
    """
    title = 'Server Cache'
    template = 'admin/widgets/w-server-cache.html'
    icon = 'rb/images/admin/set-storage.png'
    cache_data = False

    def generate_data(self, request):
        uptime = {}
        cache_stats = get_cache_stats()

        if cache_stats:
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

        return {
            'cache_stats': cache_stats,
            'uptime': uptime
        }


class NewsWidget(Widget):
    """News widget.

    Displays the latest news headlines from reviewboard.org.
    """
    title = 'Review Board News'
    template = 'admin/widgets/w-news.html'
    icon = 'rb/images/rss.png'
    actions = [
        {
            'url': 'http://www.reviewboard.org/news/',
            'label': _('More'),
        },
        {
            'label': _('Reload'),
            'id': 'reload-news',
        },
    ]
    has_data = False


class DatabaseStatsWidget(Widget):
    """Database statistics widget.

    Displays a list of totals for several important database tables.
    """
    title = 'Database Stats'
    template = 'admin/widgets/w-stats.html'

    def generate_data(self, request):
        return {
            'count_comments': Comment.objects.all().count(),
            'count_reviews': Review.objects.all().count(),
            'count_attachments': FileAttachment.objects.all().count(),
            'count_reviewdrafts': ReviewRequestDraft.objects.all().count(),
            'count_screenshots': Screenshot.objects.all().count(),
            'count_diffsets': DiffSet.objects.all().count()
        }


class RecentActionsWidget(Widget):
    """Recent actions widget.

    Displays a list of recent admin actions to the user.
    """
    title = 'Recent Actions'
    template = 'admin/widgets/w-recent-actions.html'
    has_data = False


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
                    time.mktime(time.strptime(str(obj[timestampField]),
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


class ActivityGraphWidget(Widget):
    """Detailed database statistics graph widget.

    Shows the latest database activity for multiple models in the form of
    a graph that can be navigated by date.

    This widget shows a daily view of creation activity for a list of models.
    All displayed widget data is computed on demand, rather than up-front
    during creation of the widget.
    """
    title = 'Review Board Activity'
    size = Widget.LARGE
    template = 'admin/widgets/w-stats-large.html'
    actions = [
        {
            'label': '<',
            'id': 'db-stats-graph-prev',
            'rel': 'prev',
        },
        {
            'label': '>',
            'id': 'db-stats-graph-next',
            'rel': 'next',
        },
        {
            'label': _('Reviews'),
            'classes': 'btn-s btn-s-checked',
            'rel': 'reviews',
        },
        {
            'label': _('Comments'),
            'classes': 'btn-s btn-s-checked',
            'rel': 'comments',
        },
        {

            'label': _('Review Requests'),
            'classes': 'btn-s btn-s-checked',
            'rel': 'review_requests',
        },
        {
            'label': _('Changes'),
            'classes': 'btn-s btn-s-checked',
            'rel': 'change_descriptions',
        },
    ]
    has_data = False


def register(widget, primary=False):
    if primary:
        primary_widgets.append(widget)
    else:
        secondary_widgets.append(widget)


def unregister(widget):
    try:
        primary_widgets.remove(widget)
    except ValueError:
        try:
            secondary_widgets.remove(widget)
        except ValueError:
            pass


# Register the built-in widgets
register(ActivityGraphWidget, True)
register(RepositoriesWidget, True)
register(UserActivityWidget, True)

register(ReviewRequestStatusesWidget)
register(RecentActionsWidget)
register(ReviewGroupsWidget)
register(ServerCacheWidget)
register(NewsWidget)
register(DatabaseStatsWidget)
