/**
 * A Review UI for file types which otherwise do not have one.
 */

import { spina } from '@beanbag/spina';

import { AbstractCommentBlockView } from './abstractCommentBlockView';
import {
    FileAttachmentReviewableView,
} from './fileAttachmentReviewableView';


/**
 * A Review UI for file types which otherwise do not have one.
 *
 * Normally, file types that do not have a Review UI are not linked to one.
 * However, in the case of a file attachment with multiple revisions, if one of
 * those revisions is a non-reviewable type, the user can still navigate to
 * that page. This Review UI is used as a placeholder in that case--it shows
 * the header (with revision selector) and a message saying that this file type
 * cannot be shown.
 */
@spina
export class DummyReviewableView extends FileAttachmentReviewableView {
    static commentBlockView = AbstractCommentBlockView;

    static captionTableTemplate = _.template(
        '<table><tr><%= items %></tr></table>'
    );

    static captionItemTemplate = _.template(dedent`
        <td>
         <h1 class="caption"><%- caption %></h1>
        </td>
    `);

    /**********************
     * Instance variables *
     **********************/

    /**
     * Render the view.
     */
    renderContent() {
        const $header = $('<div>')
            .addClass('review-ui-header')
            .prependTo(this.$el);

        if (this.model.get('numRevisions') > 1) {
            const $revisionLabel = $('<div id="revision_label">')
                .appendTo($header);

            const revisionLabelView = new RB.FileAttachmentRevisionLabelView({
                el: $revisionLabel,
                model: this.model,
            });
            revisionLabelView.render();
            this.listenTo(revisionLabelView, 'revisionSelected',
                          this.#onRevisionSelected);

            const $revisionSelector =
                $('<div id="attachment_revision_selector">')
                .appendTo($header);
            const revisionSelectorView =
                new RB.FileAttachmentRevisionSelectorView({
                    el: $revisionSelector,
                    model: this.model,
                });
            revisionSelectorView.render();
            this.listenTo(revisionSelectorView, 'revisionSelected',
                          this.#onRevisionSelected);

            const captionItems = [];

            let caption = this.model.get('caption');
            let revision = this.model.get('revision');

            captionItems.push(DummyReviewableView.captionItemTemplate({
                caption: _`${caption} (revision ${revision})`,
            }));

            if (this.model.get('diffAgainstFileAttachmentID') !== null) {
                caption = this.model.get('diffCaption');
                revision = this.model.get('diffRevision');

                captionItems.push(DummyReviewableView.captionItemTemplate({
                    caption: _`${caption} (revision ${revision})`,
                }));
            }

            $header.append(DummyReviewableView.captionTableTemplate({
                items: captionItems.join(''),
            }));
        } else {
            $('<h1 class="caption file-attachment-single-revision">')
                .text(this.model.get('caption'))
                .appendTo($header);
        }
    }

    /**
     * Callback for when a new file revision is selected.
     *
     * This supports single revisions and diffs. If 'base' is 0, a
     * single revision is selected, If not, the diff between `base` and
     * `tip` will be shown.
     *
     * Args:
     *     revisions (array of number):
     *         An array with two elements, representing the range of revisions
     *         to display.
     */
    #onRevisionSelected(revisions: [number, number]) {
        const [base, tip] = revisions;

        // Ignore clicks on No Diff Label.
        if (tip === 0) {
            return;
        }

        const revisionIDs = this.model.get('attachmentRevisionIDs');
        const revisionTip = revisionIDs[tip - 1];

        /*
         * Eventually these hard redirects will use a router
         * (see diffViewerPageView.js for example)
         * this.router.navigate(base + '-' + tip + '/', {trigger: true});
         */
        let redirectURL;

        if (base === 0) {
            redirectURL = `../${revisionTip}/`;
        } else {
            const revisionBase = revisionIDs[base - 1];
            redirectURL = `../${revisionBase}-${revisionTip}/`;
        }

        RB.navigateTo(redirectURL, {replace: true});
    }
}
