/**
 * An icon for showing the general complexity of a diff.
 */
import { BaseView, spina } from '@beanbag/spina';


/**
 * Options for the DiffComplexityIconView.
 *
 * Version Added:
 *     6.0
 */
interface DiffComplexityIconViewOptions {
    /** The number of deleted lines. */
    numDeletes: number;

    /** The number of inserted lines. */
    numInserts: number;

    /** The number of replaced lines. */
    numReplaces: number;

    /** The total number of lines in the diff. */
    totalLines: number;
}


/**
 * Interface to store colors for the complexity icons.
 */
interface DiffComplexityIconColors {
    /** CSS color definition for an "insert" chunk. */
    insertColor: string;

    /** CSS color definition for a "replace" chunk. */
    replaceColor: string;

    /** CSS color definition for a "delete" chunk. */
    deleteColor: string;
}


/**
 * Renders an icon showing the general complexity of a diff.
 *
 * This icon is a pie graph showing the percentage of inserts vs deletes
 * vs replaces. The size of the white inner radius is a relative indicator
 * of how large the change is for the file, representing the unchanged lines.
 * Smaller inner radiuses indicate much larger changes, whereas larger
 * radiuses represent smaller changes.
 *
 * Callers are not required to supply the total number of lines or the number
 * of replaces, allowing this to be used when only the most basic insert and
 * delete counts are available.
 */
@spina
export class DiffComplexityIconView extends BaseView<
    Backbone.Model,
    HTMLDivElement,
    DiffComplexityIconViewOptions
> {
    static ICON_SIZE = 20;
    static _iconColors: DiffComplexityIconColors = null;

    /**********************
     * Instance variables *
     **********************/

    /** The number of deleted lines. */
    numDeletes: number = null;

    /** The number of inserted lines. */
    numInserts: number = null;

    /** The number of replaced lines. */
    numReplaces: number = null;

    /** The total number of lines in the file. */
    totalLines: number = null;

    /**
     * Initialize the view.
     *
     * Each of the provided values will be normalized to something
     * the view expects.
     *
     * Args:
     *     options (DiffComplexityIconViewOptions):
     *         Options for the view.
     */
    initialize(options: DiffComplexityIconViewOptions) {
        this.numInserts = options.numInserts || 0;
        this.numDeletes = options.numDeletes || 0;
        this.numReplaces = options.numReplaces || 0;
        this.totalLines = options.totalLines || null;
    }

    /**
     * Render the icon.
     */
    onInitialRender() {
        const numTotal = this.numInserts + this.numDeletes + this.numReplaces;
        const numInsertsPct = this.numInserts / numTotal;
        const numDeletesPct = this.numDeletes / numTotal;
        const numReplacesPct = this.numReplaces / numTotal;
        const minValue = 360 * 0.15;
        const innerRadius = (
            0.5 * (this.totalLines === null
                   ? 1
                   : (this.totalLines - numTotal) / this.totalLines));
        const iconColors = DiffComplexityIconView.getIconColors();

        this.$el
            .width(DiffComplexityIconView.ICON_SIZE)
            .height(DiffComplexityIconView.ICON_SIZE)
            .plot(
                [
                    {
                        color: iconColors.insertColor,
                        data: this.#clampValue(numInsertsPct * 360, minValue)
                    },
                    {
                        color: iconColors.deleteColor,
                        data: this.#clampValue(numDeletesPct * 360, minValue)
                    },
                    {
                        color: iconColors.replaceColor,
                        data: this.#clampValue(numReplacesPct * 360, minValue)
                    },
                ],
                {
                    series: {
                        pie: {
                            innerRadius: innerRadius,
                            radius: 0.8,
                            show: true,
                        },
                    },
                }
            );
    }

    /**
     * Clamp the number to be, at minimum, minValue, unless it is 0.
     *
     * Args:
     *     val (number):
     *         The number to clamp.
     *
     *     minValue (number):
     *         The minimum to clamp ``val`` to.
     *
     * Returns:
     *     number:
     *     The clamped number.
     */
    #clampValue(
        val: number,
        minValue: number,
    ): number {
        return val === 0 ? 0 : Math.max(val, minValue);
    }

    /**
     * Return the colors used for the complexity icons.
     *
     * This will create a temporary icon on the DOM and apply the CSS
     * styles for each type of change the icon can show. It will then
     * copy these colors, caching them for all future icons, and return
     * them.
     *
     * Returns:
     *     object:
     *     An object containing the colors to use for the icon.
     */
    static getIconColors(): DiffComplexityIconColors {
        if (!DiffComplexityIconView._iconColors) {
            const $iconColor = $('<div/>')
                .hide()
                .appendTo(document.body);

            $iconColor[0].className = 'diff-changes-icon-insert';
            const insertColor = $iconColor.css('color');

            $iconColor[0].className = 'diff-changes-icon-replace';
            const replaceColor = $iconColor.css('color');

            $iconColor[0].className = 'diff-changes-icon-delete';
            const deleteColor = $iconColor.css('color');

            $iconColor.remove();

            DiffComplexityIconView._iconColors = {
                deleteColor,
                insertColor,
                replaceColor,
            };
        }

        return DiffComplexityIconView._iconColors;
    }
}
