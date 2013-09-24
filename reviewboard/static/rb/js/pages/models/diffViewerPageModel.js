/*
 * A model with all the data for the diff viewer page.
 */
RB.DiffViewerPageModel = Backbone.Model.extend({
    defaults: {
        commentsHint: null,
        files: null,
        numDiffs: 1,
        pagination: null,
        revision: null
    },

    /*
     * Parse the data given to us by the server.
     */
    parse: function(rsp) {
        return {
            commentsHint: new RB.DiffCommentsHint(rsp.comments_hint,
                                                  {parse: true}),
            files: new RB.DiffFileCollection(rsp.files, {parse: true}),
            numDiffs: rsp.num_diffs,
            pagination: new RB.Pagination(rsp.pagination, {parse: true}),
            revision: new RB.DiffRevision(rsp.revision, {parse: true})
        };
    },

    /*
     * Override for Model.set that properly updates the child objects.
     *
     * Because several of this model's properties are other backbone models, we
     * can't just call set(parse(...)) because it would replace the models
     * entirely. If this is called as part of the initial construction, it will
     * just use the models created by parse(). Otherwise, it will copy the new
     * data into the child models' attributes.
     */
    set: function(attrs, options) {
        var toSet = {
            numDiffs: attrs.numDiffs
        };

        if (this.attributes.commentsHint) {
            this.attributes.commentsHint.set(
                attrs.commentsHint.attributes);
        } else {
            toSet.commentsHint = attrs.commentsHint;
        }

        if (this.attributes.files) {
            this.attributes.files.set(attrs.files.models);
            this.attributes.files.trigger('update');
        } else {
            toSet.files = attrs.files;
        }

        if (this.attributes.pagination) {
            this.attributes.pagination.set(attrs.pagination.attributes);
        } else {
            toSet.pagination = attrs.pagination;
        }

        if (this.attributes.revision) {
            this.attributes.revision.set(attrs.revision.attributes);
        } else {
            toSet.revision = attrs.revision;
        }

        Backbone.Model.prototype.set.call(this, toSet, options);
    }
});
