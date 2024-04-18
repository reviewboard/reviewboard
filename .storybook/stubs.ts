/**
 * Stubs needed for the execution of our JavaScript.
 *
 * Version Added:
 *     7.0
 */

/*
 * Babel won't transform our JavaScript within the context of Storybook, so
 * we're going to need to put together some stubs for some tagged template
 * literals we use.
 */
window['gettext'] = (str) => str;
window['ngettext'] = (singular, plural, count) => (count === 1
                                                   ? singular
                                                   : plural);
window['interpolate'] = (fmt, obj, named) => {
    if (named) {
        return fmt.replace(/%\(\w+\)s/g, m => String(obj[m.slice(2, -2)]));
    } else {
        return fmt.replace(/%s/g, match => String(obj.shift()));
    }
};


window['IS_STORYBOOK'] = true;

/* Inject some attributes expected by the codebase. */
window['MANUAL_URL'] = 'https://www.reviewboard.org/docs/manual/latest/';
