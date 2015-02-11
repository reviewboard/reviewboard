/*
 * A model for pre-commit review request creation.
 */
RB.PreCommitModel = Backbone.Model.extend({
    defaults: {
        basedir: null,
        changeNumber: null,
        diffFile: null,
        diffValid: false,
        error: null,
        parentDiffFile: null,
        repository: null,
        state: 0
    },

    State: {
        PROMPT_FOR_DIFF: 0,
        PROMPT_FOR_BASEDIR: 1,
        PROPMT_FOR_CHANGE_NUMBER: 2,
        PROCESSING_DIFF: 3,
        UPLOADING: 4,
        PROMPT_FOR_PARENT_DIFF: 5,
        ERROR: 6
    },

    /*
     * Initialize the model.
     */
    initialize: function() {
        _super(this).initialize.apply(this, arguments);

        this.on('change:diffFile change:parentDiffFile change:basedir ' +
                'change:changeNumber change:diffValid',
                this._updateState, this);
    },

    /*
     * Reset the various state of the pre-commit creator.
     *
     * This is used when the user clicks "start over" in the middle of the
     * process.
     */
    startOver: function() {
        this.set({
            basedir: null,
            changeNumber: null,
            diffFile: null,
            diffValid: false,
            error: null,
            parentDiffFile: null,
            state: this.State.PROMPT_FOR_DIFF
        });
    },

    /*
     * Perform a state transition, based on the current state and attributes.
     */
    _updateState: function() {
        var basedir = this.get('basedir'),
            changeNumber = this.get('changeNumber'),
            diff = this.get('diffFile'),
            diffValid = this.get('diffValid'),
            parentDiff = this.get('parentDiffFile'),
            repository = this.get('repository'),
            requiresBasedir = repository.get('requiresBasedir'),
            requiresChangeNumber = repository.get('requiresChangeNumber'),
            state = this.get('state');

        switch (state) {
            case this.State.PROMPT_FOR_DIFF:
                if (diff) {
                    if (requiresBasedir && !basedir) {
                        this.set('state', this.State.PROMPT_FOR_BASEDIR);
                    } else if (requiresChangeNumber && !changeNumber) {
                        this.set('state', this.State.PROMPT_FOR_CHANGE_NUMBER);
                    } else {
                        this.set('state', this.State.PROCESSING_DIFF);
                        this._tryValidate();
                    }
                }
                break;

            case this.State.PROMPT_FOR_PARENT_DIFF:
                if (diff && parentDiff) {
                    this.set('state', this.State.PROCESSING_DIFF);
                    this._tryValidate();
                }
                break;

            case this.State.PROMPT_FOR_BASEDIR:
                console.assert(
                    diff, 'cannot be in basedir prompt state without a diff');
                if (basedir) {
                    if (requiresChangeNumber && !changeNumber) {
                        /*
                         * Right now we don't have anything that requires both a
                         * basedir and a change number, but that might change in
                         * the future.
                         */
                        this.set('state', this.State.PROMPT_FOR_CHANGE_NUMBER);
                    } else {
                        this.set('state', this.State.PROCESSING_DIFF);
                        this._tryValidate();
                    }
                }
                break;

            case this.State.PROMPT_FOR_CHANGE_NUMBER:
                console.assert(
                    diff, 'cannot be in changenum prompt state without a diff');
                if (changeNumber) {
                    this.set('state', this.State.PROCESSING_DIFF);
                    this._tryValidate();
                }
                break;

            case this.State.PROCESSING_DIFF:
                if (diffValid) {
                    this.set('state', this.State.UPLOADING);
                    this._createReviewRequest();
                }
                break;

            case this.State.UPLOADING:
                break;

            case this.State.ERROR:
                break;
        }
    },

    /*
     * Do a test validation of the selected diff and provided options.
     *
     * This starts an asynchronous process. When this process is completed
     * successfully, the 'diffValid' attribute will be set to true. If the
     * validation fails, the state will be set to State.ERROR and the 'state'
     * attribute will be set to HTML with a user-visible error.
     */
    _tryValidate: function() {
        var diff = this.get('diffFile'),
            parentDiff = this.get('parentDiffFile'),
            repository = this.get('repository'),
            uploader = new RB.ValidateDiffModel();

        this.set('diffValid', false);

        console.assert(diff);

        uploader.set({
            repository: repository.get('id'),
            localSitePrefix: repository.get('localSitePrefix'),
            basedir: this.get('basedir'),
            diff: diff,
            parentDiff: parentDiff
        });

        uploader.save({
            success: _.bind(this._onValidateSuccess, this),
            error: _.bind(this._onValidateError, this)
        });
    },

    /*
     * Callback for when validation succeeds.
     */
    _onValidateSuccess: function() {
        this.set('diffValid', true);
    },

    /*
     * Callback for when validation fails.
     */
    _onValidateError: function(model, xhr) {
        var rsp = $.parseJSON(xhr.responseText),
            newState = this.State.ERROR,
            error;

        if (rsp !== null) {
            switch (rsp.err.code) {
                case RB.APIErrors.REPO_FILE_NOT_FOUND:
                    if (   this.get('repository').get('scmtoolName') === 'Git'
                        && rsp.revision.length !== 40) {
                        error = gettext('The uploaded diff uses short revisions, but Review Board requires full revisions.<br />Please generate a new diff using the <code>--full-index</code> parameter.');
                    } else {
                        error = interpolate(
                            gettext('The file "%(file)s" (revision %(revision)s) was not found in the repository.'),
                            {
                                file: rsp.file,
                                revision: rsp.revision
                            },
                            true);

                        if (this.get('parentDiffFile') === null) {
                            // Allow the user to try providing a parent diff.
                            newState = this.State.PROMPT_FOR_PARENT_DIFF;
                        }
                    }

                    break;

                case RB.APIErrors.DIFF_PARSE_ERROR:
                    error = interpolate(
                        gettext('%(error)s<br />Line %(line)s: %(reason)s'),
                        {
                            error: rsp.err.msg,
                            line: rsp.linenum,
                            reason: rsp.reason
                        },
                        true);
                    break;

                default:
                    error = rsp.err.msg;
                    break;
            }
        } else {
            error = gettext('Unknown error');
        }

        if (error) {
            this.set({
                state: newState,
                error: error
            });
        }
    },

    /*
     * Actually create the review request.
     *
     * This should be all but guaranteed to succeed, since we've already
     * determined that the supplied parameters ought to work through the
     * ValidateDiffModel.
     */
    _createReviewRequest: function() {
        var repository = this.get('repository'),
            reviewRequest = new RB.ReviewRequest({
                commitID: this.get('changeNumber'),
                localSitePrefix: repository.get('localSitePrefix'),
                repository: repository.get('id')
            });

        reviewRequest.save({
            success: function() {
                var diff = reviewRequest.createDiff();

                diff.set({
                    basedir: this.get('basedir'),
                    diff: this.get('diffFile'),
                    parentDiff: this.get('parentDiffFile')
                });
                diff.url = reviewRequest.get('links').diffs.href;
                diff.save({
                    success: function() {
                        window.location = reviewRequest.get('reviewURL');
                    },
                    error: this._onValidateError
                }, this);
            },
            error: this._onValidateError
        }, this);
    }
});
