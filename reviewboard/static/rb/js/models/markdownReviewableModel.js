/*
 * Provides review capabilities for Markdown files.
 */
RB.MarkdownReviewable = RB.TextBasedReviewable.extend({
    defaults: _.defaults({
        rendered: ''
    }, RB.TextBasedReviewable.prototype.defaults)
});
