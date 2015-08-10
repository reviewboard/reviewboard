/*
 * Copyright 2008-2010 Christian Hammond.
 * Copyright 2010-2013 Beanbag, Inc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to
 * deal in the Software without restriction, including without limitation the
 * rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
 * sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
 * IN THE SOFTWARE.
 */
(function($) {


/*
 * IE <=8 has broken innerHTML support. Newlines and other whitespace is
 * stripped from the HTML, even when inserting into a <pre>. This doesn't
 * happen, however, if the whole html is wrapped in a <pre> before being set.
 * So our new version of html() wraps it and then removes that inner <pre>
 * tag.
 */
$.fn.old_html = $.fn.html;
$.fn.html = function(value) {
    var removePre = false,
        ret,
        preTag;

    if ($.browser.msie && value !== undefined && this[0] &&
        /^(pre|textarea)$/i.test(this[0].tagName)) {
        value = "<pre>" + value + "</pre>";
        removePre = true;
    }

    ret = this.old_html.apply(this, value === undefined ? [] : [value]);

    if (removePre) {
        preTag = this.children();
        preTag.replaceWith(preTag.contents());
    }

    return ret;
};


})(jQuery);

// vim: set et:
