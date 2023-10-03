/**
 * View that handles editing review requests.
 */
import { BaseView, spina } from '@beanbag/spina';

import {
    EnabledFeatures,
    FileAttachment,
    ResourceCollection,
    UserSession,
} from 'reviewboard/common';
import { DnDUploader } from 'reviewboard/ui';

import { ReviewRequestEditor } from '../models/reviewRequestEditorModel';
import { FileAttachmentThumbnailView } from './fileAttachmentThumbnailView';
import {
    BaseFieldView,
    ChangeDescriptionFieldView,
    CloseDescriptionFieldView,
    TextFieldView,
} from './reviewRequestFieldViews';


declare const dedent: (string) => string;


interface BannerViewOptions {
    reviewRequestEditorView: ReviewRequestEditorView;
}


/**
 * Base class for review request banners.
 *
 * This will render a banner based on the data provided by subclasses,
 * and handle actions and editing of text fields.
 */
@spina({
    prototypeAttrs: [
        'DescriptionFieldViewType',
        'actions',
        'className',
        'describeText',
        'descriptionFieldClasses',
        'descriptionFieldHTML',
        'descriptionFieldID',
        'descriptionFieldName',
        'showChangesField',
        'subtitle',
        'template',
        'title',
    ],
})
class BannerView extends BaseView<
    undefined,
    HTMLDivElement,
    BannerViewOptions
> {
    static DescriptionFieldViewType = ChangeDescriptionFieldView;
    static actions = [];
    static className = 'banner';
    static describeText = '';
    static descriptionFieldClasses = '';
    static descriptionFieldHTML = '';
    static descriptionFieldID = 'change_description';
    static descriptionFieldName = null;
    static showChangesField = true;
    static subtitle = '';
    static template = _.template(dedent`
        <h1><%- title %></h1>
        <% if (subtitle) { %>
        <p><%- subtitle %></p>
        <% } %>
        <span class="banner-actions">
        <% _.each(actions, function(action) { %>
         <input type="button" id="<%= action.id %>"
                value="<%- action.label %>" />
        <% }); %>
        <% if (showSendEmail) { %>
         <label>
          <input type="checkbox" class="send-email" checked />
          ${gettext('Send E-Mail')}
        </label>
        <% } %>
        </span>
        <% if (showChangesField) { %>
         <p><label for="field_<%- descriptionFieldID %>"><%- describeText %></label></p>
         <pre id="field_<%- descriptionFieldID %>"
              class="field field-text-area <%- descriptionFieldClasses %>"
              data-field-id="field_<%- descriptionFieldID %>"
              ><%= descriptionFieldHTML %></pre>
        <% } %>
        `);
    static title = '';

    /**********************
     * Instance variables *
     **********************/

    /** The change description field editor, if present. */
    field: BaseFieldView;

    /** The review request editor. */
    reviewRequestEditor: ReviewRequestEditor;

    /** The review request editor view. */
    reviewRequestEditorView: ReviewRequestEditorView;

    /** The review request model. */
    reviewRequest: RB.ReviewRequest;

    /** Whether to show the "Send E-mail" checkbox. */
    showSendEmail = false;

    /** The button elements. */
    $buttons: JQuery;

    /**
     * Initialize the banner.
     *
     * Args:
     *     options (BannerViewOptions):
     *         Options for the banner.
     */
    initialize(options: BannerViewOptions) {
        this.reviewRequestEditorView = options.reviewRequestEditorView;
        this.reviewRequestEditor = this.reviewRequestEditorView.model;
        this.reviewRequest = this.reviewRequestEditor.get('reviewRequest');
        this.$buttons = null;
    }

    /**
     * Render the banner.
     *
     * If there's an existing banner on the page, from the generated
     * template, then this will make use of that template. Otherwise,
     * it will construct a new one.
     */
    onInitialRender() {
        const readOnly = UserSession.instance.get('readOnly');

        if (this.$el.children().length === 0) {
            this.$el.html(this.template({
                actions: readOnly ? [] : this.actions,
                describeText: this.describeText,
                descriptionFieldClasses: this.descriptionFieldClasses,
                descriptionFieldHTML: this.descriptionFieldHTML,
                descriptionFieldID: this.descriptionFieldID,
                showChangesField: this.showChangesField && !readOnly,
                showSendEmail: this.showSendEmail,
                subtitle: this.subtitle,
                title: this.title,
            }));
        }

        if (this.DescriptionFieldViewType) {
            this.field = new this.DescriptionFieldViewType({
                el: this.$(`#field_${this.descriptionFieldID}`),
                fieldID: this.descriptionFieldID,
                model: this.reviewRequestEditor,
            });

            this.reviewRequestEditorView.addFieldView(this.field);
        }

        this.$buttons = this.$('input');

        this.reviewRequestEditor.on(
            'saving destroying',
            () => this.$buttons.prop('disabled', true));

        this.reviewRequestEditor.on(
            'saved saveFailed destroyed',
            () => this.$buttons.prop('disabled', false));
    }
}


/**
 * Base class for a banner representing a closed review request.
 *
 * This provides a button for reopening the review request. It's up
 * to subclasses to provide the other details.
 */
@spina({
    prototypeAttrs: [
        'DescriptionFieldViewType',
        'actions',
        'closeType',
        'descriptionFieldClasses',
        'descriptionFieldID',
        'descriptionFieldName',
        'events',
    ],
})
class ClosedBannerView extends BannerView {
    static DescriptionFieldViewType = CloseDescriptionFieldView;
    static actions = [
        {
            id: 'btn-review-request-reopen',
            label: _`Reopen for Review`,
        },
    ];
    static closeType = undefined;
    static descriptionFieldID = 'close_description';
    static descriptionFieldName = 'closeDescription';
    static events = {
        'click #btn-review-request-reopen': '_onReopenClicked',
    };

    /**
     * Render the banner.
     */
    onInitialRender() {
        const descriptionFieldClasses = [];

        if (this.reviewRequestEditor.get('statusMutableByUser')) {
            descriptionFieldClasses.push('editable');
        }

        if (this.reviewRequest.get('closeDescriptionRichText')) {
            descriptionFieldClasses.push('rich-text');
        }

        this.descriptionFieldClasses = descriptionFieldClasses.join(' ');
        this.descriptionFieldHTML =
            this.reviewRequestEditor.get('closeDescriptionRenderedText');

        super.onInitialRender();

        this.field.closeType = this.closeType;
    }

    /**
     * Handle a click on "Reopen for Review".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onReopenClicked() {
        this.reviewRequest.reopen()
            .catch(err => alert(err.message));

        return false;
    }
}


/**
 * A banner representing a discarded review request.
 */
@spina({
    prototypeAttrs: [
        'closeType',
        'describeText',
        'id',
        'title',
    ],
})
class DiscardedBannerView extends ClosedBannerView {
    static closeType = RB.ReviewRequest.CLOSE_DISCARDED;
    static describeText = _`Describe the reason it's discarded (optional):`;
    static id = 'discard-banner';
    static title = _`This change has been discarded.`;
}


/**
 * A banner representing a submitted review request.
 */
@spina({
    prototypeAttrs: [
        'closeType',
        'describeText',
        'id',
        'title',
    ],
})
class CompletedBannerView extends ClosedBannerView {
    static closeType = RB.ReviewRequest.CLOSE_SUBMITTED;
    static describeText = _`Describe the completed change (optional):`;
    static id = 'submitted-banner';
    static title = _`This change has been marked as completed.`;
}


/**
 * A banner representing a draft of a review request.
 *
 * Depending on the public state of the review request, this will
 * show different text and a different set of buttons.
 */
@spina({
    prototypeAttrs: [
        'describeText',
        'descriptionFieldID',
        'descriptionFieldName',
        'events',
        'id',
        'subtitle',
        'title',
        '_newDraftTemplate',
    ],
})
class DraftBannerView extends BannerView {
    static describeText = _`Describe your changes (optional):`;
    static descriptionFieldID = 'change_description';
    static descriptionFieldName = 'changeDescription';
    static events = {
        'click #btn-draft-discard': '_onDiscardDraftClicked',
        'click #btn-draft-publish': '_onPublishDraftClicked',
        'click #btn-review-request-discard': '_onCloseDiscardedClicked',
    };
    static id = 'draft-banner';
    static subtitle = _`Be sure to publish when finished.`;
    static title = _`This review request is a draft.`;
    static _newDraftTemplate = _.template(dedent`
        <div class="interdiff-link">
         <%- newDiffText %>
         <a href="<%- interdiffLink %>"><%- showChangesText %></a>
        </div>
        `);

    /**
     * Initialize the banner.
     *
     * Args:
     *     options (BannerViewOptions):
     *         Options for the view.
     */
    initialize(options: BannerViewOptions) {
        super.initialize(options);

        if (this.reviewRequest.get('public')) {
            this.showSendEmail = this.reviewRequestEditor.get('showSendEmail');
            this.title = _`This review request is a draft.`;
            this.actions = [
                {
                    id: 'btn-draft-publish',
                    label: _`Publish Changes`,
                },
                {
                    id: 'btn-draft-discard',
                    label: _`Discard Draft`,
                },
            ];
        } else {
            this.showChangesField = false;
            this.actions = [
                {
                    id: 'btn-draft-publish',
                    label: _`Publish`,
                },
                {
                    id: 'btn-review-request-discard',
                    label: _`Discard Review Request`,
                },
            ];
        }
    }

    /**
     * Handle a click on "Publish Changes".
     *
     * Begins publishing the review request. If there are any field editors
     * still open, they'll be saved first.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    async _onPublishDraftClicked() {
        const $sendEmail = this.$('.send-email');

        await this.reviewRequestEditorView.publishDraft({
            trivial: ($sendEmail.length === 1 && !$sendEmail.is(':checked')),
        });

        return false;
    }

    /**
     * Handle a click on "Discard Draft".
     *
     * Discards the draft of the review request.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    async _onDiscardDraftClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        try {
            await this.reviewRequest.draft.destroy();
        } catch (err) {
            alert(err.message);
        }
    }

    /**
     * Handle a click on "Discard Review Request".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onCloseDiscardedClicked() {
        this.reviewRequest
            .close({
                type: RB.ReviewRequest.CLOSE_DISCARDED,
            })
            .catch(err => alert(err.message));

        return false;
    }

    /**
     * Render the banner.
     */
    onInitialRender() {
        const descriptionFieldClasses = [];

        if (this.reviewRequestEditor.get('mutableByUser')) {
            descriptionFieldClasses.push('editable');
        }

        const draft = this.reviewRequest.draft;

        if (draft.get('changeDescriptionRichText')) {
            descriptionFieldClasses.push('rich-text');
        }

        this.descriptionFieldClasses = descriptionFieldClasses.join(' ');
        this.descriptionFieldHTML =
            this.reviewRequestEditor.get('changeDescriptionRenderedText');

        super.onInitialRender();

        const interdiffLink = draft.get('interdiffLink');

        if (interdiffLink) {
            this.$el.append(this._newDraftTemplate({
                interdiffLink: interdiffLink,
                newDiffText: _`This draft adds a new diff.`,
                showChangesText: _`Show changes`,
            }));
        }
    }
}


/**
 * Manages the user-visible state of an editable review request.
 *
 * This owns the fields, thumbnails, banners, and general interaction
 * around editing a review request.
 */
@spina
export class ReviewRequestEditorView extends BaseView<ReviewRequestEditor> {
    /**********************
     * Instance variables *
     **********************/

    /** The element containing the file attachment thumbnails. */
    #$attachments: JQuery = null;

    /** The parent of the file attachments element. */
    #$attachmentsContainer: JQuery = null;

    /** The container where banners are added. */
    #$bannersContainer: JQuery = null;

    /** The main fields of the review request. */
    #$main: JQuery = null;

    /** The extra fields of the review request. */
    #$extra: JQuery = null;

    /** The warning message box. */
    #$warning: JQuery = null;

    /** Whether to block layout change updates. */
    #blockResizeLayout = false;

    /** A mapping from field ID to field view instance. */
    #fieldViews: {
        [key: string]: BaseFieldView;
    } = {};

    /** The views for all of the file attachment thumbnails. */
    #fileAttachmentThumbnailViews: FileAttachmentThumbnailView[] = [];

    /** The views for all of the review reply editors. */
    #reviewReplyEditorViews: RB.ReviewReplyEditorView[] = [];

    /**
     * The active banner, if available.
     *
     * This can be either a close banner or the legacy draft banner. The
     * unified review banner is separate and manages its own lifecycle.
     */
    banner: BannerView = null;

    /** The review request draft. */
    draft: RB.ReviewRequestDraft;

    /**
     * Initialize the view.
     */
    initialize() {
        _.bindAll(this, '_checkResizeLayout', '_scheduleResizeLayout');

        this.draft = this.model.get('reviewRequest').draft;
    }

    /**
     * Add a view for a field in the review request.
     *
     * Args:
     *     view (BaseFieldView):
     *         The view which handles editing for the field.
     */
    addFieldView(view: BaseFieldView) {
        this.#fieldViews[view.fieldID] = view;
        view.reviewRequestEditorView = this;

        this.listenTo(view, 'resize', this._scheduleResizeLayout);
        this.listenTo(view, 'fieldError', err => {
            this.#$warning
                .delay(6000)
                .fadeOut(400, () => this.#$warning.hide())
                .html(err.errorText)
                .show();
        });

        this.listenTo(view, 'fieldSaved', this.showBanner);

        if (this.rendered) {
            view.render();
        }
    }

    /**
     * Return the view for the field with the given ID.
     *
     * Args:
     *     fieldID (string):
     *        The ID of the field.
     *
     * Returns:
     *     BaseFieldView:
     *     The view which handles editing for the field.
     */
    getFieldView(
        fieldID: string,
    ): BaseFieldView {
        return this.#fieldViews[fieldID];
    }

    /**
     * Render the editor.
     *
     * This will import all pre-rendered file attachment and screenshot
     * thumbnails, turning them into FileAttachment and Screenshot objects.
     */
    onInitialRender() {
        const reviewRequest = this.model.get('reviewRequest');
        const fileAttachments = this.model.get('fileAttachments');
        const draft = reviewRequest.draft;

        this.#$warning = $('#review-request-warning');
        const $screenshots = $('#screenshot-thumbnails');
        this.#$attachments = $('#file-list');
        this.#$attachmentsContainer = $(this.#$attachments.parent()[0]);
        this.#$bannersContainer = $('#review-request-banners');
        this.#$main = $('#review-request-main');
        this.#$extra = $('#review-request-extra');

        /*
         * We need to show any banners before we render the fields, since the
         * banners can add their own fields.
         */
        this.showBanner();

        if (this.model.get('editable')) {
            DnDUploader.instance.registerDropTarget(
                this.#$attachmentsContainer,
                _`Drop to add a file attachment`,
                this._uploadFile.bind(this));
        }

        this.#$attachments.find('.file-container').remove();
        fileAttachments.each(
            fileAttachment => this.buildFileAttachmentThumbnail(
                fileAttachment, fileAttachments, { noAnimation: true }));

        this.#$attachmentsContainer.find('.djblets-o-spinner').remove();
        this.#$attachmentsContainer.attr('aria-busy', 'false');

        this.listenTo(fileAttachments, 'add',
                      this.buildFileAttachmentThumbnail);
        this.listenTo(fileAttachments, 'remove', this._removeThumbnail);
        this.listenTo(fileAttachments, 'destroy', () => {
            if (fileAttachments.length === 0) {
                this.#$attachmentsContainer.hide();
            }
        });
        this.listenTo(this.model, 'replaceAttachment', this._removeThumbnail);

        /*
         * Import all the screenshots and file attachments rendered onto
         * the page.
         */
        _.each($screenshots.find('.screenshot-container'),
               this._importScreenshotThumbnail,
               this);
        _.each($('.binary'),
               this._importFileAttachmentThumbnail,
               this);

        // Render all the field views.
        for (const fieldView of Object.values(this.#fieldViews)) {
            fieldView.render();
        }

        /*
         * Update the layout constraints any time these properties
         * change. Also, right away.
         */
        $(window).resize(this._scheduleResizeLayout);
        this.listenTo(this.model, 'change:editCount', this._checkResizeLayout);
        this._checkResizeLayout();

        this._setupActions();

        this.model.on('publishError', errorText => {
            alert(errorText);

            this.$('#btn-draft-publish').enable();
            this.$('#btn-draft-discard').enable();
        });

        this.model.on('closeError', errorText => alert(errorText));
        this.model.on('saved', this.showBanner, this);
        this.model.on('published', this._refreshPage, this);
        reviewRequest.on('closed reopened', this._refreshPage, this);

        draft.on('destroyed', this._refreshPage, this);

        window.onbeforeunload = this._onBeforeUnload.bind(this);
    }

    /**
     * Warn the user if they try to navigate away with unsaved comments.
     *
     * Args:
     *     evt (Event):
     *         The event that triggered the handler.
     *
     * Returns:
     *     string:
     *     The warning message.
     *
     */
    _onBeforeUnload(
        evt: BeforeUnloadEvent,
    ): string {
        if (this.model.get('editCount') > 0) {
            /*
             * On IE, the text must be set in evt.returnValue.
             *
             * On Firefox, it must be returned as a string.
             *
             * On Chrome, it must be returned as a string, but you
             * can't set it on evt.returnValue (it just ignores it).
             */
            const msg = _`
                You have unsaved changes that will be lost if you navigate
                away from this page.
            `;
            evt = evt || window.event;
            evt.returnValue = msg;

            return msg;
        }
    }

    /**
     * Show a banner for the given state of the review request.
     */
    showBanner() {
        if (this.banner) {
            return;
        }

        const reviewRequest = this.model.get('reviewRequest');
        const state = reviewRequest.get('state');
        let BannerClass;

        if (state === RB.ReviewRequest.CLOSE_SUBMITTED) {
            BannerClass = CompletedBannerView;
        } else if (state === RB.ReviewRequest.CLOSE_DISCARDED) {
            BannerClass = DiscardedBannerView;
        } else if (state === RB.ReviewRequest.PENDING &&
                   this.model.get('hasDraft') &&
                   !EnabledFeatures.unifiedBanner) {
            BannerClass = DraftBannerView;
        } else {
            return;
        }

        let $existingBanner = this.#$bannersContainer.children();

        console.assert(BannerClass);
        console.assert($existingBanner.length <= 1);

        if ($existingBanner.length === 0) {
            $existingBanner = undefined;
        }

        this.banner = new BannerClass({
            el: $existingBanner,
            reviewRequestEditorView: this,
        });

        if ($existingBanner) {
            $existingBanner.show();
        } else {
            this.banner.$el.appendTo(this.#$bannersContainer);
        }

        this.banner.render();
    }

    /**
     * Add a review reply editor view.
     *
     * These views are constructed by the individual review views. We keep
     * track of them here so that we can save any open editors when performing
     * publish operations.
     *
     * Args:
     *     reviewReplyEditorView (RB.ReviewRequestPage.ReviewReplyEditorView):
     *          The review reply editor view.
     */
    addReviewReplyEditorView(
        reviewReplyEditorView: RB.ReviewRequestPage.ReviewReplyEditorView,
    ) {
        this.#reviewReplyEditorViews.push(reviewReplyEditorView);
    }

    /**
     * Handle a click on the "Publish Draft" button.
     *
     * Begins publishing the review request. If there are any field editors
     * still open, they'll be saved first.
     *
     * Args:
     *     options (object):
     *         Options for the publish operation.
     */
    async publishDraft(options) {
        this.model.set({
            publishing: true,
        });

        await this.saveOpenEditors();
        await this.model.publishDraft(options);
    }

    /**
     * Finish saving all open editors.
     */
    async saveOpenEditors() {
        await Promise.all(
            Object.values(this.#fieldViews)
                .filter(field => field.needsSave())
                .map(field => field.finishSave()));

        await Promise.all(
            this.#reviewReplyEditorViews
                .filter(view => view.needsSave())
                .map(field => field.save()));
    }

    /**
     * Upload a dropped file as a file attachment.
     *
     * A temporary file attachment placeholder will appear while the
     * file attachment uploads. After the upload has finished, it will
     * be replaced with the thumbnail depicting the file attachment.
     *
     * Args:
     *     file (File):
     *         The file to upload.
     */
    _uploadFile(file: File) {
        // Create a temporary file listing.
        const fileAttachment = this.model.createFileAttachment();

        fileAttachment.set('file', file);
        fileAttachment.save();
    }

    /**
     * Set up all review request actions and listens for events.
     */
    _setupActions() {
        RB.ReviewRequestActionHook.each(hook => {
            _.each(hook.get('callbacks'),
                   (handler, selector) => this.$(selector).click(handler));
        });
    }

    /**
     * Build a thumbnail for a FileAttachment.
     *
     * The thumbnail will be added to the page. The editor will listen
     * for events on the thumbnail to update the current edit state.
     *
     * This can be called either when dynamically adding a new file
     * attachment (through drag-and-drop or Add File), or after importing
     * from the rendered page.
     *
     * Args:
     *     fileAttachment (FileAttachment):
     *         The file attachment.
     *
     *     collection (Backbone.Collection):
     *         The collection of all file attachments.
     *
     *     options (object):
     *         Options.
     *
     * Option Args:
     *     $el (jQuery):
     *         The thumbnail element, if it already exists in the DOM.
     *
     *     noAnimation (boolean):
     *         Whether to disable animation.
     */
    buildFileAttachmentThumbnail(
        fileAttachment: FileAttachment,
        collection: ResourceCollection<FileAttachment>,
        options: {
            $el?: JQuery;
            noAnimation?: boolean;
        } = {},
    ) {
        const fileAttachmentComments =
            this.model.get('fileAttachmentComments');
        const $thumbnail = options.$el;

        const view = new FileAttachmentThumbnailView({
            canEdit: (this.model.get('editable') === true),
            comments: fileAttachmentComments[fileAttachment.id],
            el: $thumbnail,
            model: fileAttachment,
            renderThumbnail: ($thumbnail === undefined),
            reviewRequest: this.model.get('reviewRequest'),
            reviewRequestEditor: this.model,
        });

        view.render();

        this.#fileAttachmentThumbnailViews.push(view);

        if (!$thumbnail) {
            // This is a newly added file attachment.
            const fileAttachments = this.model.get('fileAttachments');
            const index = fileAttachments.indexOf(fileAttachment);

            this.#$attachmentsContainer.show();

            view.$el.insertBefore(this.#$attachments.children().eq(index));

            if (!options.noAnimation) {
                view.fadeIn();
            }
        }

        this.listenTo(view, 'hoverIn', $thumbnail => {
            this.#$attachments
                .find('.file')
                .not($thumbnail.find('.file')[0])
                    .addClass('faded');
        });

        this.listenTo(
            view, 'hoverOut',
            () => this.#$attachments.find('.file').removeClass('faded'));

        view.on('beginEdit', () => this.model.incr('editCount'));
        view.on('endEdit', () => this.model.decr('editCount'));

        if (!EnabledFeatures.unifiedBanner) {
            view.on('commentSaved',
                    () => RB.DraftReviewBannerView.instance.show());
        }
    }

    /**
     * Import file attachments from the rendered page.
     *
     * Each file attachment already rendered will be turned into a
     * FileAttachment, and a new thumbnail will be built for it.
     *
     * Args:
     *     thumbnailEl (Element):
     *         The existing DOM element to import.
     */
    _importFileAttachmentThumbnail(thumbnailEl: HTMLElement) {
        const $thumbnail = $(thumbnailEl);
        const id = $thumbnail.data('file-id');
        const $caption = $thumbnail.find('.file-caption .edit');
        const reviewRequest = this.model.get('reviewRequest');
        const fileAttachment = reviewRequest.draft.createFileAttachment({
            id: id,
        });

        if (!$caption.hasClass('empty-caption')) {
            fileAttachment.set('caption', $caption.text());
        }

        this.model.get('fileAttachments').add(fileAttachment, {
            $el: $thumbnail,
        });
    }

    /**
     * Import screenshots from the rendered page.
     *
     * Each screenshot already rendered will be turned into a Screenshot.
     *
     * Args:
     *     thumbnailEl (Element):
     *         The existing DOM element to import.
     */
    _importScreenshotThumbnail(thumbnailEl: HTMLElement) {
        const $thumbnail = $(thumbnailEl);
        const id = $thumbnail.data('screenshot-id');
        const reviewRequest = this.model.get('reviewRequest');
        const screenshot = reviewRequest.createScreenshot(id);
        const view = new RB.ScreenshotThumbnail({
            el: $thumbnail,
            model: screenshot,
        });

        view.render();

        this.model.get('screenshots').add(screenshot);

        view.on('beginEdit', () => this.model.incr('editCount'));
        view.on('endEdit', () => this.model.decr('editCount'));
    }

    /**
     * Conditionally resize the layout.
     *
     * This is a wrapper for _resizeLayout that verifies that there's actually
     * a layout to resize.
     */
    _checkResizeLayout() {
        /*
         * Not every page that uses this has a #review-request-main element
         * (for instance, review UIs want to have the draft banners but not
         * the review request box). In this case, just skip all of this.
         */
        if (this.#$main.length !== 0 && !this.#blockResizeLayout) {
            this._resizeLayout();
        }
    }

    /**
     * Resize the layout in response to size or position changes of fields.
     *
     * This will spread out the main text fields to cover the full height of
     * the review request box's main area. That helps keep a consistent look
     * and prevents a bunch of wasted-looking space.
     */
    _resizeLayout() {
        const $lastContent = this.#$main
            .children('.rb-c-review-request-fieldset')
            .children('.review-request-section:last-child');
        const $lastFieldContainer =
            $lastContent.find('.rb-c-review-request-field__value');
        const $lastField = $lastFieldContainer.children('.editable');
        const lastFieldView =
            this.#fieldViews[$lastField.data('field-id')] as TextFieldView;
        const lastContentTop = Math.ceil($lastContent.position().top);
        const editor = lastFieldView.inlineEditorView.textEditor;
        const detailsWidth = 300; // Defined as @details-width in reviews.less
        const detailsPadding = 10;
        const $detailsBody =
            $('#review-request-details .rb-c-review-request-fieldset__fields');
        const $detailsLabels = $detailsBody
            .find('.rb-c-review-request-field__label').eq(0);
        const $detailsValues = $detailsBody
            .find('.rb-c-review-request-field__value');

        this.#blockResizeLayout = true;

        /*
         * Make sure that the details fields wrap correctly, even if they don't
         * have wrappable characters (this combines with the white-space:
         * word-wrap: break-word style). This computation makes things handle
         * potentially unknown field labels correctly.
         */
        $detailsValues.css('max-width', (detailsWidth -
                                         $detailsLabels.outerWidth() -
                                         detailsPadding * 3) + 'px');

        /*
         * Reset all the heights so we can do calculations based on their
         * native sizes.
         */
        this.#$main.height('auto');
        $lastContent.height('auto');
        $lastField.height('auto');

        if (editor) {
            editor.setSize(null, 'auto');
        }

        /*
         * Set the review request box's main height to take up the full
         * amount of spaces between its top and the top of the "extra"
         * pane (where the issue summary table and stuff live).
         */
        this.#$main.height(Math.ceil(this.#$extra.offset().top -
                                     this.#$main.offset().top));
        const height = this.#$main.height();

        if ($lastContent.outerHeight() + lastContentTop < height) {
            $lastContent.outerHeight(height - lastContentTop);

            /*
             * Get the size of the content box, and factor in the padding at
             * the bottom, to balance out position()'s calculation of the
             * padding at the top. This ensures we get a height that matches
             * the content area of the content box.
             */
            const contentHeight = (
                $lastContent.height() -
                Math.ceil($lastFieldContainer.position().top));

            /*
             * Set the height of the editor or the editable field placeholder,
             * depending on whether we're in edit mode. There's no need to do
             * both, since this logic will be called again when the state
             * changes.
             */
            if (lastFieldView.inlineEditorView.editing() && editor) {
                editor.setSize(
                    null,
                    contentHeight -
                    lastFieldView.inlineEditorView.$buttons.height());
            } else {
                /*
                 * It's possible to squish the editable element if we force
                 * a size, so make sure it's always at least the natural
                 * height.
                 */
                const newEditableHeight = contentHeight +
                                          $lastField.getExtents('m', 'tb');

                if (newEditableHeight > $lastField.outerHeight()) {
                    $lastField.outerHeight(newEditableHeight);
                }
            }
        }

        this.#blockResizeLayout = false;
    }

    /**
     * Schedule a layout resize after the stack unwinds.
     *
     * This will only trigger a layout resize after the stack has unwound,
     * and only once every 100 milliseconds at most.
     */
    _scheduleResizeLayout = _.throttleLayout(
        () => this._checkResizeLayout(),
        { defer: true });

    /**
     * Handle a click on "Update -> Update Diff".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onUpdateDiffClicked() {
        const reviewRequest = this.model.get('reviewRequest');
        const updateDiffView = new RB.UpdateDiffView({
            model: new RB.UploadDiffModel({
                changeNumber: reviewRequest.get('commitID'),
                repository: reviewRequest.get('repository'),
                reviewRequest: reviewRequest,
            }),
        });

        updateDiffView.render();

        return false;
    }

    /**
     * Refresh the page.
     */
    _refreshPage() {
        RB.navigateTo(this.model.get('reviewRequest').get('reviewURL'));
    }

    /**
     * Remove a file attachment thumbnail.
     *
     * Version Added:
     *     6.0
     *
     * Args:
     *     attachmentModel (FileAttachment):
     *         The model of the file attachment to remove.
     */
    _removeThumbnail(attachmentModel: FileAttachment) {
        const thumbnailViews = this.#fileAttachmentThumbnailViews;
        const index = thumbnailViews.findIndex(
            view => (view.model === attachmentModel));
        thumbnailViews[index].remove();
        thumbnailViews.splice(index, 1);
    }
}
