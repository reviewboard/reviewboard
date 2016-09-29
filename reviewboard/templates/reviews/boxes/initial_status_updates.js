{% comment %}
This is very similar to templates/reviews/boxes/change.js. If you're making a
change in here, you may want to check to see if a similar change is needed
there.
{% endcomment %}

page.addBox(new RB.InitialStatusUpdatesBoxView({
    el: $('#initial-status-updates'),
    reviewRequestEditor: page.reviewRequestEditor,
    showSendEmail: {{send_email|yesno:'true,false'}},
    reviews: [
{% for update in entry.status_updates %}
{%  if update.review_id %}
        page.reviewRequest.createReview({{update.review.id}}, {
            shipIt: {{update.review.ship_it|yesno:'true,false'}},
            'public': true,
            bodyTop: '{{update.review.body_top|escapejs}}',
            bodyBottom: '{{update.review.body_bottom|escapejs}}'
        }){% if not forloop.last %},{% endif %}
{%  endif %}
{% endfor %}
    ]
}));

{% for update in entry.status_updates %}
{%  for comment in update.comments.diff_comments %}
page.queueLoadDiff(
    '{{comment.id}}',
    '{{comment.filediff.id}}{% if comment.interfilediff %}-{{comment.interfilediff.id}}{% endif %}');
{%  endfor %}
{% endfor %}
