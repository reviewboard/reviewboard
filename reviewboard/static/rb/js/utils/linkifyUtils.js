RB.LinkifyUtils = {
    /* Linkify all URLs. */
    linkifyURLs: function(text) {
        return text.replace(
            /\b([a-z]+:\/\/[\-A-Za-z0-9+&@#\/%?=~_()|!:,.;]*([\-A-Za-z0-9+@#\/%=~_();|]|))/g,
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

                var extra = '',
                    parts = url.match(/^(.*)(&[a-z]+;|\))$/),
                    openParen = url.match(/.*\(.*/);

                if (parts !== null && openParen === null) {
                    /* We caught an entity. Set it free. */
                    url = parts[1];
                    extra = parts[2];
                }

                return '<a target="_blank" href="' + url + '">' + url + '</a>' +
                       extra;
            });
    },

    /* Linkify /r/#/ review request numbers */
    linkifyReviewRequests: function(text, markdown) {
        return text.replace(
            /(^|\s|&lt;|\(|\[|{)\/(r\/\d+(\/[\-A-Za-z0-9+&@#\/%?=~_()|!:,.;]*[\-A-Za-z0-9+&@#\/%=~_()|]*)?)/g,
            function(text, m1, m2) {
                var extra = '',
                    url = m2,
                    parts = url.match(/^(.*)(&[a-z]+;|\))$/),
                    href;

                if (parts !== null) {
                    /* We caught an entity. Set it free. */
                    url = parts[1];
                    extra = parts[2];
                }

                href = SITE_ROOT + url + (url.substr(-1) === '/' ? '' : '/');

                if (markdown) {
                    return m1 + '[/' + url + '](' + href + ')' + extra;
                } else {
                    return m1 + '<a target="_blank" href="' + href + '">/' + url + '</a>' + extra;
                }
            });
    },

    /* Bug numbers */
    linkifyBugs: function(text, bugTrackerURL, markdown) {
        if (bugTrackerURL) {
            return text.replace(
                /\b(bug|issue) (#([^.,\s]+)|#?(\d+))/gi,
                function(text, m2, m3, bugnum1, bugnum2) {
                    /*
                     * The bug number can appear in either of those groups,
                     * depending on how this was typed, so try both.
                     */
                    var bugnum = bugnum1 || bugnum2,
                        href = bugTrackerURL.replace("%s", bugnum);

                    if (markdown) {
                        return '[' + text + '](' + href + ')';
                    } else {
                        return '<a target="_blank" href="' + href + '">' + text + '</a>';
                    }
                });
        } else {
            return text;
        }
    },

    /*
     * Linkifies a block of text, turning URLs, /r/#/ paths, and bug numbers
     * into clickable links.
     */
    linkifyText: function(text, bugTrackerURL) {
        text = text.htmlEncode();
        text = RB.LinkifyUtils.linkifyURLs(text);
        text = RB.LinkifyUtils.linkifyReviewRequests(text);
        text = RB.LinkifyUtils.linkifyBugs(text, bugTrackerURL);
        return text;
    }
};
