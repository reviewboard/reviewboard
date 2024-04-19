/**
 * Displays a review UI for images.
 */

import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';

import { type ImageReviewable } from '../models/imageReviewableModel';
import { type AbstractReviewableViewOptions } from './abstractReviewableView';
import {
    FileAttachmentReviewableView,
} from './fileAttachmentReviewableView';
import { RegionCommentBlockView } from './regionCommentBlockView';


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
 * An object to hold the size of an image.
 *
 * Version Added:
 *     7.0
 */
interface ImageSize {
    height: number;
    width: number;
}


/**
 * Base class for providing a view onto an image or diff of images.
 *
 * This handles the common functionality, such as loading images, determining
 * the image region, rendering, and so on.
 *
 * Subclasses must, at a minimum, provide a 'mode', 'modeName', and must set
 * $commentRegion to an element representing the region where comments are
 * allowed.
 */
@spina({
    prototypeAttrs: ['mode', 'modeName'],
})
class BaseImageView extends BaseView<ImageReviewable> {
    /**
     * The name of the diff mode, used in element IDs.
     *
     * This should be overridden by subclasses.
     */
    static mode: string = null;

    /**
     * The user-visible name of the diff mode.
     *
     * This should be overridden by subclasses.
     */
    static modeName: string = null;

    /**********************
     * Instance variables *
     **********************/

    /** The current comment region. */
    $commentRegion: JQuery;

    /** The image elements. */
    protected _$images: JQuery;

    /**
     * Initialize the view.
     */
    initialize() {
        this.$commentRegion = null;

        this.listenTo(this.model,
                      'change:scale',
                      (model, scale) => this._onScaleChanged(scale));
    }

    /**
     * Return the CSS class name for this view.
     *
     * Returns:
     *     string:
     *     A class name based on the current mode.
     */
    static className() {
        return `image-diff-${this.mode}`;
    }

    /**
     * Load a list of images.
     *
     * Once each image is loaded, the view's _onImagesLoaded function will
     * be called. Subclasses can override this to provide functionality based
     * on image sizes and content.
     *
     * Args:
     *     $images (jQuery):
     *         The image elements to load.
     */
    loadImages($images: JQuery) {
        const scale = this.model.get('scale');

        let loadsRemaining = $images.length;

        this._$images = $images;

        $images.each((ix: number, image: HTMLImageElement) => {
            const $image = $(image);

            if ($image.data('initial-width') === undefined) {
                image.onload = () => {
                    loadsRemaining--;
                    console.assert(loadsRemaining >= 0);

                    $image
                        .data({
                            'initial-height': image.height,
                            'initial-width': image.width,
                        })
                        .css({
                            height: image.height * scale,
                            width: image.width * scale,
                        });

                    if (loadsRemaining === 0) {
                        _.defer(() => {
                            this._onImagesLoaded();
                            this.trigger('regionChanged');
                        });
                    }
                };
            } else {
                loadsRemaining--;

                if (loadsRemaining === 0) {
                    this._onImagesLoaded();
                    this.trigger('regionChanged');
                }
            }
        });
    }

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
            height: $region.height(),
            left: offset.left,
            top: offset.top,
            width: $region.width(),
        };
    }

    /**
     * Callback handler for when the images on the view are loaded.
     *
     * Subclasses that override this method must call the base method so that
     * images can be scaled appropriately.
     */
    _onImagesLoaded() {
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
    }

    /**
     * Handle the image scale being changed.
     *
     * Args:
     *     scale (number):
     *         The new image scaling factor (where 1.0 is 100%, 0.5 is 50%,
     *         etc).
     */
    _onScaleChanged(scale: number) {
        this._$images.each((index, el) => {
            const $image = $(el);

            $image.css({
                height: $image.data('initial-height') * scale,
                width: $image.data('initial-width') * scale,
            });
        });
    }

    /**
     * Return the initial size of the image.
     *
     * Subclasses must override this.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize(): ImageSize {
        console.assert(
            false, 'subclass of BaseImageView must implement getInitialSize');

        return null;
    }
}


/**
 * Displays a single image.
 *
 * This view is used for standalone images, without diffs. It displays the
 * image and allows it to be commented on.
 */
@spina
class ImageAttachmentView extends BaseImageView {
    static mode = 'attachment';
    static tagName = 'img';

    /**
     * Render the view.
     */
    onInitialRender() {
        this.$el.attr({
            src: this.model.get('imageURL'),
            title: this.model.get('caption'),
        });

        this.$commentRegion = this.$el;

        this.loadImages(this.$el);
    }

    /**
     * Return the initial size of the image.
     *
     * Subclasses must override this.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize(): ImageSize {
        const $img = this._$images.eq(0);

        return {
            height: $img.data('initial-height'),
            width: $img.data('initial-width'),
        };
    }
}


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
@spina
class ImageDifferenceDiffView extends BaseImageView {
    static mode = 'difference';
    static modeName = _`Difference`;

    static template = _.template(dedent`
        <div class="image-container">
         <canvas></canvas>
        </div>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The canvas used for drawing the difference. */
    #$canvas: JQuery<HTMLCanvasElement>;

    /** The (hidden) original image element. */
    #origImage: HTMLImageElement = null;

    /** The maximum height of the original and modified images. */
    #maxHeight: number;

    /** The maximum width of the original and modified images. */
    #maxWidth: number;

    /** The (hidden) modified image element. */
    #modifiedImage: HTMLImageElement = null;

    /**
     * Render the view.
     *
     * Image elements representing the original and modified images will be
     * created and loaded. After loading, _onImagesLoaded will handle
     * populating the canvas with the difference view.
     */
    onInitialRender() {
        this.$el.html(ImageDifferenceDiffView.template(this.model.attributes));

        this.$commentRegion = this.$('canvas');
        this.#$canvas = this.$commentRegion as JQuery<HTMLCanvasElement>;

        this.#origImage = new Image();
        this.#origImage.src = this.model.get('diffAgainstImageURL');

        this.#modifiedImage = new Image();
        this.#modifiedImage.src = this.model.get('imageURL');

        this.loadImages($([this.#origImage, this.#modifiedImage]));
    }

    /**
     * Render the difference between two images onto the canvas.
     */
    _onImagesLoaded() {
        const origImage = this.#origImage;
        const modifiedImage = this.#modifiedImage;
        const scale = this.model.get('scale');

        this.#maxWidth = Math.max(origImage.width, modifiedImage.width);
        this.#maxHeight = Math.max(origImage.height, modifiedImage.height);

        super._onImagesLoaded();

        this.#$canvas
            .attr({
                height: this.#maxHeight,
                width: this.#maxWidth,
            })
            .css({
                height: this.#maxHeight * scale + 'px',
                width: this.#maxWidth * scale + 'px',
            });

        const $modifiedCanvas: JQuery<HTMLCanvasElement> =
            ($('<canvas>') as JQuery<HTMLCanvasElement>)
            .attr({
                height: this.#maxHeight,
                width: this.#maxWidth,
            });

        const origContext = this.#$canvas[0].getContext('2d');
        origContext.drawImage(origImage, 0, 0);

        const modifiedContext = $modifiedCanvas[0].getContext('2d');
        modifiedContext.drawImage(modifiedImage, 0, 0);

        const origImageData = origContext.getImageData(
            0, 0, this.#maxWidth, this.#maxHeight);
        const origPixels = origImageData.data;

        const modifiedPixels = modifiedContext.getImageData(
            0, 0, this.#maxWidth, this.#maxHeight).data;

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
    }

    /**
     * Handle the image scale being changed.
     *
     * Args:
     *     scale (number):
     *         The new image scaling factor (where 1.0 is 100%, 0.5 is 50%,
     *         etc).
     */
    _onScaleChanged(scale) {
        this.#$canvas.css({
            height: this.#maxHeight * scale + 'px',
            width: this.#maxWidth * scale + 'px',
        });
    }

    /**
     * Return the initial size of the image.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize(): ImageSize {
        return {
            height: this.#maxHeight,
            width: this.#maxWidth,
        };
    }
}


/**
 * Displays an onion skin view of two images.
 *
 * Onion skinning allows the user to see subtle changes in two images by
 * altering the transparency of the modified image. Through a slider, they'll
 * be able to play around with the transparency and see if any pixels move,
 * disappear, or otherwise change.
 */
@spina
class ImageOnionDiffView extends BaseImageView {
    static mode = 'onion';
    static modeName = _`Onion Skin`;

    static template = _.template(dedent`
        <div class="image-containers">
         <div class="orig-image">
          <img title="<%- caption %>" src="<%- diffAgainstImageURL %>">
         </div>
         <div class="modified-image">
          <img title="<%- caption %>" src="<%- imageURL %>">
         </div>
        </div>
        <div class="image-slider"></div>
    `);

    static DEFAULT_OPACITY = 0.25;

    /**********************
     * Instance variables *
     **********************/

    /** The modified image. */
    #$modifiedImage: JQuery = null;

    /** The container element for the modified image. */
    #$modifiedImageContainer: JQuery = null;

    /** The original image. */
    #$origImage: JQuery = null;

    /**
     * Render the view.
     *
     * This will set up the slider and set it to a default of 25% opacity.
     *
     * Returns:
     *     ImageOnionDiffView:
     *     This object, for chaining.
     */
    onInitialRender() {
        this.$el.html(ImageOnionDiffView.template(this.model.attributes));

        this.$commentRegion = this.$('.image-containers');
        this.#$origImage = this.$('.orig-image img');
        this.#$modifiedImage = this.$('.modified-image img');
        this.#$modifiedImageContainer = this.#$modifiedImage.parent();

        this.$('.image-slider')
            .slider({
                slide: (e, ui) => this.setOpacity(ui.value / 100.0),
                value: ImageOnionDiffView.DEFAULT_OPACITY * 100,
            });

        this.setOpacity(ImageOnionDiffView.DEFAULT_OPACITY);

        this.loadImages(this.$('img'));
    }

    /**
     * Set the opacity value for the images.
     *
     * Args:
     *     percentage (number):
     *         The opacity percentage, in [0.0, 1.0].
     */
    setOpacity(percentage: number) {
        this.#$modifiedImageContainer.css('opacity', percentage);
    }

    /**
     * Position the images after they load.
     *
     * The images will be layered on top of each other, consuming the
     * same width and height.
     */
    _onImagesLoaded() {
        super._onImagesLoaded();
        this._resize();
    }

    /**
     * Handle the image scale being changed.
     *
     * Args:
     *     scale (number):
     *         The new image scaling factor (where 1.0 is 100%, 0.5 is 50%,
     *         etc).
     */
    _onScaleChanged(scale: number) {
        super._onScaleChanged(scale);
        this._resize();
    }

    /**
     * Resize the image containers.
     */
    _resize() {
        const scale = this.model.get('scale');
        const origW = this.#$origImage.data('initial-width') * scale;
        const origH = this.#$origImage.data('initial-height') * scale;
        const newW = this.#$modifiedImage.data('initial-width') * scale;
        const newH = this.#$modifiedImage.data('initial-height') * scale;

        this.#$origImage.parent()
            .width(origW)
            .height(origH);

        this.#$modifiedImage.parent()
            .width(newW)
            .height(newH);

        this.$('.image-containers')
            .width(Math.max(origW, newW))
            .height(Math.max(origH, newH));
    }

    /**
     * Return the initial size of the image.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize(): ImageSize {
        return {
            height: Math.max(this.#$origImage.data('initial-height'),
                             this.#$modifiedImage.data('initial-height')),
            width: Math.max(this.#$origImage.data('initial-width'),
                            this.#$modifiedImage.data('initial-width')),
        };
    }
}


/**
 * Displays an overlapping split view between two images.
 *
 * The images will be overlapping, and a horizontal slider will control how
 * much of the modified image is shown. The modified image will overlap the
 * original image. This makes it easy to compare the two images incrementally.
 */
@spina
class ImageSplitDiffView extends BaseImageView {
    static mode = 'split';
    static modeName = _`Split`;

    static template = _.template(dedent`
        <div class="image-containers">
         <div class="image-diff-split-container-orig">
          <div class="orig-image">
           <img title="<%- caption %>" src="<%- diffAgainstImageURL %>">
          </div>
         </div>
         <div class="image-diff-split-container-modified">
          <div class="modified-image">
           <img title="<%- caption %>" src="<%- imageURL %>">
          </div>
         </div>
        </div>
        <div class="image-slider"></div>
    `);

    /** The default slider position of 25%. */
    static DEFAULT_SPLIT_PCT = 0.25;

    /**********************
     * Instance variables *
     **********************/

    /** The modified image. */
    #$modifiedImage: JQuery = null;

    /** The container for the modified image. */
    #$modifiedSplitContainer: JQuery = null;

    /** The original image. */
    #$origImage: JQuery = null;

    /** The container for the original image. */
    #$origSplitContainer: JQuery = null;

    /** The slider element. */
    #$slider: JQuery = null;

    /** The maximimum height of the original and modified images. */
    #maxHeight = 0;

    /** The maximum width of the original and modified images. */
    #maxWidth = 0;

    /**
     * Render the view.
     */
    onInitialRender() {
        this.$el.html(ImageSplitDiffView.template(this.model.attributes));

        this.$commentRegion = this.$('.image-containers');
        this.#$origImage = this.$('.orig-image img');
        this.#$modifiedImage = this.$('.modified-image img');
        this.#$origSplitContainer = this.$('.image-diff-split-container-orig');
        this.#$modifiedSplitContainer =
            this.$('.image-diff-split-container-modified');

        this.#$slider = this.$('.image-slider')
            .slider({
                slide: (e, ui) => this.setSplitPercentage(ui.value / 100.0),
                value: ImageSplitDiffView.DEFAULT_SPLIT_PCT * 100,
            });

        this.loadImages(this.$('img'));

        return this;
    }

    /**
     * Set the percentage for the split view.
     *
     * Args:
     *     percentage (number):
     *         The position of the slider, in [0.0, 1.0].
     */
    setSplitPercentage(percentage: number) {
        this.#$origSplitContainer.outerWidth(this.#maxWidth * percentage);
        this.#$modifiedSplitContainer.outerWidth(
            this.#maxWidth * (1.0 - percentage));
    }

    /**
     * Position the images after they load.
     *
     * The images will be layered on top of each other, anchored to the
     * top-left.
     *
     * The slider will match the width of the two images, in order to
     * position the slider's handle with the divider between images.
     */
    _onImagesLoaded() {
        super._onImagesLoaded();
        this._resize();
    }

    /**
     * Handle the image scale being changed.
     *
     * Args:
     *     scale (number):
     *         The new image scaling factor (where 1.0 is 100%, 0.5 is 50%,
     *         etc).
     */
    _onScaleChanged(scale: number) {
        super._onScaleChanged(scale);
        this._resize();
    }

    /**
     * Resize the image containers.
     */
    _resize() {
        const $origImageContainer = this.#$origImage.parent();
        const scale = this.model.get('scale');
        const origW = this.#$origImage.data('initial-width') * scale;
        const origH = this.#$origImage.data('initial-height') * scale;
        const newW = this.#$modifiedImage.data('initial-width') * scale;
        const newH = this.#$modifiedImage.data('initial-height') * scale;
        const maxH = Math.max(origH, newH);
        const maxOuterH = maxH + $origImageContainer.getExtents('b', 'tb');

        this.#maxWidth = Math.max(origW, newW);
        this.#maxHeight = Math.max(origH, newH);

        $origImageContainer
            .outerWidth(origW)
            .height(origH);

        this.#$modifiedImage.parent()
            .outerWidth(newW)
            .height(newH);

        this.#$origSplitContainer
            .outerWidth(this.#maxWidth)
            .height(maxOuterH);

        this.#$modifiedSplitContainer
            .outerWidth(this.#maxWidth)
            .height(maxOuterH);

        this.$('.image-containers')
            .width(this.#maxWidth)
            .height(maxH);

        this.#$slider.width(this.#maxWidth);

        /* Now that these are loaded, set the default for the split. */
        this.setSplitPercentage(ImageSplitDiffView.DEFAULT_SPLIT_PCT);
    }

    /**
     * Return the initial size of the image.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize(): ImageSize {
        return {
            height: this.#maxHeight,
            width: this.#maxWidth,
        };
    }
}


/**
 * Displays a two-up, side-by-side view of two images.
 *
 * The images will be displayed horizontally, side-by-side. Comments will
 * only be able to be added against the new file.
 */
@spina
class ImageTwoUpDiffView extends BaseImageView {
    static mode = 'two-up';
    static modeName = _`Two-Up`;

    static template = _.template(dedent`
        <div class="image-container image-container-orig">
         <div class="orig-image">
          <img title="<%- caption %>" src="<%- diffAgainstImageURL %>">
         </div>
        </div>
        <div class="image-container image-container-modified">
         <div class="modified-image">
          <img title="<%- caption %>" src="<%- imageURL %>">
         </div>
        </div>
    `);

    /**********************
     * Instance variables *
     **********************/

    /** The original image. */
    #$origImage: JQuery = null;

    /** The modified image. */
    #$modifiedImage: JQuery = null;

    /**
     * Render the view.
     */
    onInitialRender() {
        this.$el.html(ImageTwoUpDiffView.template(this.model.attributes));
        this.$commentRegion = this.$('.modified-image img');

        this.#$origImage = this.$('.orig-image img');
        this.#$modifiedImage = this.$('.modified-image img');

        this.loadImages(this.$('img'));
    }

    /**
     * Return the initial size of the image.
     *
     * Returns:
     *     object:
     *     An object containing the initial height and width of the image.
     */
    getInitialSize(): ImageSize {
        return {
            height: Math.max(this.#$origImage.data('initial-height'),
                             this.#$modifiedImage.data('initial-height')),
            width: Math.max(this.#$origImage.data('initial-width'),
                            this.#$modifiedImage.data('initial-width')),
        };
    }
}


/** An object for holding information about the current selection. */
interface ActiveSelection {
    beginX?: number;
    beginY?: number;
}


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
@spina
export class ImageReviewableView<
    TModel extends ImageReviewable = ImageReviewable
> extends FileAttachmentReviewableView<TModel> {
    static className = 'image-review-ui';

    static commentBlockView = RegionCommentBlockView;

    static events: EventsHash = {
        'click .image-diff-mode': '_onImageModeClicked',
        'click .image-resolution-menu .menu-item': '_onImageZoomLevelClicked',
        'mousedown .selection-container': '_onMouseDown',
        'mousemove .selection-container': '_onMouseMove',
        'mouseup .selection-container': '_onMouseUp',
    };

    static modeItemTemplate = _.template(dedent`
        <li>
         <a class="image-diff-mode" href="#" data-mode="<%- mode %>">
          <%- name %>
         </a>
        </li>
    `);

    static captionTableTemplate = _.template(
        '<table><tr><%= items %></tr></table>'
    );

    static captionItemTemplate = _.template(dedent`
        <td>
         <h1 class="caption">
          <%- caption %>
         </h1>
        </td>
    `);

    static errorTemplate = _.template(dedent`
        <div class="review-ui-error">
         <div class="rb-icon rb-icon-warning"></div>
         <%- errorStr %>
        </div>
    `);

    static ANIM_SPEED_MS = 200;

    /**********************
     * Instance variables *
     **********************/

    /** The container for all of the diff views. */
    #$imageDiffs: JQuery;

    /** The UI for choosing the diff mode. */
    #$modeBar: JQuery = null;

    /** The selection area container. */
    #$selectionArea: JQuery;

    /** The selection box . */
    #$selectionRect: JQuery;

    /** The active selection. */
    #activeSelection: ActiveSelection = {};

    /** The block views for all existing comments. */
    #commentBlockViews: RegionCommentBlockView[] = [];

    /** The views for the different diff modes. */
    #diffModeViews: { [key: string]: BaseImageView } = {};

    /** The menu elements for the different diff modes. */
    #diffModeSelectors: { [key: string]: JQuery } = {};

    /** The basic image view. */
    #imageView: ImageAttachmentView = null;

    /**
     * Initialize the view.
     */
    initialize(options: Partial<AbstractReviewableViewOptions> = {}) {
        super.initialize(options);

        _.bindAll(this, '_adjustPos');

        /*
         * Add any CommentBlockViews to the selection area when they're
         * created.
         */
        this.on('commentBlockViewAdded', commentBlockView => {
            commentBlockView.setSelectionRegionSizeFunc(
                () => _.pick(this.#imageView.getSelectionRegion(),
                             'width', 'height'));
            commentBlockView.setScale(this.model.get('scale'));

            this.#$selectionArea.append(commentBlockView.$el);

            this.#commentBlockViews.push(commentBlockView);
            this.listenTo(
                commentBlockView, 'removing', () => {
                    this.#commentBlockViews =
                        _.without(this.#commentBlockViews, commentBlockView);
                });
        });

        this.listenTo(this.model, 'change:scale', (model, scale) => {
            this.#commentBlockViews.forEach(view => view.setScale(scale));

            this.$('.image-resolution-menu-current')
                .text(scalingFactors.get(scale));

            /*
             * We must wait for the image views to finish scaling themselves,
             * otherwise the comment blocks will be in incorrect places.
             */
            _.defer(this._adjustPos);
        });
    }

    /**
     * Render the view.
     *
     * This will set up a selection area over the image and create a
     * selection rectangle that will be shown when dragging.
     *
     * Any time the window resizes, the comment positions will be adjusted.
     */
    renderContent() {
        const hasDiff = !!this.model.get('diffAgainstFileAttachmentID');

        this.#$selectionArea = $('<div>')
            .addClass('selection-container')
            .hide()
            .proxyTouchEvents();

        this.#$selectionRect = $('<div>')
            .addClass('selection-rect')
            .prependTo(this.#$selectionArea)
            .proxyTouchEvents()
            .hide();

        /*
         * Register a hover event to hide the comments when the mouse
         * is not over the comment area.
         */
        this.$el
            .hover(
                () => {
                    this.#$selectionArea.show();
                    this._adjustPos();
                },
                () => {
                    if (this.#$selectionRect.is(':hidden') &&
                        !this.commentDlg) {
                        this.#$selectionArea.hide();
                    }
                });

        const $wrapper = $('<div class="image-content">')
            .append(this.#$selectionArea);

        if (this.model.get('diffTypeMismatch')) {
            this.$el.append(ImageReviewableView.errorTemplate({
                errorStr: _`
                    These revisions cannot be compared because they
                    are different file types.`,
            }));
        } else if (hasDiff) {
            this.#$modeBar = $('<ul class="image-diff-modes">')
                .appendTo(this.$el);

            this.#$imageDiffs = $('<div class="image-diffs">');

            this._addDiffMode(ImageTwoUpDiffView);
            this._addDiffMode(ImageDifferenceDiffView);
            this._addDiffMode(ImageSplitDiffView);
            this._addDiffMode(ImageOnionDiffView);

            $wrapper
                .append(this.#$imageDiffs)
                .appendTo(this.$el);

            this._setDiffMode(ImageTwoUpDiffView.mode);
        } else {
            if (this.renderedInline) {
                /*
                 * When we're rendered inline, even if we don't have a diff, we
                 * add the mode bar so that we have somewhere to stick the
                 * resolution drop-down. This needs to have an empty anchor in
                 * it for layout to succeed.
                 *
                 * This will be reworked later once we spend some time giving
                 * review UIs some love, possibly with something like a
                 * floating toolbar.
                 */
                this.#$modeBar = $('<ul class="image-diff-modes">')
                    .append('<li><a>&nbsp;</a></li>')
                    .appendTo(this.$el);
            }

            this.#imageView = new ImageAttachmentView({
                model: this.model,
            });

            $wrapper
                .append(this.#imageView.$el)
                .appendTo(this.$el);

            this.#imageView.render();
        }

        /*
         * Reposition the selection area on page resize or loaded, so that
         * comments are in the right locations.
         */
        $(window).on({
            'load': this._adjustPos,
            'resize': this._adjustPos,
        });

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
                          this._onRevisionSelected);

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
                          this._onRevisionSelected);

            if (!this.renderedInline) {
                if (hasDiff) {
                    const caption = this.model.get('caption');
                    const revision = this.model.get('fileRevision');
                    const diffCaption = this.model.get('diffCaption');
                    const diffRevision = this.model.get('diffRevision');

                    const captionItems = [
                        ImageReviewableView.captionItemTemplate({
                            caption:
                                _`${diffCaption} (revision ${diffRevision})`,
                        }),
                        ImageReviewableView.captionItemTemplate({
                            caption: _`${caption} (revision ${revision})`,
                        }),
                    ];

                    $header.append(ImageReviewableView.captionTableTemplate({
                        items: captionItems.join(''),
                    }));
                } else {
                    const $captionBar =
                        $('<div class="image-single-revision">')
                        .appendTo($header);

                    const caption = this.model.get('caption');
                    const revision = this.model.get('fileRevision');
                    $('<h1 class="caption">')
                        .text(_`${caption} (revision ${revision})`)
                        .appendTo($captionBar);
                }
            }
        } else {
            if (!this.renderedInline) {
                $header.addClass('image-single-revision');

                $('<h1 class="caption">')
                    .text(this.model.get('caption'))
                    .appendTo($header);
            }
        }

        const $resolutionMenu = $(dedent`
            <li class="image-resolution-menu has-menu">
             <a href="#" class="menu-header">
              <span class="fa fa-search-plus"></span>
              <span class="image-resolution-menu-current">100%</span>
              <span class="rb-icon rb-icon-dropdown-arrow">
             </a>
             <ul class="menu"></ul>
            </li>
        `);
        const $menu = $resolutionMenu.find('.menu');

        scalingFactors.forEach((text, scale) => {
            $(`<li class="menu-item" data-image-scale="${scale}">`)
                .text(text)
                .appendTo($menu);
        });

        if (this.#$modeBar !== null) {
            this.#$modeBar.append($resolutionMenu);
        } else {
            this.$('.caption').after($resolutionMenu);
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
     *     revisions (Array of number):
     *         A two-element array of [base, tip] revisions.
     */
    _onRevisionSelected(revisions: [number, number]) {
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

        RB.navigateTo(redirectURL, {replace: true});
    }

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
    _addDiffMode(ViewClass: typeof BaseImageView) {
        const mode = ViewClass.prototype.mode;
        const view = new ViewClass({
            model: this.model,
        });

        this.#diffModeViews[mode] = view;
        view.$el.hide();
        this.#$imageDiffs.append(view.$el);
        view.render();

        const $selector = $(ImageReviewableView.modeItemTemplate({
            mode: mode,
            name: view.modeName,
        }));

        /*
         * Since we're making the text bold when selected, we need to reserve
         * the right amount of space for the bold text, so that the contents
         * don't shift.
         *
         * This is kind of ugly, but really the only good way.
         */
        $selector
            .appendTo(this.#$modeBar)
            .addClass('selected');
        const selectorWidth = $selector.outerWidth(true);

        $selector
            .removeClass('selected')
            .width(selectorWidth);

        this.#diffModeSelectors[mode] = $selector;
    }

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
    _setDiffMode(mode: string) {
        const newView = this.#diffModeViews[mode];

        if (this.#imageView) {
            this.#diffModeSelectors[this.#imageView.mode]
                .removeClass('selected');

            newView.$el.show();
            const height = newView.$el.height();
            newView.$el.hide();

            this.#$imageDiffs.animate({
                duration: ImageReviewableView.ANIM_SPEED_MS,
                height: height,
            });

            this.#$selectionArea.fadeOut(ImageReviewableView.ANIM_SPEED_MS);
            this.#imageView.$el.fadeOut(
                ImageReviewableView.ANIM_SPEED_MS,
                () => this._showDiffMode(newView, true));
        } else {
            this._showDiffMode(newView);
        }

        this.#diffModeSelectors[newView.mode]
            .addClass('selected');
    }

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
    _showDiffMode(
        newView: BaseImageView,
        animate?: boolean,
    ) {
        if (this.#imageView) {
            this.stopListening(this.#imageView, 'regionChanged');
        }

        this.#imageView = newView;

        if (animate) {
            this.#imageView.$el.fadeIn(ImageReviewableView.ANIM_SPEED_MS);
            this.#$selectionArea.fadeIn(ImageReviewableView.ANIM_SPEED_MS);
        } else {
            this.#imageView.$el.show();
            this.#$selectionArea.show();
        }

        this.listenTo(this.#imageView, 'regionChanged', this._adjustPos);

        this._adjustPos();
    }

    /**
     * Handler for when a mode in the diff mode bar is clicked.
     *
     * Sets the diff view to the given mode.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onImageModeClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        this._setDiffMode($(e.target).data('mode'));
    }

    /**
     * Handler for when a zoom level is clicked.
     *
     * Args:
     *     e (Event):
     *         The event which triggered the callback.
     */
    _onImageZoomLevelClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        this.model.set('scale', $(e.target).data('image-scale'));
    }

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
    _onMouseDown(e: MouseEvent) {
        if (e.which === 1 &&
            !this.commentDlg &&
            !$(e.target).hasClass('selection-flag')) {
            const offset = this.#$selectionArea.offset();

            this.#activeSelection.beginX =
                e.pageX - Math.floor(offset.left) - 1;
            this.#activeSelection.beginY =
                e.pageY - Math.floor(offset.top) - 1;

            const updateData = {
                height: 1,
                left: this.#activeSelection.beginX,
                top: this.#activeSelection.beginY,
                width: 1,
            };

            this.#$selectionRect
                .css(updateData)
                .data(updateData)
                .show();

            if (this.#$selectionRect.is(':hidden')) {
                this.commentDlg.close();
            }

            e.stopPropagation();
            e.preventDefault();
        }
    }

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
    _onMouseUp(e: MouseEvent) {
        if (!this.commentDlg &&
            this.#$selectionRect.is(':visible')) {
            e.stopPropagation();
            e.preventDefault();

            this.#$selectionRect.hide();

            /*
             * If we don't pass an arbitrary minimum size threshold,
             * don't do anything. This helps avoid making people mad
             * if they accidentally click on the image.
             */
            const position = this.#$selectionRect.data();
            const scale = this.model.get('scale');

            if (position.width > 5 && position.height > 5) {
                this.createAndEditCommentBlock({
                    height: Math.floor(position.height / scale),
                    width: Math.floor(position.width / scale),
                    x: Math.floor(position.left / scale),
                    y: Math.floor(position.top / scale),
                });
            }
        }
    }

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
    _onMouseMove(e: MouseEvent) {
        if (!this.commentDlg && this.#$selectionRect.is(':visible')) {
            const offset = this.#$selectionArea.offset();
            const x = e.pageX - Math.floor(offset.left) - 1;
            const y = e.pageY - Math.floor(offset.top) - 1;
            const updateData: JQuery.PlainObject<string | number> = {};

            if (this.#activeSelection.beginX <= x) {
                updateData.left = this.#activeSelection.beginX;
                updateData.width = x - this.#activeSelection.beginX;
            } else {
                updateData.left = x;
                updateData.width = this.#activeSelection.beginX - x;
            }

            if (this.#activeSelection.beginY <= y) {
                updateData.top = this.#activeSelection.beginY;
                updateData.height = y - this.#activeSelection.beginY;
            } else {
                updateData.top = y;
                updateData.height = this.#activeSelection.beginY - y;
            }

            this.#$selectionRect
                .css(updateData)
                .data(updateData);

            e.stopPropagation();
            e.preventDefault();
        }
    }

    /**
     * Reposition the selection area to the right locations.
     */
    _adjustPos() {
        const region = this.#imageView.getSelectionRegion();

        this.#$selectionArea
            .width(region.width)
            .height(region.height)
            .css({
                left: region.left,
                top: region.top,
            });

        if (this.#$imageDiffs) {
            this.#$imageDiffs.height(this.#imageView.$el.height());
        }
    }
}
