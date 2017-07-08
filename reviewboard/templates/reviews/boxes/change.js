{% comment %}
This is very similar to templates/reviews/boxes/initial_status_updates.js. If
you're making a change in here, you may want to check to see if a similar
change is needed there.
{% endcomment %}

page.addBox(new RB.ChangeBoxView({
    el: $('#changedesc{{entry.changedesc.id}}'),
    reviewRequestEditorView: page.reviewRequestEditorView,
    model: new RB.ReviewRequestPageChangeEntry({
        diffCommentsData: [
{% for update in entry.status_updates %}
{%  for comment in update.comments.diff_comments %}
            ['{{comment.id}}',
             '{{comment.filediff.id}}{% if comment.interfilediff %}-{{comment.interfilediff.id}}{% endif %}']{% if not forloop.last %},{% endif %}
{%  endfor %}
{% endfor %}
        ],
        reviewsData: [
{% for update in entry.status_updates %}
{%  if update.review_id %}
            {
                id: {{update.review.id}},
                shipIt: {{update.review.ship_it|yesno:'true,false'}},
                'public': true,
                bodyTop: '{{update.review.body_top|escapejs}}',
                bodyBottom: '{{update.review.body_bottom|escapejs}}'
            }{% if not forloop.last %},{% endif %}
{%  endif %}
{% endfor %}
        ],
        reviewRequestEditor: page.reviewRequestEditor
    }, {
        parse: true
    })
}));
