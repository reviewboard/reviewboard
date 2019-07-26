RB.LinkifyUtils = {
    URL_RE: new RegExp(
        '\\b((' + [
            'https://',
            'http://',
            'ftp://',
            'ftps://',
            'gopher://',
            'mailto:',
            'news:',
            'sms:'
        ].join('|') +
        ')[\\-A-Za-z0-9+&@#\/%?=~_()|!:,.;]*([\\-A-Za-z0-9+@#\/%=~_();|]|))',
        'g'
    ),

    /**
     * Linkify all URLs within some text.
     *
     * This will turn things that look like URLs into clickable links.
     *
     * Args:
     *     text (string):
     *         The text to linkify.
     *
     * Returns:
     *     string:
     *     The given text with all URLs replaced by <a> tags.
     */
    linkifyURLs(text) {
        return text.replace(
            RB.LinkifyUtils.URL_RE,
            function(url) {
                /*
                 * We might catch an entity at the end of the URL. This is hard
                 * to avoid, since we can't rely on advanced RegExp techniques
                 * in all browsers. So, we'll now search for it and prevent it
                 * from being part of the URL if it exists. However, a URL with
                 * an open bracket will not have its close bracket removed. This
                 * was a modification to the original bug fix.
                 *
                 * See bug 1069.
                 */
                const parts = url.match(/^(.*)(&[a-z]+;|\))$/);
                const openParen = url.match(/.*\(.*/);

                let extra = '';

                if (parts !== null && openParen === null) {
                    /* We caught an entity. Set it free. */
                    url = parts[1];
                    extra = parts[2];
                }

                return `<a target="_blank" href="${url}">${url}</a>${extra}`;
            });
    },

    /**
     * Linkify /r/# review request numbers.
     *
     * This will turn things that look like references to other review requests
     * into clickable links.
     *
     * Args:
     *     text (string):
     *         The text to linkify.
     *
     * Returns:
     *     string:
     *     The given text with all "/r/#" text replaced by <a> tags.
     */
    linkifyReviewRequests(text) {
        return text.replace(
            /(^|\s|&lt;|\(|\[|{)\/(r\/\d+(\/[\-A-Za-z0-9+&@#\/%?=~_()|!:,.;]*[\-A-Za-z0-9+&@#\/%=~_()|]*)?)/g,
            function(text, m1, m2) {
                const parts = m2.match(/^(.*)(&[a-z]+;|\))$/);

                let extra = '';
                let url = m2;

                if (parts !== null) {
                    /* We caught an entity. Set it free. */
                    url = parts[1];
                    extra = parts[2];
                }

                const href = SITE_ROOT + url + (url.substr(-1) === '/' ? '' : '/');

                return `${m1}<a target="_blank" href="${href}" class="review-request-link">/${url}</a>${extra}`;
            });
    },

    /**
     * Linkify bug numbers.
     *
     * This will turn things that look like references to bugs (such as
     * "bug 408") into clickable links.
     *
     * Args:
     *     text (string):
     *         The text to linkify.
     *
     *     bugTrackerURL (string):
     *         The URL to use when formatting the bug number. This is expected
     *         to have the literal ``--bug_id--`` in it, which will be replaced
     *         by the captured bug ID.
     *
     * Returns:
     *     string:
     *     The given text with all bug references replaced by <a> tags.
     */
    linkifyBugs(text, bugTrackerURL) {
        if (bugTrackerURL) {
            return text.replace(
                /\b(bug|issue) (#([^.,)\]\s]+)|#?(\d+))/gi,
                function(text, m2, m3, bugnum1, bugnum2) {
                    /*
                     * The bug number can appear in either of those groups,
                     * depending on how this was typed, so try both.
                     */
                    const bugnum = bugnum1 || bugnum2;
                    const href = bugTrackerURL.replace("--bug_id--", bugnum);

                    return `<a target="_blank" href="${href}">${text}</a>`;
                });
        } else {
            return text;
        }
    },

    /**
     * Linkify text using all available methods.
     *
     * Linkifies a block of text, turning URLs, /r/#/ paths, and bug numbers
     * into clickable links.
     *
     * Args:
     *     text (string):
     *         The text to linkify.
     *
     *     bugTrackerURL (string):
     *         The URL to use when formatting the bug number. This is expected
     *         to have the literal ``--bug_id--`` in it, which will be replaced
     *         by the captured bug ID.
     *
     *     isHTMLEncoded (boolean):
     *         Whether or not the given text has already had dangerous
     *         characters (like < or >) replaced by their HTML entities. If
     *         this is false, the text will first be encoded.
     *
     * Returns:
     *     string:
     *     The given text with all linkifyable items replaced by <a> tags.
     */
    linkifyText(text, bugTrackerURL, isHTMLEncoded) {
        if (!isHTMLEncoded) {
            text = text.htmlEncode();
        }

        text = RB.LinkifyUtils.linkifyURLs(text);
        text = RB.LinkifyUtils.linkifyReviewRequests(text);
        text = RB.LinkifyUtils.linkifyBugs(text, bugTrackerURL);
        return text;
    },

    /**
     * Linkify text within a pre-established DOM tree.
     *
     * This iterates through a tree of nodes, linkifying any text nodes that
     * reference bug URLs, review requests, or contain unlinked plain-text
     * URLs.
     *
     * This will avoid linking anything within a <pre> tag, to avoid messing
     * with code blocks, and <a> tags, to avoid linkifying existing links.
     *
     * Args:
     *     el (Element):
     *         The element to linkify.
     *
     *     bugTrackerURL (string):
     *         The URL to use when formatting the bug number. This is expected
     *         to have the literal ``--bug_id--`` in it, which will be replaced
     *         by the captured bug ID.
     */
    linkifyChildren(el, bugTrackerURL) {
        for (let i = 0; i < el.childNodes.length; i++) {
            const node = el.childNodes[i];

            if (node.nodeType === node.TEXT_NODE) {
                if (node.textContent) {
                    const newText = RB.LinkifyUtils.linkifyText(
                        node.textContent, bugTrackerURL);

                    if (newText !== node.textContent) {
                        $(node).replaceWith(newText);
                    }
                }
            } else if (node.nodeType === node.ELEMENT_NODE) {
                if (node.nodeName !== 'PRE' && node.nodeName !== 'A') {
                    RB.LinkifyUtils.linkifyChildren(node, bugTrackerURL);
                }
            }
        }
    }
};
