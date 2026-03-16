/**
 * A view for a committed revision.
 */

import {
    type DialogView,
    craft,
    paint,
    renderInto,
} from '@beanbag/ink';
import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';


/**
 * A view for a committed revision.
 *
 * This is used specifically for new review request creation. A click on the
 * element will either navigate the page to the review request (if one exists),
 * or emit a 'create' event.
 */
@spina
export class CommitView extends BaseView {
    static className = 'commit';

    /**
     * Template for the main view.
     */
    static template = _.template(dedent`
        <div class="progress"></div>
        <% if (accessible) { %>
         <div class="summary">
          <% if (reviewRequestURL) { %>
           <span class="ink-i-circle-arrow-right jump-to-commit"></span>
          <% } %>
          <%- summary %>
         </div>
        <% } %>
        <div class="commit-info">
         <span class="revision">
          <span class="ink-i-vcs-commit"></span>
          <%- revision %>
          <% if (!accessible) { %>
           ${_.escape(`(not accessible on this repository)`)}
          <% } %>
         </span>
         <% if (accessible && author) { %>
          <span class="author">
           <span class="ink-i-user"></span>
           <%- author %>
          </span>
         <% } %>
         <% if (date) { %>
          <span class="time">
           <span class="ink-i-clock"></span>
           <time class="timesince" datetime="<%- date %>"></time>
          </span>
         <% } %>
        </div>
    `);

    static events: EventsHash = {
        'click': '_onClick',
    };

    /**
     * Render the view.
     */
    protected onInitialRender() {
        const model = this.model;

        if (!model.get('accessible')) {
            this.$el.addClass('disabled');
        }

        let commitID = model.get('id');

        if (commitID.length === 40) {
            commitID = commitID.slice(0, 7);
        }

        if (model.get('reviewRequestURL')) {
            this.$el.addClass('has-review-request');
        }

        const date = model.get('date');

        this.$el.html(CommitView.template(Object.assign(
            {},
            model.attributes,
            {
                author: model.get('authorName') || _`<unknown>`,
                date: date ? date.toISOString() : null,
                revision: commitID,
            })));

        renderInto(
            this.$('.progress'),
            paint`<Ink.Spinner />`);

        if (date) {
            this.$('.timesince').timesince();
        }
    }

    /**
     * Handler for when the commit is clicked.
     *
     * Shows a confirmation dialog allowing the user to proceed or cancel.
     */
    private _onClick() {
        const model = this.model;

        if (!model.get('accessible')) {
            return;
        }

        const url = model.get('reviewRequestURL');

        if (url) {
            RB.navigateTo(url);

            return;
        }

        const onCreateClicked = () => {
            model.trigger('create', model);
        };

        const dialog = craft<DialogView>`
            <Ink.Dialog title=${_`Create Review Request?`}
                        onClose=${() => dialog.remove()}>
             <Ink.Dialog.Body>
              <p>
               ${_`
                You are creating a new review request from the following
                published commit:
               `}
              </p>
              <p>
               <code>
               ${model.get('id').slice(0, 7)}</code>
               ${' '}
               ${model.get('summary')}
              </p>
              <p>${_`Are you sure you want to continue?`}</p>
             </Ink.Dialog.Body>
             <Ink.Dialog.PrimaryActions>
              <Ink.DialogAction type="primary"
                                action="callback-and-close"
                                callback=${onCreateClicked}>
               ${_`Create Review Request`}
              </Ink.DialogAction>
              <Ink.DialogAction action="close">
               ${_`Cancel`}
              </Ink.DialogAction>
             </Ink.Dialog.PrimaryActions>
            </Ink.Dialog>
        `;
        dialog.open();
    }

    /**
     * Toggle a progress indicator on for this commit.
     */
    showProgress() {
        this.$('.progress').show();
    }

    /**
     * Toggle a progress indicator off for this commit.
     */
    cancelProgress() {
        this.$('.progress').hide();
    }
}
