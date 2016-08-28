page.addBox(new RB.ReviewBoxView({
    model: page.reviewRequest.createReview({{entry.review.id}}, {
        shipIt: {{entry.review.ship_it|yesno:'true,false'}},
        'public': true,
        bodyTop: '{{entry.review.body_top|escapejs}}',
        bodyBottom: '{{entry.review.body_bottom|escapejs}}'
    }),
    el: $('#review{{entry.review.id}}'),
    reviewRequestEditor: page.reviewRequestEditor,
    showSendEmail: {{send_email|yesno:'true,false'}}
}));

{% for comment in entry.comments.diff_comments %}
page.queueLoadDiff(
    '{{comment.id}}',
    '{{comment.filediff.id}}{% if comment.interfilediff %}-{{comment.interfilediff.id}}{% endif %}');
{% endfor %}
