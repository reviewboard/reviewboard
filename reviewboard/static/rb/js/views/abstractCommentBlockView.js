RB.AbstractCommentBlockView = Backbone.View.extend({
    events: {
        'click': '_onClicked'
    },

    /*
     * Disposes ScreenshotCommentBlockView.
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
                side: 'lrbt'
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
        commentDlg.positionToSide(this.$el, {
            side: 'r',
            fitOnScreen: true
        });
    },

    /*
     * Notifies the user of some update. This notification appears in the
     * comment area.
     */
    notify: function(text, cb) {
        var offset = this.$el.offset(),
            bubble = $('<div/>')
                .addClass('bubble')
                .appendTo(this.$el)
                .text(text);

        bubble
            .css('opacity', 0)
            .move(Math.round((this.$el.width()  - bubble.width())  / 2),
                  Math.round((this.$el.height() - bubble.height()) / 2))
            .animate({
                top: '-=10px',
                opacity: 0.8
            }, 350, 'swing')
            .delay(1200)
            .animate({
                top: '+=10px',
                opacity: 0
            }, 350, 'swing', function() {
                bubble.remove();

                if (_.isFunction(cb)) {
                    cb();
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

        function addEntry(comment) {
            return $('<li>')
                .text(comment.text.truncate())
                .appendTo(list);
        }

        if (draftComment) {
            addEntry(draftComment)
                .addClass("draft");
        }

        _.each(this.model.get('serializedComments'), addEntry);

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

        $.event.add(comment, 'textChanged', _.bind(this._updateTooltip, this));

        $.event.add(comment, 'deleted', function() {
            $el.queue(function() {
                self.notify('Comment Deleted', function() {
                    $el.dequeue();
                });
            });
        });

        $.event.add(comment, 'destroyed', function() {
            /* Discard the comment block if empty. */
            if (self.model.isEmpty()) {
                $el.fadeOut(350, function() { self.dispose(); })
            } else {
                $el.removeClass('draft');
                self._updateTooltip();
            }
        });

        $.event.add(comment, 'saved', function() {
            self._updateTooltip();
            self.notify('Comment Saved');
            showReviewBanner();
        });

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
