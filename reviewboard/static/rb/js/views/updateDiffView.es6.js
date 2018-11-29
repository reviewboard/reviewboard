/**
 * A view for updating the diff on a review request.
 */
RB.UpdateDiffView = RB.UploadDiffView.extend({
    className: 'update-diff',

    template: _.template(dedent`
        <div class="input dnd" id="prompt-for-diff">
         <form>
          <%= selectDiff %>
         </form>
        </div>
        <div class="input dnd" id="prompt-for-parent-diff">
         <form>
          <div id="parent-diff-error-contents" />
          <%= selectParentDiff %>
         </form>
         <a href="#" class="startover"><%- startOver %></a>
        </div>
        <div class="input" id="prompt-for-basedir">
         <form id="basedir-form">
          <%- baseDir %>
          <input id="basedir-input" />
          <input type="submit" value="<%- ok %>" />
         </form>
         <a href="#" class="startover"><%- startOver %></a>
        </div>
        <div class="input" id="processing-diff">
         <div class="spinner"><span class="fa fa-spinner fa-pulse"></div>
        </div>
        <div class="input" id="uploading-diffs">
         <div class="spinner"><span class="fa fa-spinner fa-pulse"></div>
        </div>
        <div class="input" id="error-indicator">
         <div id="error-contents" />
         <a href="#" class="startover"><%- startOver %></a>
        </div>
    `),

    /**
     * Render the view.
     *
     * Returns:
     *     RB.UpdateDiffView:
     *     This object, for chaining.
     */
    render() {
        RB.UploadDiffView.prototype.render.call(this);

        this.$el.modalBox({
            title: gettext('Update Diff'),
            buttons: [
                $('<input type="button" />')
                    .val(gettext('Cancel')),
            ],
        });

        return this;
    },
});
