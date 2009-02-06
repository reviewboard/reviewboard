{% load djblets_utils %}
  /*
   * Initial state from the server. These should all be thought of as
   * constants, not state.
   */
{% if not error %}
  var gBugTrackerURL = "{{review_request.repository.bug_tracker}}";
  var gReviewRequestPath = '{{review_request.get_absolute_url}}';
  var gReviewRequestId = "{{review_request.id}}";
  var gReviewRequestSummary = "{{review_request.summary|escapejs}}";
  var gReviewPending = {% if review %}true{% else %}false{% endif %};
{% ifuserorperm review_request.submitter "reviews.can_edit_reviewrequest" %}
{% ifequal review_request.status 'P' %}
  var gEditable = true;
{% endifequal %}
{% endifuserorperm %}
{% else %}{# error #}
  var gReviewPending = false;
{% endif %}{# !error #}

  var gUserURL = "{% url user user %}";
  var gUserAuthenticated = {{user.is_authenticated|lower}};
{% if not user.is_anonymous %}
  var gUserFullName = "{{user|user_displayname}}";
{% endif %}
