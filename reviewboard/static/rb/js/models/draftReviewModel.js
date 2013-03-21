/*
 * Draft reviews.
 *
 * Draft reviews are more complicated than most objects. A draft may already
 * exist on the server, in which case we need to be able to get its ID. A
 * special resource exists at /reviews/draft/ which will redirect to the
 * existing draft if one exists, and return 404 if not.
 */
RB.DraftReview = RB.Review.extend({
    /*
     * Calls a function when the object is ready to use.
     */
    ready: function(options, context) {
        var self = this;

        if (!this.get('loaded') && this.isNew()) {
            /*
             * Start by delegating to RB.Review.prototype.ready. Because the
             * object is "new", this will make sure that the parentObject is
             * ready.
             */
            options = _.defaults({
                ready: function() {
                    self._retrieveDraft.call(self, options, context);
                },
            }, options);
        }
        RB.Review.prototype.ready.call(this, options, context);
    },

    /*
     * Custom URL implementation which will return the special draft resource if
     * we have yet to redirect and otherwise delegate to the prototype
     * implementation.
     */
    url: function() {
        if (!this.get('loaded') && this.isNew()) {
            return this.get('parentObject').links.reviews.href + 'draft/';
        } else {
            return RB.Review.prototype.url.call(this);
        }
    },

    /*
     * Try to retrieve an existing draft review from the server. This uses the
     * special draft/ resource within the reviews list, which will redirect to
     * an existing draft review if one exists.
     */
    _retrieveDraft: function(options, context) {
        var self = this;

        console.assert(!this.get('loaded'));
        console.assert(this.isNew());

        Backbone.Model.prototype.fetch.call(this, {
            success: function() {
                if (options.ready()) {
                    options.ready.call(self);
                }
            },
            error: function(model, xhr) {
                if (xhr.status === 404) {
                    self.ready = RB.Review.prototype.ready;
                    self.url = RB.Review.prototype.url;
                    RB.Review.prototype.ready.call(self, options, context);
                } else if (options.error) {
                    options.error.call(xhr, status, err);
                }
            }
        });
    }
});
