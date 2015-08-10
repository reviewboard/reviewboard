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
 * If appropriate, reload gravatar <img> tags with retina resolution
 * equivalents.
 */
$.fn.retinaGravatar = function() {
    if (window.devicePixelRatio > 1) {
        $(this).each(function() {
            var $el = $(this),
                src = $el.attr('src'),
                parts = src.split('?', 2),
                params,
                param,
                baseurl,
                size,
                i;

            if (parts.length === 2) {
                baseurl = parts[0];
                params = parts[1].split('&');

                for (i = 0; i < params.length; i++) {
                    param = params[i].split('=', 2);

                    if (param.length === 2 && param[0] === 's') {
                        size = parseInt(param[1], 10);
                        params[i] = 's=' + Math.floor(size * window.devicePixelRatio);
                    }
                }

                $el
                    .attr('src', baseurl + '?' + params.join('&'))
                    .removeClass('gravatar')
                    .addClass('gravatar-retina');
            } else {
                console.log('Failed to parse URL for gravatar ' + src);
            }
        });
    }

    return this;
};


})(jQuery);

// vim: set et:
