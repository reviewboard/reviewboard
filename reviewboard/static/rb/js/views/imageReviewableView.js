(function() {


var BaseImageView,
    ImageAttachmentView,
    ImageDifferenceDiffView,
    ImageOnionDiffView,
    ImageSplitDiffView,
    ImageTwoUpDiffView;


/*
 * Base class for providing a view onto an image or diff of images.
 *
 * This handles the common functionality, such as loading images, determining
 * the image region, rendering, and so on.
 *
 * Subclasses must, at a minimum, provide a 'mode', 'name', and must set
 * $commentRegion to an element representing the region where comments are
 * allowed.
 */
BaseImageView = Backbone.View.extend({
    template: null,
    mode: null,
    name: null,

    /*
     * Initializes the view.
     */
    initialize: function() {
        this.$commentRegion = null;
    },

    /*
     * Computes a CSS class name for this view.
     *
     * The class name is based on the view mode.
     */
    className: function() {
        return 'image-diff-' + this.mode;
    },

    /*
     * Renders the view.
     *
     * This will by default render the template into the element and begin
     * loading images.
     */
    render: function() {
        if (this.template) {
            this.$el.html(this.template(this.model.attributes));
        }

        this.loadImages(this.$('img'));

        return this;
    },

    /*
     * Loads a list of images.
     *
     * Once each image is loaded, the view's onImagesLoaded function will
     * be called. Subclasses can override this to provide functionality based
     * on image sizes and content.
     */
    loadImages: function(images) {
        var loadsRemaining = images.length;

        _.each(images, function(image) {
            image.onload = _.bind(function() {
                loadsRemaining--;
                console.assert(loadsRemaining >= 0);

                $(image)
                    .width(image.width)
                    .height(image.height);

                if (loadsRemaining === 0) {
                    this.onImagesLoaded();
                    this.trigger('regionChanged');
                }
            }, this);
        }, this);
    },

    /*
     * Returns the region of the view where commenting can take place.
     *
     * The region is based on the $commentRegion member variable, which must
     * be set by a subclass.
     */
    getSelectionRegion: function() {
        var $region = this.$commentRegion,
            offset = $region.position();

        /*
         * The margin: 0 auto means that position.left() will return
         * the left-most part of the entire block, rather than the actual
         * position of the region on Chrome. Every other browser returns 0
         * for this margin, as we'd expect. So, just play it safe and
         * offset by the margin-left. (Bug #1050)
         */
        offset.left += $region.getExtents('m', 'l');

        return {
            left: offset.left,
            top: offset.top,
            width: $region.width(),
            height: $region.height()
        };
    },

    /*
     * Callback handler for when the images on the view are loaded.
     *
     * By default, this doesn't do anything. Subclasses can override this
     * to provide logic dependent on loaded images.
     */
    onImagesLoaded: function() {
    }
});


/*
 * Displays a single image.
 *
 * This view is used for standalone images, without diffs. It displays the
 * image and allows it to be commented on.
 */
ImageAttachmentView = BaseImageView.extend({
    mode: 'attachment',
    tagName: 'img',

    /*
     * Renders the view.
     */
    render: function() {
        this.$el.attr({
            title: this.model.get('caption'),
            src: this.model.get('imageURL')
        });

        this.$commentRegion = this.$el;

        return this;
    }
});


/*
 * Displays a color difference view of two images.
 *
 * Each pixel in common between images will be shown in black. Added pixels
 * in the new image are shown as they would in the image itself. Differences
 * in pixel values are shown as well.
 *
 * See:
 * http://jeffkreeftmeijer.com/2011/comparing-images-and-creating-image-diffs/
 */
ImageDifferenceDiffView = BaseImageView.extend({
    mode: 'difference',
    name: gettext('Difference'),

    template: _.template([
        '<div class="image-container">',
        ' <canvas></canvas>',
        '</div>'
    ].join('')),

    /*
     * Initializes the view.
     */
    initialize: function() {
        _super(this).initialize.call(this);

        this._origImage = null;
        this._modifiedImage = null;
    },

    /*
     * Renders the view.
     *
     * Image elements representing the original and modified images will be
     * created and loaded. After loading, onImagesLoaded will handle populating
     * the canvas with the difference view.
     */
    render: function() {
        this.$el.html(this.template(this.model.attributes));

        this.$commentRegion = this.$('canvas');

        this._origImage = new Image();
        this._origImage.src = this.model.get('diffAgainstImageURL');

        this._modifiedImage = new Image();
        this._modifiedImage.src = this.model.get('imageURL');

        this.loadImages([this._origImage, this._modifiedImage]);

        return this;
    },

    /*
     * Renders the difference between two images onto the canvas.
     */
    onImagesLoaded: function() {
        var origImage = this._origImage,
            modifiedImage = this._modifiedImage,
            maxWidth = Math.max(origImage.width, modifiedImage.width),
            maxHeight = Math.max(origImage.height, modifiedImage.height),
            $origCanvas = this.$('canvas'),
            $modifiedCanvas = $('<canvas/>'),
            origContext = $origCanvas[0].getContext('2d'),
            modifiedContext = $modifiedCanvas[0].getContext('2d'),
            origImageData,
            origPixels,
            origPixelsLen,
            modifiedPixels,
            i;

        $origCanvas[0].width = maxWidth;
        $origCanvas[0].height = maxHeight;
        $modifiedCanvas[0].width = maxWidth;
        $modifiedCanvas[0].height = maxHeight;

        origContext.drawImage(origImage, 0, 0);
        modifiedContext.drawImage(modifiedImage, 0, 0);

        origImageData = origContext.getImageData(0, 0, maxWidth, maxHeight);
        origPixels = origImageData.data;
        origPixelsLen = origPixels.length;

        modifiedPixels = modifiedContext.getImageData(0, 0, maxWidth,
                                                      maxHeight).data;

        for (i = 0; i < origPixelsLen; i += 4) {
            origPixels[i] += modifiedPixels[i] -
                             2 * Math.min(origPixels[i], modifiedPixels[i]);
            origPixels[i + 1] += modifiedPixels[i + 1] -
                                 2 * Math.min(origPixels[i + 1],
                                              modifiedPixels[i + 1]);
            origPixels[i + 2] += modifiedPixels[i + 2] -
                                 2 * Math.min(origPixels[i + 2],
                                              modifiedPixels[i + 2]);
            origPixels[i + 3] = modifiedPixels[i + 3];
        }

        origContext.putImageData(origImageData, 0, 0);
    }
});


/*
 * Displays an onion skin view of two images.
 *
 * Onion skinning allows the user to see subtle changes in two images by
 * altering the transparency of the modified image. Through a slider, they'll
 * be able to play around with the transparency and see if any pixels move,
 * disappear, or otherwise change.
 */
ImageOnionDiffView = BaseImageView.extend({
    mode: 'onion',
    name: gettext('Onion Skin'),

    template: _.template([
        '<div class="image-containers">',
        ' <div class="orig-image">',
        '  <img title="<%- caption %>" src="<%- diffAgainstImageURL %>" />',
        ' </div>',
        ' <div class="modified-image">',
        '  <img title="<%- caption %>" src="<%- imageURL %>" />',
        ' </div>',
        '</div>',
        '<div class="image-slider"></div>'
    ].join('')),

    DEFAULT_OPACITY: 0.25,

    /*
     * Initializes the view.
     */
    initialize: function() {
        _super(this).initialize.call(this);

        this._$origImage = null;
        this._$modifiedImage = null;
        this._$modifiedImageContainer = null;
    },

    /*
     * Renders the view.
     *
     * This will set up the slider and set it to a default of 25% opacity.
     */
    render: function() {
        _super(this).render.call(this);

        this.$commentRegion = this.$('.image-containers');
        this._$origImage = this.$('.orig-image img');
        this._$modifiedImage = this.$('.modified-image img');
        this._$modifiedImageContainer = this._$modifiedImage.parent();

        this.$('.image-slider')
            .slider({
                value: this.DEFAULT_OPACITY * 100,

                slide: _.bind(function(event, ui) {
                    this.setOpacity(ui.value / 100.0);
                }, this)
            });

        this.setOpacity(this.DEFAULT_OPACITY);

        return this;
    },

    /*
     * Sets the opacity value for the images.
     *
     * This takes a value between 0.0 and 1.0 as the opacity.
     */
    setOpacity: function(pct) {
        this._$modifiedImageContainer.css('opacity', pct);
    },

    /*
     * Positions the images after they load.
     *
     * The images will be layered on top of each other, consuming the
     * same width and height.
     */
    onImagesLoaded: function() {
        var origWidth = this._$origImage.width(),
            origHeight = this._$origImage.height(),
            modifiedWidth = this._$modifiedImage.width(),
            modifiedHeight = this._$modifiedImage.height();

        this._$origImage.parent()
            .width(origWidth)
            .height(origHeight);

        this._$modifiedImage.parent()
            .width(modifiedWidth)
            .height(modifiedHeight);

        this.$('.image-containers')
            .width(Math.max(origWidth, modifiedWidth))
            .height(Math.max(origHeight, modifiedHeight));
    }
});


/*
 * Displays an overlapping split view between two images.
 *
 * The images will be overlapping, and a horizontal slider will control how
 * much of the modified image is shown. The modified image will overlap the
 * original image. This makes it easy to compare the two images incrementally.
 */
ImageSplitDiffView = BaseImageView.extend({
    mode: 'split',
    name: gettext('Split'),

    template: _.template([
        '<div class="image-containers">',
        ' <div class="image-diff-split-container-orig">',
        '  <div class="orig-image">',
        '   <img title="<%- caption %>" src="<%- diffAgainstImageURL %>" />',
        '  </div>',
        ' </div>',
        ' <div class="image-diff-split-container-modified">',
        '  <div class="modified-image">',
        '   <img title="<%- caption %>" src="<%- imageURL %>" />',
        '  </div>',
        ' </div>',
        '</div>',
        '<div class="image-slider"></div>'
    ].join('')),

    DEFAULT_SPLIT_PCT: 0.25,

    /*
     * Initializes the view.
     */
    initialize: function() {
        _super(this).initialize.call(this);

        this._$modifiedImage = null;
        this._$origImage = null;
        this._$origSplitContainer = null;
        this._$modifiedSplitContainer = null;
        this._$slider = null;
        this._maxWidth = 0;
    },

    /*
     * Renders the view.
     *
     * This will set up the slider and set it to a default of 25%.
     */
    render: function() {
        _super(this).render.call(this);

        this.$commentRegion = this.$('.image-containers');
        this._$origImage = this.$('.orig-image img');
        this._$modifiedImage = this.$('.modified-image img');
        this._$origSplitContainer = this.$('.image-diff-split-container-orig');
        this._$modifiedSplitContainer =
            this.$('.image-diff-split-container-modified');

        this._$slider = this.$('.image-slider')
            .slider({
                value: this.DEFAULT_SPLIT_PCT * 100,
                slide: _.bind(function(event, ui) {
                    this.setSplitPct(ui.value / 100.0);
                }, this)
            });

        return this;
    },

    /*
     * Sets the percentage for the split view.
     */
    setSplitPct: function(pct) {
        this._$origSplitContainer.outerWidth(this._maxWidth * pct);
        this._$modifiedSplitContainer.outerWidth(this._maxWidth * (1.0 - pct));
    },

    /*
     * Positions the images after they load.
     *
     * The images will be layered on top of each other, anchored to the
     * top-left.
     *
     * The slider will match the width of the two images, in order to
     * position the slider's handle with the divider between images.
     */
    onImagesLoaded: function() {
        var $origImageContainer = this._$origImage.parent(),
            origWidth = this._$origImage.outerWidth(),
            origHeight = this._$origImage.height(),
            modifiedWidth = this._$modifiedImage.outerWidth(),
            modifiedHeight = this._$modifiedImage.height(),
            maxHeight = Math.max(origHeight, modifiedHeight),
            maxOuterHeight = maxHeight +
                             $origImageContainer.getExtents('b', 'tb');

        this._maxWidth = Math.max(origWidth, modifiedWidth);

        $origImageContainer
            .outerWidth(origWidth)
            .height(origHeight);

        this._$modifiedImage.parent()
            .outerWidth(modifiedWidth)
            .height(modifiedHeight);

        this._$origSplitContainer
            .outerWidth(this._maxWidth)
            .height(maxOuterHeight);

        this._$modifiedSplitContainer
            .outerWidth(this._maxWidth)
            .height(maxOuterHeight);

        this.$('.image-containers')
            .width(this._maxWidth)
            .height(maxHeight);

        this._$slider.width(this._maxWidth);

        /* Now that these are loaded, set the default for the split. */
        this.setSplitPct(this.DEFAULT_SPLIT_PCT);
    }
});


/*
 * Displays a two-up, side-by-side view of two images.
 *
 * The images will be displayed horizontally, side-by-side. Comments will
 * only be able to be added against the new file.
 */
ImageTwoUpDiffView = BaseImageView.extend({
    mode: 'two-up',
    name: gettext('Two-Up'),

    template: _.template([
        '<div class="image-container image-container-orig">',
        ' <div class="orig-image">',
        '  <img title="<%- caption %>" src="<%- diffAgainstImageURL %>" />',
        ' </div>',
        '</div>',
        '<div class="image-container image-container-modified">',
        ' <div class="modified-image">',
        '  <img title="<%- caption %>" src="<%- imageURL %>" />',
        ' </div>',
        '</div>'
    ].join('')),

    /*
     * Renders the view.
     */
    render: function() {
        _super(this).render.call(this);

        this.$commentRegion = this.$('.modified-image img');

        return this;
    }
});


/*
 * Displays a review UI for images.
 *
 * This supports reviewing individual images, and diffs between images.
 *
 * In the case of individual images, the image will be displayed, centered,
 * and all existing comments will be shown as selection boxes on top of it.
 * Users can click and drag across part of the image to leave a comment on
 * that area.
 *
 * Image diffs can be shown in multiple modes. This supports a "two-up"
 * side-by-side view, an overlapping split view, Onion Skinning view, and
 * a color difference view.
 */
RB.ImageReviewableView = RB.FileAttachmentReviewableView.extend({
    className: 'image-review-ui',

    commentBlockView: RB.RegionCommentBlockView,

    events: {
        'click .image-diff-modes a': '_onImageModeClicked',
        'mousedown .selection-container': '_onMouseDown',
        'mouseup .selection-container': '_onMouseUp',
        'mousemove .selection-container': '_onMouseMove'
    },

    modeItemTemplate: _.template(
        '<li><a href="#" data-mode="<%- mode %>"><%- name %></a></li>'
    ),

    ANIM_SPEED_MS: 200,

    /*
     * Initializes the view.
     */
    initialize: function(options) {
        RB.FileAttachmentReviewableView.prototype.initialize.call(
            this, options);

        _.bindAll(this, '_adjustPos');

        this._activeSelection = {};
        this._diffModeSelectors = {};
        this._diffModeViews = {};

        /*
         * Add any CommentBlockViews to the selection area when they're
         * created.
         */
        this.on('commentBlockViewAdded', function(commentBlockView) {
            this._$selectionArea.append(commentBlockView.$el);
        }, this);
    },

    /*
     * Renders the view.
     *
     * This will set up a selection area over the image and create a
     * selection rectangle that will be shown when dragging.
     *
     * Any time the window resizes, the comment positions will be adjusted.
     */
    renderContent: function() {
        var self = this;

        this._$selectionArea = $('<div/>')
            .addClass('selection-container')
            .hide()
            .proxyTouchEvents();

        this._$selectionRect = $('<div/>')
            .addClass('selection-rect')
            .prependTo(this._$selectionArea)
            .proxyTouchEvents()
            .hide();

        if (!this.renderedInline) {
            this.$el.append(
                $('<h1 class="caption"/>').text(this.model.get('caption')));
        }

        this.$el
            /*
             * Register a hover event to hide the comments when the mouse
             * is not over the comment area.
             */
            .hover(
                function() {
                    self._$selectionArea.show();
                    self._adjustPos();
                },
                function() {
                    if (self._$selectionRect.is(':hidden') &&
                        !self.commentDlg) {
                        self._$selectionArea.hide();
                    }
                })
            .append(this._$selectionArea);

        if (this.model.get('diffAgainstFileAttachmentID')) {
            this._$modeBar = $('<ul class="image-diff-modes"/>')
                .appendTo(this.$el);

            this._$imageDiffs = $('<div class="image-diffs"/>');

            this._addDiffMode(ImageTwoUpDiffView);
            this._addDiffMode(ImageDifferenceDiffView);
            this._addDiffMode(ImageSplitDiffView);
            this._addDiffMode(ImageOnionDiffView);

            this.$el.append(this._$imageDiffs);

            this._setDiffMode(ImageTwoUpDiffView.prototype.mode);
        } else {
            this._imageView = new ImageAttachmentView({
                model: this.model
            });

            this._imageView.$el.appendTo(this.$el);
            this._imageView.render();
        }

        /*
         * Reposition the selection area on page resize or loaded, so that
         * comments are in the right locations.
         */
        $(window)
            .resize(this._adjustPos)
            .load(this._adjustPos);

        return this;
    },

    /*
     * Registers a diff mode.
     *
     * This will register a class for the mode and add an entry to the
     * mode bar.
     */
    _addDiffMode: function(ViewClass) {
        var mode = ViewClass.prototype.mode,
            view = new ViewClass({
                model: this.model
            }),
            $selector = $(this.modeItemTemplate({
                mode: mode,
                name: view.name
            })),
            selectorWidth;

        this._diffModeViews[mode] = view;
        view.$el.hide();
        this._$imageDiffs.append(view.$el);
        view.render();

        /*
         * Since we're making the text bold when selected, we need to reserve
         * the right amount of space for the bold text, so that the contents
         * don't shift.
         *
         * This is kind of ugly, but really the only good way.
         */
        $selector
            .appendTo(this._$modeBar)
            .addClass('selected');
        selectorWidth = $selector.width();
        $selector
            .removeClass('selected')
            .width(selectorWidth);

        this._diffModeSelectors[mode] = $selector;
    },

    /*
     * Sets the current diff mode.
     *
     * That mode will be displayed on the page and comments will be shown.
     *
     * The height of the review UI will animate to the new height for this
     * mode.
     */
    _setDiffMode: function(mode) {
        var newView = this._diffModeViews[mode],
            height;

        if (this._imageView) {
            this._diffModeSelectors[this._imageView.mode]
                .removeClass('selected');
            this._diffModeSelectors[newView.mode]
                .addClass('selected');

            newView.$el.show();
            height = newView.$el.height();
            newView.$el.hide();

            this._$imageDiffs.animate({
                height: height,
                duration: this.ANIM_SPEED_MS
            });

            this._$selectionArea.fadeOut(this.ANIM_SPEED_MS);
            this._imageView.$el.fadeOut(
                this.ANIM_SPEED_MS,
                _.bind(function() {
                    this._showDiffMode(newView, true);
                }, this));
        } else {
            this._showDiffMode(newView);
        }
    },

    /*
     * Shows the diff mode.
     *
     * This is called by _setDiffMode when it's ready to actually show the
     * new mode.
     *
     * The new mode will be faded in, if we're animating, or immediately shown
     * otherwise.
     */
    _showDiffMode: function(newView, animate) {
        if (this._imageView) {
            this.stopListening(this._imageView, 'regionChanged');
        }

        this._imageView = newView;

        if (animate) {
            this._imageView.$el.fadeIn(this.ANIM_SPEED_MS);
            this._$selectionArea.fadeIn(this.ANIM_SPEED_MS);
        } else {
            this._imageView.$el.show();
            this._$selectionArea.show();
        }

        this.listenTo(this._imageView, 'regionChanged', this._adjustPos);

        this._adjustPos();
    },

    /*
     * Handler for when a mode in the diff mode bar is clicked.
     *
     * Sets the diff view to the given mode.
     */
    _onImageModeClicked: function(e) {
        e.preventDefault();
        e.stopPropagation();

        this._setDiffMode($(e.target).data('mode'));
    },

    /*
     * Handles a mousedown on the selection area.
     *
     * If this is the first mouse button, and it's not being placed on
     * an existing comment block, then this will begin the creation of a new
     * comment block starting at the mousedown coordinates.
     */
    _onMouseDown: function(evt) {
        if (evt.which === 1 &&
            !this.commentDlg &&
            !$(evt.target).hasClass('selection-flag')) {
            var offset = this._$selectionArea.offset();

            this._activeSelection.beginX =
                evt.pageX - Math.floor(offset.left) - 1;
            this._activeSelection.beginY =
                evt.pageY - Math.floor(offset.top) - 1;

            this._$selectionRect
                .move(this._activeSelection.beginX,
                      this._activeSelection.beginY)
                .width(1)
                .height(1)
                .show();

            if (this._$selectionRect.is(':hidden')) {
                this.commentDlg.close();
            }

            return false;
        }
    },

    /*
     * Handles a mouseup on the selection area.
     *
     * This will finalize the creation of a comment block and pop up the
     * comment dialog.
     */
    _onMouseUp: function(evt) {
        if (!this.commentDlg &&
            this._$selectionRect.is(":visible")) {
            var width = this._$selectionRect.width(),
                height = this._$selectionRect.height(),
                offset = this._$selectionRect.position();

            evt.stopPropagation();
            this._$selectionRect.hide();

            /*
             * If we don't pass an arbitrary minimum size threshold,
             * don't do anything. This helps avoid making people mad
             * if they accidentally click on the image.
             */
            if (width > 5 && height > 5) {
                this.createAndEditCommentBlock({
                    x: Math.floor(offset.left),
                    y: Math.floor(offset.top),
                    width: width,
                    height: height
                });
            }
        }
    },

    /*
     * Handles a mousemove on the selection area.
     *
     * If we're creating a comment block, this will update the
     * size/position of the block.
     */
    _onMouseMove: function(evt) {
        if (!this.commentDlg && this._$selectionRect.is(":visible")) {
            var offset = this._$selectionArea.offset(),
                x = evt.pageX - Math.floor(offset.left) - 1,
                y = evt.pageY - Math.floor(offset.top) - 1;

            this._$selectionRect
                .css(this._activeSelection.beginX <= x
                     ? {
                           left:  this._activeSelection.beginX,
                           width: x - this._activeSelection.beginX
                       }
                     : {
                           left:  x,
                           width: this._activeSelection.beginX - x
                       })
                .css(this._activeSelection.beginY <= y
                     ? {
                           top:    this._activeSelection.beginY,
                           height: y - this._activeSelection.beginY
                       }
                     : {
                           top:    y,
                           height: this._activeSelection.beginY - y
                       });

            return false;
        }
    },

    /*
     * Reposition the selection area to the right locations.
     */
    _adjustPos: function() {
        var region = this._imageView.getSelectionRegion();

        this._$selectionArea
            .width(region.width)
            .height(region.height)
            .css({
                left: region.left,
                top: region.top
            });
    }
});


})();
