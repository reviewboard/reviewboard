/**
 * A view for pre-commit review request creation.
 *
 * This will guide users through several steps, depending on the requirements of
 * the repository.
 */
RB.PreCommitView = RB.UploadDiffView.extend({
    className: 'pre-commit',

    template: _.template(dedent`
        <div class="section-header"><%- pendingChangeHeader %></div>
        <div class="tip">
         <strong><%- tipHeader %></strong>
         <%= tip %>
        </div>
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
        <div class="input" id="prompt-for-change-number">
         <form id="changenum-form">
          <%- changeNum %>
          <input type="number" step="1" id="changenum-input" />
          <input type="submit" value="<%- ok %>" />
         </form>
         <a href="#" class="startover"><%- startOver %></a>
        </div>
        <div class="input" id="processing-diff">
         <div class="spinner"><span class="fa fa-spinner fa-pulse"></div>
        </div>
        <div class="input" id="uploading-diffs">
         <div><span class="fa fa-spinner fa-pulse"></div>
        </div>
        <div class="input" id="error-indicator">
         <div id="error-contents" />
         <a href="#" class="startover"><%- startOver %></a>
        </div>
    `),
});
