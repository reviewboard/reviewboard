/**
 * A review.
 *
 * This corresponds to a top-level review. Replies are encapsulated in
 * RB.ReviewReply.
 *
 * Model Attributes:
 *     forceTextType (string):
 *         The text format type to request for text in all responses.
 *
 *     shipIt (boolean):
 *         Whether this review has the "Ship It!" state.
 *
 *     public (boolean):
 *         Whether this review has been published.
 *
 *     bodyTop (string):
 *         The contents of the header that shows up above all comments in the
 *         review.
 *
 *     bodyTopRichText (boolean):
 *         Whether the ``bodyTop`` field should be rendered as Markdown.
 *
 *     bodyBottom (string):
 *         The contents of the footer that shows up below all comments in the
 *         review.
 *
 *     bodyBottomRichText (boolean):
 *         Whether the ``bodyBottom`` field should be rendered as Markdown.
 *
 *     draftReply (RB.ReviewReply):
 *         The draft reply to this review, if any.
 *
 *     htmlTextFields (object):
 *         The contents of any HTML-rendered text fields, if the caller fetches
 *         or posts with ``includeTextTypes=html``. The keys in this object are
 *         the field names, and the values are the HTML versions of those
 *         attributes.
 *
 *     includeTextTypes (string):
 *         A comma-separated list of text types to include in the payload when
 *         syncing the model.
 *
 *     markdownTextFields (object):
 *         The source contents of any Markdown text fields, if the caller
 *         fetches or posts with ``includeTextTypes=markdown``. The keys in
 *         this object are the field names, and the values are the Markdown
 *         source of those fields.
 *
 *     rawTextFields (object):
 *         The contents of the raw text fields, if the caller fetches or posts
 *         with includeTextTypes=raw. The keys in this object are the field
 *         names, and the values are the raw versions of those attributes.
 *
 *     timestamp (string):
 *         The timestamp of this review.
 */
RB.Review = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            forceTextType: null,
            shipIt: false,
            'public': false,
            bodyTop: null,
            bodyTopRichText: false,
            bodyBottom: null,
            bodyBottomRichText: false,
            draftReply: null,
            htmlTextFields: {},
            includeTextTypes: null,
            markdownTextFields: {},
            rawTextFields: {},
            timestamp: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'review',

    attrToJsonMap: {
        bodyBottom: 'body_bottom',
        bodyBottomRichText: 'body_bottom_text_type',
        bodyTop: 'body_top',
        bodyTopRichText: 'body_top_text_type',
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types',
        shipIt: 'ship_it'
    },

    serializedAttrs: [
        'forceTextType',
        'includeTextTypes',
        'shipIt',
        'bodyTop',
        'bodyTopRichText',
        'bodyBottom',
        'bodyBottomRichText',
        'public'
    ],

    deserializedAttrs: [
        'shipIt',
        'bodyTop',
        'bodyBottom',
        'public',
        'timestamp'
    ],

    serializers: {
        forceTextType: RB.JSONSerializers.onlyIfValue,
        includeTextTypes: RB.JSONSerializers.onlyIfValue,
        bodyTopRichText: RB.JSONSerializers.textType,
        bodyBottomRichText: RB.JSONSerializers.textType,
        'public': value => value ? 1 : undefined
    },

    supportsExtraData: true,

    /**
     * Parse the response from the server.
     *
     * Args:
     *    rsp (object):
     *        The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(rsp) {
        const rawTextFields = rsp.raw_text_fields || rsp;
        const data = RB.BaseResource.prototype.parseResourceData.call(
            this, rsp);

        data.bodyTopRichText =
            (rawTextFields.body_top_text_type === 'markdown');
        data.bodyBottomRichText =
            (rawTextFields.body_bottom_text_type === 'markdown');

        if (rsp.raw_text_fields) {
            data.rawTextFields = {
                bodyBottom: rsp.raw_text_fields.body_bottom,
                bodyTop: rsp.raw_text_fields.body_top
            };
        }

        if (rsp.markdown_text_fields) {
            data.markdownTextFields = {
                bodyBottom: rsp.markdown_text_fields.body_bottom,
                bodyTop: rsp.markdown_text_fields.body_top
            };
        }

        if (rsp.html_text_fields) {
            data.htmlTextFields = {
                bodyBottom: rsp.html_text_fields.body_bottom,
                bodyTop: rsp.html_text_fields.body_top,
            };
        }

        return data;
    },

    /**
     * Create a new diff comment for this review.
     *
     * Args:
     *     options (object):
     *         Options for creating the review.
     *
     * Option Args:
     *     id (number):
     *         The ID for the new model (in the case of existing comments).
     *
     *     fileDiffID (number):
     *         The ID of the FileDiff that this comment is for.
     *
     *     interFileDiffID (number):
     *         The ID of the FileDiff that represents the "new" side of an
     *         interdiff. If this is specified, the ``fileDiffID`` argument
     *         represents the "old" side.
     *
     *         This option is mutually exclusive with ``baseFileDiffID``.
     *
     *     beginLineNum (number):
     *         The line number of the start of the comment.
     *
     *     endLineNum (number):
     *         The line number of the end of the comment.
     *
     *     baseFileDiffID (number):
     *         The ID of the base FileDiff in the cumulative diff that the
     *         comment is to be made upon.
     *
     *         This option is mutually exclusive with ``interFileDiffID``.
     *
     * Returns:
     *     RB.DiffComment:
     *     The new comment object.
     */
    createDiffComment(...args) {
        let options;

        if (args.length === 1) {
            options = args[0];
        } else {
            console.warn([
                'RB.Review.createDiffComment(id, fileDiffID, ',
                'interFileDiffID, beginLineNum, endLineNum) is deprecated. ',
                'Use RB.Review.createDiffComment(options) instead.',
            ].join(''));

            options = {
                id: args[0],
                fileDiffID: args[1],
                interFileDiffID: args[2],
                beginLineNum: args[3],
                endLineNum: args[4],
            };
        }

        if (!!options.interFileDiffID && !!options.baseFileDiffID) {
            console.error(
                'Options `interFileDiffID` and `baseFileDiffID` for ' +
                'RB.Review.createDiffComment() are mutually exclusive.');
            return;
        }

        return new RB.DiffComment(_.defaults({parentObject: this}, options));
    },

    /**
     * Create a new screenshot comment for this review.
     *
     * Args:
     *     id (number):
     *         The ID for the new model (in the case of existing comments).
     *
     *     screenshotID (number):
     *         The ID of the Screenshot that this comment is for.
     *
     *     x (number):
     *         The X coordinate of the pixel for the upper left of the comment
     *         region.
     *
     *     y (number):
     *         The Y coordinate of the pixel for the upper left of the comment
     *         region.
     *
     *     width (number):
     *         The width of the comment region, in pixels.
     *
     *     height (number):
     *         The height of the comment region, in pixels.
     *
     * Returns:
     *     RB.ScreenshotComment:
     *     The new comment object.
     */
    createScreenshotComment(id, screenshotID, x, y, width, height) {
        return new RB.ScreenshotComment({
            parentObject: this,
            id: id,
            screenshotID: screenshotID,
            x: x,
            y: y,
            width: width,
            height: height
        });
    },

    /**
     * Create a new file attachment comment for this review.
     *
     * Args:
     *     id (number):
     *         The ID for the new model (in the case of existing comments).
     *
     *     fileAttachmentID (number):
     *         The ID of the FileAttachment that this comment is for.
     *
     *     diffAgainstFileAttachmentID (number):
     *         The ID of the FileAttachment that the ``fileAttachmentID`` is
     *         diffed against, if the comment is for a file diff.
     *
     * Returns:
     *     RB.FileAttachmentComment:
     *     The new comment object.
     */
    createFileAttachmentComment(id, fileAttachmentID,
                                diffAgainstFileAttachmentID) {
        return new RB.FileAttachmentComment({
            parentObject: this,
            id: id,
            fileAttachmentID: fileAttachmentID,
            diffAgainstFileAttachmentID: diffAgainstFileAttachmentID
        });
    },

    /**
     * Create a new general comment for this review.
     *
     * Args:
     *     id (number):
     *         The ID for the new model (in the case of existing comments).
     *
     *     issueOpened (boolean):
     *         Whether this comment should have an open issue.
     *
     * Returns:
     *     RB.GeneralComment:
     *     The new comment object.
     */
    createGeneralComment(id, issueOpened) {
        return new RB.GeneralComment({
            parentObject: this,
            id: id,
            issueOpened: issueOpened
        });
    },

    /**
     * Create a new reply.
     *
     * If an existing draft reply exists, return that. Otherwise create a draft
     * reply.
     *
     * Returns:
     *     RB.ReviewReply:
     *     The new reply object.
     */
    createReply() {
        let draftReply = this.get('draftReply');

        if (draftReply === null) {
            draftReply = new RB.ReviewReply({
                parentObject: this
            });
            this.set('draftReply', draftReply);

            draftReply.once('published', () => {
                const reviewRequest = this.get('parentObject');
                reviewRequest.markUpdated(draftReply.get('timestamp'));
                this.set('draftReply', null);
            });
        }

        return draftReply;
    }
});
