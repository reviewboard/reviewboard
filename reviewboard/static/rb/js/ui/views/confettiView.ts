/**
 * Whimsical confetti animation for pages.
 *
 * Version Added:
 *     8.1
 */

import {
    type BaseModel,
    BaseView,
    spina,
} from '@beanbag/spina';

import _ from 'underscore';


/**
 * Options for ConfettiView.
 *
 * Version Added:
 *     8.1
 */
interface ConfettiViewOptions {
    /** Velocity retained after each bounce. */
    bounceFrictionX?: number;

    /** Minimum velocity for bouncing. */
    bounceMinVelocity?: number;

    /** The colors available for the confetti. */
    colors?: string[];

    /** The number of pieces of confetti to display. */
    count?: number;

    /** Padding to apply to the floor at the bottom of the viewport. */
    floorPadding?: number;

    /** The gravity to apply to confetti. */
    gravity?: number;

    /** The maximum duration for the confetti animation. */
    maxDurationMs?: number;

    /** The maximum number of platform candidate checks per frame. */
    maxPlatformChecks?: number;

    /**
     * The origin for the confetti.
     *
     * This may be an element or a point.
     *
     * If not provided, this defaults to a position half-way cross the
     * canvas, near the top.
     */
    origin?: DOMPoint | HTMLElement;

    /**
     * The maximum aspect ratio of pieces.
     *
     * This is defined as ``height / width``.
     */
    pieceAspectRatioMax?: number;

    /**
     * The minimum aspect ratio of pieces.
     *
     * This is defined as ``height / width``.
     */
    pieceAspectRatioMin?: number;

    /** The maximum bounce for a piece. */
    pieceBounceMax?: number;

    /** The minimum bounce for a piece. */
    pieceBounceMin?: number;

    /** The maximum size for a piece, in pixels. */
    pieceSizeMax?: number;

    /** The minimum size for a piece, in pixels. */
    pieceSizeMin?: number;

    /** The maximum rotational velocity, in radians per tick. */
    pieceSpinMaxRadPerSec?: number;

    /** The size of any tracked platforms, in pixels. */
    platformBucketSizePx?: number;

    /** Selectors for any platform elements the confetti should land on. */
    platformSelectors?: string;

    /** Maximum speed multiplier applied to the launch speed for pieces. */
    speedScaleMax?: number;

    /** Minimum speed multiplier applied to the launch speed for pieces. */
    speedScaleMin?: number;

    /**
     * The starting angle that pieces should be launched at, in degrees.
     *
     * -90 would launch straight up. 0 would launch to the right.
     */
    startAngleDeg?: number;

    /** The starting speed for any piece movement. */
    startSpeed?: number;

    /**
     * The total launch spread for all pieces, in degrees.
     *
     * Pieces are evenly distributed around ``startAngleDegrees`` within this
     * range. Larger values will spread out more.
     */
    startSpreadDeg?: number;

    /** The horizontal spread of launch positions, in pixels. */
    startSpreadHorizPx?: number;

    /** The vertical spread of launch positions, in pixels. */
    startSpreadVertPx?: number;

    /** The z-index for the confetti rendering. */
    zIndex?: number;
}


/**
 * An X/Y position on the screen.
 *
 * Version Added:
 *     8.1
 */
interface Position {
    /** The X coordinate in pixels. */
    x: number;

    /** The Y coordinate in pixels. */
    y: number;
}


/**
 * A velocity of a piece.
 *
 * Version Added:
 *     8.1
 */
interface Velocity {
    /** The X velocity in pixels. */
    x: number;

    /** The Y velocity in pixels. */
    y: number;

    /** The rotation velocity. */
    rotation: number;
}


/**
 * Information on a platform that confetti can land on.
 *
 * Version Added:
 *     8.1
 */
interface Platform {
    /** The bounds of the platform. */
    bounds: DOMRect;

    /** The platform's element. */
    el?: HTMLElement;
}


/**
 * Information on a piece of confetti.
 *
 * Version Added:
 *     8.1
 */
interface ConfettiPiece {
    /** The amount of bounce applied to this piece when it hits a platform. */
    bounce: number;

    /** The current bounds for the piece. */
    bounds: DOMRect;

    /** The color of the piece. */
    color: string;

    /** The phase of the flip after bounce. */
    flipPhase: number;

    /** The relative X position from the landed platform. */
    landRelX: number | null;

    /** Whether the piece has landed. */
    landedOn: Platform | null;

    /** The previous position for the piece. */
    prevPos: Position;

    /** The current rotation for the piece. */
    rotation: number;

    /** The velocity for the piece. */
    velocity: Velocity;
}


/**
 * A view managing a full-page confetti animation.
 *
 * This displays an overlay onto the page that can launch confetti out from
 * any location or element, spreading across the page, bouncing, and
 * eventually landing.
 *
 * Confetti will land on the floor (bottom of the viewport), and on any
 * platforms defined by the ``platformSelectors`` option. Platforms can be
 * buttons, input elements, or anything else. Any confetti that lands on a
 * platform will stick to the top of that platform as the page resizes.
 *
 * This is implemented as a full-page canvas overlay with all pointer events
 * turned off. When the animation runs, all confetti will be updated on each
 * animation frame until either the time runs out or all pieces have landed.
 *
 * The physics, speed, origins, angles, sizes, colors, and every other aspect
 * of the animation can be controlled by the caller, allowing for different
 * levels of excitement in the confetti.
 *
 * The default colors are intended for use in both light and dark modes.
 *
 * The view should be appended directly to ``document.body``.
 *
 * Version Added:
 *     8.1
 */
@spina
export class ConfettiView extends BaseView<
    BaseModel,
    HTMLCanvasElement,
    ConfettiViewOptions
> {
    static tagName = 'canvas';

    /** Maximum calculated delta time between animation frames. */
    static MAX_FRAME_TIME = 0.33;

    /** Position multiplier used to simulate a piece flipping horizontally. */
    static FLIP_RADIANS_PER_PX = 0.02;

    /** Minimum scale applied when flipping a piece vertically. */
    static FLIP_SCALE_Y_MIN = 0.35;

    /** Maximum scale applied when flipping a piece vertically. */
    static FLIP_SCALE_Y_MAX = 1.2;

    /**********************
     * Instance variables *
     **********************/

    /** Whether the confetti is currently being animated. */
    #animating = false;

    /**
     * The cached bounds of the canvas.
     *
     * This is updated on resize.
     */
    #canvasBounds: DOMRect;

    /** The 2D drawing context for the canvas. */
    #canvasCtx: CanvasRenderingContext2D;

    /** The cached device pixel ratio of the canvas. */
    #devicePixelRatio: number;

    /** The floor at the bottom of the viewport. */
    #floor: Platform;

    /** All options provided by the caller. */
    #options: Required<ConfettiViewOptions>;

    /** The list of all pieces of confetti. */
    #pieces: ConfettiPiece[];

    /**
     * Lists of platforms, organized into searchable buckets.
     *
     * Each bucket represents a column on the screen, with a width defined by
     * the ``platformBucketSizePx`` option. Any platforms that intersect that
     * column will be added to the bucket's array.
     *
     * This makes it easy to take any X position and grab all platforms in that
     * column. This can then be used to help land confetti on the platform.
     */
    #platformBuckets: Platform[][];

    /** The handle for the last animation frame request. */
    #requestAnimationHandle: (number | null) = null;

    /**
     * Initialize the confetti view.
     *
     * Args:
     *     options (ConfettiViewOptions):
     *         The options for controlling the confetti display.
     */
    initialize(
        options: ConfettiViewOptions,
    ) {
        /*
         * The default options for the view.
         *
         * We're defining this inline to avoid needing to store any state
         * in memory that's unlikely to be used in most pages (and certainly
         * more than once).
         */
        const defaultOptions: Required<ConfettiViewOptions> = {
            bounceFrictionX: 0.6,
            bounceMinVelocity: 120,
            colors: [
                '#FF4D6D',
                '#FFD166',
                '#06D6A0',
                '#4EA8DE',
                '#B5179E',
                '#F77F00',
            ],
            count: 70,
            floorPadding: 0,
            gravity: 700,
            maxDurationMs: 6000,
            maxPlatformChecks: 10,
            origin: null,
            pieceAspectRatioMin: 0.7,
            pieceAspectRatioMax: 1.5,
            pieceBounceMax: 0.45,
            pieceBounceMin: 0.2,
            pieceSizeMin: 4,
            pieceSizeMax: 10,
            pieceSpinMaxRadPerSec: 10,
            platformBucketSizePx: 200,
            platformSelectors: 'button, input',
            speedScaleMax: 1.1,
            speedScaleMin: 0.55,
            startAngleDeg: -90,
            startSpeed: 600,
            startSpreadDeg: 150,
            startSpreadHorizPx: 40,
            startSpreadVertPx: 10,
            zIndex: 9999,
        };

        this.#options = _.defaults({}, options, defaultOptions);

        /* Define the floor. */
        this.#floor = {
            bounds: DOMRect.fromRect({
                x: 0,
                y: 0,
                width: 0,
                height: 0,
            }),
        };
    }

    /**
     * Run the confetti animation.
     *
     * This will build the pieces and platform state and then begin running
     * the confetti animation in each animation frame.
     *
     * Args:
     *     onDone (function):
     *         A callback to call when the animation completes.
     */
    run(
        onDone?: () => void,
    ) {
        if (this.#animating) {
            throw new Error('The animation is already running.');
        }

        const constructor = this.constructor as typeof ConfettiView;

        this.#checkHandleResize();
        this.#buildPlatforms();
        this.#buildPieces();

        /* Pull out the options we need to refer to. */
        const options = this.#options;
        const gravity = options.gravity;
        const maxDurationMs = options.maxDurationMs;

        /* Pull out the state we'll be working with each frame. */
        const canvasCtx = this.#canvasCtx;
        const pieces = this.#pieces;

        /*
         * These are our cheap caches, which will be reset if the canvas
         * size or DPI changes.
         */
        let canvasBounds = this.#canvasBounds;
        let devicePixelRatio = this.#devicePixelRatio;

        /*
         * Store the start time of the animation, for both time deltas and
         * to cut off the animation when the max duration is hit.
         */
        const maxFrameTime = constructor.MAX_FRAME_TIME;
        const startTime = performance.now();
        let lastTime = startTime;

        /* Our local frame handler. */
        const onFrame = (
            now: number,
        ) => {
            const dt = Math.min(maxFrameTime, (now - lastTime) / 1000);
            lastTime = now;

            /*
             * Perform a resize check per-frame, in case the DPI changes,
             * since we can't reliably know this from an event.
             */
            if (this.#checkHandleResize()) {
                /* There was a resize. Pull in the new state. */
                canvasBounds = this.#canvasBounds;
                devicePixelRatio = this.#devicePixelRatio;
            }

            /*
             * Clear drawing and reset the transformation.
             *
             * It's ultimately faster and less error-prone by resetting the
             * context than to clear each piece.
             */
            canvasCtx.reset();
            canvasCtx.setTransform(
                devicePixelRatio,
                0,
                0,
                devicePixelRatio,
                0,
                0,
            );

            let allLanded = true;

            /*
             * Update and draw all pieces.
             *
             * Landed pieces will not be moved.
             */
            for (const piece of pieces) {
                if (!piece.landedOn) {
                    const pieceBounds = piece.bounds;
                    const pieceVelocity = piece.velocity;

                    /*
                     * Store the previous Y for this piece, which will be
                     * used to calculate whether it's passed a platform.
                     */
                    piece.prevPos = {
                        x: pieceBounds.x,
                        y: pieceBounds.y,
                    };

                    /* Increase velocity by the gravity. */
                    pieceVelocity.y += gravity * dt;

                    /*
                     * Move the piece's position based on the velocity.
                     *
                     * The X position will be capped to fit on-screen. The
                     * Y position is allowed to extend beyond the top of the
                     * screen.
                     */
                    pieceBounds.x += pieceVelocity.x * dt;
                    pieceBounds.y = Math.min(
                        canvasBounds.height - pieceBounds.height,
                        pieceBounds.y + pieceVelocity.y * dt,
                    );

                    this.#bounceOffSides(piece);

                    piece.rotation += pieceVelocity.rotation * dt;

                    /* See if this has landed on something. */
                    if (!this.#attemptLandingOnPlatform(piece) &&
                        !this.#attemptLandingOnFloor(piece)) {
                        allLanded = false;
                    }
                }

                /* Draw this. */
                this.#drawPiece(piece);
            }

            /*
             * Check whether to continue or end animation.
             *
             * This will end when all pieces have landed or time has elapsed.
             */
            if (allLanded || (now - startTime) > maxDurationMs) {
                /* We're done! */
                this.#requestAnimationHandle = null;
                this.#animating = false;

                if (onDone) {
                    onDone();
                }
            } else {
                /* Schedule the next frame. */
                this.#requestAnimationHandle = requestAnimationFrame(onFrame);
            }
        }

        /* Begin animating the confetti. */
        this.#animating = true;
        this.#requestAnimationHandle = requestAnimationFrame(onFrame);
    }

    /**
     * Handle initial rendering of the view.
     *
     * This will establish the canvas drawing context and styling, and begin
     * handling events.
     *
     * No confetti will be drawn at this stage.
     */
    protected onInitialRender() {
        const el = this.el;

        this.#canvasCtx = el.getContext('2d', {
            alpha: true,
        });

        /* Set the canvas as a full-page overlay, with events turned off. */
        const canvasStyle = el.style;
        canvasStyle.position = 'fixed';
        canvasStyle.left = '0';
        canvasStyle.top = '0';
        canvasStyle.width = '100vw';
        canvasStyle.height = '100vh';
        canvasStyle.pointerEvents = 'none';
        canvasStyle.zIndex = String(this.#options.zIndex);

        window.addEventListener('resize', this.#onWindowResize);
    }

    /**
     * Handle removing the view.
     *
     * This will clear out state and disable any events or animation.
     */
    protected onRemove() {
        /* Cancel any further animation. */
        const handle = this.#requestAnimationHandle;

        if (handle) {
            cancelAnimationFrame(handle);
        }

        /* Remove any event listeners. */
        window.removeEventListener('resize', this.#onWindowResize);

        /* Clear out state. */
        this.#animating = false;
        this.#canvasCtx = null;
        this.#platformBuckets = null;
    }

    /**
     * Build all the confetti pieces.
     *
     * All pieces will originated from the caller-provided origin or, if not
     * provided, an area half-way through and near the top of the canvas.
     *
     * Each piece will have a semi-random (but generally caller-controlled)
     * size, spin, position, speed, bounce, spread, and angle of launch.
     */
    #buildPieces() {
        const options = this.#options;
        const canvasBounds = this.#canvasBounds;

        /* Determine the origin for the pieces. */
        const origin = options.origin;
        let originX: number;
        let originY: number;

        if (origin) {
            if (origin instanceof HTMLElement) {
                /*
                 * The origin is an element, so position this half-way across
                 * the top of the element.
                 */
                const originBounds = origin.getBoundingClientRect();

                originX = originBounds.left + (originBounds.width / 2);
                originY = originBounds.top;
            } else {
                originX = origin.x;
                originY = origin.y;
            }
        }

        /*
         * Default to positioning half-way across the bounds, 18% from the
         * top of the canvas.
         */
        originX ??= canvasBounds.width * 0.5;
        originY ??= canvasBounds.height * 0.18;

        const colors = options.colors;
        const numColors = colors.length;
        const startSpeed = options.startSpeed;
        const numPieces = options.count;

        /*
         * Define some constants we'll use below. We don't need these on the
         * class, since they're just used within this loop.
         */
        const TO_RADS = Math.PI / 180;
        const startAngleDeg = options.startAngleDeg * TO_RADS;
        const startSpreadDeg = options.startSpreadDeg * TO_RADS;
        const speedScaleMin = options.speedScaleMin;
        const speedScaleRange = options.speedScaleMax - speedScaleMin;
        const sizeMin = options.pieceSizeMin;
        const sizeRange = options.pieceSizeMax - sizeMin;
        const startSpreadHorizPx = options.startSpreadHorizPx;
        const startSpreadVertPx = options.startSpreadVertPx;
        const aspectRatioMin = options.pieceAspectRatioMin;
        const aspectRatioRange = options.pieceAspectRatioMax - aspectRatioMin;
        const bounceMin = options.pieceBounceMin;
        const bounceRange = options.pieceBounceMax - bounceMin;
        const spinMaxRadPerSec = options.pieceSpinMaxRadPerSec;
        const flipPhase = Math.PI * 2;

        /* Build all pieces of confetti. */
        const pieces: ConfettiPiece[] = new Array(numPieces);

        for (let i = 0; i < numPieces; i++) {
            const angle = startAngleDeg +
                          ((Math.random() - 0.5) * startSpreadDeg);
            const speed = startSpeed *
                          (speedScaleMin + (Math.random() * speedScaleRange));
            const size = sizeMin + (Math.random() * sizeRange);

            pieces[i] = {
                bounds: DOMRect.fromRect({
                    x: originX + (Math.random() - 0.5) * startSpreadHorizPx,
                    y: originY + (Math.random() - 0.5) * startSpreadVertPx,
                    width: size,
                    height: size * (aspectRatioMin +
                                    (Math.random() * aspectRatioRange)),
                }),
                bounce: bounceMin + Math.random() * bounceRange,
                color: colors[Math.floor(Math.random() * numColors)],
                flipPhase: Math.random() * flipPhase,
                landedOn: null,
                landRelX: null,
                prevPos: {
                    x: originX,
                    y: originY,
                },
                rotation: Math.random() * Math.PI,
                velocity: {
                    x: Math.cos(angle) * speed,
                    y: Math.sin(angle) * speed,
                    rotation: (Math.random() - 0.5) * spinMaxRadPerSec,
                },
            };
        }

        this.#pieces = pieces;
    }

    /**
     * Build the platform buckets.
     *
     * This will find all elements matching the platform selectors, grouping
     * them into per-column buckets based on their position.
     */
    #buildPlatforms() {
        const options = this.#options;

        const canvasBounds = this.#canvasBounds;
        const offsetX = canvasBounds.left;
        const offsetY = canvasBounds.top;

        const platformEls = document.querySelectorAll<HTMLElement>(
            options.platformSelectors);
        const platforms: Platform[] = [];

        /*
         * Find all matching elements that fit within the bounds of the canvas.
         */
        for (const platformEl of platformEls) {
            const bounds = platformEl.getBoundingClientRect();

            if (bounds.width > 1 &&
                bounds.height > 1 &&
                bounds.top >= canvasBounds.top &&
                bounds.left >= canvasBounds.left &&
                bounds.right <= canvasBounds.right) {
                /*
                 * The platform top fits into the bounds of the canvas. It's
                 * a candidate platform for any landing confetti.
                 */
                platforms.push({
                    bounds: DOMRect.fromRect({
                        x: bounds.left - offsetX,
                        y: bounds.top - offsetY,
                        width: bounds.width,
                        height: bounds.height,
                    }),
                    el: platformEl,
                });
            }
        }

        /*
         * Sort the results by Y position before we group into buckets.
         *
         * This will ensure that every bucket has a sorted list from top-most
         * to bottom-most platform.
         */
        platforms.sort((a, b) => (a.bounds.top - b.bounds.top));

        /* Determine the column width of each bucket. */
        const bucketSizePx = options.platformBucketSizePx;
        const numBuckets = Math.max(
            1,
            Math.ceil(canvasBounds.width / bucketSizePx),
        );

        /* Create the buckets. */
        const buckets: Platform[][] = new Array(numBuckets);

        for (let i = 0; i < numBuckets; i++) {
            buckets[i] = [];
        }

        this.#platformBuckets = buckets;

        /* Place our sorted platforms into the buckets. */
        for (const platform of platforms) {
            /*
             * Compute bucket indexes for the left-most and right-most edges
             * of the platform.
             */
            const platformBounds = platform.bounds;
            const bucketIndexLeft = this.#getPlatformBucketIndex(
                platformBounds.left);
            const bucketIndexRight = this.#getPlatformBucketIndex(
                platformBounds.right);

            /* Add this platform to every bucket in that range. */
            for (let i = bucketIndexLeft; i <= bucketIndexRight; i++) {
                buckets[i].push(platform);
            }
        }

        /* Specially handle updating the floor's bounds. */
        this.#updateFloor();
    }

    /**
     * Update the floor.
     *
     * This will set the floor to the full width of the viewport, placed
     * at the very bottom but raised up for the provided padding.
     */
    #updateFloor() {
        const canvasBounds = this.#canvasBounds;
        const floorBounds = this.#floor.bounds;

        floorBounds.y = canvasBounds.height - this.#options.floorPadding;
        floorBounds.width = canvasBounds.width;
    }

    /**
     * Draw a piece of confetti.
     *
     * Args:
     *     piece (ConfettiPiece):
     *         The piece to draw.
     */
    #drawPiece(
        piece: ConfettiPiece,
    ) {
        const pieceBounds = piece.bounds;
        const pieceWidth = pieceBounds.width;
        const pieceHeight = pieceBounds.height;
        const centerX = pieceBounds.x + (pieceWidth / 2);
        const centerY = pieceBounds.y + (pieceHeight / 2);

        const constructor = this.constructor as typeof ConfettiView;
        const flipScaleYMin = constructor.FLIP_SCALE_Y_MIN;

        const ctx = this.#canvasCtx;

        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(piece.rotation);

        if (!piece.landedOn) {
            const flip = Math.cos(
                piece.flipPhase +
                pieceBounds.x * constructor.FLIP_RADIANS_PER_PX,
            );

            ctx.scale(
                1,
                flipScaleYMin +
                (Math.abs(flip) * (constructor.FLIP_SCALE_Y_MAX -
                                   flipScaleYMin)),
            );
        }

        ctx.fillStyle = piece.color;
        ctx.fillRect(
            -pieceWidth / 2,
            -pieceHeight / 2,
            pieceWidth,
            pieceHeight,
        );

        ctx.restore();
    }

    /**
     * Bounce a piece off the sides of the canvas.
     *
     * If the piece has hit a side, it will be deflected back in.
     *
     * Args:
     *     piece (ConfettiPiece):
     *         The piece of confetti to check.
     */
    #bounceOffSides(
        piece: ConfettiPiece,
    ) {
        const canvasBounds = this.#canvasBounds;
        const pieceBounds = piece.bounds;
        const pieceVelocity = piece.velocity;

        if (pieceBounds.x <= 0 && pieceVelocity.x < 0) {
            pieceBounds.x = 0;
            pieceVelocity.x = -pieceVelocity.x * piece.bounce;
        } else if (pieceBounds.right >= canvasBounds.width &&
                   pieceVelocity.x > 0) {
            pieceBounds.x = canvasBounds.width - pieceBounds.width;
            pieceVelocity.x = -pieceVelocity.x * piece.bounce;
        }
    }

    /**
     * Attempt landing a piece of confetti on a platform.
     *
     * This will check the piece against all platforms that touch the
     * midpoint of the piece. If the piece moves down across the top of the
     * platform, it will begin bouncing or landing on that platform.
     *
     * If the piece enters a platform's bounds from the left or right side, it
     * will bounce off that side and continue falling, eventually landing on
     * top of the nearest platform.
     *
     * Args:
     *     piece (ConfettiPiece):
     *         The piece of confetti to check.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the piece fully landed on a platform. ``false`` if it
     *     didn't, or if it hit a platform but began bouncing.
     */
    #attemptLandingOnPlatform(
        piece: ConfettiPiece,
    ): boolean {
        const pieceVelocity = piece.velocity;

        if (pieceVelocity.y <= 0) {
            /* It's not moving, so don't bother checking. */
            return false;
        }

        const options = this.#options;
        const pieceBounds = piece.bounds;
        const prevPiecePos = piece.prevPos;

        const centerX = pieceBounds.x + (pieceBounds.width / 2);
        const platformBucketIndex = this.#getPlatformBucketIndex(centerX);
        const platformBuckets = this.#platformBuckets;
        const maxPlatformChecks = options.maxPlatformChecks;

        /*
         * Build candidate buckets for the midpoint and the two buckets on
         * either side.
         */
        const candidates = [
            platformBuckets[platformBucketIndex],
            (platformBucketIndex > 0
             ? platformBuckets[platformBucketIndex - 1]
             : null),
            (platformBucketIndex + 1 < platformBuckets.length
             ? platformBuckets[platformBucketIndex + 1]
             : null),
        ];

        let numChecks = 0;

        /* Check all candidate buckets. */
        for (const candidate of candidates) {
            if (!candidate) {
                /* This was one of the nulls from above. */
                continue;
            }

            /* Check each platform in the bucket. */
            for (const platform of candidate) {
                numChecks++;

                if (numChecks > maxPlatformChecks) {
                    /*
                     * We've hit our limit, for performance reasons. Bail.
                     */
                    return false;
                }

                const platformBounds = platform.bounds;

                if (pieceBounds.bottom < platformBounds.top) {
                    /*
                     * We reached the last viable platform in the bucket. The
                     * platforms are sorted, so we now know that this piece
                     * is above all remaining platforms in the list. We can
                     * skip the rest.
                     */
                    break;
                }

                if (pieceBounds.right <= platformBounds.left ||
                    pieceBounds.left >= platformBounds.right) {
                    /* This is out of bounds. Skip it. */
                    continue;
                }

                /* Check if the piece hit or passed the top of a platform. */
                const prevBottom = prevPiecePos.y + pieceBounds.height;
                const curBottom = pieceBounds.bottom;

                if (curBottom >= platformBounds.y &&
                    prevBottom <= platformBounds.y) {
                    /*
                     * The piece crossed the top boundary for the platform.
                     * It will land on top of it once it finishes bouncing.
                     */
                    return this.#bounceOrLandPiece(piece, platform);
                }

                const centerY = pieceBounds.y + (pieceBounds.height / 2);

                /* Check if the piece hit a vertical side of a platform. */
                if (pieceBounds.left <= platformBounds.right &&
                    pieceBounds.right >= platformBounds.left &&
                    centerY <= platformBounds.bottom &&
                    centerY >= platformBounds.top) {
                    if (prevPiecePos.x < pieceBounds.left) {
                        /*
                         * The piece came from the left. Bounce it off the
                         * left side and let it continue falling.
                         */
                        return this.#bounceOrLandPiece(
                            piece,
                            platform,
                            'left');
                    } else {
                        return this.#bounceOrLandPiece(
                            piece,
                            platform,
                            'right');
                    }
                }
            }
        }

        /* The piece didn't land on any platforms. */
        return false;
    }

    /**
     * Attempt landing a piece of confetti on the floor.
     *
     * Args:
     *     piece (ConfettiPiece):
     *         The piece of confetti to check.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the piece fully landed on the floor. ``false`` if it
     *     didn't, or if it hit the floor but began bouncing.
     */
    #attemptLandingOnFloor(
        piece: ConfettiPiece,
    ): boolean {
        const floor = this.#floor;

        if (piece.bounds.bottom >= floor.bounds.y) {
            return this.#bounceOrLandPiece(piece, floor);
        }

        return false;
    }

    /**
     * Bounce or land a piece on a platform.
     *
     * This is called when there's a collision between the piece and any
     * platform (including the floor). It will bounce the piece, if there's
     * any momentum left, or land the piece on it, keeping it from moving
     * further.
     *
     * Args:
     *     piece (ConfettiPiece):
     *         The piece of confetti to check.
     *
     *     platform (Platform):
     *         The platform to bounce or land on.
     *
     *     lateralDirection (string):
     *         If the piece hit a vertical side of the platform, this is the
     *         lateral direction that the piece was travelling (``left`` or
     *         ``right``).
     *
     * Returns:
     *     boolean:
     *     ``true`` if the piece fully landed on the platform. ``false`` if it
     *     just bounced.
     */
    #bounceOrLandPiece(
        piece: ConfettiPiece,
        platform: Platform,
        lateralDirection: string = null,
    ): boolean {
        const options = this.#options;
        const pieceBounds = piece.bounds;
        const pieceVelocity = piece.velocity;
        const platformBounds = platform.bounds;

        /* Cap the position of the piece to not clip beyond the bounds. */
        if (lateralDirection === 'left') {
            pieceBounds.x = platformBounds.left - pieceBounds.width;
        } else if (lateralDirection === 'right') {
            pieceBounds.x = platformBounds.right;
        } else {
            pieceBounds.y = platformBounds.top - pieceBounds.height;
        }

        /* Check if the piece is still bouncing. */
        if (Math.abs(pieceVelocity.y) >= options.bounceMinVelocity ||
            Math.abs(pieceVelocity.x) >= options.bounceMinVelocity) {
            /*
             * The piece is bouncing. Reduce its velocity and adjust its
             * position based on the bounce.
             */

            if (lateralDirection) {
                piece.velocity.x = -piece.velocity.x * piece.bounce;
            } else {
                pieceVelocity.x *= options.bounceFrictionX;
                pieceVelocity.y = -pieceVelocity.y * piece.bounce;
            }

            return false;
        } else {
            /* The piece has finished bouncing. Land it and stop moving. */
            piece.landedOn = platform;
            piece.landRelX = pieceBounds.x - platformBounds.x;
            pieceVelocity.x = 0;
            pieceVelocity.y = 0;
            pieceVelocity.rotation = 0;

            return true;
        }
    }

    /**
     * Return the bucket index for a given X position.
     *
     * Args:
     *     x (number):
     *         The X position for the bucket.
     *
     * Returns:
     *     number:
     *     The index of the bucket.
     */
    #getPlatformBucketIndex(
        x: number,
    ): number {
        return Math.max(
            0,
            Math.min(Math.floor(x / this.#options.platformBucketSizePx),
                     this.#platformBuckets.length - 1),
        );
    }

    /**
     * Return the current device pixel ratio for the screen.
     *
     * Returns:
     *     number:
     *     The device pixel ratio.
     */
    #getDevicePixelRatio(): number {
        return Math.max(
            1,
            window.devicePixelRatio || 1,
        );
    }

    /**
     * Check whether the canvas or DPI has changed, and handle it.
     *
     * This will check if the canvas bounds and/or DPI has changed. If so,
     * platform and piece state will be updated accordingly.
     *
     * If the canvas size has changed, any pieces will be updated to stay on
     * their platform at the existing offset.
     *
     * If the confetti is still being animated, this will only update state
     * and won't handle any drawing, but if animation has stopped, this will
     * redraw all confetti pieces for the new positions.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the size or DPI has changed. ``false`` if it has not.
     */
    #checkHandleResize(): boolean {
        const el = this.el;
        const canvasBounds = el.getBoundingClientRect();
        const devicePixelRatio = this.#getDevicePixelRatio();

        const prevCanvasBounds = this.#canvasBounds;

        const widthChanged = (
            !prevCanvasBounds ||
            prevCanvasBounds.width !== canvasBounds.width
        );

        const heightChanged = (
            !prevCanvasBounds ||
            prevCanvasBounds.height !== canvasBounds.height
        );

        const sizeChanged = widthChanged || heightChanged;
        const dpiChanged = (this.#devicePixelRatio !== devicePixelRatio);

        if (!sizeChanged && !dpiChanged) {
            /* Nothing has changed, so we can bail. */
            return false;
        }

        /* The bounds or DPI have changed, so compute and store state. */
        this.#canvasBounds = canvasBounds;
        this.#devicePixelRatio = devicePixelRatio;

        /* Set the resolution of the canvas. */
        el.width = Math.round(canvasBounds.width * devicePixelRatio);
        el.height = Math.round(canvasBounds.height * devicePixelRatio);

        const pieces = this.#pieces;

        if (sizeChanged) {
            /* Update the locations of all platforms. */
            this.#updateFloor();

            const platformBuckets = this.#platformBuckets;

            if (platformBuckets) {
                const offsetX = canvasBounds.left;
                const offsetY = canvasBounds.top;

                for (const bucket of platformBuckets) {
                    for (const platform of bucket) {
                        const bounds = platform.el.getBoundingClientRect();

                        platform.bounds = DOMRect.fromRect({
                            x: bounds.left - offsetX,
                            y: bounds.top - offsetY,
                            width: bounds.width,
                            height: bounds.height,
                        });
                    }
                }
            }

            if (pieces) {
                /*
                 * Shift down all landed pieces, anchoring them to the top of
                 * the platform but retaining their X offset into the platform.
                 */
                for (const piece of pieces) {
                    const landedOn = piece.landedOn;

                    if (landedOn) {
                        const pieceBounds = piece.bounds;
                        const platformBounds = landedOn.bounds;

                        pieceBounds.x = platformBounds.x + piece.landRelX;
                        pieceBounds.y = platformBounds.y - pieceBounds.height;
                    }
                }
            }
        }

        if (this.#animating) {
            /* We only need to rebuild the platforms if the size changes. */
        } else if (pieces) {
            const canvasCtx = this.#canvasCtx;
            canvasCtx.reset();
            canvasCtx.setTransform(
                devicePixelRatio,
                0,
                0,
                devicePixelRatio,
                0,
                0,
            );

            for (const piece of pieces) {
                this.#drawPiece(piece);
            }
        }

        return true;
    }

    /**
     * Handle window resize events.
     *
     * If not animating, this will run the animation handler.
     *
     * If it is currently animating, this won't do anything, as the frame
     * renderer will already perform resize/DPI checks.
     */
    #onWindowResize = () => {
        /*
         * Only perform a canvas resize if we're not animating, since the
         * animation frames need to handle that specially.
         */
        if (!this.#animating) {
            this.#checkHandleResize();
        }
    }
}
