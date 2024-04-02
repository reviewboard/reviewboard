import babel from '@rollup/plugin-babel';
import commonjs from '@rollup/plugin-commonjs';
import externalGlobals from 'rollup-plugin-external-globals';
import path from 'path';
import resolve from '@rollup/plugin-node-resolve';

import {
    makeReviewBoardRollupConfig,
} from '@beanbag/reviewboard/packaging/js/rollup-common.mjs';


export function buildReviewBoardExtensionConfig(options) {
    const modulePaths = options.modulePaths || [];

    return makeReviewBoardRollupConfig({
        ...options,

        modulePaths: [
            ...modulePaths,

            'node_modules/@beanbag/reviewboard/static/lib/js',
            'node_modules/@beanbag/reviewboard/static/rb/js',
            'node_modules/@beanbag/djblets/static/djblets/js',
        ],
    });
}


export function rollupExtension(options) {
    return args => buildExtensionPackagingConfig(options);
}
