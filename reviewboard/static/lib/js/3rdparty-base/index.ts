import 'babel-polyfill';
import jQuery from 'jquery';


/* Export what's needed to the global namespace. */
const _global = typeof globalThis !== 'undefined' ? globalThis : self;

_global.$ = jQuery
_global.jQuery = jQuery
