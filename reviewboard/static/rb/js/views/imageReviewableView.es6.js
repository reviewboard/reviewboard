(function() {


/**
 * A mapping of available image scaling factors to the associated label.
 */
const scalingFactors = new Map([
    [0.33, '33%'],
    [0.5, '50%'],
    [1.0, '100%'],
    [2.0, '200%'],
]);


/**
 * Base class for providing a view onto an image or diff of images.
 *
 * This handles the common functionality, such as loading images, determining
 * the image region, rendering, and so on.
 *
 * Subclasses must, at a minimum, provide a 'mode', 'name', and must set
 * $commentRegion to an element representing the region where comments are
 * allowed.
 */
const BaseImageView = Backbone.View.extend({
    template: null,
    mode: null,
    name: null,

    /**
     * Initialize the view.
     */
    initialize() {
        this.$commentRegion = null;

        this.listenTo(this.model,
                      'change:scale',
                      (model, scale) => this._onScaleChanged(scale));
    },

    /**
     * Compute a CSS class name for this view.
     *
     * Returns:
     *     string:
     *     A class name based on the current mode.
     */
    className() {
        return `image-diff-${this.mode}`;
    },

    /**
     * Load a list of images.
     *
     * Once each image is loaded, the view's onImagesLoaded function will
     * be called. Subclasses can override this to provide functionality based
     * on image sizes and content.
     *
     * Args:
     *     $images (jQuery):
     *         The image elements to load.
     */
    loadImages($images) {
        const scale = this.model.get('scale');

        let loadsRemaining = $images.length;

        this._$images = $images;

        $images.each((ix, image) => {
            const $image = $(image);

            if ($image.data('initial-width') === undefined) {
                image.onload = () => {
                    loadsRemaining--;
                    console.assert(loadsRemaining >= 0);

                    $image
                        .data({
                            'initial-width': image.width,
                            'initial-height': image.height,
                        })
                        .css({
                            width: image.width * scale,
                            height: image.height * scale,
                        });

                    if (loadsRemaining === 0) {
                        this.onImagesLoaded();
                        this.trigger('regionChanged');
                    }
                };
            } else {
                loadsRemaining--;
                if (loadsRemaining === 0) {
                    this.onImagesLoaded();
                    this.trigger('regionChanged');
                }
            }
        });
    },

    /**
     * Return the region of the view where commenting can take place.
     *
     * The region is based on the $commentRegion member variable, which must
     * be set by a subclass.
     *
     * Returns:
     *     object:
     *     An object with ``left``, ``top``, ``width``, and ``height`` keys.
     */
    getSelectionRegion() {
        const $region = this.$commentRegion;
        const offset = $region.position();

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

    /**
     * Callback handler for when the images on the view are loaded.
     *
     * Subclasses that override this method must call the base method so that
     * images can be scaled appropriately.
     */
    onImagesLoaded() {
        let scale = null;

        /*
         * If the image is obviously a 2x or 3x pixel ratio, pre-select the
         * right scaling factor.
         *
         * Otherwise, we select the largest scaling factor that allows the
         * entire image to be shown (or the smallest scaling factor if the
         * scaled image is still too large).
         */
        const filename = this.model.get('filename');

        /*
         * The `filename` attribute does not exist for screenshots, so we need
         * to check it.
         */
        if (filename) {
            if (filename.includes('@2x.')) {
                scale = 0.5;
            } else if (filename.includes('@3x.')) {
                scale = 0.33;
            }
        }

        if (scale === null) {
            const {width} = this.getInitialSize();
            const maxWidth = this.$el.closest('.image-content').width();
            const scales = Array
                .from(scalingFactors.keys())
                .filter(f => (f <= 1));

            for (let i = scales.length - 1; i >= 0; i--) {
                scale = scales[i];

                if (width * scale <= maxWidth) {
                    break;
                }
            }
        }

        this.model.set('scale', scale);
    },

    /**
     * Handle the image scale being changed.
     *
     * Args:
     *     scale (number):
     *         The new image scaling factor (where 1.0 is 100%, 0.5 is 50%,
     *         etc).
     */
    _onScaleChanged(scale) {
        this._$images.each((index, el) => {
            const $image = $(el);

            $image.css({
                width: $image.data('initial-width') * scale,
                height: $image.data('initial-height') * scale,
            });
        });
    },

    /**
     * Return the initial size of the image.
     *
     * Subclasses must override this.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize() {
        console.assert(
            false, 'subclass of BaseImageView must implement getInitialSize');
    },
});


/**
 * Displays a single image.
 *
 * This view is used for standalone images, without diffs. It displays the
 * image and allows it to be commented on.
 */
const ImageAttachmentView = BaseImageView.extend({
    mode: 'attachment',
    tagName: 'img',

    /**
     * Render the view.
     *
     * Returns:
     *     ImageAttachmentView:
     *     This object, for chaining.
     */
    render() {
        this.$el.attr({
            title: this.model.get('caption'),
            src: this.model.get('imageURL')
        });

        this.$commentRegion = this.$el;

        this.loadImages(this.$el);

        return this;
    },

    /**
     * Return the initial size of the image.
     *
     * Subclasses must override this.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize() {
        const $img = this._$images.eq(0);

        return {
            width: $img.data('initial-width'),
            height: $img.height('initial-height'),
        };
    },
});


/**
 * Displays a color difference view of two images.
 *
 * Each pixel in common between images will be shown in black. Added pixels
 * in the new image are shown as they would in the image itself. Differences
 * in pixel values are shown as well.
 *
 * See:
 * http://jeffkreeftmeijer.com/2011/comparing-images-and-creating-image-diffs/
 */
const ImageDifferenceDiffView = BaseImageView.extend({
    mode: 'difference',
    name: gettext('Difference'),

    template: _.template([
        '<div class="image-container">',
        ' <canvas></canvas>',
        '</div>'
    ].join('')),

    /**
     * Initialize the view.
     */
    initialize() {
        _super(this).initialize.call(this);

        this._origImage = null;
        this._modifiedImage = null;
    },

    /**
     * Render the view.
     *
     * Image elements representing the original and modified images will be
     * created and loaded. After loading, onImagesLoaded will handle populating
     * the canvas with the difference view.
     *
     * Returns:
     *     ImageDifferenceDiffView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template(this.model.attributes));

        this.$commentRegion = this.$('canvas');
        this._$canvas = this.$commentRegion;

        this._origImage = new Image();
        this._origImage.src = this.model.get('diffAgainstImageURL');

        this._modifiedImage = new Image();
        this._modifiedImage.src = this.model.get('imageURL');

        this.loadImages($([this._origImage, this._modifiedImage]));

        return this;
    },

    /**
     * Render the difference between two images onto the canvas.
     */
    onImagesLoaded() {
        const origImage = this._origImage;
        const modifiedImage = this._modifiedImage;
        const scale = this.model.get('scale');

        this._maxWidth = Math.max(origImage.width, modifiedImage.width);
        this._maxHeight = Math.max(origImage.height, modifiedImage.height);

        _super(this).onImagesLoaded.call(this);

        this._$canvas
            .attr({
                width: this._maxWidth,
                height: this._maxHeight
            })
            .css({
                width: this._maxWidth * scale + 'px',
                height: this._maxHeight * scale + 'px'
            });

        const $modifiedCanvas = $('<canvas/>')
            .attr({
                width: this._maxWidth,
                height: this._maxHeight
            });

        const origContext = this._$canvas[0].getContext('2d');
        origContext.drawImage(origImage, 0, 0);

        const modifiedContext = $modifiedCanvas[0].getContext('2d');
        modifiedContext.drawImage(modifiedImage, 0, 0);

        const origImageData = origContext.getImageData(
            0, 0, this._maxWidth, this._maxHeight);
        const origPixels = origImageData.data;

        const modifiedPixels = modifiedContext.getImageData(
            0, 0, this._maxWidth, this._maxHeight).data;

        for (let i = 0; i < origPixels.length; i += 4) {
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
    },

    /**
     * Handle the image scale being changed.
     *
     * Args:
     *     scale (number):
     *         The new image scaling factor (where 1.0 is 100%, 0.5 is 50%,
     *         etc).
     */
    _onScaleChanged(scale) {
        this._$canvas.css({
            width: this._maxWidth * scale + 'px',
            height: this._maxHeight * scale + 'px',
        });
    },

    /**
     * Return the initial size of the image.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize() {
        return {
            width: this._maxWidth,
            height: this._maxHeight,
        };
    },
});


/**
 * Displays an onion skin view of two images.
 *
 * Onion skinning allows the user to see subtle changes in two images by
 * altering the transparency of the modified image. Through a slider, they'll
 * be able to play around with the transparency and see if any pixels move,
 * disappear, or otherwise change.
 */
const ImageOnionDiffView = BaseImageView.extend({
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

    /**
     * Initialize the view.
     */
    initialize() {
        _super(this).initialize.call(this);

        this._$origImage = null;
        this._$modifiedImage = null;
        this._$modifiedImageContainer = null;
    },

    /**
     * Render the view.
     *
     * This will set up the slider and set it to a default of 25% opacity.
     *
     * Returns:
     *     ImageOnionDiffView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template(this.model.attributes));

        this.$commentRegion = this.$('.image-containers');
        this._$origImage = this.$('.orig-image img');
        this._$modifiedImage = this.$('.modified-image img');
        this._$modifiedImageContainer = this._$modifiedImage.parent();

        this.$('.image-slider')
            .slider({
                value: this.DEFAULT_OPACITY * 100,
                slide: (e, ui) => this.setOpacity(ui.value / 100.0)
            });

        this.setOpacity(this.DEFAULT_OPACITY);

        this.loadImages(this.$('img'));

        return this;
    },

    /**
     * Set the opacity value for the images.
     *
     * Args:
     *     percentage (number):
     *         The opacity percentage, in [0.0, 1.0].
     */
    setOpacity(percentage) {
        this._$modifiedImageContainer.css('opacity', percentage);
    },

    /**
     * Position the images after they load.
     *
     * The images will be layered on top of each other, consuming the
     * same width and height.
     */
    onImagesLoaded() {
        _super(this).onImagesLoaded.call(this);
        this._resize();
    },

    /**
     * Handle the image scale being changed.
     *
     * Args:
     *     scale (number):
     *         The new image scaling factor (where 1.0 is 100%, 0.5 is 50%,
     *         etc).
     */
    _onScaleChanged(scale) {
        _super(this)._onScaleChanged.call(this, scale);
        this._resize();
    },

    /**
     * Resize the image containers.
     */
    _resize() {
        const scale = this.model.get('scale');
        const origW = this._$origImage.data('initial-width') * scale;
        const origH = this._$origImage.data('initial-height') * scale;
        const newW = this._$modifiedImage.data('initial-width') * scale;
        const newH = this._$modifiedImage.data('initial-height') * scale;

        this._$origImage.parent()
            .width(origW)
            .height(origH);

        this._$modifiedImage.parent()
            .width(newW)
            .height(newH);

        this.$('.image-containers')
            .width(Math.max(origW, newW))
            .height(Math.max(origH, newH));
    },

    /**
     * Return the initial size of the image.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize() {
        return {
            width: Math.max(this._$origImage.data('initial-width'),
                            this._$modifiedImage.data('initial-width')),
            height: Math.max(this._$origImage.data('initial-height'),
                             this._$modifiedImage.data('initial-height')),
        };
    },
});


/**
 * Displays an overlapping split view between two images.
 *
 * The images will be overlapping, and a horizontal slider will control how
 * much of the modified image is shown. The modified image will overlap the
 * original image. This makes it easy to compare the two images incrementally.
 */
const ImageSplitDiffView = BaseImageView.extend({
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

    // The default slider position of 25%
    DEFAULT_SPLIT_PCT: 0.25,

    /**
     * Initialize the view.
     */
    initialize() {
        _super(this).initialize.call(this);

        this._$modifiedImage = null;
        this._$origImage = null;
        this._$origSplitContainer = null;
        this._$modifiedSplitContainer = null;
        this._$slider = null;
        this._maxWidth = 0;
    },

    /**
     * Render the view.
     *
     * Returns:
     *     ImageSplitDiffView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template(this.model.attributes));

        this.$commentRegion = this.$('.image-containers');
        this._$origImage = this.$('.orig-image img');
        this._$modifiedImage = this.$('.modified-image img');
        this._$origSplitContainer = this.$('.image-diff-split-container-orig');
        this._$modifiedSplitContainer =
            this.$('.image-diff-split-container-modified');

        this._$slider = this.$('.image-slider')
            .slider({
                value: this.DEFAULT_SPLIT_PCT * 100,
                slide: (e, ui) => this.setSplitPercentage(ui.value / 100.0)
            });

        this.loadImages(this.$('img'));

        return this;
    },

    /**
     * Set the percentage for the split view.
     *
     * Args:
     *     percentage (number):
     *         The position of the slider, in [0.0, 1.0].
     */
    setSplitPercentage(percentage) {
        this._$origSplitContainer.outerWidth(this._maxWidth * percentage);
        this._$modifiedSplitContainer.outerWidth(
            this._maxWidth * (1.0 - percentage));
    },

    /**
     * Position the images after they load.
     *
     * The images will be layered on top of each other, anchored to the
     * top-left.
     *
     * The slider will match the width of the two images, in order to
     * position the slider's handle with the divider between images.
     */
    onImagesLoaded() {
        _super(this).onImagesLoaded.call(this);
        this._resize();
    },

    /**
     * Handle the image scale being changed.
     *
     * Args:
     *     scale (number):
     *         The new image scaling factor (where 1.0 is 100%, 0.5 is 50%,
     *         etc).
     */
    _onScaleChanged(scale) {
        _super(this)._onScaleChanged.call(this, scale);
        this._resize();
    },

    /**
     * Resize the image containers.
     */
    _resize() {
        const $origImageContainer = this._$origImage.parent();
        const scale = this.model.get('scale');
        const origW = this._$origImage.data('initial-width') * scale;
        const origH = this._$origImage.data('initial-height') * scale;
        const newW = this._$modifiedImage.data('initial-width') * scale;
        const newH = this._$modifiedImage.data('initial-height') * scale;
        const maxH = Math.max(origH, newH);
        const maxOuterH = maxH + $origImageContainer.getExtents('b', 'tb');

        this._maxWidth = Math.max(origW, newW);
        this._maxHeight = Math.max(origH, newH);

        $origImageContainer
            .outerWidth(origW)
            .height(origH);

        this._$modifiedImage.parent()
            .outerWidth(newW)
            .height(newH);

        this._$origSplitContainer
            .outerWidth(this._maxWidth)
            .height(maxOuterH);

        this._$modifiedSplitContainer
            .outerWidth(this._maxWidth)
            .height(maxOuterH);

        this.$('.image-containers')
            .width(this._maxWidth)
            .height(maxH);

        this._$slider.width(this._maxWidth);

        /* Now that these are loaded, set the default for the split. */
        this.setSplitPercentage(this.DEFAULT_SPLIT_PCT);
    },

    /**
     * Return the initial size of the image.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize() {
        return {
            width: this._maxWidth,
            height: this._maxHeight,
        };
    },
});


/**
 * Displays a two-up, side-by-side view of two images.
 *
 * The images will be displayed horizontally, side-by-side. Comments will
 * only be able to be added against the new file.
 */
const ImageTwoUpDiffView = BaseImageView.extend({
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

    /**
     * Render the view.
     *
     * Returns:
     *     ImageTwoUpDiffView:
     *     This object, for chaining.
     */
    render() {
        this.$el.html(this.template(this.model.attributes));
        this.$commentRegion = this.$('.modified-image img');

        this._$origImage = this.$('.orig-image img');
        this._$modifiedImage = this.$('.modified-image img');

        this.loadImages(this.$('img'));

        return this;
    },

    /**
     * Return the initial size of the image.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize() {
        return {
            width: Math.max(this._$origImage.data('initial-width'),
                            this._$modifiedImage.data('initial-width')),
            height: Math.max(this._$origImage.data('initial-height'),
                             this._$modifiedImage.data('initial-height')),
        };
    },
});


/**
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
        'click .image-diff-mode': '_onImageModeClicked',
        'click .image-resolution-menu .menu-item': '_onImageZoomLevelClicked',
        'mousedown .selection-container': '_onMouseDown',
        'mouseup .selection-container': '_onMouseUp',
        'mousemove .selection-container': '_onMouseMove'
    },

    modeItemTemplate: _.template(
        '<li><a class="image-diff-mode" href="#" data-mode="<%- mode %>"><%- name %></a></li>'
    ),

    captionTableTemplate: _.template(
        '<table><tr><%= items %></tr></table>'
    ),

    captionItemTemplate: _.template([
        '<td>',
        ' <h1 class="caption">',
        '  <%- caption %>',
        ' </h1>',
        '</td>'
    ].join('')),

    errorTemplate: _.template([
        '<div class="review-ui-error">',
        ' <div class="rb-icon rb-icon-warning"></div>',
        ' <%- errorStr %>',
        '</div>'
        ].join('')),

    ANIM_SPEED_MS: 200,

    /**
     * Initialize the view.
     */
    initialize() {
        RB.FileAttachmentReviewableView.prototype.initialize.apply(
            this, arguments);

        _.bindAll(this, '_adjustPos');

        this._activeSelection = {};
        this._diffModeSelectors = {};
        this._diffModeViews = {};
        this._commentBlockViews = [];

        /*
         * Add any CommentBlockViews to the selection area when they're
         * created.
         */
        this.on('commentBlockViewAdded', commentBlockView => {
            commentBlockView.setSelectionRegionSizeFunc(
                () => _.pick(this._imageView.getSelectionRegion(),
                             'width', 'height'));
            commentBlockView.setScale(this.model.get('scale'));

            this._$selectionArea.append(commentBlockView.$el);

            this._commentBlockViews.push(commentBlockView);
            this.listenTo(
                commentBlockView, 'removing', () => {
                    this._commentBlockViews =
                        _.without(this._commentBlockViews, commentBlockView);
                });
        });

        this.listenTo(this.model, 'change:scale', (model, scale) => {
            this._commentBlockViews.forEach(view => view.setScale(scale));

            this.$('.image-resolution-menu-current')
                .text(scalingFactors.get(scale));

            /*
             * We must wait for the image views to finish scaling themselves,
             * otherwise the comment blocks will be in incorrect places.
             */
            _.defer(this._adjustPos);
        });
    },

    /**
     * Render the view.
     *
     * This will set up a selection area over the image and create a
     * selection rectangle that will be shown when dragging.
     *
     * Any time the window resizes, the comment positions will be adjusted.
     *
     * Returns:
     *     RB.ImageReviewableView:
     *     This object, for chaining.
     */
    renderContent() {
        const hasDiff = !!this.model.get('diffAgainstFileAttachmentID');

        this._$selectionArea = $('<div/>')
            .addClass('selection-container')
            .hide()
            .proxyTouchEvents();

        this._$selectionRect = $('<div/>')
            .addClass('selection-rect')
            .prependTo(this._$selectionArea)
            .proxyTouchEvents()
            .hide();

        this.$el
            /*
             * Register a hover event to hide the comments when the mouse
             * is not over the comment area.
             */
            .hover(
                () => {
                    this._$selectionArea.show();
                    this._adjustPos();
                },
                () => {
                    if (this._$selectionRect.is(':hidden') &&
                        !this.commentDlg) {
                        this._$selectionArea.hide();
                    }
                });

        const $wrapper = $('<div class="image-content" />')
            .append(this._$selectionArea);

        if (this.model.get('diffTypeMismatch')) {
            this.$el.append(this.errorTemplate({
                errorStr: gettext('These revisions cannot be compared because they are different file types.')
            }));
        } else if (hasDiff) {
            this._$modeBar = $('<ul class="image-diff-modes"/>')
                .appendTo(this.$el);

            this._$imageDiffs = $('<div class="image-diffs"/>');

            this._addDiffMode(ImageTwoUpDiffView);
            this._addDiffMode(ImageDifferenceDiffView);
            this._addDiffMode(ImageSplitDiffView);
            this._addDiffMode(ImageOnionDiffView);

            $wrapper
                .append(this._$imageDiffs)
                .appendTo(this.$el);

            this._setDiffMode(ImageTwoUpDiffView.prototype.mode);
        } else {
            this._imageView = new ImageAttachmentView({
                model: this.model
            });

            $wrapper
                .append(this._imageView.$el)
                .appendTo(this.$el);

            this._imageView.render();
        }

        /*
         * Reposition the selection area on page resize or loaded, so that
         * comments are in the right locations.
         */
        $(window).on({
            'load': this._adjustPos,
            'resize': this._adjustPos,
        });

        const $header = $('<div />')
            .addClass('review-ui-header')
            .prependTo(this.$el);

        if (this.model.get('numRevisions') > 1) {
            const $revisionLabel = $('<div id="revision_label" />')
                .appendTo($header);
            this._revisionLabelView = new RB.FileAttachmentRevisionLabelView({
                el: $revisionLabel,
                model: this.model
            });
            this._revisionLabelView.render();
            this.listenTo(this._revisionLabelView, 'revisionSelected',
                          this._onRevisionSelected);

            const $revisionSelector = $('<div id="attachment_revision_selector" />')
                .appendTo($header);
            this._revisionSelectorView = new RB.FileAttachmentRevisionSelectorView({
                el: $revisionSelector,
                model: this.model
            });
            this._revisionSelectorView.render();
            this.listenTo(this._revisionSelectorView, 'revisionSelected',
                          this._onRevisionSelected);

            if (!this.renderedInline) {
                if (hasDiff) {
                    const captionItems = [
                        this.captionItemTemplate({
                            caption: interpolate(
                                gettext('%(caption)s (revision %(revision)s)'),
                                {
                                    caption: this.model.get('diffCaption'),
                                    revision: this.model.get('diffRevision')
                                },
                                true)
                        }),
                        this.captionItemTemplate({
                            caption: interpolate(
                                gettext('%(caption)s (revision %(revision)s)'),
                                {
                                    caption: this.model.get('caption'),
                                    revision: this.model.get('fileRevision')
                                },
                                true)
                        })
                    ];

                    $header.append(this.captionTableTemplate({
                        items: captionItems.join('')
                    }));
                } else {
                    const $captionBar = $('<div class="image-single-revision">')
                        .appendTo($header);

                    $('<h1 class="caption" />')
                        .text(interpolate(
                            gettext('%(caption)s (revision %(revision)s)'),
                            {
                                caption: this.model.get('caption'),
                                revision: this.model.get('fileRevision')
                            },
                            true))
                        .appendTo($captionBar);
                }
            }
        } else {
            if (!this.renderedInline) {
                $header.addClass('image-single-revision');

                $('<h1 class="caption" />')
                    .text(this.model.get('caption'))
                    .appendTo($header);
            }
        }

        const $resolutionMenu = $([
          '<li class="image-resolution-menu has-menu">',
          ' <a href="#" class="menu-header">',
          '  <span class="fa fa-search-plus"></span>',
          '  <span class="image-resolution-menu-current">100%</span>',
          '  <span class="rb-icon rb-icon-dropdown-arrow">',
          ' </a>',
          ' <ul class="menu" />',
          '</li>',
        ].join(''));
        const $menu = $resolutionMenu.find('.menu');

        scalingFactors.forEach((text, scale) => {
            $(`<li class="menu-item" data-image-scale="${scale}" />`)
                .text(text)
                .appendTo($menu);
        });

        if (hasDiff) {
            this._$modeBar.append($resolutionMenu);
        } else {
            this.$('.caption').after($resolutionMenu);
        }
    },

    /**
     * Callback for when a new file revision is selected.
     *
     * This supports single revisions and diffs. If 'base' is 0, a
     * single revision is selected, If not, the diff between `base` and
     * `tip` will be shown.
     *
     * Args:
     *     revisions (Array of number):
     *         A two-element array of [base, tip] revisions.
     */
    _onRevisionSelected(revisions) {
        const revisionIDs = this.model.get('attachmentRevisionIDs');
        const [base, tip] = revisions;

        // Ignore clicks on No Diff Label
        if (tip === 0) {
            return;
        }

        /*
         * Eventually these hard redirects will use a router
         * (see diffViewerPageView.js for example)
         * this.router.navigate(base + '-' + tip + '/', {trigger: true});
         */
        const revisionTip = revisionIDs[tip-1];
        let redirectURL;

        if (base === 0) {
            redirectURL = `../${revisionTip}/`;
        } else {
            const revisionBase = revisionIDs[base-1];
            redirectURL = `../${revisionBase}-${revisionTip}/`;
        }

        window.location.replace(redirectURL);
    },

    /**
     * Register a diff mode.
     *
     * This will register a class for the mode and add an entry to the
     * mode bar.
     *
     * Args:
     *     ViewClass (function):
     *         The constructor for the view class.
     */
    _addDiffMode(ViewClass) {
        const mode = ViewClass.prototype.mode;
        const view = new ViewClass({
            model: this.model
        });

        this._diffModeViews[mode] = view;
        view.$el.hide();
        this._$imageDiffs.append(view.$el);
        view.render();

        const $selector = $(this.modeItemTemplate({
            mode: mode,
            name: view.name
        }));

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
        const selectorWidth = $selector.outerWidth(true);
        $selector
            .removeClass('selected')
            .width(selectorWidth);

        this._diffModeSelectors[mode] = $selector;
    },

    /**
     * Set the current diff mode.
     *
     * That mode will be displayed on the page and comments will be shown.
     *
     * The height of the review UI will animate to the new height for this
     * mode.
     *
     * Args:
     *     mode (string):
     *         The new diff mode.
     */
    _setDiffMode(mode) {
        const newView = this._diffModeViews[mode];

        if (this._imageView) {
            this._diffModeSelectors[this._imageView.mode]
                .removeClass('selected');

            newView.$el.show();
            const height = newView.$el.height();
            newView.$el.hide();

            this._$imageDiffs.animate({
                height: height,
                duration: this.ANIM_SPEED_MS
            });

            this._$selectionArea.fadeOut(this.ANIM_SPEED_MS);
            this._imageView.$el.fadeOut(
                this.ANIM_SPEED_MS,
                () => this._showDiffMode(newView, true));
        } else {
            this._showDiffMode(newView);
        }

        this._diffModeSelectors[newView.mode]
            .addClass('selected');
    },

    /**
     * Show the diff mode.
     *
     * This is called by _setDiffMode when it's ready to actually show the
     * new mode.
     *
     * The new mode will be faded in, if we're animating, or immediately shown
     * otherwise.
     *
     * Args:
     *     newView (Backbone.View):
     *         The new view to show.
     *
     *     animate (boolean):
     *         Whether to animate the transition.
     */
    _showDiffMode(newView, animate) {
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

    /**
     * Handler for when a mode in the diff mode bar is clicked.
     *
     * Sets the diff view to the given mode.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onImageModeClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._setDiffMode($(e.target).data('mode'));
    },

    /**
     * Handler for when a zoom level is clicked.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onImageZoomLevelClicked(e) {
        e.preventDefault();
        e.stopPropagation();
        this.model.set('scale', $(e.target).data('image-scale'));
    },

    /**
     * Handle a mousedown on the selection area.
     *
     * If this is the first mouse button, and it's not being placed on
     * an existing comment block, then this will begin the creation of a new
     * comment block starting at the mousedown coordinates.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onMouseDown(e) {
        if (e.which === 1 &&
            !this.commentDlg &&
            !$(e.target).hasClass('selection-flag')) {
            const offset = this._$selectionArea.offset();

            this._activeSelection.beginX =
                e.pageX - Math.floor(offset.left) - 1;
            this._activeSelection.beginY =
                e.pageY - Math.floor(offset.top) - 1;

            const updateData = {
                left: this._activeSelection.beginX,
                top: this._activeSelection.beginY,
                width: 1,
                height: 1
            };

            this._$selectionRect
                .css(updateData)
                .data(updateData)
                .show();

            if (this._$selectionRect.is(':hidden')) {
                this.commentDlg.close();
            }

            return false;
        }
    },

    /**
     * Handle a mouseup on the selection area.
     *
     * This will finalize the creation of a comment block and pop up the
     * comment dialog.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onMouseUp(e) {
        if (!this.commentDlg &&
            this._$selectionRect.is(':visible')) {
            e.stopPropagation();
            this._$selectionRect.hide();

            /*
             * If we don't pass an arbitrary minimum size threshold,
             * don't do anything. This helps avoid making people mad
             * if they accidentally click on the image.
             */
            const position = this._$selectionRect.data();
            const scale = this.model.get('scale');

            if (position.width > 5 && position.height > 5) {
                this.createAndEditCommentBlock({
                    x: Math.floor(position.left / scale),
                    y: Math.floor(position.top / scale),
                    width: Math.floor(position.width / scale),
                    height: Math.floor(position.height / scale),
                });
            }
        }
    },

    /**
     * Handle a mousemove on the selection area.
     *
     * If we're creating a comment block, this will update the
     * size/position of the block.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onMouseMove(e) {
        if (!this.commentDlg && this._$selectionRect.is(':visible')) {
            const offset = this._$selectionArea.offset();
            const x = e.pageX - Math.floor(offset.left) - 1;
            const y = e.pageY - Math.floor(offset.top) - 1;
            const updateData = {};

            if (this._activeSelection.beginX <= x) {
                updateData.left = this._activeSelection.beginX;
                updateData.width = x - this._activeSelection.beginX;
            } else {
                updateData.left = x;
                updateData.width = this._activeSelection.beginX - x;
            }

            if (this._activeSelection.beginY <= y) {
                updateData.top = this._activeSelection.beginY;
                updateData.height = y - this._activeSelection.beginY;
            } else {
                updateData.top = y;
                updateData.height = this._activeSelection.beginY - y;
            }

            this._$selectionRect
                .css(updateData)
                .data(updateData);

            return false;
        }
    },

    /**
     * Reposition the selection area to the right locations.
     */
    _adjustPos() {
        const region = this._imageView.getSelectionRegion();

        this._$selectionArea
            .width(region.width)
            .height(region.height)
            .css({
                left: region.left,
                top: region.top
            });

        if (this._$imageDiffs) {
            this._$imageDiffs.height(this._imageView.$el.height());
        }
    }
});


})();
