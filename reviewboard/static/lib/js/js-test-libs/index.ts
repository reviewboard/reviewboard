/* The order matters for these jasmine imports. */
import 'jasmine-core/lib/jasmine-core/jasmine.js';
import 'jasmine-core/lib/jasmine-core/jasmine-html.js';
import 'jasmine-core/lib/jasmine-core/boot0.js';
import 'jasmine-core/lib/jasmine-core/boot1.js';

import { suite } from '@beanbag/jasmine-suites';

import './jasmine-sourcemaps';
import './jasmine-hide-filtered';

/* Export what's needed to the global namespace. */
const _global = typeof globalThis !== 'undefined' ? globalThis : self;

_global.suite = suite;
