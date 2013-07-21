/*
 * Displays a thumbnail for a screenshot.
 *
 * Screenshot thumbnails allow the caption to be edited and the screenshot
 * to be deleted.
 *
 * This expects to take an existing element for the thumbnail contents, and
 * will attach handlers for interaction.
 *
 * The following signals are provided, on top of the standard Backbone.View
 * signals:
 *
 *     * beginEdit
 *       - Editing of the screenshot (caption) has begun.
 *
 *     * endEdit
 *       - Editing of the screenshot (caption) has finished.
 */
RB.ScreenshotThumbnail = Backbone.View.extend({
    events: {
        'click a.delete': '_onDeleteClicked'
    },

    /*
     * Renders the thumbnail.
     *
     * This will listen for events on the screenshot and for events on the
     * thumbnail itself (to allow for caption editing).
     */
    render: function() {
        var self = this;

        this.model.on('destroy', function() {
            this.$el.fadeOut(function() {
                self.remove();
            });
        }, this);

        this.$caption = this.$el.find('a.edit')
            .inlineEditor({
                editIconClass: 'rb-icon rb-icon-edit',
                showButtons: false
            })
            .on({
                'beginEdit': function() {
                    self.trigger('beginEdit');
                },
                'cancel': function() {
                    self.trigger('endEdit');
                },
                'complete': function(e, value) {
                    /*
                     * We want to set the caption after ready() finishes,
                     * it case it loads state and overwrites.
                     */
                    self.model.ready({
                        ready: function() {
                            self.model.set('caption', value);
                            self.trigger('endEdit');
                            self.model.save();
                        }
                    });
                }
            });

        return this;
    },

    /*
     * Deletes the screenshot.
     *
     * Once the screenshot has been deleted, the view will be removed.
     */
    _onDeleteClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this.model.destroy();
    }
});
