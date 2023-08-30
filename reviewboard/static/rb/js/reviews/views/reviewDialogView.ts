/**
 * The review dialog.
 */

import { BaseView, spina } from '@beanbag/spina';

import {
    ClientCommChannel,
    EnabledFeatures,
    ResourceCollection,
    Review,
    UserSession,
} from 'reviewboard/common';
import {
    MenuButtonView,
    RichTextInlineEditorView,
    SlideshowView,
    TextEditorView,
} from 'reviewboard/ui';

import { ReviewRequestEditor } from '../models/reviewRequestEditorModel';


declare const MANUAL_URL: string;
const REVIEW_DOCS_URL = `${MANUAL_URL}users/#reviewing-code-and-documents`;


/**
 * Base class for displaying a comment in the review dialog.
 */
@spina({
    prototypeAttrs: [
        'editorTemplate',
        'thumbnailTemplate',
    ],
})
class BaseCommentView<
    TModel extends Backbone.Model = Backbone.Model,
    TElement extends Element = HTMLDivElement,
    TExtraViewOptions extends object = undefined
> extends BaseView<TModel, TElement, TExtraViewOptions> {
    static tagName = 'li';
    static events = {
        'click .delete-comment': '_deleteComment',
    };

    /** The template to use for rendering the comment editor. */
    static editorTemplate = _.template(dedent`
        <div class="edit-fields">
         <div class="edit-field">
          <div class="comment-text-field">
           <label class="comment-label" for="<%= id %>">
            <%- commentText %>
            <a href="#" role="button" class="delete-comment"
               aria-label="<%- deleteCommentText %>"
               title="<%- deleteCommentText %>"
               ><span class="fa fa-trash-o" aria-hidden="true"></span></a>
           </label>
           <pre id="<%= id %>" class="reviewtext rich-text"
                data-rich-text="true"><%- text %></pre>
          </div>
         </div>
         <div class="edit-field">
          <input class="issue-opened" id="<%= issueOpenedID %>"
                 type="checkbox">
          <label for="<%= issueOpenedID %>"><%- openAnIssueText %></label>
          <% if (showVerify) { %>
           <input class="issue-verify" id="<%= verifyIssueID %>"
                  type="checkbox">
           <label for="<%= verifyIssueID %>"><%- verifyIssueText %></label>
          <% } %>
         </div>
        </div>
    `);

    /** The template to use for rendering comment thumbnails. */
    static thumbnailTemplate = null;

    /**********************
     * Instance variables *
     **********************/

    /** The checkbox for whether to open an issue. */
    $issueOpened: JQuery = null;

    /** The comment editor. */
    $editor: JQuery = null;

    /** The inline editor. */
    inlineEditorView: RichTextInlineEditorView = null;

    /** The text editor. */
    textEditor: TextEditorView = null;

    /** Checkbox for controlling whether issue verification is required. */
    #$issueVerify: JQuery = null;

    /** Views added by extension hooks. */
    #hookViews: Backbone.View[] = [];

    /** The original state of the comment extra data field. */
    #origExtraData: { [key: string]: unknown };

    /**
     * Initialize the view.
     */
    initialize(options: TExtraViewOptions) {
        this.#origExtraData = _.clone(this.model.get('extraData'));
    }

    /**
     * Remove the view.
     *
     * Returns:
     *     BaseCommentView:
     *     This object, for chaining.
     */
    remove(): this {
        this.#hookViews.forEach(view => view.remove());
        this.#hookViews = [];

        return super.remove();
    }

    /**
     * Return whether or not the comment needs to be saved.
     *
     * The comment will need to be saved if the inline editor is currently
     * open.
     *
     * Returns:
     *     boolean:
     *     Whether the comment needs to be saved.
     */
    needsSave(): boolean {
        return (this.inlineEditorView.isDirty() ||
                !_.isEqual(this.model.get('extraData'), this.#origExtraData));
    }

    /**
     * Save the final state of the view.
     *
     * Saves the inline editor and notifies the caller when the model is
     * synced.
     *
     * Args:
     *     options (object):
     *         Options for the model save operation.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    save(options: Backbone.ModelSaveOptions): Promise<void> {
        /*
         * If the inline editor needs to be saved, ask it to do so. This will
         * call this.model.save(). If it does not, just save the model
         * directly.
         */
        return new Promise<void>(resolve => {
            if (this.inlineEditorView.isDirty()) {
                this.model.once('sync', () => resolve());
                this.inlineEditorView.submit();
            } else {
                resolve(this.model.save(_.extend({
                    attrs: ['forceTextType', 'includeTextTypes', 'extraData'],
                }, options)));
            }
        });
    }

    /**
     * Render the comment view.
     */
    onInitialRender() {
        this.$el
            .addClass('draft')
            .append(this.renderThumbnail())
            .append(this.editorTemplate({
                commentText: _`Comment`,
                deleteCommentText: _`Delete comment`,
                id: _.uniqueId('draft_comment_'),
                issueOpenedID: _.uniqueId('issue-opened'),
                openAnIssueText: _`Open an Issue`,
                showVerify: EnabledFeatures.issueVerification,
                text: this.model.get('text'),
                verifyIssueID: _.uniqueId('issue-verify'),
                verifyIssueText: RB.CommentDialogView._verifyIssueText,
            }))
            .find('time.timesince')
                .timesince()
            .end();

        this.$issueOpened = this.$('.issue-opened')
            .prop('checked', this.model.get('issueOpened'))
            .change(() => {
                this.model.set('issueOpened',
                               this.$issueOpened.prop('checked'));

                if (!this.model.isNew()) {
                    /*
                     * We don't save the issueOpened attribute for unsaved
                     * models because the comment won't exist yet. If we did,
                     * clicking cancel when creating a new comment wouldn't
                     * delete the comment.
                     */
                    this.model.save({
                        attrs: ['forceTextType', 'includeTextTypes',
                                'issueOpened'],
                    });
                }
            });

        this.#$issueVerify = this.$('.issue-verify')
            .prop('checked', this.model.requiresVerification())
            .change(() => {
                const extraData = _.clone(this.model.get('extraData'));
                extraData.require_verification =
                    this.#$issueVerify.prop('checked');
                this.model.set('extraData', extraData);

                if (!this.model.isNew()) {
                    /*
                     * We don't save the extraData attribute for unsaved models
                     * because the comment won't exist yet. If we did, clicking
                     * cancel when creating a new comment wouldn't delete the
                     * comment.
                     */
                    this.model.save({
                        attrs: ['forceTextType', 'includeTextTypes',
                                'extra_data.require_verification'],
                    });
                }
            });

        const $editFields = this.$('.edit-fields');

        this.$editor = this.$('pre.reviewtext');

        this.inlineEditorView = new RichTextInlineEditorView({
            editIconClass: 'rb-icon rb-icon-edit',
            el: this.$editor,
            multiline: true,
            notifyUnchangedCompletion: true,
            textEditorOptions: {
                bindRichText: {
                    attrName: 'richText',
                    model: this.model,
                },
            },
        });
        this.inlineEditorView.render();

        this.textEditor = this.inlineEditorView.textEditor;

        this.listenTo(this.inlineEditorView, 'complete', value => {
            const attrs = ['forceTextType', 'includeTextTypes',
                           'richText', 'text'];

            if (this.model.isNew()) {
                /*
                 * If this is a new comment, we have to send whether or not an
                 * issue was opened because toggling the issue opened checkbox
                 * before it is completed won't save the status to the server.
                 */
                attrs.push('extra_data.require_verification', 'issueOpened');
            }

            this.model.set({
                richText: this.textEditor.richText,
                text: value,
            });
            this.model.save({
                attrs: attrs,
            });
        });

        this.listenTo(this.model, `change:${this._getRawValueFieldsName()}`,
                      this._updateRawValue);
        this._updateRawValue();

        this.listenTo(this.model, 'saved', this.renderText);
        this.renderText();

        this.listenTo(this.model, 'destroying',
                      () => this.stopListening(this.model));

        RB.ReviewDialogCommentHook.each(hook => {
            const HookView = hook.get('viewType');
            const hookView = new HookView({
                extension: hook.get('extension'),
                model: this.model,
            });

            this.#hookViews.push(hookView);

            $('<div class="edit-field"/>')
                .append(hookView.$el)
                .appendTo($editFields);
            hookView.render();
        });
    }

    /**
     * Render the thumbnail for this comment.
     *
     * Returns:
     *     jQuery:
     *     The rendered thumbnail element.
     */
    renderThumbnail(): JQuery {
        if (this.thumbnailTemplate === null) {
            return null;
        }

        return $(this.thumbnailTemplate(this.model.attributes));
    }

    /**
     * Render the text for this comment.
     */
    renderText() {
        const reviewRequest =
            this.model.get('parentObject').get('parentObject');

        if (this.$editor) {
            RB.formatText(this.$editor, {
                bugTrackerURL: reviewRequest.get('bugTrackerURL'),
                isHTMLEncoded: true,
                newText: this.model.get('text'),
                richText: this.model.get('richText'),
            });
        }
    }

    /**
     * Delete the comment associated with the model.
     */
    _deleteComment() {
        if (confirm(_`Are you sure you want to delete this comment?`)) {
            this.model.destroy();
        }
    }

    /**
     * Update the stored raw value of the comment text.
     *
     * This updates the raw value stored in the inline editor as a result of a
     * change to the value in the model.
     */
    _updateRawValue() {
        if (this.$editor) {
            this.inlineEditorView.options.hasRawValue = true;
            this.inlineEditorView.options.rawValue =
                this.model.get(this._getRawValueFieldsName()).text;
        }
    }

    /**
     * Return the field name for the raw value.
     *
     * Returns:
     *     string:
     *     The field name to use, based on the whether the user wants to use
     *     Markdown or not.
     */
    _getRawValueFieldsName() {
        return UserSession.instance.get('defaultUseRichText')
            ? 'markdownTextFields'
            : 'rawTextFields';
    }
}


/**
 * Options for the DiffCommentView.
 *
 * Version Added:
 *     6.0
 */
interface DiffCommentViewOptions {
    /** The view that handles loading diff fragments. */
    diffQueue: RB.DiffFragmentQueueView;
}


/**
 * Displays a view for diff comments.
 */
@spina({
    prototypeAttrs: ['thumbnailTemplate'],
})
export class DiffCommentView extends BaseCommentView<
    RB.DiffComment,
    HTMLDivElement,
    DiffCommentViewOptions
> {
    static thumbnailTemplate = _.template(dedent`
        <div class="review-dialog-comment-diff"
             id="review_draft_comment_container_<%= id %>">
         <table class="sidebyside loading">
          <thead>
           <tr>
            <th class="filename"><%- revisionText %></th>
           </tr>
          </thead>
          <tbody>
           <% for (var i = 0; i < numLines; i++) { %>
            <tr><td><pre>&nbsp;</pre></td></tr>
           <% } %>
          </tbody>
         </table>
        </div>
    `);

    /** The stored view options. */
    options: DiffCommentViewOptions;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (DiffCommentViewOptions):
     *         Options for the view.
     */
    initialize(options: DiffCommentViewOptions) {
        this.options = options;

        super.initialize(options);
    }

    /**
     * Render the comment view.
     *
     * After rendering, this will queue up a load of the diff fragment
     * to display. The view will show a spinner until the fragment has
     * loaded.
     */
    onInitialRender() {
        super.onInitialRender();

        const fileDiffID = this.model.get('fileDiffID');
        const interFileDiffID = this.model.get('interFileDiffID');

        this.options.diffQueue.queueLoad(
            this.model.id,
            interFileDiffID ? fileDiffID + '-' + interFileDiffID
            : fileDiffID);
    }

    /**
     * Render the thumbnail.
     *
     * Returns:
     *     jQuery:
     *     The rendered thumbnail element.
     */
    renderThumbnail(): JQuery {
        const fileDiff = this.model.get('fileDiff');
        const interFileDiff = this.model.get('interFileDiff');
        let revisionText;

        if (interFileDiff) {
            revisionText = interpolate(
                _`%(filename)s (Diff revisions %(fileDiffRevision)s - %(interFileDiffRevision)s)`,
                {
                    fileDiffRevision: fileDiff.get('sourceRevision'),
                    filename: fileDiff.get('destFilename'),
                    interfileDiffRevision: interFileDiff.get('sourceRevision'),
                },
                true);
        } else {
            revisionText = interpolate(
                _`%(filename)s (Diff revision %(fileDiffRevision)s)`,
                {
                    fileDiffRevision: fileDiff.get('sourceRevision'),
                    filename: fileDiff.get('destFilename'),
                },
                true);
        }

        return $(this.thumbnailTemplate({
            id: this.model.get('id'),
            numLines: this.model.getNumLines(),
            revisionText: revisionText,
        }));
    }
}


/**
 * Displays a view for file attachment comments.
 */
@spina({
    prototypeAttrs: ['thumbnailTemplate'],
})
class FileAttachmentCommentView extends BaseCommentView<
    RB.FileAttachmentComment
> {
    static thumbnailTemplate = _.template(dedent`
        <div class="file-attachment">
         <span class="filename">
          <a href="<%- reviewURL %>"><%- linkText %></a>
         </span>
         <span class="diffrevision"><%- revisionsStr %></span>
         <div class="thumbnail"><%= thumbnailHTML %></div>
        </div>
    `);

    /**
     * Render the thumbnail.
     *
     * Returns:
     *     jQuery:
     *     The rendered thumbnail element.
     */
    renderThumbnail(): JQuery {
        const fileAttachment = this.model.get('fileAttachment');
        const diffAgainstFileAttachment =
            this.model.get('diffAgainstFileAttachment');
        const revision = fileAttachment.get('revision');
        let revisionsStr;

        if (!revision) {
            /* This predates having a revision. Don't show anything. */
            revisionsStr = '';
        } else if (diffAgainstFileAttachment) {
            const revision1 = diffAgainstFileAttachment.get('revision');

            revisionsStr = _`(Revisions ${revision1} - ${revision})`;
        } else {
            revisionsStr = _`(Revision ${revision})`;
        }

        return $(this.thumbnailTemplate(_.defaults({
            revisionsStr: revisionsStr,
        }, this.model.attributes)));
    }
}


/**
 * Displays a view for general comments.
 */
@spina({
    prototypeAttrs: ['thumbnailTemplate'],
})
class GeneralCommentView extends BaseCommentView {
    static thumbnailTemplate = null;
}


/**
 * Displays a view for screenshot comments.
 */
@spina({
    prototypeAttrs: ['thumbnailTemplate'],
})
class ScreenshotCommentView extends BaseCommentView<
    RB.ScreenshotComment
> {
    static thumbnailTemplate = _.template(dedent`
        <div class="screenshot">
         <span class="filename">
          <a href="<%- screenshot.reviewURL %>"><%- displayName %></a>
         </span>
         <img src="<%= thumbnailURL %>" width="<%= width %>"
              height="<%= height %>" alt="<%- displayName %>" />
        </div>
    `);

    /**
     * Render the thumbnail.
     *
     * Returns:
     *     jQuery:
     *     The rendered thumbnail element.
     */
    renderThumbnail(): JQuery {
        const screenshot = this.model.get('screenshot');

        return $(this.thumbnailTemplate(_.defaults({
            displayName: screenshot.getDisplayName(),
            screenshot: screenshot.attributes,
        }, this.model.attributes)));
    }
}


/**
 * Options for the HeaderFooterCommentView.
 *
 * Version Added:
 *     6.0
 */
interface HeaderFooterCommentViewOptions {
    /** The text to show in the label for the comment field. */
    commentText: string;

    /** The text to show in the "add" link. */
    linkText: string;

    /** The property name to modify (either ``bodyTop`` or ``bodyBottom``). */
    propertyName: string;

    /** The property name of the rich text field for the content property. */
    richTextPropertyName: string;
}


/**
 * The header or footer for a review.
 */
@spina({
    prototypeAttrs: ['editorTemplate'],
})
class HeaderFooterCommentView extends BaseView<
    Review,
    HTMLDivElement,
    HeaderFooterCommentViewOptions
> {
    static tagName = 'li';
    static events = {
        'click .add-link': 'openEditor',
    };

    static editorTemplate = _.template(dedent`
        <div class="edit-fields">
         <div class="edit-field">
          <div class="add-link-container">
           <a href="#" class="add-link"><%- linkText %></a>
          </div>
          <div class="comment-text-field">
           <label for="<%= id %>" class="comment-label">
            <%- commentText %>
           </label>
           <pre id="<%= id %>" class="reviewtext rich-text"
                data-rich-text="true"><%- text %></pre>
          </div>
         </div>
        </div>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The editor element. */
    $editor: JQuery = null;

    /** The text to show in the label for the comment field. */
    commentText: string;

    /** The inline editor view. */
    inlineEditorView: RichTextInlineEditorView;

    /** The text to show in the "add" link. */
    linkText: string;

    /** The property name to modify (either ``bodyTop`` or ``bodyBottom``). */
    propertyName: string;

    /** The property name of the rich text field for the content property. */
    richTextPropertyName: string;

    /** The text editor view. */
    textEditor: TextEditorView = null;

    /** The container element for the editor. */
    #$editorContainer: JQuery = null;

    /** The container element for the "add" link. */
    #$linkContainer: JQuery = null;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (HeaderFooterCommentViewOptions):
     *         Options for the view.
     */
    initialize(options: HeaderFooterCommentViewOptions) {
        this.propertyName = options.propertyName;
        this.richTextPropertyName = options.richTextPropertyName;
        this.linkText = options.linkText;
        this.commentText = options.commentText;
    }

    /**
     * Set the text of the link.
     *
     * Args:
     *     linkText (string):
     *         The text to show in the "add" link.
     */
    setLinkText(linkText: string) {
        this.$('.add-link').text(linkText);
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        const text = this.model.get(this.propertyName);

        this.$el
            .addClass('draft')
            .append(this.editorTemplate({
                commentText: this.commentText,
                id: this.propertyName,
                linkText: this.linkText,
                text: text || '',
            }))
            .find('time.timesince')
                .timesince()
            .end();


        this.$editor = this.$('pre.reviewtext');

        this.inlineEditorView = new RichTextInlineEditorView({
            editIconClass: 'rb-icon rb-icon-edit',
            el: this.$editor,
            multiline: true,
            notifyUnchangedCompletion: true,
            textEditorOptions: {
                bindRichText: {
                    attrName: this.richTextPropertyName,
                    model: this.model,
                },
            },
        });
        this.inlineEditorView.render();

        this.textEditor = this.inlineEditorView.textEditor;

        this.listenTo(this.inlineEditorView, 'complete', value => {
            this.model.set(this.propertyName, value);
            this.model.set(this.richTextPropertyName,
                           this.textEditor.richText);
            this.model.save({
                attrs: [this.propertyName, this.richTextPropertyName,
                        'forceTextType', 'includeTextTypes'],
            });
        });
        this.listenTo(this.inlineEditorView, 'cancel', () => {
            if (!this.model.get(this.propertyName)) {
                this.#$editorContainer.hide();
                this.#$linkContainer.show();
            }
        });

        this.#$editorContainer = this.$('.comment-text-field');
        this.#$linkContainer = this.$('.add-link-container');

        this.listenTo(this.model, `change:${this._getRawValueFieldsName()}`,
                      this._updateRawValue);
        this._updateRawValue();

        this.listenTo(this.model, 'saved', this.renderText);
        this.renderText();
    }

    /**
     * Render the text for this comment.
     */
    renderText() {
        if (this.$editor) {
            const text = this.model.get(this.propertyName);

            if (text) {
                const reviewRequest = this.model.get('parentObject');

                this.#$editorContainer.show();
                this.#$linkContainer.hide();
                RB.formatText(this.$editor, {
                    bugTrackerURL: reviewRequest.get('bugTrackerURL'),
                    isHTMLEncoded: true,
                    newText: text,
                    richText: this.model.get(this.richTextPropertyName),
                });
            } else {
                this.#$editorContainer.hide();
                this.#$linkContainer.show();
            }
        }
    }

    /**
     * Return whether or not the comment needs to be saved.
     *
     * The comment will need to be saved if the inline editor is currently
     * open.
     *
     * Returns:
     *     boolean:
     *     Whether the comment needs to be saved.
     */
    needsSave(): boolean {
        return this.inlineEditorView.isDirty();
    }

    /**
     * Save the final state of the view.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    save(): Promise<void> {
        return new Promise<void>(resolve => {
            this.model.once('sync', () => resolve());
            this.inlineEditorView.submit();
        });
    }

    /**
     * Open the editor.
     *
     * This is used for the 'Add ...' link handler, as well as for the default
     * state of the dialog when there are no comments.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered the action.
     *
     * Returns:
     *     boolean:
     *     false, always.
     */
    openEditor(
        ev?: Event,
    ): boolean {
        this.#$linkContainer.hide();
        this.#$editorContainer.show();

        this.inlineEditorView.startEdit();

        if (ev) {
            ev.preventDefault();
        }

        return false;
    }

    /**
     * Delete the comment.
     *
     * This is a no-op, since headers and footers can't be deleted.
     */
    _deleteComment() {
    }

    /**
     * Update the stored raw value of the comment text.
     *
     * This updates the raw value stored in the inline editor as a result of a
     * change to the value in the model.
     */
    _updateRawValue() {
        if (this.$editor) {
            const rawValues = this.model.get(this._getRawValueFieldsName());

            this.inlineEditorView.options.hasRawValue = true;
            this.inlineEditorView.options.rawValue =
                rawValues[this.propertyName];
        }
    }

    /**
     * Return the field name for the raw value.
     *
     * Returns:
     *     string:
     *     The field name to use, based on the whether the user wants to use
     *     Markdown or not.
     */
    _getRawValueFieldsName(): string {
        return UserSession.instance.get('defaultUseRichText')
               ? 'markdownTextFields'
               : 'rawTextFields';
    }
}


/**
 * View to show tips to the user about creating reviews.
 *
 * Version Added:
 *     6.0
 */
@spina
class TipsSlideshowView extends SlideshowView {
    static className = 'rb-c-alert -is-info';
    static template = dedent`
        <div class="rb-c-slideshow -is-auto-cycled">
         <span class="rb-c-alert__close"
               role="button"
               aria-label="${gettext('Close')}"
               title="${gettext('Close')}"
               tabindex="0"></span>
         <div class="rb-c-alert__content">
          <div class="rb-c-alert__heading">
           <nav class="rb-c-slideshow__nav">
            <label for="">${gettext('Tip:')}</label>
            <a class="rb-c-slideshow__nav-prev"
               href="#"
               role="button"
               aria-label="${gettext('Previous')}"
               title="${gettext('Previous')}">
             <span class="fa fa-caret-left"></span>
            </a>
            <a class="rb-c-slideshow__nav-next"
               href="#"
               role="button"
               aria-label="${gettext('Next')}"
               title="${gettext('Next')}">
             <span class="fa fa-caret-right"></span>
            </a>
           </nav>
          </div>
          <ul class="rb-c-slideshow__slides">
          </ul>
         </div>
        </div>
    `;

    #tips: string[] = [
        _`To add a comment to a code change or text file attachment, click on
          a line number or click and drag over multiple line numbers in the
          diff viewer. You'll be able to see and edit the comment from both
          the diff viewer and here in the review dialog.`,
        _`When reviewing image file attachments, add comments by clicking and
          dragging out a region.`,
        _`To add comments that aren't tied to a specific code change or file
          attachment, click on the "Add General Comment" button at the bottom
          of the review dialog or in the Review menu. This is useful for
          comments that apply to the review request as a whole or for ones
          that don't refer to any specific areas.`,
        _`For file attachments that don't have a review interface, you can
          add a comment through the "Add Comment" button when hovering over
          the file attachment. The comment can then be seen and edited here
          in the review dialog.`,
        _`Until you publish your review, your review and any comments in it
          are only visible to you and can be edited freely. After you publish,
          your review will be visible to others on the review request and you
          won't be able to edit it anymore.`,
        _`Use a "Ship It!" in your review to show your approval for a review
          request. This can be toggled at the top of this review dialog, or
          you can quickly post a "Ship It!" review with no other content in
          it by clicking on the "Ship It!" action in the Review menu.`,
        _`The optional header and footer fields can be useful for providing a
          summary or conclusion for your review, or for encouraging remarks.`,
        _`For more information on reviewing code and documents, visit our
          <a href="${REVIEW_DOCS_URL}">documentation</a>.`,
    ];

    static events = {
        'click .rb-c-alert__close': '_onCloseClicked',
    };

    /**
     * Render the view.
     */
    onInitialRender() {
        this.$el
            .html(TipsSlideshowView.template)
            .attr({
                'aria-label': _`Tips`,
                'aria-roledescription': 'carousel',
            });

        const $slides = this.$('.rb-c-slideshow__slides');
        const li = dedent`
            <li class="rb-c-slideshow__slide"
                role="group"
                aria-hidden="false"
                aria-roledescription="slide">`;

        for (const tip of this.#tips) {
            $(li)
                .html(tip)
                .appendTo($slides);
        }

        super.onInitialRender();
    }

    /**
     * Handler for when the close icon is clicked.
     *
     * Args:
     *     ev (JQuery.ClickEvent):
     *         The event.
     */
    private _onCloseClicked(ev: JQuery.ClickEvent) {
        ev.stopPropagation();
        ev.preventDefault();

        this.trigger('hide');
    }
}


/**
 * Options for the ReviewDialogView.
 *
 * Version Added:
 *     6.0
 */
interface ReviewDialogViewOptions {
    /** The selector for a container element for the dialog. */
    container?: string;

    /** The review request editor. */
    reviewRequestEditor: ReviewRequestEditor;
}


/**
 * Options for creating the ReviewDialogView.
 *
 * Version Added:
 *     6.0
 */
interface ReviewDialogViewCreationOptions extends ReviewDialogViewOptions {
    /** The review instance. */
    review: RB.Review;
}


/**
 * Creates a dialog for modifying a draft review.
 *
 * This provides editing capabilities for creating or modifying a new
 * review. The list of comments are retrieved from the server, providing
 * context for the comments.
 */
@spina({
    prototypeAttrs: ['template'],
})
export class ReviewDialogView extends BaseView<
    Review,
    HTMLDivElement,
    ReviewDialogViewOptions
> {
    static id = 'review-form-comments';
    static className = 'review';

    static template = _.template(dedent`
        <div class="edit-field">
         <input id="id_shipit" type="checkbox" />
         <label for="id_shipit"><%- shipItText %></label>
        </div>
        <div class="review-dialog-hooks-container"></div>
        <div class="edit-field body-top"></div>
        <ol id="review-dialog-body-top-comments" class="review-comments"></ol>
        <ol id="review-dialog-general-comments" class="review-comments"></ol>
        <ol id="review-dialog-screenshot-comments" class="review-comments"></ol>
        <ol id="review-dialog-file-attachment-comments" class="review-comments"></ol>
        <ol id="review-dialog-diff-comments" class="review-comments"></ol>
        <ol id="review-dialog-body-bottom-comments" class="review-comments"></ol>
        <div class="spinner"><span class="djblets-o-spinner"></span></div>
        <div class="edit-field body-bottom"></div>
    `);

    /** The review dialog instance. */
    static instance: ReviewDialogView = null;

    /**
     * Create the review dialog.
     *
     * Args:
     *     options (ReviewDialogViewOptions):
     *         Options for the dialog.
     *
     * Returns:
     *     ReviewDialogView:
     *     The new dialog instance.
     */
    static create(
        options: ReviewDialogViewCreationOptions,
    ): ReviewDialogView {
        console.assert(!this.instance,
                       'A ReviewDialogView is already opened');
        console.assert(options.review, 'A review must be specified');

        const dialog = new this({
            container: options.container,
            model: options.review,
            reviewRequestEditor: options.reviewRequestEditor,
        });
        this.instance = dialog;

        dialog.render();

        dialog.on('closed', () => {
            this.instance = null;
        });

        return dialog;
    }

    /**********************
     * Instance variables *
     **********************/

    /** The view options. */
    options: ReviewDialogViewOptions;

    /** The elements for the diff comment views. */
    #$diffComments: JQuery = $();

    /** The dialog element. */
    #$dlg: JQuery = null;

    /** The elements for the file attachment comment views. */
    #$fileAttachmentComments: JQuery = $();

    /** The elements for the general comment views. */
    #$generalComments: JQuery = $();

    /** The elements for the screenshot comment views. */
    #$screenshotComments: JQuery = $();

    /** The default for whether to use rich text (Markdown). */
    #defaultUseRichText: boolean;

    /** The queue for loading diff fragments. */
    #diffQueue: RB.DiffFragmentQueueView;

    /** The set of additional views added by extension hooks. */
    #hookViews: Backbone.View[] = [];

    /** The publish button. */
    #publishButton: MenuButtonView = null;

    /** Additional data to send when calling this.model.ready(). */
    #queryData: JQuery.PlainObject;

    /** The buttons for the dialog. */
    _$buttons: JQuery = null;

    /** The "ship it" checkbox. */
    _$shipIt: JQuery = null;

    /** The loading spinner. */
    _$spinner: JQuery = null;

    /** The view for the review header editor. */
    _bodyBottomView: HeaderFooterCommentView;

    /** The view for the review footer editor. */
    _bodyTopView: HeaderFooterCommentView;

    /** The set of views for all comments. */
    _commentViews: BaseCommentView[] = [];

    /** The collection of diff comments. */
    _diffCommentsCollection: ResourceCollection<RB.DiffComment>;

    /** The collection of file attachment comments. */
    _fileAttachmentCommentsCollection:
        ResourceCollection<RB.FileAttachmentComment>;

    /** The collection of general comments. */
    _generalCommentsCollection: ResourceCollection<RB.GeneralComment>;

    /** The collection of screenshot comments. */
    _screenshotCommentsCollection: ResourceCollection<RB.ScreenshotComment>;

    /** The link to show the tips carousel when hidden. */
    #showTips: JQuery = null;

    /** The carousel showing tips for creating reviews. */
    #tipsView: TipsSlideshowView = null;

    /**
     * Initialize the review dialog.
     *
     * Args:
     *     options (ReviewDialogViewOptions):
     *         Options for the view.
     */
    initialize(options: ReviewDialogViewOptions) {
        this.options = options;

        const reviewRequest = this.model.get('parentObject');
        this.#diffQueue = new RB.DiffFragmentQueueView({
            containerPrefix: 'review_draft_comment_container',
            queueName: 'review_draft_diff_comments',
            reviewRequestPath: reviewRequest.get('reviewURL'),
        });

        this._diffCommentsCollection =
            new ResourceCollection<RB.DiffComment>([], {
                extraQueryData: {
                    'order-by': 'filediff,first_line',
                },
                model: RB.DiffComment,
                parentResource: this.model,
            });

        this._bodyTopView = new HeaderFooterCommentView({
            commentText: _`Header`,
            linkText: _`Add header`,
            model: this.model,
            propertyName: 'bodyTop',
            richTextPropertyName: 'bodyTopRichText',
        });

        this._bodyBottomView = new HeaderFooterCommentView({
            commentText: _`Footer`,
            linkText: _`Add footer`,
            model: this.model,
            propertyName: 'bodyBottom',
            richTextPropertyName: 'bodyBottomRichText',
        });

        this.listenTo(this._diffCommentsCollection, 'add', comment => {
            const view = new DiffCommentView({
                diffQueue: this.#diffQueue,
                model: comment,
            });
            this._renderComment(view, this.#$diffComments);
        });

        this._fileAttachmentCommentsCollection =
            new ResourceCollection<RB.FileAttachmentComment>([], {
                model: RB.FileAttachmentComment,
                parentResource: this.model,
            });

        this.listenTo(this._fileAttachmentCommentsCollection, 'add',
                      comment => {
            const view = new FileAttachmentCommentView({ model: comment });
            this._renderComment(view, this.#$fileAttachmentComments);
        });

        this._generalCommentsCollection =
            new RB.ResourceCollection<RB.FileAttachmentComment>([], {
                model: RB.GeneralComment,
                parentResource: this.model,
            });

        this.listenTo(this._generalCommentsCollection, 'add', comment => {
            const view = new GeneralCommentView({ model: comment });
            this._renderComment(view, this.#$generalComments);
        });

        this._screenshotCommentsCollection =
            new ResourceCollection<RB.ScreenshotComment>([], {
                model: RB.ScreenshotComment,
                parentResource: this.model,
            });

        this.listenTo(this._screenshotCommentsCollection, 'add', comment => {
            const view = new ScreenshotCommentView({ model: comment });
            this._renderComment(view, this.#$screenshotComments);
        });

        this.#defaultUseRichText =
            UserSession.instance.get('defaultUseRichText');

        this.#queryData = {
            'force-text-type': 'html',
        };

        if (this.#defaultUseRichText) {
            this.#queryData['include-text-types'] = 'raw,markdown';
        } else {
            this.#queryData['include-text-types'] = 'raw';
        }

        this._setTextTypeAttributes(this.model);

        this.options.reviewRequestEditor.incr('editCount');
    }

    /**
     * Remove the dialog from the DOM.
     *
     * This will remove all the extension hook views from the dialog,
     * and then remove the dialog itself.
     *
     * Returns:
     *     ReviewDialogView:
     *     This object, for chaining.
     */
    remove(): this {
        if (this.#publishButton) {
            this.#publishButton.remove();
            this.#publishButton = null;
        }

        this.#hookViews.forEach(view => view.remove());
        this.#hookViews = [];

        return super.remove();
    }

    /**
     * Close the review dialog.
     *
     * The dialog will be removed from the screen, and the "closed"
     * event will be triggered.
     */
    close() {
        this.options.reviewRequestEditor.decr('editCount');
        this.#$dlg.modalBox('destroy');
        this.trigger('closed');

        this.remove();
    }

    /**
     * Render the dialog.
     *
     * The dialog will be shown on the screen, and the comments from
     * the server will begin loading and rendering.
     */
    onInitialRender() {
        this.$el.html(this.template({
            addFooterText: _`Add footer`,
            addHeaderText: _`Add header`,
            markdownDocsURL: MANUAL_URL + 'users/markdown/',
            markdownText: _`Markdown Reference`,
            shipItText: _`Ship It`,
        }));

        this.#$diffComments = this.$('#review-dialog-diff-comments');
        this.#$fileAttachmentComments =
            this.$('#review-dialog-file-attachment-comments');
        this.#$generalComments = this.$('#review-dialog-general-comments');
        this.#$screenshotComments =
            this.$('#review-dialog-screenshot-comments');
        this._$spinner = this.$('.spinner');
        this._$shipIt = this.$('#id_shipit');

        const $hooksContainer = this.$('.review-dialog-hooks-container');

        this.#tipsView = new TipsSlideshowView({
            autoCycleTimeMS: 5000,
        });
        this.#tipsView.render();
        this.#tipsView.$el
            .hide()
            .prependTo(this.$el);

        this.listenTo(this.#tipsView, 'hide', () => {
            UserSession.instance.set('showReviewDialogTips', false);
            this.#updateTipsVisibility(false);
        });

        this.#showTips = $('<a href="#" id="show-review-tips" role="button">')
            .text(_`Show tips`)
            .hide()
            .prependTo(this.$el)
            .click(e => {
                e.stopPropagation();
                e.preventDefault();

                this.#updateTipsVisibility(true);
                UserSession.instance.set('showReviewDialogTips', true);
            });

        this.#updateTipsVisibility(
            UserSession.instance.get('showReviewDialogTips'));

        RB.ReviewDialogHook.each(hook => {
            const HookView = hook.get('viewType');
            const hookView = new HookView({
                extension: hook.get('extension'),
                model: this.model,
            });

            this.#hookViews.push(hookView);

            $hooksContainer.append(hookView.$el);
            hookView.render();
        });

        this._bodyTopView.$el.appendTo(
            this.$('#review-dialog-body-top-comments'));
        this._bodyBottomView.$el.appendTo(
            this.$('#review-dialog-body-bottom-comments'));

        /*
         * Even if the model is already loaded, we may not have the right text
         * type data. Force it to reload.
         */
        this.model.set('loaded', false);

        this.model.ready({ data: this.#queryData })
            .then(() => {
                this._renderDialog();
                this._bodyTopView.render();
                this._bodyBottomView.render();

                if (this.model.isNew() || this.model.get('bodyTop') === '') {
                    this._bodyTopView.openEditor();
                }

                if (this.model.isNew()) {
                    this._$spinner.remove();
                    this._$spinner = null;

                    this._handleEmptyReview();
                    this.trigger('loadCommentsDone');
                } else {
                    this._$shipIt.prop('checked', this.model.get('shipIt'));
                    this._loadComments();
                }

                this.listenTo(this.model, 'change:bodyBottom',
                              this._handleEmptyReview);
            });
    }

    /**
     * Load the comments from the server.
     *
     * This will begin chaining together the loads of each set of
     * comment types. Each loaded comment will be rendered to the
     * dialog once loaded.
     */
    async _loadComments() {
        const collections = [
            this._screenshotCommentsCollection,
            this._fileAttachmentCommentsCollection,
            this._diffCommentsCollection,
        ];

        if (EnabledFeatures.generalComments) {
            /*
             * Prepend the General Comments so they're fetched and shown
             * first.
             */
            collections.unshift(this._generalCommentsCollection);
        }

        const loadCollections = collections.map(async collection => {
            await collection.fetchAll({ data: this.#queryData });

            if (collection === this._diffCommentsCollection) {
                this.#diffQueue.loadFragments();
            }
        });

        try {
            await Promise.all(loadCollections);

            this._$spinner.remove();
            this._$spinner = null;

            this._handleEmptyReview();

            this.trigger('loadCommentsDone');
        } catch(err) {
            alert(err.message); // TODO: provide better output.
        }
    }

    /**
     * Properly set the view when the review is empty.
     */
    _handleEmptyReview() {
        /*
         * We only display the bottom textarea if we have comments or the user
         * has previously set the bottom textarea -- we don't want the user to
         * not be able to remove their text.
         */
        if (this._commentViews.length === 0 && !this.model.get('bodyBottom')) {
            this._bodyBottomView.$el.hide();
            this._bodyTopView.setLinkText(_`Add text`);
        }
    }

    /**
     * Render a comment to the dialog.
     *
     * Args:
     *     view (BaseCommentView):
     *         The view to render.
     *
     *     $container (jQuery):
     *         The container to add the view to.
     */
    _renderComment(view, $container) {
        this._setTextTypeAttributes(view.model);

        this._commentViews.push(view);

        this.listenTo(view.model, 'destroyed', () => {
            view.$el.fadeOut({
                complete: () => {
                    view.remove();
                    this._handleEmptyReview();
                },
            });

            this._commentViews = _.without(this._commentViews, view);
        });

        $container.append(view.$el);
        view.render();

        this.#$dlg.scrollTop(view.$el.position().top +
                             this.#$dlg.getExtents('p', 't'));
    }

    /**
     * Render the dialog.
     *
     * This will create and render a dialog to the screen, adding
     * this view's element as the child.
     */
    _renderDialog() {
        const $leftButtons = $('<div class="review-dialog-buttons-left"/>');
        const $rightButtons = $('<div class="review-dialog-buttons-right"/>');
        const buttons = [$leftButtons, $rightButtons];

        if (EnabledFeatures.generalComments) {
            $leftButtons.append(
                $('<input type="button" />')
                    .val(_`Add General Comment`)
                    .attr('title',
                          _`Add a new general comment to the review`)
                    .click(() => this.#onAddCommentClicked())
            );
        }

        $rightButtons.append(
            $('<div id="review-form-publish-split-btn-container" />'));

        $rightButtons.append(
            $('<input type="button"/>')
                .val(_`Discard Review`)
                .click(() => this._onDiscardClicked()));

        $rightButtons.append(
            $('<input type="button"/>')
                .val(_`Close`)
                .click(() => {
                    this._saveReview(false);
                    return false;
                }));

        const reviewRequest = this.model.get('parentObject');

        this.#$dlg = $('<div/>')
            .attr('id', 'review-form')
            .append(this.$el)
            .modalBox({
                boxID: 'review-form-modalbox',
                buttons: buttons,
                container: this.options.container || 'body',
                stretchX: true,
                stretchY: true,
                title: _`Review for: ${reviewRequest.get('summary')}`,
            })
            .on('close', () => this._saveReview(false))
            .attr('scrollTop', 0)
            .trigger('ready');

        /* Must be done after the dialog is rendered. */

        this.#publishButton = new MenuButtonView({
            ariaMenuLabel: _`More publishing options`,
            direction: 'up',
            el: $('#review-form-publish-split-btn-container'),
            menuItems: [
                {
                    onClick: () => {
                        this._saveReview(true, {
                            publishToOwnerOnly: true,
                        });
                        this.close();

                        return false;
                    },
                    text: _`... and only e-mail the owner`,
                },
                {
                    onClick: () => {
                        this._saveReview(true, {
                            publishAndArchive: true,
                        });
                        this.close();

                        return false;
                    },
                    text: _`... and archive the review request`,
                },
            ],
            onPrimaryButtonClick: () => {
                this._saveReview(true);

                return false;
            },
            text: _`Publish Review`,
        });

        this.#publishButton.render();

        this._$buttons = this.#$dlg.modalBox('buttons');
    }

    /**
     * Handle a click on the "Add Comment" button.
     *
     * Returns:
     *     boolean:
     *     This always returns false to indicate that the dialog should not
     *     close.
     */
    #onAddCommentClicked() {
        const comment = this.model.createGeneralComment(
            undefined,
            UserSession.instance.get('commentsOpenAnIssue'));

        this._generalCommentsCollection.add(comment);
        this._bodyBottomView.$el.show();
        this._commentViews[this._commentViews.length - 1]
            .inlineEditorView.startEdit();

        return false;
    }

    /**
     * Handle a click on the "Discard Review" button.
     *
     * Prompts the user to confirm that they want the review discarded.
     * If they confirm, the review will be discarded.
     *
     * Returns:
     *     boolean:
     *     This always returns false to indicate that the dialog should not
     *     close.
     */
    _onDiscardClicked() {
        const $cancelButton = $('<input type="button">')
            .val(_`Cancel`);

        const $discardButton = $('<input type="button">')
            .val(_`Discard`)
            .click(async () => {
                this.close();
                await this.model.destroy();

                ClientCommChannel.getInstance().reload();

                if (!EnabledFeatures.unifiedBanner) {
                    RB.DraftReviewBannerView.instance.hideAndReload();
                }
            });

        $('<p/>')
            .text(_`
                If you discard this review, all related comments will be
                permanently deleted.
            `)
            .modalBox({
                buttons: [
                    $cancelButton,
                    $discardButton,
                ],
                title: _`Are you sure you want to discard this review?`,
            });

        return false;
    }

    /**
     * Save the review.
     *
     * First, this loops over all the comment editors and saves any which are
     * still in the editing phase.
     *
     * Args:
     *     publish (boolean):
     *         Whether the review should be published.
     *
     *     options (object):
     *         Options for the model save operation.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    _saveReview(
        publish: boolean,
        options: {
            publishAndArchive?: boolean;
            publishToOwnerOnly?: boolean;
        } = {},
    ): Promise<void> {
        if (publish && options.publishToOwnerOnly) {
            this.model.set('publishToOwnerOnly', true);
        }

        if (publish && options.publishAndArchive) {
            this.model.set('publishAndArchive', true);
        }

        this._$buttons.prop('disabled');

        let madeChanges = false;
        $.funcQueue('reviewForm').clear();

        function maybeSave(view) {
            if (view.needsSave()) {
                $.funcQueue('reviewForm').add(() => {
                    madeChanges = true;
                    view.save()
                        .then(() => $.funcQueue('reviewForm').next());
                });
            }
        }

        maybeSave(this._bodyTopView);
        maybeSave(this._bodyBottomView);
        this._commentViews.forEach(view => maybeSave(view));

        $.funcQueue('reviewForm').add(() => {
            const shipIt = this._$shipIt.prop('checked');
            const saveFunc = publish ? this.model.publish : this.model.save;

            if (this.model.get('public') === publish &&
                this.model.get('shipIt') === shipIt) {
                $.funcQueue('reviewForm').next();
            } else {
                madeChanges = true;
                this.model.set({
                    shipIt: shipIt,
                });

                saveFunc.call(this.model, {
                    attrs: [
                        'forceTextType',
                        'includeTextTypes',
                        'public',
                        'publishAndArchive',
                        'publishToOwnerOnly',
                        'shipIt',
                    ]})
                    .then(() => $.funcQueue('reviewForm').next())
                    .catch(err => {
                        console.error('Failed to save review', err);
                    });
            }
        });

        $.funcQueue('reviewForm').add(() => {
            this.close();

            if (EnabledFeatures.unifiedBanner) {
                if (publish) {
                    // Reload the page.
                    RB.navigateTo(
                        this.model.get('parentObject').get('reviewURL'));
                }
            } else {
                const reviewBanner = RB.DraftReviewBannerView.instance;

                if (reviewBanner) {
                    if (publish) {
                        reviewBanner.hideAndReload();
                    } else if (this.model.isNew() && !madeChanges) {
                        reviewBanner.hide();
                    } else {
                        reviewBanner.show();
                    }
                }
            }

            $.funcQueue('reviewForm').next();
        });

        return new Promise<void>(resolve => {
            $.funcQueue('reviewForm').add(() => resolve());
            $.funcQueue('reviewForm').start();
        });
    }

    /**
     * Set the text attributes on a model for forcing and including types.
     *
     * Args:
     *     model (Backbone.Model):
     *         The model to set the text type attributes on.
     */
    _setTextTypeAttributes(model: Backbone.Model) {
        model.set({
            forceTextType: 'html',
            includeTextTypes: this.#defaultUseRichText
                              ? 'raw,markdown' : 'raw',
        });
    }

    /**
     * Update the visibility of the tips box.
     *
     * Args:
     *     show (boolean):
     *         Whether to show the tips.
     */
    #updateTipsVisibility(show: boolean) {
        this.#tipsView.$el.toggle(show);
        this.#showTips.toggle(!show);
    }
}
