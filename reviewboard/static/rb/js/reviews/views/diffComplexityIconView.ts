/**
 * An icon for showing the general complexity of a diff.
 */

import {
    BaseModel,
    BaseView,
    spina,
} from '@beanbag/spina';
import _ from 'underscore';


/**
 * Options for the DiffComplexityIconView.
 *
 * Version Changed:
 *     7.0:
 *     Added ``iconSize``.
 *
 * Version Added:
 *     6.0
 */
export interface DiffComplexityIconViewOptions {
    /**
     * The size to set for the width and height of the icon, in pixels.
     *
     * Version Added:
     *     7.0
     */
    iconSize: number;

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
 * Information on a segment of the diff complexity graph.
 *
 * Version Added:
 *     7.0
 */
interface DiffSegment {
    /** The class name used for the segment. */
    className: string;

    /** The percentage of the graph taken up by the segment. */
    pct: number;

    /** The title text for the segment. */
    title: string;
}


/**
 * The data backing the diff complexity graph.
 *
 * Version Added:
 *     7.0
 */
interface GraphData {
    /**
     * The total number of changes represented by the graph.
     *
     * This is the sum of the inserts, deletes, and replaces.
     */
    numTotal: number;

    /** The segments to render in the graph. */
    segments: DiffSegment[];
}


/* Some useful constants we'll use a lot. */
const HALF_PI = Math.PI / 2;
const TAU = Math.PI * 2;
const RADIANS_PER_DEGREE = Math.PI / 180;


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
 *
 * Version Changed:
 *     7.0:
 *     This was rewritten to generate a SVG. It's effectively a full rewrite.
 */
@spina
export class DiffComplexityIconView extends BaseView<
    BaseModel,
    HTMLDivElement,
    DiffComplexityIconViewOptions
> {
    static className = 'rb-c-diff-complexity-icon';

    /** The default icon size for the graph in pixels. */
    static ICON_SIZE = 20;

    /**
     * The ratio of the inner radius to the total number of unchanged lines.
     *
     * Version Added:
     *     7.0
     */
    static _INNER_RADIUS_RATIO = 0.6;

    /**
     * The gap size between segments.
     *
     * Version Added:
     *     7.0
     */
    static _SEGMENT_GAP = 1.25;

    /**
     * The percentage of the icon size taken up by padding.
     *
     * This is a percentage a scale from 0 to 1.
     *
     * Version Added:
     *     7.0
     */
    static _PADDING_PCT = 0.2;

    /**
     * The minimum percentage value used for any segment.
     *
     * This is a percentage a scale from 0 to 1.
     *
     * Version Added:
     *     7.0
     */
    static _MIN_VALUE_PCT = 0.1;

    /**********************
     * Instance variables *
     **********************/

    /** The size of the icon in width and height. */
    iconSize = DiffComplexityIconView.ICON_SIZE;

    /** The number of deleted lines. */
    numDeletes = 0;

    /** The number of inserted lines. */
    numInserts = 0;

    /** The number of replaced lines. */
    numReplaces = 0;

    /** The total number of lines in the file. */
    totalLines: number | null = null;

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
        if (options) {
            this.numInserts = options.numInserts || 0;
            this.numDeletes = options.numDeletes || 0;
            this.numReplaces = options.numReplaces || 0;
            this.totalLines = options.totalLines || null;
            this.iconSize = options.iconSize || this.iconSize;
        }
    }

    /**
     * Render the icon.
     *
     * This will calculate the data for the graph and then render it to an
     * inner SVG.
     */
    protected onInitialRender() {
        const graphData = this.#generateData();

        if (graphData === null) {
            /* There's nothing to render. */
            return;
        }

        /*
         * Determine the common positioning and segment data we're going to
         * work with.
         */
        const el = this.el;
        const segments = graphData.segments;
        const iconSize = this.iconSize;
        const center = iconSize / 2;
        const gap = DiffComplexityIconView._SEGMENT_GAP;

        /*
         * If we only have one segment, we'll need to handle rendering this
         * slightly differently, and avoid any gaps. Track this.
         */
        const wholeDonut = (segments.length === 1);

        /*
         * Calculate our radiuses.
         *
         * We'll fudge the numbers a bit to add some padding around the
         * outside and to keep a reasonable ratio on the inside. It'll be
         * 75% of the available size.
         */
        const radius = Math.round(center *
                                  (1 - DiffComplexityIconView._PADDING_PCT));
        const totalLines = this.totalLines;
        const innerRadius = Math.max(
            wholeDonut ? 0 : gap,
            Math.ceil(
                center * DiffComplexityIconView._INNER_RADIUS_RATIO *
                (totalLines === null
                 ? 1
                 : (totalLines - graphData.numTotal) / totalLines)));

        /* Set the size of our icon. */
        el.setAttribute('role', 'figure');
        el.style.width = `${iconSize}px`;
        el.style.height = `${iconSize}px`;

        /*
         * Build the outer SVG element.
         *
         * NOTE: JQuery can't create SVG elements, as it'll get the namespace
         *       wrong. Ink (as of this writing -- April 16, 2024) can't
         *       either. We must create by hand.
         */
        const svgEl = document.createElementNS(
            'http://www.w3.org/2000/svg',
            'svg');
        svgEl.setAttribute('aria-hidden', 'true');
        svgEl.setAttribute('width', '100%');
        svgEl.setAttribute('height', '100%');
        svgEl.setAttribute('viewBox', `0 0 ${iconSize} ${iconSize}`);

        /* Begin building the graph data. */
        const titles: string[] = [];
        let startAngle = 0;

        for (const segment of segments) {
            const pct = segment.pct;
            let pathData: string;

            if (wholeDonut) {
                /*
                 * Prepare the path data for the whole donut segment.
                 * We'll be drawing two 180 degree semicircles each for the
                 * outer and inner radiuses. This is needed because an arc
                 * can't itself be 360 degrees.
                 */
                pathData = dedent`
                    M ${center} ${center - radius}
                    A ${radius} ${radius}
                      0 1 1
                      ${center} ${center + radius}
                    A ${radius} ${radius}
                      0 1 1
                      ${center} ${center - radius}
                    M ${center} ${center - innerRadius}
                    A ${innerRadius} ${innerRadius}
                      0 1 0
                      ${center} ${center + innerRadius}
                    A ${innerRadius} ${innerRadius}
                      0 1 0
                      ${center} ${center - innerRadius}
                    Z
                `;
            } else {
                /*
                 * Calculate the coordinates for each point in the segment's
                 * arc, taking care to ensure a consistent gap between
                 * segments.
                 */
                const segmentAngleRadians = (pct * 360) * RADIANS_PER_DEGREE;

                /*
                 * We have to set the large-arc-path to 1 if greatr than 180
                 * degrees in order for the arc to render correctly.
                 */
                const largeArcPath = segmentAngleRadians > Math.PI ? 1 : 0;

                /*
                 * Determine the gaps we want at both the inner and outer
                 * points.
                 *
                 * If there's no inner radius (or a very tiny one), we could
                 * get a NaN, so we always fall back on the gap.
                 */
                const gapAngleOuter =
                    Math.asin(gap / (2 * radius));
                const gapAngleInner =
                    Math.asin(gap / (2 * innerRadius));

                /*
                 * Calculate the coordinates of the inner and outer radiuses.
                 */
                const endAngle = startAngle + segmentAngleRadians;

                const outerCoords = this.#getCoords(
                    startAngle + gapAngleOuter,
                    endAngle - gapAngleOuter,
                    radius,
                    center);
                const innerCoords = this.#getCoords(
                    startAngle + gapAngleInner,
                    endAngle - gapAngleInner,
                    innerRadius,
                    center);

                /*
                 * Prepare the path data for the segment.
                 *
                 * We'll be drawing this as two arcs (an outer and inner),
                 * with lines connecting them.
                 */
                pathData = dedent`
                    M ${innerCoords[0]}
                    L ${outerCoords[0]}
                    A ${radius} ${radius}
                      0 ${largeArcPath} 1
                      ${outerCoords[1]}
                    L ${innerCoords[1]}
                    A ${innerRadius} ${innerRadius}
                      0 ${largeArcPath} 0
                      ${innerCoords[0]}
                    Z
                `;
            }

            const pathEl = document.createElementNS(
                'http://www.w3.org/2000/svg',
                'path');
            pathEl.classList.add(segment.className);
            pathEl.setAttribute('d', pathData);
            svgEl.appendChild(pathEl);

            titles.push(segment.title);
            startAngle += pct * TAU;
        }

        el.appendChild(svgEl);

        /* Generate a title for the graph showing the line counts. */
        const numTotal = graphData.numTotal;
        const titlesStr = titles.join(', ');
        const label =
            N_(`${numTotal} of ${totalLines} line changed: ${titlesStr}`,
               `${numTotal} of ${totalLines} lines changed: ${titlesStr}`,
               totalLines);

        el.setAttribute('aria-label', label);

        const titleEl = document.createElementNS(
            'http://www.w3.org/2000/svg',
            'title');
        titleEl.textContent = label;
        svgEl.appendChild(titleEl);
    }

    /**
     * Return the start and end coordinates for an arc on a segment.
     *
     * This will determine the coordinates that make up the arc, and
     * return them as pairs of strings for placement insode of a
     * ``<path>``.
     *
     * Args:
     *     startAngle (number):
     *         The angle from the center for the start of the segment.
     *
     *     endAngle (number):
     *         The angle from the center for the end of the segment.
     *
     *     radius (number):
     *         The radius used for the arc.
     *
     *     center (number):
     *         The center of the graph.
     *
     * Returns:
     *     Array:
     *     A 2-array of strings, one for the starting coordinates and one
     *     for the ending coordinates.
     */
    #getCoords(
        startAngle: number,
        endAngle: number,
        radius: number,
        center: number,
    ): [string, string] {
        const startRadians = startAngle - HALF_PI;
        const endRadians = endAngle - HALF_PI;

        const startX = center + radius * Math.cos(startRadians);
        const startY = center + radius * Math.sin(startRadians);
        const endX = center + radius * Math.cos(endRadians);
        const endY = center + radius * Math.sin(endRadians);

        return [
            `${startX} ${startY}`,
            `${endX} ${endY}`,
        ];
    }

    /**
     * Generate data for the graph.
     *
     * This will compute the inserts, deletes, and replaces, along with
     * styling and title data, returning data used for render.
     *
     * Any empty segments will be filtered out, and any that fall below a
     * minimum size will be capped to that minimum, taking away from the
     * size of the largest segment.
     *
     * Returns:
     *     GraphData:
     *     The generated graph data, or ``null`` if there's nothing to
     *     render.
     */
    #generateData(): GraphData | null {
        const numInserts = this.numInserts;
        const numDeletes = this.numDeletes;
        const numReplaces = this.numReplaces;

        const numTotal = numInserts + numDeletes + numReplaces;

        if (numTotal === 0) {
            return null;
        }

        /*
         * Start by building a map of all data and filtering to segments with
         * non-0 percentages.
         */
        const minValuePct = DiffComplexityIconView._MIN_VALUE_PCT;
        let anyBelowMin = false;
        let availLen = 0;
        let largestOldIndex: number = null;
        let largestNewIndex: number = null;

        const segments: DiffSegment[] = [
            {
                className: 'rb-c-diff-complexity-icon__insert',
                pct: numInserts / numTotal,
                title: N_(`${numInserts} line added`,
                          `${numInserts} lines added`,
                          numInserts),
            },
            {
                className: 'rb-c-diff-complexity-icon__delete',
                pct: numDeletes / numTotal,
                title: N_(`${numDeletes} line deleted`,
                          `${numDeletes} lines deleted`,
                          numDeletes),
            },
            {
                className: 'rb-c-diff-complexity-icon__replace',
                pct: numReplaces / numTotal,
                title: N_(`${numReplaces} line replaced`,
                          `${numReplaces} lines replaced`,
                          numReplaces),
            },
        ].filter((data, index, array) => {
            /* Filter out any segments that would be 0 in length. */
            if (data.pct <= 0) {
                return false;
            }

            /*
             * Check for any segments below the minimum value, and also
             * locate the largest segment.
             */
            if (data.pct < minValuePct) {
                anyBelowMin = true;
            } else if (largestOldIndex === null ||
                       data.pct > array[largestOldIndex].pct) {
                largestOldIndex = index;
                largestNewIndex = availLen;
            }

            availLen++;

            return true;
        });

        if (anyBelowMin) {
            /*
             * We now need to set some minimums and subtract from the largest
             * segment.
             */
            console.assert(largestNewIndex !== null);

            for (let i = 0; i < segments.length; i++) {
                const data = segments[i];

                if (data.pct < minValuePct) {
                    const pctDiff = minValuePct - data.pct;
                    data.pct = minValuePct;

                    /* Subtract this from the largest segment. */
                    segments[largestNewIndex].pct -= pctDiff;
                }
            }
        }

        return {
            numTotal: numTotal,
            segments: segments,
        };
    }
}
