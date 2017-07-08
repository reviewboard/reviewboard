page.addBox(new RB.ReviewBoxView({
    el: $('#review{{entry.review.id}}'),
    model: new RB.ReviewRequestPageReviewEntry({
        diffCommentsData: [
{%  for comment in entry.comments.diff_comments %}
            ['{{comment.id}}',
             '{{comment.filediff.id}}{% if comment.interfilediff %}-{{comment.interfilediff.id}}{% endif %}']{% if not forloop.last %},{% endif %}
{%  endfor %}
        ],
        reviewData: {
            id: {{entry.review.id}},
            shipIt: {{entry.review.ship_it|yesno:'true,false'}},
            'public': true,
            bodyTop: '{{entry.review.body_top|escapejs}}',
            bodyBottom: '{{entry.review.body_bottom|escapejs}}'
        },
        reviewRequestEditor: page.reviewRequestEditor
    }, {
        parse: true
    })
}));
