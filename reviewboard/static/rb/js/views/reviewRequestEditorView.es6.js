(function() {


/**
 * Base class for review request banners.
 *
 * This will render a banner based on the data provided by subclasses,
 * and handle actions and editing of text fields.
 */
const BannerView = Backbone.View.extend({
    className: 'banner',
    title: '',
    subtitle: '',
    actions: [],
    showChangesField: true,
    describeText: '',
    fieldOptions: {},
    descriptionFieldID: 'change_description',
    descriptionFieldName: null,
    descriptionFieldHTML: '',
    descriptionFieldClasses: '',
    showSendEmail: false,
    DescriptionFieldViewType: RB.ReviewRequestFields.ChangeDescriptionFieldView,

    template: _.template(dedent`
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
          <%- sendEmailText %>
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
        `),

    /**
     * Initialize the banner.
     *
     * Args:
     *     options (object):
     *         Options for the banner.
     *
     * Option Args:
     *     reviewRequestEditorView (RB.ReviewRequestEditorView):
     *         The review request editor.
     */
    initialize(options) {
        this.reviewRequestEditorView = options.reviewRequestEditorView;
        this.reviewRequestEditor = this.reviewRequestEditorView.model;
        this.reviewRequest = this.reviewRequestEditor.get('reviewRequest');
        this.$buttons = null;
    },

    /**
     * Render the banner.
     *
     * If there's an existing banner on the page, from the generated
     * template, then this will make use of that template. Otherwise,
     * it will construct a new one.
     *
     * Returns:
     *     BannerView:
     *     This object, for chaining.
     */
    render() {
        const readOnly = RB.UserSession.instance.get('readOnly');

        if (this.$el.children().length === 0) {
            this.$el.html(this.template({
                title: this.title,
                subtitle: this.subtitle,
                actions: readOnly ? [] : this.actions,
                showChangesField: this.showChangesField && !readOnly,
                describeText: this.describeText,
                descriptionFieldID: this.descriptionFieldID,
                descriptionFieldHTML: this.descriptionFieldHTML,
                descriptionFieldClasses: this.descriptionFieldClasses,
                showSendEmail: this.showSendEmail,
                sendEmailText: gettext('Send E-Mail'),
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

        return this;
    },
});


/**
 * Base class for a banner representing a closed review request.
 *
 * This provides a button for reopening the review request. It's up
 * to subclasses to provide the other details.
 */
const ClosedBannerView = BannerView.extend({
    descriptionFieldID: 'close_description',
    descriptionFieldName: 'closeDescription',
    DescriptionFieldViewType: RB.ReviewRequestFields.CloseDescriptionFieldView,

    actions: [
        {
            id: 'btn-review-request-reopen',
            label: gettext('Reopen for Review'),
        },
    ],

    closeType: undefined,

    events: {
        'click #btn-review-request-reopen': '_onReopenClicked',
    },

    /**
     * Render the banner.
     *
     * Returns:
     *     ClosedBannerView:
     *     This object, for chaining.
     */
    render() {
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

        BannerView.prototype.render.apply(this, arguments);

        this.field.closeType = this.closeType;

        return this;
    },

    /**
     * Handle a click on "Reopen for Review".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onReopenClicked() {
        this.reviewRequest.reopen({
            error: (model, xhr) => alert(xhr.errorText),
        });

        return false;
    },
});


/**
 * A banner representing a discarded review request.
 */
const DiscardedBannerView = ClosedBannerView.extend({
    id: 'discard-banner',
    title: gettext('This change has been discarded.'),
    describeText: gettext("Describe the reason it's discarded (optional):"),
    closeType: RB.ReviewRequest.CLOSE_DISCARDED,
});


/**
 * A banner representing a submitted review request.
 */
const SubmittedBannerView = ClosedBannerView.extend({
    id: 'submitted-banner',
    title: gettext('This change has been marked as submitted.'),
    describeText: gettext('Describe the submission (optional):'),
    closeType: RB.ReviewRequest.CLOSE_SUBMITTED,
});


/**
 * A banner representing a draft of a review request.
 *
 * Depending on the public state of the review request, this will
 * show different text and a different set of buttons.
 */
const DraftBannerView = BannerView.extend({
    id: 'draft-banner',
    title: gettext('This review request is a draft.'),
    subtitle: gettext('Be sure to publish when finished.'),
    describeText: gettext('Describe your changes (optional):'),
    descriptionFieldID: 'change_description',
    descriptionFieldName: 'changeDescription',

    _newDraftTemplate: _.template(dedent`
        <div class="interdiff-link">
         <%- newDiffText %>
         <a href="<%- interdiffLink %>"><%- showChangesText %></a>
        </div>
        `),

    events: {
        'click #btn-draft-publish': '_onPublishDraftClicked',
        'click #btn-draft-discard': '_onDiscardDraftClicked',
        'click #btn-review-request-discard': '_onCloseDiscardedClicked',
    },

    /**
     * Initialize the banner.
     */
    initialize() {
        BannerView.prototype.initialize.apply(this, arguments);

        if (this.reviewRequest.get('public')) {
            this.showSendEmail = this.reviewRequestEditor.get('showSendEmail');
            this.title = gettext('This review request is a draft.');
            this.actions = [
                {
                    id: 'btn-draft-publish',
                    label: gettext('Publish Changes'),
                },
                {
                    id: 'btn-draft-discard',
                    label: gettext('Discard Draft'),
                },
            ];
        } else {
            this.showChangesField = false;
            this.actions = [
                {
                    id: 'btn-draft-publish',
                    label: gettext('Publish'),
                },
                {
                    id: 'btn-review-request-discard',
                    label: gettext('Discard Review Request'),
                },
            ];
        }
    },

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
    _onPublishDraftClicked() {
        const $sendEmail = this.$('.send-email');

        this.reviewRequestEditorView.publishDraft({
            trivial: ($sendEmail.length === 1 && !$sendEmail.is(':checked')),
        });

        return false;
    },

    /**
     * Handle a click on "Discard Draft".
     *
     * Discards the draft of the review request.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onDiscardDraftClicked() {
        this.reviewRequest.draft.destroy({
            error: xhr => alert(xhr.errorText),
        });

        return false;
    },

    /**
     * Handle a click on "Discard Review Request".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onCloseDiscardedClicked() {
        this.reviewRequest.close({
            type: RB.ReviewRequest.CLOSE_DISCARDED,
        });

        return false;
    },

    /**
     * Render the banner.
     *
     * Returns:
     *     DraftBannerView:
     *     This object, for chaining.
     */
    render() {
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

        BannerView.prototype.render.apply(this, arguments);

        const interdiffLink = draft.get('interdiffLink');

        if (interdiffLink) {
            this.$el.append(this._newDraftTemplate({
                newDiffText: gettext('This draft adds a new diff.'),
                showChangesText: gettext('Show changes'),
                interdiffLink: interdiffLink,
            }));
        }

        return this;
    },
});


/**
 * Manages the user-visible state of an editable review request.
 *
 * This owns the fields, thumbnails, banners, and general interaction
 * around editing a review request.
 */
RB.ReviewRequestEditorView = Backbone.View.extend({
    defaultFields: [
        {
            fieldID: 'branch',
        },
        {
            fieldID: 'bugs_closed',
            fieldName: 'bugsClosed',
            selector: '#field_bugs_closed',
            useEditIconOnly: true,
        },
        {
            fieldID: 'depends_on',
            fieldName: 'dependsOn',
            useEditIconOnly: true,
        },
        {
            fieldID: 'description',
            allowMarkdown: true,
        },
        {
            fieldID: 'summary',
        },
        {
            fieldID: 'submitter',
            fieldName: 'submitter',
            useEditIconOnly: true,
        },
        {
            fieldID: 'target_groups',
            fieldName: 'targetGroups',
            useEditIconOnly: true,
        },
        {
            fieldID: 'target_people',
            fieldName: 'targetPeople',
            useEditIconOnly: true,
        },
        {
            fieldID: 'testing_done',
            fieldName: 'testingDone',
            allowMarkdown: true,
        },
    ],

    events: {
        'click #archive-review-request-link': '_onArchiveClicked',
        'click #unarchive-review-request-link': '_onUnarchiveClicked',
        'click #mute-review-request-link': '_onMuteClicked',
        'click #unmute-review-request-link': '_onUnmuteClicked',
        'click #toggle-unarchived': '_onUnarchiveClicked',
        'click #toggle-archived': '_onArchiveClicked',
    },

    _archiveActionsTemplate: _.template(dedent`
        <% if (visibility === RB.ReviewRequest.VISIBILITY_VISIBLE) { %>
         <li><a id="archive-review-request-link" href="#"><%- archiveText %></a></li>
         <li><a id="mute-review-request-link" href="#"><%- muteText %></a></li>
        <% } else if (visibility === RB.ReviewRequest.VISIBILITY_ARCHIVED) { %>
         <li><a id="unarchive-review-request-link" href="#"><%- unarchiveText %></a></li>
        <% } else if (visibility === RB.ReviewRequest.VISIBILITY_MUTED) { %>
         <li><a id="unmute-review-request-link" href="#"><%- unmuteText %></a></li>
        <% } %>
        `),

    /**
     * Initialize the view.
     */
    initialize() {
        _.bindAll(this, '_checkResizeLayout', '_scheduleResizeLayout',
                  '_onCloseDiscardedClicked', '_onCloseSubmittedClicked',
                  '_onDeleteReviewRequestClicked', '_onUpdateDiffClicked',
                  '_onArchiveClicked', '_onUnarchiveClicked',
                  '_onMuteClicked', '_onUnmuteClicked', '_onUploadFileClicked');

        this._fieldViews = {};
        this._fileAttachmentThumbnailViews = [];
        this.rendered = false;

        this.draft = this.model.get('reviewRequest').draft;
        this.banner = null;
        this._$main = null;
        this._$extra = null;
        this._blockResizeLayout = false;
    },

    /**
     * Add a view for a field in the review request.
     *
     * Args:
     *     view (RB.ReviewRequestFields.BaseFieldView):
     *         The view which handles editing for the field.
     */
    addFieldView(view) {
        this._fieldViews[view.fieldID] = view;
        view.reviewRequestEditorView = this;

        this.listenTo(view, 'resize', this._scheduleResizeLayout);
        this.listenTo(view, 'fieldError', err => {
            this._$warning
                .delay(6000)
                .fadeOut(400, () => this._$warning.hide())
                .html(err.errorText)
                .show();
        });
        this.listenTo(view, 'fieldSaved', this.showBanner);

        if (this.rendered) {
            view.render();
        }
    },

    /**
     * Return the view for the field with the given ID.
     *
     * Args:
     *     fieldID (string):
     *        The ID of the field.
     *
     * Returns:
     *     RB.ReviewRequestFields.BaseFieldView:
     *     The view which handles editing for the field.
     */
    getFieldView(fieldID) {
        return this._fieldViews[fieldID];
    },

    /**
     * Render the editor.
     *
     * This will import all pre-rendered file attachment and screenshot
     * thumbnails, turning them into FileAttachment and Screenshot objects.
     *
     * Returns:
     *     RB.ReviewRequestEditorView:
     *     This object, for chaining.
     */
    render() {
        const reviewRequest = this.model.get('reviewRequest');
        const fileAttachments = this.model.get('fileAttachments');
        const draft = reviewRequest.draft;

        this._$box = this.$('.review-request');
        this._$warning = $('#review-request-warning');
        this._$screenshots = $('#screenshot-thumbnails');
        this._$attachments = $('#file-list');
        this._$attachmentsContainer = $(this._$attachments.parent()[0]);
        this._$bannersContainer = $('#review-request-banners');
        this._$main = $('#review-request-main');
        this._$extra = $('#review-request-extra');

        this.listenTo(reviewRequest, 'change:visibility',
                      this._updateArchiveVisibility);
        this._updateArchiveVisibility();

        /*
         * We need to show any banners before we render the fields, since the
         * banners can add their own fields.
         */
        this.showBanner();

        if (this.model.get('editable')) {
            RB.DnDUploader.instance.registerDropTarget(
                this._$attachmentsContainer,
                gettext('Drop to add a file attachment'),
                this._uploadFile.bind(this));
        }

        this._$attachments.find('.file-container').remove();
        fileAttachments.each(
            fileAttachment => this.buildFileAttachmentThumbnail(
                fileAttachment, fileAttachments, { noAnimation: true }));

        this._$attachmentsContainer.find('.djblets-o-spinner').remove();
        this._$attachmentsContainer.attr('aria-busy', 'false');

        this.listenTo(fileAttachments, 'add', this.buildFileAttachmentThumbnail);
        this.listenTo(fileAttachments, 'remove', model => {
            const index = this._fileAttachmentThumbnailViews.findIndex(
                view => (view.model === model));
            this._fileAttachmentThumbnailViews[index].remove();
            this._fileAttachmentThumbnailViews.splice(index, 1);
        });
        this.listenTo(fileAttachments, 'destroy', () => {
            if (fileAttachments.length === 0) {
                this._$attachmentsContainer.hide();
            }
        });

        /*
         * Import all the screenshots and file attachments rendered onto
         * the page.
         */
        _.each(this._$screenshots.find('.screenshot-container'),
               this._importScreenshotThumbnail,
               this);
        _.each($('.binary'),
               this._importFileAttachmentThumbnail,
               this);

        // Render all the field views.
        for (let fieldID in this._fieldViews) {
            if (this._fieldViews.hasOwnProperty(fieldID)) {
                this._fieldViews[fieldID].render();
            }
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

        this.rendered = true;

        return this;
    },

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
    _onBeforeUnload(evt) {
        if (this.model.get('editCount') > 0) {
            /*
             * On IE, the text must be set in evt.returnValue.
             *
             * On Firefox, it must be returned as a string.
             *
             * On Chrome, it must be returned as a string, but you
             * can't set it on evt.returnValue (it just ignores it).
             */
            const msg = gettext('You have unsaved changes that will be lost if you navigate away from this page.');
            evt = evt || window.event;

            evt.returnValue = msg;
            return msg;
        }
    },

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
            BannerClass = SubmittedBannerView;
        } else if (state === RB.ReviewRequest.CLOSE_DISCARDED) {
            BannerClass = DiscardedBannerView;
        } else if (state === RB.ReviewRequest.PENDING &&
                   this.model.get('hasDraft')) {
            BannerClass = DraftBannerView;
        } else {
            return;
        }

        let $existingBanner = this._$bannersContainer.children();

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
            this.banner.$el.appendTo(this._$bannersContainer);
        }

        this.banner.render();
    },

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
    publishDraft(options) {
        // Save all the fields if we need to.
        const fields = Object.values(this._fieldViews)
            .filter(view => view.needsSave());

        this.model.set({
            publishing: true,
            pendingSaveCount: fields.length,
        });

        if (fields.length === 0) {
            this.model.publishDraft(options);
        } else {
            fields.forEach(field => field.finishSave());
        }
    },

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
    _uploadFile(file) {
        // Create a temporary file listing.
        const fileAttachment = this.model.createFileAttachment();

        fileAttachment.set('file', file);
        fileAttachment.save();
    },

    /**
     * Set up all review request actions and listens for events.
     */
    _setupActions() {
        const $closeDiscarded = this.$('#discard-review-request-action');
        const $closeSubmitted = this.$('#submit-review-request-action');
        const $deletePermanently = this.$('#delete-review-request-action');
        const $updateDiff = this.$('#upload-diff-action');
        const $uploadFile = this.$('#upload-file-action');

        /*
         * We don't want the click event filtering from these down to the
         * parent menu, so we can't use events above.
         */
        $closeDiscarded.click(this._onCloseDiscardedClicked);
        $closeSubmitted.click(this._onCloseSubmittedClicked);
        $deletePermanently.click(this._onDeleteReviewRequestClicked);
        $updateDiff.click(this._onUpdateDiffClicked);
        $uploadFile.click(this._onUploadFileClicked);

        RB.ReviewRequestActionHook.each(hook => {
            _.each(hook.get('callbacks'),
                   (handler, selector) => this.$(selector).click(handler));
        });
    },

    /**
     * Build a thumbnail for a FileAttachment.
     *
     * The thumbnail will eb added to the page. The editor will listen
     * for events on the thumbnail to update the current edit state.
     *
     * This can be called either when dynamically adding a new file
     * attachment (through drag-and-drop or Add File), or after importing
     * from the rendered page.
     *
     * Args:
     *     fileAttachment (RB.FileAttachment):
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
     */
    buildFileAttachmentThumbnail(fileAttachment, collection, options={}) {
        const fileAttachmentComments = this.model.get('fileAttachmentComments');
        const $thumbnail = options.$el;

        const view = new RB.FileAttachmentThumbnail({
            el: $thumbnail,
            model: fileAttachment,
            comments: fileAttachmentComments[fileAttachment.id],
            renderThumbnail: ($thumbnail === undefined),
            reviewRequest: this.model.get('reviewRequest'),
            reviewRequestEditor: this.model,
            canEdit: (this.model.get('editable') === true)
        });

        view.render();

        this._fileAttachmentThumbnailViews.push(view);

        if (!$thumbnail) {
            // This is a newly added file attachment.
            const fileAttachments = this.model.get('fileAttachments');
            const index = fileAttachments.indexOf(fileAttachment);

            this._$attachmentsContainer.show();

            view.$el.insertBefore(this._$attachments.children().eq(index));

            if (!options.noAnimation) {
                view.fadeIn();
            }
        }

        this.listenTo(view, 'hoverIn', $thumbnail => {
            this._$attachments
                .find('.file')
                .not($thumbnail.find('.file')[0])
                    .addClass('faded');
        });

        this.listenTo(
            view, 'hoverOut',
            () => this._$attachments.find('.file').removeClass('faded'));

        view.on('beginEdit', () => this.model.incr('editCount'));
        view.on('endEdit', () => this.model.decr('editCount'));
        view.on('commentSaved', () => RB.DraftReviewBannerView.instance.show());
    },

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
    _importFileAttachmentThumbnail(thumbnailEl) {
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
    },

    /**
     * Import screenshots from the rendered page.
     *
     * Each screenshot already rendered will be turned into a Screenshot.
     *
     * Args:
     *     thumbnailEl (Element):
     *         The existing DOM element to import.
     */
    _importScreenshotThumbnail(thumbnailEl) {
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
    },

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
        if (this._$main.length !== 0 && !this._blockResizeLayout) {
            this._resizeLayout();
        }
    },

    /**
     * Resize the layout in response to size or position changes of fields.
     *
     * This will spread out the main text fields to cover the full height of
     * the review request box's main area. That helps keep a consistent look
     * and prevents a bunch of wasted-looking space.
     */
    _resizeLayout() {
        const $lastContent = this._$main.children('.review-request-section:last-child');
        const $lastFieldContainer = $lastContent.children('.field-container');
        const $lastField = $lastFieldContainer.children('.editable');
        const lastFieldView = this._fieldViews[$lastField.data('field-id')];
        const lastContentTop = Math.ceil($lastContent.position().top);
        const editor = lastFieldView.inlineEditorView.textEditor;
        const detailsWidth = 300; // Defined as @details-width in reviews.less
        const detailsPadding = 10;
        const $detailsBody = $('#review-request-details tbody');
        const $detailsLabels = $detailsBody.find('th:first-child');
        const $detailsValues = $detailsBody.find('span');

        this._blockResizeLayout = true;

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
        this._$main.height('auto');
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
        this._$main.height(this._$extra.offset().top -
                           this._$main.offset().top);
        const height = this._$main.height();

        if ($lastContent.outerHeight() + lastContentTop < height) {
            $lastContent.outerHeight(height - lastContentTop);

            /*
             * Get the size of the content box, and factor in the padding at
             * the bottom, to balance out position()'s calculation of the
             * padding at the top. This ensures we get a height that matches
             * the content area of the content box.
             */
            const contentHeight = $lastContent.height() -
                                  Math.ceil($lastFieldContainer.position().top);

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

        this._blockResizeLayout = false;
    },

    /**
     * Schedule a layout resize after the stack unwinds.
     *
     * This will only trigger a layout resize after the stack has unwound,
     * and only once every 100 milliseconds at most.
     */
    _scheduleResizeLayout: _.throttleLayout(
        function() { this._checkResizeLayout(); },
        { defer: true, }),

    /**
     * Handle a click on "Close -> Discarded".
     *
     * The user will be asked for confirmation before the review request is
     * discarded.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onCloseDiscardedClicked() {
        const confirmText = gettext(
            "Are you sure you want to discard this review request?");

        if (confirm(confirmText)) {
            this.model.get('reviewRequest').close({
                type: RB.ReviewRequest.CLOSE_DISCARDED,
                error: (model, xhr) => this.model.trigger(
                    'closeError', xhr.errorText),
            });
        }

        return false;
    },

    /**
     * Handle a click on "Close -> Submitted".
     *
     * If there's an unpublished draft, this will first confirm if the
     * user is sure.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onCloseSubmittedClicked() {
        /*
         * This is a non-destructive event, so don't confirm unless there's
         * a draft.
         */
        let submit = true;

        if (this.banner) {
            submit = confirm(gettext("You have an unpublished draft. If you close this review request, the draft will be discarded. Are you sure you want to close the review request?"));
        }

        if (submit) {
            this.model.get('reviewRequest').close({
                type: RB.ReviewRequest.CLOSE_SUBMITTED,
                error: (model, xhr) => this.model.trigger(
                    'closeError', xhr.errorText),
            });
        }

        return false;
    },

    /**
     * Handle a click on "Close -> Delete Permanently".
     *
     * The user will be asked for confirmation before the review request is
     * deleted.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onDeleteReviewRequestClicked() {
        const $dlg = $('<p>')
            .text(gettext('This deletion cannot be undone. All diffs and reviews will be deleted as well.'))
            .modalBox({
                title: gettext('Are you sure you want to delete this review request?'),
                buttons: [
                    $(`<input type="button" value="${gettext('Cancel')}"/>`),
                    $(`<input type="button" value="${gettext('Delete')}"/>`)
                        .click(() => {
                            this.model.get('reviewRequest').destroy({
                                buttons: $('input', $dlg.modalBox('buttons')),
                                success: () => {
                                    window.location = SITE_ROOT;
                                },
                            });
                        }),
                ]
            });

        return false;
    },

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
    },

    /**
     * Handle a click on the "Add File" button.
     *
     * This method displays a popup for attachment upload.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the action.
     */
    _onUploadFileClicked(e) {
        e.stopPropagation();
        e.preventDefault();

        const uploadDialog = new RB.UploadAttachmentView({
            reviewRequestEditor: this.model,
        });
        uploadDialog.show();
    },

    /**
     * Handle a click on "Archive -> Archive".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onArchiveClicked() {
        return this._updateArchiveState(
            RB.UserSession.instance.archivedReviewRequests,
            true,
            RB.ReviewRequest.VISIBILITY_ARCHIVED);
    },

    /**
     * Handle a click on "Archive -> Unarchive".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onUnarchiveClicked() {
        return this._updateArchiveState(
            RB.UserSession.instance.archivedReviewRequests,
            false,
            RB.ReviewRequest.VISIBILITY_VISIBLE);
    },

    /**
     * Handle a click on "Archive -> Mute".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onMuteClicked() {
        return this._updateArchiveState(
            RB.UserSession.instance.mutedReviewRequests,
            true,
            RB.ReviewRequest.VISIBILITY_MUTED);
    },

    /**
     * Handle a click on "Archive -> Unmute".
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _onUnmuteClicked() {
        return this._updateArchiveState(
            RB.UserSession.instance.mutedReviewRequests,
            false,
            RB.ReviewRequest.VISIBILITY_VISIBLE);
    },

    /**
     * Update archive/mute state.
     *
     * Args:
     *     collection (Backbone.Collection):
     *         The collection representing the user's archived or muted review
     *         requests.
     *
     *     add (boolean):
     *         True if the review request should be added to the collection
     *         (archived or muted), false if it shold be removed (unarchived or
     *         unmuted).
     *
     *     newState (number):
     *         The new state for the review request's ``visibility`` attribute.
     *
     * Returns:
     *     boolean:
     *     False, always.
     */
    _updateArchiveState(collection, add, newState) {
        const reviewRequest = this.model.get('reviewRequest');
        const options = {
            success: () => reviewRequest.set('visibility', newState),
        };

        if (add) {
            collection.addImmediately(reviewRequest, options, this);
        } else {
            collection.removeImmediately(reviewRequest, options, this);
        }

        return false;
    },

    /**
     * Update the visibility of the archive/mute menu items.
     */
    _updateArchiveVisibility() {
        const visibility = this.model.get('reviewRequest').get('visibility');

        this.$('#hide-review-request-menu').html(this._archiveActionsTemplate({
            visibility: visibility,
            archiveText: gettext('Archive'),
            muteText: gettext('Mute'),
            unarchiveText: gettext('Unarchive'),
            unmuteText: gettext('Unmute'),
        }));

        const visible = (visibility === RB.ReviewRequest.VISIBILITY_VISIBLE);

        const iconClass = (visible
                           ? 'rb-icon-archive-off'
                           : 'rb-icon-archive-on');

        const iconTitle = (visible
                           ? gettext('Archive review request')
                           : gettext('Unarchive review request'));

        const iconId = (visible
                        ? 'toggle-archived'
                        : 'toggle-unarchived');

        this.$('#hide-review-request-link')
            .html(`<span class="rb-icon ${iconClass}" id="${iconId}" title="${iconTitle}"></span>`);

        if (RB.UserSession.instance.get('readOnly')) {
            this.$('#hide-review-request-menu').hide();
        }
    },

    /**
     * Refresh the page.
     */
    _refreshPage() {
        window.location = this.model.get('reviewRequest').get('reviewURL');
    },
});


})();
