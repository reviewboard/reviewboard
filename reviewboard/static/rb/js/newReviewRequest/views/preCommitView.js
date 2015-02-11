/*
 * A view for pre-commit review request creation.
 *
 * This will guide users through several steps, depending on the requirements of
 * the repository.
 */
RB.PreCommitView = Backbone.View.extend({
    className: 'pre-commit',

    template: _.template([
        '<div class="section-header"><%- pendingChangeHeader %></div>',
        '<div class="tip">',
        ' <strong><%- tipHeader %></strong>',
        ' <%= tip %>',
        '</div>',
        '<div class="input dnd" id="prompt-for-diff">',
        ' <form>',
        '  <%= selectDiff %>',
        ' </form>',
        '</div>',
        '<div class="input dnd" id="prompt-for-parent-diff">',
        ' <form>',
        '  <div id="parent-diff-error-contents" />',
        '  <%= selectParentDiff %>',
        ' </form>',
        ' <a href="#" class="startover"><%- startOver %></a>',
        '</div>',
        '<div class="input" id="prompt-for-basedir">',
        ' <form id="basedir-form">',
        '  <%- baseDir %>',
        '  <input id="basedir-input" />',
        '  <input type="submit" value="<%- ok %>" />',
        ' </form>',
        ' <a href="#" class="startover"><%- startOver %></a>',
        '</div>',
        '<div class="input" id="prompt-for-change-number">',
        ' <form id="changenum-form">',
        '  <%- changeNum %>',
        '  <input type="number" step="1" id="changenum-input" />',
        '  <input type="submit" value="<%- ok %>" />',
        ' </form>',
        ' <a href="#" class="startover"><%- startOver %></a>',
        '</div>',
        '<div class="input" id="processing-diff"></div>',
        '<div class="input" id="uploading-diffs"></div>',
        '<div class="input" id="error-indicator">',
        ' <div id="error-contents" />',
        ' <a href="#" class="startover"><%- startOver %></a>',
        '</div>'
    ].join('')),

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

    initialize: function() {
        this.listenTo(this.model, 'change:state', this._onStateChanged);
        this.listenTo(this.model, 'change:error', this._onErrorChanged);
    },

    /*
     * Render the view.
     */
    render: function() {
        var self = this;

        this.$el.html(this.template({
            pendingChangeHeader: gettext('New Review Request for Pending Change'),
            tipHeader: gettext('Tip:'),
            tip: gettext('We recommend using <code>rbt post</code> from <a href="https://www.reviewboard.org/docs/rbtools/dev/">RBTools</a> to create and update review requests.'),
            selectDiff: gettext('<input type="button" id="select-diff-file" value="Select"> or drag and drop a diff file to begin.'),
            selectParentDiff: gettext('<input type="button" id="select-parent-diff-file" value="Select"> or drag and drop a parent diff file if you have one.'),
            baseDir: gettext('What is the base directory for this diff?'),
            changeNum: gettext('What is the change number for this diff?'),
            startOver: gettext('Start Over'),
            ok: gettext('OK')
        }));

        this._$fileInput = $('<input type="file" />')
            .hide()
            .appendTo(this.$el)
            .change(function() {
                self._handleFiles(self._$fileInput.get(0).files);
            });
        this._$promptForDiff = this.$('#prompt-for-diff');
        this._$promptForParentDiff = this.$('#prompt-for-parent-diff');
        this._$promptForBasedir = this.$('#prompt-for-basedir');
        this._$promptForChangeNumber = this.$('#prompt-for-change-number');
        this._$processingDiff = this.$('#processing-diff');
        this._$uploading = this.$('#uploading-diffs');
        this._$error = this.$('#error-indicator');
        this._$errorContents = this.$('#error-contents');
        this._$diffRevisionError = this.$('#parent-diff-error-contents');

        this._onStateChanged(this.model, this.model.get('state'));

        return this;
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
            this._handleFiles(files);
        }
    },

    /*
     * Handle a selected diff file.
     *
     * In the case where the current state is PROMPT_FOR_DIFF, this will take
     * the diff file (selected either through drag-and-drop or the file chooser)
     * and set it in the model, triggering the validation stage.
     */
    _handleFiles: function(files) {
        switch(this.model.get('state')) {
            case this.model.State.PROMPT_FOR_DIFF:
                this.model.set('diffFile', files[0]);
                break;

            case this.model.State.PROMPT_FOR_PARENT_DIFF:
                this.model.set('parentDiffFile', files[0]);
                break;

            default:
                console.assert('File received in wrong state');
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
