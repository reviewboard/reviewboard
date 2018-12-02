/**
 * A view which gives the user hints about comments in other revisions.
 */
RB.DiffCommentsHintView = Backbone.View.extend({
    events: {
        'click .revision': '_onRevisionSelected',
        'click .interdiff': '_onInterdiffSelected',
    },

    template: _.template(dedent`
        <div class="box-container">
         <div class="box important">
          <div class="box-inner comments-hint">
           <h1><%- unpublishedCommentsHeader %></h1>
           <p><%- unpublishedCommentsText %></p>
           <ul>
           </ul>
          </div>
         </div>
        </div>
    `),

    /**
     * Initialize the view.
     */
    initialize() {
        this.listenTo(this.model, 'change', this.render);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.DiffCommentsHintView:
     *     This object, for chaining.
     */
    render() {
        const revisionText = gettext('Revision %s');
        const interdiffText = gettext('Interdiff revision %(oldRevision)s - %(newRevision)s');

        if (this.model.get('hasOtherComments')) {
            this.$el.html(this.template({
                unpublishedCommentsHeader: gettext('You have unpublished comments on other revisions'),
                unpublishedCommentsText: gettext('Your review consists of comments on the following revisions:')
            }));

            const $ul = this.$('ul');

            this.model.get('diffsetsWithComments').forEach(diffset => {
                const $li = $('<li/>')
                    .addClass('revision')
                    .data('revision', diffset.revision)
                    .text(interpolate(revisionText, [diffset.revision]))
                    .appendTo($ul);

                if (diffset.isCurrent) {
                    $li.addClass('current');
                }
            });

            this.model.get('interdiffsWithComments').forEach(interdiff => {
                const $li = $('<li/>')
                    .addClass('interdiff')
                    .data({
                        'first-revision': interdiff.oldRevision,
                        'second-revision': interdiff.newRevision
                    })
                    .text(interpolate(
                        interdiffText,
                        {
                            oldRevision: interdiff.oldRevision,
                            newRevision: interdiff.newRevision
                        },
                        true))
                    .appendTo($ul);

                if (interdiff.isCurrent) {
                    $li.addClass('current');
                }
            });
        } else {
            this.$el.empty();
        }

        return this;
    },

    /**
     * Callback for when a single revision is selected.
     *
     * Args:
     *     ev (Event):
     *         The click event.
     */
    _onRevisionSelected(ev) {
        const $target = $(ev.currentTarget);

        if (!$target.hasClass('current')) {
            this.trigger('revisionSelected', [0, $target.data('revision')]);
        }
    },

    /**
     * Callback for when an interdiff is selected.
     *
     * Args:
     *     ev (Event):
     *         The click event.
     */
    _onInterdiffSelected(ev) {
        const $target = $(ev.currentTarget);

        if (!$target.hasClass('current')) {
            this.trigger('revisionSelected',
                         [$target.data('first-revision'),
                          $target.data('second-revision')]);
        }
    }
});
