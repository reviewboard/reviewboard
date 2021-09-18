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
     * Version Changed:
     *     5.0:
     *     Deprecated the callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Options for the operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async publish(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.DraftReview.publish was called using callbacks. ' +
                         'Callers should be updated to use promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.publish(newOptions));
        }

        this.trigger('publishing');

        await this.ready();

        this.set('public', true);

        try {
            await this.save({ attrs: options.attrs });
        } catch (err) {
            this.trigger('publishError', err.xhr.errorText);
            throw err;
        }

        this.trigger('published');
    }
}, RB.DraftResourceModelMixin));
