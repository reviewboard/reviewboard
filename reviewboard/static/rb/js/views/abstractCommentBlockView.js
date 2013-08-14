RB.AbstractCommentBlockView = Backbone.View.extend({
    events: {
        'click': '_onClicked'
    },

    tooltipSides: 'lrbt',

    /*
     * Disposes the comment block.
     *
     * This will remove the view and the tooltip.
     */
    dispose: function() {
        this.remove();
        this._$tooltip.remove();
    },

    /*
     * Renders the comment block.
     *
     * Along with the block, a floating tooltip will be created that
     * displays summaries of the comments.
     */
    render: function() {
        this._$tooltip = $.tooltip(this.$el, {
                side: this.tooltipSides
            })
            .addClass('comments');

        this.renderContent();

        this.model.on('change:draftComment', this._onDraftCommentChanged, this);
        this._onDraftCommentChanged();

        this._updateTooltip();

        return this;
    },

    /*
     * Positions the comment dlg to the right side of comment block.
     *
     * This can be overridden to change where the comment dialog will
     * be displayed.
     */
    positionCommentDlg: function(commentDlg) {
        commentDlg.positionBeside(this.$el, {
            side: 'r',
            fitOnScreen: true
        });
    },

    /*
     * Positions the notification bubble around the comment block.
     *
     * This can be overridden to change where the bubble will be displayed.
     * By default, it is centered over the block.
     */
    positionNotifyBubble: function($bubble) {
        $bubble.move(Math.round((this.$el.width()  - $bubble.width())  / 2),
                     Math.round((this.$el.height() - $bubble.height()) / 2));
    },

    /*
     * Notifies the user of some update. This notification appears in the
     * comment area.
     */
    notify: function(text, cb, context) {
        var $bubble = $('<div/>')
                .addClass('bubble')
                .appendTo(this.$el)
                .text(text);

        $bubble.css('opacity', 0);

        this.positionNotifyBubble($bubble);

        $bubble
            .animate({
                top: '-=10px',
                opacity: 0.8
            }, 350, 'swing')
            .delay(1200)
            .animate({
                top: '+=10px',
                opacity: 0
            }, 350, 'swing', function() {
                $bubble.remove();

                if (_.isFunction(cb)) {
                    cb.call(context);
                }
            });
    },

    /*
     * Updates the tooltip contents.
     *
     * The contents will show the summary of each comment, including
     * the draft comment, if any.
     */
    _updateTooltip: function() {
        var list = $('<ul/>'),
            draftComment = this.model.get('draftComment');

        function addEntry(text) {
            return $('<li>')
                .text(text.truncate())
                .appendTo(list);
        }

        if (draftComment) {
            addEntry(draftComment.get('text'))
                .addClass("draft");
        }

        _.each(this.model.get('serializedComments'), function(comment) {
            addEntry(comment.text);
        });

        this._$tooltip
            .empty()
            .append(list);
    },

    /*
     * Handles when the model's draftComment property changes.
     *
     * If there's a new draft comment, we'll begin listening for updates
     * on it in order to update the tooltip or display notification bubbles.
     *
     * The comment block's style will reflect whether or not we have a
     * draft comment.
     *
     * If the draft comment is deleted, and there are no other comments,
     * the view will be removed.
     */
    _onDraftCommentChanged: function() {
        var self = this,
            $el = this.$el,
            comment = this.model.get('draftComment');

        if (!comment) {
            $el.removeClass('draft');
            return;
        }

        comment.on('change:text', this._updateTooltip, this);

        comment.on('destroy', function() {
            this.notify(gettext('Comment Deleted'), function() {
                /* Discard the comment block if empty. */
                if (this.model.isEmpty()) {
                    $el.fadeOut(350, function() { self.dispose(); });
                } else {
                    $el.removeClass('draft');
                    this._updateTooltip();
                }
            }, this);
        }, this);

        comment.on('saved', function() {
            this._updateTooltip();
            this.notify(gettext('Comment Saved'));
            RB.DraftReviewBannerView.instance.show();
        }, this);

        $el.addClass('draft');
    },

    /*
     * Handler for when the comment block is clicked.
     *
     * Emits the 'clicked' signal so that parent views can process it.
     */
    _onClicked: function() {
        this.trigger('clicked');
    }
});
