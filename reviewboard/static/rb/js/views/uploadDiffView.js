/*
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
        'click #select-parent-diff-file': '_onSelectFileClicked'
    },

    /*
     * Initialize the view.
     */
    initialize: function() {
        this.listenTo(this.model, 'change:state', this._onStateChanged);
        this.listenTo(this.model, 'change:error', this._onErrorChanged);
    },

    /*
     * Render the view.
     */
    render: function() {
        var self = this,
            selectDiffText;

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
            ok: gettext('OK')
        }));

        this._$fileInput = $('<input type="file" />')
            .hide()
            .appendTo(this.$el)
            .change(function() {
                self.model.handleFiles(self._$fileInput.get(0).files);
            });
        this._$diffRevisionError = this.$('#parent-diff-error-contents');
        this._$error = this.$('#error-indicator');
        this._$errorContents = this.$('#error-contents');
        this._$processingDiff = this.$('#processing-diff');
        this._$promptForBasedir = this.$('#prompt-for-basedir');
        this._$promptForChangeNumber = this.$('#prompt-for-change-number');
        this._$promptForDiff = this.$('#prompt-for-diff');
        this._$promptForParentDiff = this.$('#prompt-for-parent-diff');
        this._$uploading = this.$('#uploading-diffs');

        this._onStateChanged(this.model, this.model.get('state'));

        return this;
    },

    /*
     * Return whether drag-and-drop is supported on this browser.
     *
     * We check if the DOM has the appropriate support for file drag-and-drop,
     * which will give us the right answer on most browsers. We also need to
     * check iOS specifically, as Safari lies about the support.
     */
    _canDragDrop: function() {
        return ('draggable' in this.el ||
                ('ondragstart' in this.el && 'ondrop' in this.el)) &&
               !navigator.userAgent.match('iPhone OS') &&
               !navigator.userAgent.match('iPad');
    },

    /*
     * Callback for when the model's error attribute changes.
     *
     * Updates the text and position of error indicators in the various pages.
     */
    _onErrorChanged: function(model, error) {
        var errorHTML = '<div class="rb-icon rb-icon-warning"></div>' + error,
            innerHeight,
            outerHeight;

        this._$errorContents.html(errorHTML);
        this._$diffRevisionError.html(errorHTML);

        innerHeight = this._$errorContents.height();
        outerHeight = this._$error.height();

        this._$errorContents.css({
            top: Math.floor((outerHeight - innerHeight) / 2) + 'px'
        });
    },

    /*
     * Callback for when the model's state attribute changes.
     *
     * Sets the corresponding element visible and all others invisible.
     */
    _onStateChanged: function(model, state) {
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

    /*
     * Event handler for a dragenter event.
     */
    _onDragEnter: function(event) {
        event.stopPropagation();
        event.preventDefault();

        this.$('.dnd').addClass('drag-hover');
        return false;
    },

    /*
     * Event handler for a dragover event.
     */
    _onDragOver: function(event) {
        var dt = event.originalEvent.dataTransfer;

        event.stopPropagation();
        event.preventDefault();

        if (dt) {
            dt.dropEffect = 'copy';
        }

        return false;
    },

    /*
     * Event handler for a dragleave event.
     */
    _onDragLeave: function(event) {
        var dt = event.originalEvent.dataTransfer;

        event.stopPropagation();
        event.preventDefault();

        this.$('.dnd').removeClass('drag-hover');

        if (dt) {
            dt.dropEffect = "none";
        }

        return false;
    },

    /*
     * Event handler for a drop event.
     */
    _onDrop: function(event) {
        var dt = event.originalEvent.dataTransfer,
            files = dt && dt.files;

        event.stopPropagation();
        event.preventDefault();

        if (files) {
            this.model.handleFiles(files);
        }
    },

    /*
     * Handle when the user inputs a base directory.
     */
    _onBasedirSubmit: function() {
        var basedir = this.$('#basedir-input').val();

        if (basedir) {
            this.model.set('basedir', basedir);
        }
        return false;
    },

    /*
     * Handle when the user inputs a change number.
     */
    _onChangenumSubmit: function() {
        var changenum = this.$('#changenum-input').val();

        if (changenum) {
            this.model.set('changeNumber', changenum);
        }
        return false;
    },

    /*
     * Callback when "start over" is clicked.
     */
    _onStartOverClicked: function() {
        var input = this._$fileInput.clone(true);

        this._$fileInput.replaceWith(input);
        this._$fileInput = input;

        this.model.startOver();

        return false;
    },

    /*
     * Callback when "Select [diff file]" is clicked.
     */
    _onSelectFileClicked: function() {
        this._$fileInput.click();
    }
});
