/**
 * Format the given text and put it into an element.
 *
 * If the given element is expected to be rich text, this will put the contents
 * of the new text directly into the element (since it has already been
 * rendered using Markdown).
 *
 * Otherwise, this will add links to review requests and bug trackers but
 * otherwise leave the text alone.
 *
 * Args:
 *     $el (jQuery):
 *         The element to put the text into
 *
 *     options (object):
 *          Options for the format operation.
 *
 * Option Args:
 *     newText (string):
 *         The text to format.
 *
 *     richText (boolean):
 *         Whether the new text is already formatted from Markdown.
 *
 *     bugTrackerURL (string):
 *         The bug tracker URL to use when linking bugs.
 *
 *     isHTMLEncoded (string):
 *         Whether the new text has already had dangerous characters (like <
 *         and >) escaped to their entities.
 */
RB.formatText = function($el, options={}) {
    if (options.richText) {
        if (options.newText !== undefined) {
            $el.html(options.newText);
        }

        $el
            .addClass('rich-text')
            .find('a')
                .attr('target', '_blank');

        RB.LinkifyUtils.linkifyChildren($el[0], options.bugTrackerURL);
    } else if (options.newText !== undefined) {
        $el
            .html(RB.LinkifyUtils.linkifyText(options.newText || '',
                                              options.bugTrackerURL,
                                              options.isHTMLEncoded))
            .removeClass('rich-text');
    } else if ($el !== undefined && $el.length !== 0) {
        RB.LinkifyUtils.linkifyChildren($el[0], options.bugTrackerURL);
    }
};
