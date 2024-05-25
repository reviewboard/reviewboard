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
          <div id="parent-diff-error-contents"></div>
          <%= selectParentDiff %>
         </form>
         <a href="#" class="startover"><%- startOver %></a>
        </div>
        <div class="input" id="prompt-for-basedir">
         <form id="basedir-form">
          <%- baseDir %>
          <input id="basedir-input">
          <button class="ink-c-button" type="submit">"<%- ok %>"</button>
         </form>
         <a href="#" class="startover"><%- startOver %></a>
        </div>
        <div class="input" id="processing-diff">
         <div class="spinner"><span class="ink-c-spinner"></span></div>
        </div>
        <div class="input" id="uploading-diffs">
         <div class="spinner"><span class="ink-c-spinner"></span></div>
        </div>
        <div class="input" id="error-indicator">
         <div id="error-contents"></div>
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

        this.$el
            .modalBox({
                buttons: [
                    Ink.paintComponent(
                        'Ink.Button',
                        {},
                        _`Cancel`
                    ),
                ],
                title: _`Update Diff`,
            })
            .on('close', () => this.$el.modalBox('destroy'));

        return this;
    },
});
