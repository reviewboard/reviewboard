/**
 * A label that indicates the state of a field in a review request draft.
 *
 */
import { BaseView, spina } from '@beanbag/spina';


/**
 * The possible color themes for the FieldStateLabelView.
 *
 * Version Added:
 *     6.0
 */
export enum FieldStateLabelThemes {
    DRAFT = 'draft',
    DELETED = 'deleted',
}


/**
 * Options for the FieldStateLabelView.
 *
 * Version Added:
 *     6.0
 */
export interface FieldStateLabelViewOptions {
    /**
     * The state text to display in the label.
     */
    state: string;

    /**
     * Whether the label should be displayed inline.
     */
    inline?: boolean;

    /**
     * The color theme of the label.
     */
    theme?: FieldStateLabelThemes;
}


/**
 * A label that indicates the state of a field in a review request draft.
 *
 * This is useful to show which fields have been modified in a review
 * request draft.
 *
 * Version Added:
 *     6.0
 */
@spina
export class FieldStateLabelView extends BaseView<
    Backbone.Model,
    HTMLDivElement,
    FieldStateLabelViewOptions
> {
    static className = 'rb-c-field-state-label';

    /**********************
     * Instance variables *
     **********************/

    /**
     * The state text to display in the label.
     */
    #state: string;

    /**
     * Whether the label should be displayed inline.
     *
     * This defaults to false.
     */
    #inline: boolean;

    /**
     * The color theme of the label.
     *
     * This defaults to Draft.
     */
    #theme: string;

    /**
     * Initialize the menu button.
     *
     * Args:
     *     options (FieldStateLabelViewOptions):
     *         Options for the view.
     */
    initialize(options: FieldStateLabelViewOptions) {
        this.#state = options.state;
        this.#inline = options.inline || false;
        this.#theme = options.theme || FieldStateLabelThemes.DRAFT;
    }

    /**
     * Render the view.
     */
    onInitialRender() {
        this.$el
            .addClass(this.className)
            .addClass(`-is-${this.#theme}`)
            .text(this.#state);

        if (this.#inline) {
            this.$el.addClass('-is-inline');
        }
    }
}