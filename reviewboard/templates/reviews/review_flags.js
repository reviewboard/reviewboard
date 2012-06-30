{% load djblets_utils %}
  /*
   * Initial state from the server. These should all be thought of as
   * constants, not state.
   */
{% if not error %}
  var gBugTrackerURL = "{{review_request.repository.bug_tracker}}";
  var gReviewRequestPath = "{{review_request.get_absolute_url}}";
  var gReviewRequestId = "{{review_request.display_id}}";
  var gReviewRequestSummary = "{{review_request.summary|escapejs}}";
  var gReviewRequestSitePrefix = "{% if review_request.local_site %}s/{{review_request.local_site.name}}/{% endif %}";
  var gReviewPending = {% if review %}true{% else %}false{% endif %};
{%  if request.user.pk == review_request.submitter_id or perms.reviews.can_edit_reviewrequest %}
{%   if review_request.status == 'P' %}
  var gEditable = true;
{%   endif %}
{%  endif %}
{% else %}{# error #}
  var gReviewPending = false;
{% endif %}{# !error #}
