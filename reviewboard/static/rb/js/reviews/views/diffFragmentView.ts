/**
 * A view for managing a loaded diff fragment and its state.
 */

import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';

import { API } from 'reviewboard/common';
import { CenteredElementManager } from 'reviewboard/ui';

import { type LoadDiffOptions } from '../utils/diffFragmentQueue';


/**
 * Options for the DiffFragmentView.
 *
 * Version Added:
 *     8.0
 */
export interface DiffFragmentViewOptions {
    /**
     * Whether or not the controls on the view can be collapsed.
     *
     * If collapsible, they will also start collapsed. This defaults to
     * ``false``.
     */
    collapsible?: boolean;

    /** The function to call to load more of the diff. */
    loadDiff?: (options: LoadDiffOptions) => Promise<void>;
}


/**
 * A view for managing a loaded diff fragment and its state.
 *
 * This displays a fragment of a diff, offering options for expanding and
 * collapsing content.
 */
@spina
export class DiffFragmentView extends BaseView<
    undefined,
    HTMLDivElement,
    DiffFragmentViewOptions
> {
    static events: EventsHash = {
        'click .diff-expand-btn': '_onExpandButtonClicked',
        'click .rb-c-diff-collapse-button': '_onCollapseButtonClicked',
        'mouseenter': '_tryShowControlsDelayed',
        'mouseleave': '_tryHideControlsDelayed',
    };

    /** The exposed headers height to show when collapsed. */
    static COLLAPSED_HEADERS_HEIGHT = 4;

    /** The timeout for a mouseout event to fire after it actually occurs. */
    static _controlsHoverTimeout = 250;

    /**********************
     * Instance variables *
     **********************/

    /**
     * The diff header elements.
     *
     * This is public for consumption in unit tests.
     */
    _$diffHeaders: JQuery = null;

    /**
     * The table element.
     *
     * This is public for consumption in unit tests.
     */
    _$table: JQuery = null;

    /**
     * The table header element.
     *
     * This is public for consumption in unit tests.
     */
    _$thead: JQuery = null;

    /**
     * Whether the fragment can be collapsed.
     *
     * This is public for consumption in unit tests.
     */
    _collapsible: boolean;

    /** The manager for centering controls. */
    #centeredMgr: CenteredElementManager = null;

    /** Whether this fragment has expanded context. */
    #contextExpanded = false;

    /** The function to call to load more of the diff. */
    #loadDiff: (options: LoadDiffOptions) => Promise<void>;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (DiffFragmentViewOptions, optional):
     *         Options for the view.
     */
    initialize(
        options: DiffFragmentViewOptions,
    ) {
        this.#loadDiff = options.loadDiff;
        this._collapsible = !!options.collapsible;
    }

    /**
     * Render the view.
     *
     * This will start the view off in a collapsed mode.
     */
    protected onRender() {
        /*
         * Make sure this class isn't on the fragment, in case we're
         * reloading content.
         */
        this.$el.removeClass('allow-transitions');

        this._$table = this.$el.children('table');
        this._$diffHeaders = this._$table.find('.diff-header');
        this._$thead = this._$table.children('thead');

        if (this._collapsible && this.$el.is(':visible')) {
            this.hideControls();
        } else {
            /*
             * If we're not collapsible, then we're always expanded
             * by default.
             */
            this.showControls();
        }

        if (this._collapsible) {
            /*
             * Once we've hidden the controls, we want to enable transitions
             * for hovering. We don't apply this before (or make it implicit)
             * because we don't want all the transitions to take place on page
             * load, as it's both visually weird and messes with the height
             * calculation for the collapsed areas.
             */
            _.defer(() => this.$el.addClass('allow-transitions'));
        }
    }

    /**
     * Remove the view.
     */
    protected onRemove() {
        if (this.#centeredMgr) {
            this.#centeredMgr.remove();
            this.#centeredMgr = null;
        }
    }

    /**
     * Show the controls on the specified comment container.
     */
    showControls() {
        /* This will effectively control the opacity of the controls. */
        this._$table
            .removeClass('collapsed')
            .addClass('expanded');

        /*
         * Undo all the transforms, so that these animate to their normal
         * positions.
         */
        this._$thead.css('transform', '');
        this._$diffHeaders.css('transform', '');
    }

    /**
     * Hide the controls on the specified comment container.
     *
     * Args:
     *     animate (boolean, optional):
     *         Whether to animate hiding the controls. By default, this is
     *         ``true``.
     */
    hideControls(animate?: boolean) {
        /*
         * Never hide the controls when context has been expanded. It creates
         * a sort of jarring initial effect.
         */
        if (this.#contextExpanded) {
            return;
        }

        if (animate === false) {
            this.$el.removeClass('allow-transitions');
        }

        this._$table
            .removeClass('expanded')
            .addClass('collapsed');

        const $firstDiffHeader = this._$diffHeaders.eq(0);

        if ($firstDiffHeader.hasClass('diff-header-above')) {
            /*
             * If the first diff header is present, we'll need to transition
             * the header down to be flush against the collapsed header.
             */
            const translateY = $firstDiffHeader.height() -
                               DiffFragmentView.COLLAPSED_HEADERS_HEIGHT;

            this._$thead.css('transform', `translateY(${translateY}px)`);
        }

        /*
         * The diff headers won't have the same heights exactly. We need to
         * compute the proper scale for the correct size per-header.
         */
        this._$diffHeaders.each((i, el) => {
            const $header = $(el);
            const scale = (DiffFragmentView.COLLAPSED_HEADERS_HEIGHT /
                                    $header.height());

            $header.css('transform', `scaleY(${scale})`);
        });

        if (animate === false) {
            _.defer(() => this.$el.addClass('allow-transitions'));
        }
    }

    /**
     * Expand or collapse the diff fragment.
     *
     * This will grab information from the expand/collapse button provided
     * and load a new diff fragment representing the state described in that
     * button. The new diff will represent either an expanded or collapsed
     * state.
     *
     * Once fetched, this will reset the state based on the new fragment and
     * re-render the view.
     *
     * Args:
     *     $btn (jQuery):
     *         The button element that triggered the event leading to this
     *         function call.
     */
    async _expandOrCollapse($btn: JQuery) {
        await this.#loadDiff({
            linesOfContext: $btn.data('lines-of-context'),
        });

        API.setActivityIndicator(false, {});

        /* All our HTML has changed, so clean up and re-render everything. */
        if (this.#centeredMgr !== null) {
            this.#centeredMgr.remove();
            this.#centeredMgr = null;
        }

        const $collapseButtons = this.$('.rb-c-diff-collapse-button');

        /*
         * Check if we have any collapse buttons. If so, we'll need to track
         * them in a CenteredElementManager.
         */
        if ($collapseButtons.length > 0) {
            this.#centeredMgr = new CenteredElementManager({
                elements: new Map(Array.prototype.map.call(
                    $collapseButtons,
                    (el: HTMLElement) => {
                        const $chunks = $(el)
                            .closest('.sidebyside')
                            .children('tbody')
                            .not('.diff-header');

                        return [el, {
                            $bottom: $chunks.eq(-1),
                            $top: $chunks.eq(0),
                        }];
                    })),
            });
            this.#centeredMgr.updatePosition();

            this.#contextExpanded = true;
        } else {
            this.#contextExpanded = false;
        }

        this.render();

        if (!this.#contextExpanded) {
            this._tryHideControlsDelayed();
        }
    }

    /**
     * Attempt to hide the controls in the given container after a delay.
     */
    private _tryShowControlsDelayed() {
        if (this._collapsible) {
            _.delay(() => {
                if (this.$el.is(':hover')) {
                    this.showControls();
                }
            }, DiffFragmentView._controlsHoverTimeout);
        }
    }

    /**
     * Attempt to hide the controls in the given container after a delay.
     */
    private _tryHideControlsDelayed() {
        if (this._collapsible) {
            _.delay(() => {
                if (!this.$el.is(':hover')) {
                    this.hideControls();
                }
            }, DiffFragmentView._controlsHoverTimeout);
        }
    }

    /**
     * Expand a diff fragment.
     *
     * When the expand button is clicked, this will trigger loading of a
     * new diff fragment containing the context as defined by the data
     * attributes on the button.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    private _onExpandButtonClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        this._expandOrCollapse($(e.currentTarget as HTMLElement));
    }

    /**
     * Collapse an expanded diff fragment.
     *
     * When the collapse button is clicked, this will trigger loading of a
     * new diff fragment containing the context as defined by the data
     * attributes on the button.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    private _onCollapseButtonClicked(e: Event) {
        e.preventDefault();
        e.stopPropagation();

        this._expandOrCollapse($(e.currentTarget as HTMLElement));
    }
}
