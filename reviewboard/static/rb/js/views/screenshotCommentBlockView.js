/*
 * Provides a visual region over a screenshot showing comments.
 *
 * This will show a selection rectangle over part of a screenshot indicating
 * there are comments there. It will also show the number of comments,
 * along with a tooltip showing comment summaries.
 */
RB.ScreenshotCommentBlockView = Backbone.View.extend({
    className: 'selection',

    events: {
        'click': '_onClicked'
    },

    /*
     * Initializes ScreenshotCommentBlockView.
     */
    initialize: function() {
        this.on('change:x change:y change:width change:height',
                this._updateDimensions, this);
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
     * Along with the block's rectangle, a floating tooltip will also be
     * created that displays summaries of the comments.
     *
     * After rendering, the block's style and count will be updated whenever
     * the appropriate state is changed in the model.
     */
    render: function() {
        this._updateDimensions();

        this._$tooltip = $.tooltip(this.$el, {
                side: 'lrbt'
            })
            .addClass('comments');

        this._$flag = $('<div/>')
            .addClass('selection-flag')
            .appendTo(this.$el);

        this.model.on('change:count', this._updateCount, this);
        this._updateCount();

        this.model.on('change:draftComment', this._onDraftCommentChanged, this);
        this._onDraftCommentChanged();

        this._updateTooltip();

        return this;
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
     * Updates the position and size of the comment block.
     *
     * The new position and size will reflect the x, y, width, and height
     * properties in the model.
     */
    _updateDimensions: function() {
        var model = this.model;

        this.$el
            .move(model.get('x'), model.get('y'), 'absolute')
            .width(model.get('width'))
            .height(model.get('height'));
    },

    /*
     * Updates the displayed count of comments.
     */
    _updateCount: function() {
        this._$flag.text(this.model.get('count'));
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
            var item = $('<li>').appendTo(list);
            item.text(comment.text.truncate());
            return item;
        }

        if (draftComment !== null) {
            addEntry(draftComment)
                .addClass("draft");
        }

        _.each(this.comments, addEntry);

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
            this._$flag.removeClass('flag-draft');
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
                self._$flag.removeClass('flag-draft');
                self._updateCount();
                self._updateTooltip();
            }
        });

        $.event.add(comment, 'saved', function() {
            self._updateTooltip();
            self.notify('Comment Saved');
            showReviewBanner();
        });

        $el.addClass('draft');
        this._$flag.addClass('flag-draft');
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
