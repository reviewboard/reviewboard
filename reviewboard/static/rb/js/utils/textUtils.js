(function() {


/*
 * NOTE: Any changes made here or in escapeMarkdown below should be
 *       reflected in reviewboard/reviews/markdown_utils.py.
 */
var MARKDOWN_SPECIAL_CHARS_RE = /([\\`\*_\{\}\[\]\(\)\>\#\+\-\.\!])/g,
    ESCAPE_CHARS_RE = /(^\s*(\d+\.)+|^\s*(\#)+|^\s*[-\+]+|[\\`\*_\{\}\[\]\(\)\>\!])/gm;


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
 * If it's not expected to be rich text, but we want to force conversion to
 * rich text, this will escape the text and turn it into valid Markdown.
 *
 * Otherwise, if it's not expected and won't be converted, then it will add
 * links to review requests and bug trackers but otherwise leave the text alone.
 */
RB.formatText = function($el, text, bugTrackerURL, options) {
    var markedUp;
        elRichText = $el.data('rich-text');

    if (options && options.forceRichText && !elRichText) {
        text = RB.escapeMarkdown(text);
        $el.data('rich-text', true);
        elRichText = true;
    }

    markedUp = text;

    if (elRichText) {
        /*
         * If there's an inline editor attached to this element, set up some
         * options first. Primarily, we need to pass in the raw value of the
         * text as an option, rather than let it pull it out of the DOM.
         */
        if ($el.data('inlineEditor')) {
            $el.inlineEditor('option', {
                hasRawValue: true,
                matchHeight: false,
                rawValue: text
            });
        }

        if (markedUp.length > 0) {
            // Now linkify and markdown-ize
            markedUp = RB.LinkifyUtils.linkifyReviewRequests(markedUp, true);
            markedUp = RB.LinkifyUtils.linkifyBugs(markedUp, bugTrackerURL, true);
            markedUp = marked(markedUp);

            /*
             * markup() adds newlines to each directive, resulting in a trailing
             * newline for the contents. Since this may be formatted inside a
             * <pre>, we want to make sure we don't have that extra newline.
             */
            markedUp = markedUp.trim();
        }

        $el
            .empty()
            .append(markedUp)
            .addClass('rich-text')
            .removeClass('loading')
            .find('a')
                .attr('target', '_blank');
    } else {
        $el.html(RB.LinkifyUtils.linkifyText(text, bugTrackerURL));
    }
};


/*
 * Escapes text, turning it into valid Markdown, without causing any existing
 * characters to be interpreted as Markdown.
 */
RB.escapeMarkdown = function(text) {
    return text.replace(ESCAPE_CHARS_RE, function(text, m1) {
        return m1.replace(MARKDOWN_SPECIAL_CHARS_RE, '\\$1');
    });
};


}());
