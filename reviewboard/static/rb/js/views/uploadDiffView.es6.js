/**
 * An abstract view for uploading diffs.
 *
 * This is extended by the PreCommitView (for creating new review requests)
 * and UpdateDiffView (for updating the diff on existing review requests).
 */
RB.UploadDiffView = Backbone.View.extend({
    events: {
        'dragenter .dnd': '_onDragEnter',
        'dragover .dnd': '_onDragOver',
        'dragleave .dnd': '_onDragLeave',
        'drop .dnd': '_onDrop',
        'submit #basedir-form': '_onBasedirSubmit',
        'submit #changenum-form': '_onChangenumSubmit',
        'click .startover': '_onStartOverClicked',
        'click #select-diff-file': '_onSelectFileClicked',
        'click #select-parent-diff-file': '_onSelectFileClicked',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        this.listenTo(this.model, 'change:state', this._onStateChanged);
        this.listenTo(this.model, 'change:error', this._onErrorChanged);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.UploadDiffView:
     *     This object, for chaining.
     */
    render() {
        let selectDiffText;
        let selectParentDiffText;

        if (this._canDragDrop()) {
            selectDiffText = gettext('<input type="button" id="select-diff-file" value="Select"> or drag and drop a diff file to begin');
            selectParentDiffText = gettext('<input type="button" id="select-parent-diff-file" value="Select"> or drag and drop a parent diff file if you have one');
        } else {
            selectDiffText = gettext('<input type="button" id="select-diff-file" value="Select"> a file to begin');
            selectParentDiffText = gettext('<input type="button" id="select-parent-diff-file" value="Select"> a parent diff file if you have one');
        }

        this.$el.html(this.template({
            pendingChangeHeader: gettext('Create from a local change'),
            tipHeader: gettext('Tip:'),
            tip: gettext('Use <tt>rbt post</tt> from <a href="https://www.reviewboard.org/downloads/rbtools/">RBTools</a> to more easily create and update review requests.'),
            selectDiff: selectDiffText,
            selectParentDiff: selectParentDiffText,
            baseDir: gettext('What is the base directory for this diff?'),
            changeNum: gettext('What is the change number for this diff?'),
            startOver: gettext('Start Over'),
            ok: gettext('OK'),
        }));

        this._$fileInput = $('<input type="file">')
            .hide()
            .appendTo(this.$el)
            .change(() => this.model.handleFiles(this._$fileInput.get(0).files));
        this._$diffRevisionError = this.$('#parent-diff-error-contents');
        this._$error = this.$('#error-indicator')
            .hide();
        this._$errorContents = this.$('#error-contents');
        this._$processingDiff = this.$('#processing-diff')
            .hide();
        this._$promptForBasedir = this.$('#prompt-for-basedir')
            .hide();
        this._$promptForChangeNumber = this.$('#prompt-for-change-number')
            .hide();
        this._$promptForDiff = this.$('#prompt-for-diff')
            .hide();
        this._$promptForParentDiff = this.$('#prompt-for-parent-diff')
            .hide();
        this._$uploading = this.$('#uploading-diffs')
            .hide();

        this._onStateChanged(this.model, this.model.get('state'));

        return this;
    },

    /**
     * Return whether drag-and-drop is supported on this browser.
     *
     * We check if the DOM has the appropriate support for file drag-and-drop,
     * which will give us the right answer on most browsers. We also need to
     * check iOS specifically, as Safari lies about the support.
     *
     * Returns:
     *     boolean:
     *     Whether the user's browser supports drag-and-drop of files.
     */
    _canDragDrop() {
        return ('draggable' in this.el ||
                ('ondragstart' in this.el && 'ondrop' in this.el)) &&
               !navigator.userAgent.match('iPhone OS') &&
               !navigator.userAgent.match('iPad');
    },

    /**
     * Callback for when the model's error attribute changes.
     *
     * Updates the text and position of error indicators in the various pages.
     *
     * Args:
     *     model (RB.UploadDiffModel):
     *         The model which handles uploading the diff.
     *
     *     error (string):
     *         The text of the error.
     */
    _onErrorChanged(model, error) {
        const errorHTML = `<div class="rb-icon rb-icon-warning"></div> ${error}`;

        this._$errorContents.html(errorHTML);
        this._$diffRevisionError.html(errorHTML);

        const innerHeight = this._$errorContents.height();
        const outerHeight = this._$error.height();

        this._$errorContents.css({
            top: Math.floor((outerHeight - innerHeight) / 2) + 'px',
        });
    },

    /**
     * Callback for when the model's state attribute changes.
     *
     * Sets the corresponding element visible and all others invisible.
     *
     * Args:
     *     model (RB.UploadDiffModel):
     *         The model which handles uploading the diff.
     *
     *     state (number):
     *         The current state of the upload process.
     */
    _onStateChanged(model, state) {
        this._$promptForDiff.setVisible(
            state === this.model.State.PROMPT_FOR_DIFF);
        this._$promptForParentDiff.setVisible(
            state === this.model.State.PROMPT_FOR_PARENT_DIFF);
        this._$promptForBasedir.setVisible(
            state === this.model.State.PROMPT_FOR_BASEDIR);
        this._$processingDiff.setVisible(
            state === this.model.State.PROCESSING_DIFF);
        this._$promptForChangeNumber.setVisible(
            state === this.model.State.PROMPT_FOR_CHANGE_NUMBER);
        this._$uploading.setVisible(state === this.model.State.UPLOADING);
        this._$error.setVisible(state === this.model.State.ERROR);
    },

    /**
     * Event handler for a dragenter event.
     *
     * Args:
     *     event (Event):
     *         The dragenter event.
     */
    _onDragEnter(event) {
        event.stopPropagation();
        event.preventDefault();

        this.$('.dnd').addClass('drag-hover');
    },

    /**
     * Event handler for a dragover event.
     *
     * Args:
     *     event (Event):
     *         The dragover event.
     */
    _onDragOver(event) {
        event.stopPropagation();
        event.preventDefault();

        const dt = event.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = 'copy';
        }
    },

    /**
     * Event handler for a dragleave event.
     *
     * Args:
     *     event (Event):
     *         The dragleave event.
     */
    _onDragLeave(event) {
        event.stopPropagation();
        event.preventDefault();

        this.$('.dnd').removeClass('drag-hover');

        const dt = event.originalEvent.dataTransfer;

        if (dt) {
            dt.dropEffect = "none";
        }
    },

    /**
     * Event handler for a drop event.
     *
     * Args:
     *     event (Event):
     *         The drop event.
     */
    _onDrop(event) {
        event.stopPropagation();
        event.preventDefault();

        const  dt = event.originalEvent.dataTransfer;
        const files = dt && dt.files;

        if (files) {
            this.model.handleFiles(files);
        }
    },

    /**
     * Handle when the user inputs a base directory.
     *
     * Args:
     *     event (Event):
     *         The form submit event.
     */
    _onBasedirSubmit(event) {
        event.stopPropagation();
        event.preventDefault();

        const basedir = this.$('#basedir-input').val();

        if (basedir) {
            this.model.set('basedir', basedir);
        }
    },

    /**
     * Handle when the user inputs a change number.
     */
    _onChangenumSubmit() {
        const changenum = this.$('#changenum-input').val();

        if (changenum) {
            this.model.set('changeNumber', changenum);
        }
    },

    /**
     * Callback when "start over" is clicked.
     */
    _onStartOverClicked() {
        const $input = this._$fileInput.clone(true);

        this._$fileInput.replaceWith($input);
        this._$fileInput = $input;

        this.model.startOver();
    },

    /**
     * Callback when "Select [diff file]" is clicked.
     */
    _onSelectFileClicked() {
        this._$fileInput.click();
    },
});
