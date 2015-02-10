/*
 * A Review UI for file types which otherwise do not have one.
 *
 * Normally, file types that do not have a Review UI are not linked to one.
 * However, in the case of a file attachment with multiple revisions, if one of
 * those revisions is a non-reviewable type, the user can still navigate to
 * that page. This Review UI is used as a placeholder in that case--it shows
 * the header (with revision selector) and a message saying that this file type
 * cannot be shown.
 */
RB.DummyReviewableView = RB.FileAttachmentReviewableView.extend({
    commentBlockView: RB.AbstractCommentBlockView,

    captionTableTemplate: _.template(
        '<table><tr><%= items %></tr></table>'
    ),

    captionItemTemplate: _.template([
        '<td>',
        ' <h1 class="caption">',
        '  <%- caption %>',
        ' </h1>',
        '</td>'
    ].join('')),

    /*
     * Initializes the view.
     */
    initialize: function(options) {
        RB.FileAttachmentReviewableView.prototype.initialize.call(
            this, options);
    },

    /*
     * Renders the view.
     */
    renderContent: function() {
        var hasDiff = this.model.get('diffAgainstFileAttachmentID') !== null,
            captionItems = [],
            $header,
            $revisionLabel,
            $revisionSelector;

        $header = $('<div/>')
            .addClass('review-ui-header')
            .prependTo(this.$el);

        if (this.model.get('numRevisions') > 1) {
            $revisionLabel = $('<div id="revision_label"/>')
                .appendTo($header);
            this._revisionLabelView = new RB.FileAttachmentRevisionLabelView({
                el: $revisionLabel,
                model: this.model
            });
            this._revisionLabelView.render();
            this.listenTo(this._revisionLabelView, 'revisionSelected',
                          this._onRevisionSelected);

            $revisionSelector = $('<div id="attachment_revision_selector" />')
                .appendTo($header);
            this._revisionSelectorView = new RB.FileAttachmentRevisionSelectorView({
                el: $revisionSelector,
                model: this.model
            });
            this._revisionSelectorView.render();
            this.listenTo(this._revisionSelectorView, 'revisionSelected',
                          this._onRevisionSelected);

            console.log(this.model.get('caption'), this.model.get('fileRevision'));

            captionItems.push(this.captionItemTemplate({
                caption: interpolate(
                    gettext('%(caption)s (revision %(revision)s)'),
                    {
                        caption: this.model.get('caption'),
                        revision: this.model.get('fileRevision')
                    },
                    true)
            }));

            if (hasDiff) {
                captionItems.push(this.captionItemTemplate({
                    caption: interpolate(
                        gettext('%(caption)s (revision %(revision)s)'),
                        {
                            caption: this.model.get('diffCaption'),
                            revision: this.model.get('diffRevision')
                        },
                        true)
                }));
            }

            $header.append(this.captionTableTemplate({
                items: captionItems.join('')
            }));
        }
    },

    /*
     * Callback for when a new file revision is selected.
     *
     * This supports single revisions and diffs. If 'base' is 0, a
     * single revision is selected, If not, the diff between `base` and
     * `tip` will be shown.
     */
    _onRevisionSelected: function(revisions) {
        var revisionIDs = this.model.get('attachmentRevisionIDs'),
            base = revisions[0],
            tip = revisions[1],
            revisionBase,
            revisionTip,
            redirectURL;

        // Ignore clicks on No Diff Label
        if (tip === 0) {
            return;
        }

        revisionTip = revisionIDs[tip-1];

        /* Eventually these hard redirects will use a router
         * (see diffViewerPageView.js for example)
         * this.router.navigate(base + '-' + tip + '/', {trigger: true});
         */

        if (base === 0) {
            redirectURL = '../' + revisionTip + '/';
        } else {
            revisionBase = revisionIDs[base-1];
            redirectURL = '../' + revisionBase + '-' + revisionTip + '/';
        }
        window.location.replace(redirectURL);
    }
});
