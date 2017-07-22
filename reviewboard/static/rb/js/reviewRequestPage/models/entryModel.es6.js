/**
 * An entry on the review request page.
 *
 * This represents entries on the review request page, such as reviews and
 * review request changes. It stores common state used by all entries.
 *
 * This is meant to be subclassed to handle parsing of custom content or
 * storing custom state, but can be used as-is for simple entries.
 *
 * Model Attributes:
 *     reviewRequestEditor (RB.ReviewRequestEditor):
 *         The review request editor managing state on the page.
 */
RB.ReviewRequestPage.Entry = Backbone.Model.extend({
    defaults: {
        reviewRequestEditor: null,
    },

    /**
     * Parse attributes for the model.
     *
     * Args:
     *     attrs (object):
     *         The attributes provided when constructing the model instance.
     *
     * Returns:
     *     object:
     *     The resulting attributes used for the model instance.
     */
    parse(attrs) {
        return {
            reviewRequestEditor: attrs.reviewRequestEditor,
        };
    },
});
