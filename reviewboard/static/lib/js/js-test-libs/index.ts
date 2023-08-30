import { suite } from '@beanbag/jasmine-suites';


/* Export what's needed to the global namespace. */
const _global = typeof globalThis !== 'undefined' ? globalThis : self;

_global.suite = suite;
