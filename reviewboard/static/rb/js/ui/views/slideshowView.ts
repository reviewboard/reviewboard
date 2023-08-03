/**
 * A slideshow for navigating and cycling between content.
 */

import { BaseView, spina } from '@beanbag/spina';


/**
 * Options for the SlideshowView.
 *
 * Version Added:
 *     6.0
 */
interface SlideshowViewOptions {
    /**
     * The time in milliseconds between automatic cyling of slides.
     *
     * If not provided, this will default to either the ``data-cycle-time-ms=``
     * attribute on the element (if present) or 2 seconds.
     *
     * If a slide contains animations, this will be the amount of time after
     * the last animation completes before cycling.
     */
    autoCycleTimeMS?: number;

    /**
     * The maximum number of times to automatically cycle through.
     *
     * This sets a limit on the number of times automatic cycling will go
     * through a full iteration and restart. This defaults to 5.
     */
    maxAutoCycles?: number;

    /**
     * The time in milliseconds before starting a new cycle.
     *
     * After reaching the final slide, this controls the delay before starting
     * the slideshow over from the beginning. This defaults to 6 seconds.
     */
    restartCycleTimeMS?: number;
}


/**
 * A slideshow for navigating and cycling between content.
 *
 * Slideshows can automatically cycle between content periodically, up to
 * a maximum number of times. Users can choose to navigate to specific pages,
 * which will turn off the automatic navigation.
 *
 * Automatic cycling between slides can be made aware of any animations that
 * need to play in the slide. Setting a ``data-last-animation=`` attribute on
 * the element will cause the slideshow to wait for that particular animation
 * to end before scheduling a switch to another slide.
 *
 * If the user moves the mouse over a slide, automatic cycling will be
 * temporarily paused, allowing the user to spend more time viewing or
 * interacting with the content.
 *
 * Version Added:
 *     6.0
 */
@spina
export class SlideshowView extends BaseView<
    Backbone.Model,
    HTMLDivElement,
    SlideshowViewOptions
> {
    static events = {
        'click .rb-c-slideshow__nav-item': '_onNavItemClick',
        'click .rb-c-slideshow__nav-next': '_onNextClick',
        'click .rb-c-slideshow__nav-prev': '_onPrevClick',
        'keydown': '_onKeyDown',
        'mouseenter .rb-c-slideshow__slide-content': '_onSlideMouseEnter',
        'mouseleave .rb-c-slideshow__slide-content': '_onSlideMouseLeave',
    };

    /**
     * A selector for matching child elements that need tabindex managed.
     */
    static TABINDEX_SEL =
        'a[href], button, input, select, textarea, [tabindex="0"]';

    /**********************
     * Instance variables *
     **********************/

    #$curNavItem: JQuery = null;
    #$curSlide: JQuery = null;
    #$navItems: JQuery<HTMLAnchorElement> = null;
    #$slides: JQuery = null;
    #$slidesContainer: JQuery = null;

    /**
     * The time in milliseconds between automatic cyling of slides.
     *
     * If not provided, this will default to either the ``data-cycle-time-ms=``
     * attribute on the element (if present) or 2 seconds.
     *
     * If a slide contains animations, this will be the amount of time after
     * the last animation completes before cycling.
     */
    #autoCycleTimeMS: number;

    #curIndex = 0;
    #cycleAutomaticallyEnabled = false;
    #cycleAutomaticallyPaused = false;
    #cycleTimeout: number;
    #maxFullAutoCycles: number;
    #numFullAutoCycles = 0;
    #numSlides = 0;
    #restartCycleTimeMS: number;

    /**
     * Initialize the slideshow.
     *
     * Args:
     *     options (SlideshowViewOptions):
     *         Options for the view.
     */
    initialize(options: SlideshowViewOptions = {}) {
        this.#autoCycleTimeMS =
            options.autoCycleTimeMS ||
            parseInt(this.$el.data('auto-cycle-time-ms'), 10) ||
            2000;
        this.#restartCycleTimeMS = options.restartCycleTimeMS || 6000;
        this.#maxFullAutoCycles = options.maxAutoCycles || 5;
        this.#numFullAutoCycles = 0;
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        const $nav = this.$('.rb-c-slideshow__nav');
        this.#$navItems = $nav.children('.rb-c-slideshow__nav-item') as
            JQuery<HTMLAnchorElement>;

        this.#$slidesContainer = this.$('.rb-c-slideshow__slides');
        this.#$slides =
            this.#$slidesContainer.children('.rb-c-slideshow__slide');
        this.#numSlides = this.#$slides.length;

        this.#$slides.each((i, el) => {
            const $el = $(el);

            $el.data('slide-index', i);
            this.#disableSlide($el);
        });

        /*
         * If the URL is pointing to a particular slide, then switch to it
         * immediately.
         */
        let slideIndex = 0;

        if (window.location.hash && this.#$navItems.length) {
            const $navItem =
                this.#$navItems.filter(`[href="${window.location.hash}"]`);

            if ($navItem.length > 0) {
                slideIndex = this.#$navItems.index($navItem[0]);
            }
        }

        this.setSlide(slideIndex);

        this.setAutomaticCyclingEnabled(this.$el.hasClass('-is-auto-cycled'));
    }

    /**
     * Queue automatic cycling to the next slide.
     *
     * This will only queue up a cycle if automatic cycling is enabled and
     * not paused.
     *
     * If the slide has a ``data-last-animation=`` attribute defined, this will
     * wait until that animation has ended before scheduling the next slide.
     */
    queueNextSlide() {
        this.unqueueNextSlide();

        if (!this.#cycleAutomaticallyEnabled ||
            this.#cycleAutomaticallyPaused) {
            return;
        }

        function _scheduleNextSlide() {
            this.#cycleTimeout = setTimeout(
                this.#autoCycleNext.bind(this),
                (this.#curIndex + 1 >= this.#numSlides
                 ? this.#restartCycleTimeMS : this.#autoCycleTimeMS));
        }

        const $slide = this.#$curSlide;
        const lastAnimation = $slide.data('last-animation');

        if (lastAnimation) {
            const expectedIndex = this.#curIndex;

            $slide.on(
                'animationend.slideshow-queue-slide',
                (e: JQuery.TriggeredEvent) => {
                    const origEv = e.originalEvent as AnimationEvent;

                    if (origEv.animationName === lastAnimation &&
                        this.#curIndex === expectedIndex) {
                        _scheduleNextSlide.call(this);
                    }
                });
        } else {
            _scheduleNextSlide.call(this);
        }
    }

    /**
     * Unqueue a previously-queued automatic cycle.
     */
    unqueueNextSlide() {
        if (this.#cycleTimeout) {
            clearTimeout(this.#cycleTimeout);
            this.#cycleTimeout = null;
        }
    }

    /**
     * Immediately switch to the previous slide.
     *
     * If the current slide is the first in the list, this will switch to the
     * last slide.
     */
    prevSlide() {
        this.setSlide(this.#curIndex === 0
                      ? this.#numSlides - 1
                      : this.#curIndex - 1);
    }

    /**
     * Immediately switch to the next slide.
     *
     * If the current slide is the last in the list, this will switch to the
     * first slide.
     */
    nextSlide() {
        this.setSlide(this.#curIndex + 1 >= this.#numSlides
                      ? 0
                      : this.#curIndex + 1);
    }

    /**
     * Set the current slide to the specified index.
     *
     * If automatic cycling is enabled, the next slide will be queued up
     * after the switch.
     *
     * Args:
     *     index (number):
     *         The index of the slide to switch to.
     */
    setSlide(index: number) {
        const $oldSlide = this.#$curSlide;
        let $newNavItem: JQuery<HTMLAnchorElement> = null;
        let $newSlide: JQuery = null;

        if (this.#$navItems.length) {
            /* We're navigating with a full TOC. */
            $newNavItem = this.#$navItems.eq(index);
            const $oldNavItem = this.#$curNavItem;

            if ($oldNavItem) {
                $oldNavItem.attr('aria-selected', 'false');
            }

            $newNavItem.attr('aria-selected', 'true');

            $newSlide = this.#$slides.filter($newNavItem[0].hash);
        } else {
            /* We're navigating with next/prev buttons. */
            $newSlide = this.#$slides.eq(index);
        }

        $newSlide.css('display', 'block');

        const offsetLeft = $newSlide[0].clientLeft;

        if ($oldSlide) {
            this.#disableSlide($oldSlide);
        }

        this.#enableSlide($newSlide);

        $newSlide.css('transform', `translate3d(-${offsetLeft}px, 0, 0)`);

        this.#$slidesContainer
            .data('selected-index', index)
            .css('transform', `translate3d(-${index * 100}%, 0, 0)`);

        if ($newNavItem) {
            this.#$curNavItem = $newNavItem;
        }

        this.#$curSlide = $newSlide;
        this.#curIndex = index;

        this.queueNextSlide();
    }

    /**
     * Set whether automatic cycling is enabled.
     *
     * Args:
     *     enabled (boolean):
     *         Whether to enable automatic cycling.
     */
    setAutomaticCyclingEnabled(enabled: boolean) {
        if (this.#cycleAutomaticallyEnabled === enabled) {
            return;
        }

        this.#cycleAutomaticallyEnabled = enabled;

        this.#$slidesContainer.attr('aria-live', enabled ? 'off' : 'polite');
        this.#$curSlide.off('animationend.slideshow-queue-slide');

        this.unqueueNextSlide();

        if (enabled) {
            this.queueNextSlide();
        }
    }

    /**
     * Automatically cycle to the next slide.
     *
     * This will disable automatic cycling if the number of full auto-cycles
     * is reached after switching to the next slide.
     */
    #autoCycleNext() {
        this.nextSlide();

        if (this.#curIndex === 0) {
            this.#numFullAutoCycles++;

            if (this.#numFullAutoCycles >= this.#maxFullAutoCycles) {
                /*
                 * We've rewound and have cycled the full amount of
                 * times allowed. Disable any further auto-cycling.
                 */
                this.setAutomaticCyclingEnabled(false);
            }
        }
    }

    /**
     * Disable a slide.
     *
     * This will hide it and disable tab navigation to any relevant children.
     *
     * Args:
     *     $slide (jQuery):
     *         The slide element to disable.
     */
    #disableSlide($slide: JQuery) {
        $slide
            .off('animationend.slideshow-queue-slide')
            .attr({
                'aria-hidden': 'true',
                'hidden': '',
                'tabindex': '-1',
            })
            .find(SlideshowView.TABINDEX_SEL)
                .attr('tabindex', '-1');
    }

    /**
     * Enable a slide.
     *
     * This will show it and enable tab navigation to any relevant children.
     *
     * Args:
     *     $slide (jQuery):
     *         The slide element to disable.
     */
    #enableSlide($slide: JQuery) {
        $slide
            .attr({
                'aria-hidden': 'false',
                tabindex: '0',
            })
            .removeAttr('hidden')
            .find(SlideshowView.TABINDEX_SEL)
                .removeAttr('tabindex');
    }

    /**
     * Handle a click on a navigation item.
     *
     * This will switch to the slide referenced by the navigation item, and
     * disable automatic cycling.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event.
     */
    private _onNavItemClick(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        const index = this.#$navItems.index(e.target);

        if (index !== -1) {
            this.setAutomaticCyclingEnabled(false);
            this.setSlide(index);
        }
    }

    /**
     * Handle a click on the "next" navigation item.
     *
     * This will switch to the next slide, and disable automatic cycling.
     *
     * Args:
     *     e (jQuery.ClickEvent):
     *         The click event.
     */
    private _onNextClick(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        this.setAutomaticCyclingEnabled(false);
        this.nextSlide();
    }

    /**
     * Handle a click on the "previous" navigation item.
     *
     * This will switch to the previous slide, and disable automatic cycling.
     *
     * Args:
     *     e (jQuery.ClickEvent):
     *         The click event.
     */
    private _onPrevClick(e: JQuery.ClickEvent) {
        e.preventDefault();
        e.stopPropagation();

        this.setAutomaticCyclingEnabled(false);
        this.prevSlide();
    }

    /**
     * Handle keydown events on the slideshow.
     *
     * If Left or Right are pressed, this will navigate to the previous or
     * next slide, respectively.
     *
     * Args:
     *     e (jQuery.Event):
     *         The keydown event.
     *
     * Returns:
     *     boolean:
     *     ``false`` if the key is handled. ``undefined`` otherwise.
     */
    private _onKeyDown(
        e: JQuery.KeyDownEvent,
    ): boolean {
        let handled = true;

        switch (e.key) {
            case 'ArrowLeft':
                this.prevSlide();
                this.#$curNavItem.focus();
                break;

            case 'ArrowRight':
                this.nextSlide();
                this.#$curNavItem.focus();
                break;

            default:
                handled = false;
                break;
        }

        if (handled) {
            return false;
        }
    }

    /**
     * Handle a mouseenter event on the slide.
     *
     * This will pause cycling until the user has moved the mouse away.
     */
    private _onSlideMouseEnter() {
        this.unqueueNextSlide();
        this.#cycleAutomaticallyPaused = true;
    }

    /**
     * Handle a mouseleave event on the slide.
     *
     * This will unpause cycling.
     */
    private _onSlideMouseLeave() {
        this.#cycleAutomaticallyPaused = false;

        if (this.#cycleAutomaticallyEnabled) {
            this.queueNextSlide();
        }
    }
}
