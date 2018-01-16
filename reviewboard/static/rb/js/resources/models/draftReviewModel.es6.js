/**
 * A draft review.
 *
 * Draft reviews are more complicated than most objects. A draft may already
 * exist on the server, in which case we need to be able to get its ID. A
 * special resource exists at /reviews/draft/ which will redirect to the
 * existing draft if one exists, and return 404 if not.
 */
RB.DraftReview = RB.Review.extend(_.extend({
    defaults: _.defaults({
        publishAndArchive: false,
        publishToOwnerOnly: false,
    }, RB.Review.prototype.defaults()),

    attrToJsonMap: _.defaults({
        publishAndArchive: 'publish_and_archive',
        publishToOwnerOnly: 'publish_to_owner_only',
    }, RB.Review.prototype.attrToJsonMap),

    serializedAttrs: [
        'publishAndArchive',
        'publishToOwnerOnly',
    ].concat(RB.Review.prototype.serializedAttrs),

    serializers: _.defaults({
        publishAndArchive: RB.JSONSerializers.onlyIfValue,
        publishToOwnerOnly: RB.JSONSerializers.onlyIfValue,
    }, RB.Review.prototype.serializers),


    /**
     * Publish the review.
     *
     * Before publish, the "publishing" event will be triggered.
     *
     * After the publish has succeeded, the "published" event will be
     * triggered.
     *
     * Args:
     *     options (object):
     *         Options for the operation, including callbacks.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    publish(options={}, context=undefined) {
        this.trigger('publishing');

        this.ready({
            ready: () => {
                this.set('public', true);
                this.save({
                    attrs: options.attrs,
                    success: () => {
                        this.trigger('published');

                        if (_.isFunction(options.success)) {
                            options.success.call(context);
                        }
                    },
                    error: (model, xhr) => {
                        model.trigger('publishError', xhr.errorText);

                        if (_.isFunction(options.error)) {
                            options.error.call(context, model, xhr);
                        }
                    }
                }, this);
            },
            error: error
        }, this);
    }
}, RB.DraftResourceModelMixin));
