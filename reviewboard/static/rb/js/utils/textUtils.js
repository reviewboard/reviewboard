(function() {


/*
 * Format the given text and put it into $el.
 *
 * If the given element is expected to be rich text, this will format the text
 * using Markdown.
 *
 * Otherwise, if it's not expected and won't be converted, then it will add
 * links to review requests and bug trackers but otherwise leave the text alone.
 */
RB.formatText = function($el, options) {
    options = options || {};

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


/*
 * Format a timestamp in the same way that Django templates would.
 */
RB.FormatTimestamp = function(timestamp) {
    return timestamp.format('MMMM Do, YYYY, h:mm ') +
           (timestamp.hour() < 12 ? 'a.m.' : 'p.m.');
};


}());
