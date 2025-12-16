import Masonry from 'masonry-layout';


/* Export what's needed to the global namespace. */
const _global = typeof globalThis !== 'undefined' ? globalThis : self;
_global.Masonry = Masonry;
