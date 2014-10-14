(function() {


// If `marked` is defined, initialize it with our preferred options
if (marked !== undefined) {
    marked.setOptions({
        gfm: true,
        tables: true,
        breaks: true,
        pedantic: false,
        sanitize: true,
        smartLists: true,
        langPrefix : 'language-',
        highlight: function(code, lang) {
            // Use google code prettify to render syntax highlighting
            return prettyPrintOne(_.escape(code), lang, true /* line nos. */);
        }
    });
}


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

    if ($el.data('rich-text')) {
        if (options.newText !== undefined) {
            $el
                .html(options.newText)
                .addClass('rich-text')
        }

        $el.find('a').attr('target', '_blank');
        RB.LinkifyUtils.linkifyChildren($el[0], options.bugTrackerURL);
    } else if (options.newText !== undefined) {
        $el.html(RB.LinkifyUtils.linkifyText(options.text,
                                             options.bugTrackerURL));
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
