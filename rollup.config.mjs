import babel from '@rollup/plugin-babel';
import commonjs from '@rollup/plugin-commonjs';
import resolve from '@rollup/plugin-node-resolve';

import {
    commonRollupConfig,
    makeReviewBoardRollupConfig
} from '@beanbag/reviewboard/packaging/js/rollup-common.mjs';


/*
 * Configuration for the 3rdparty-base bundle.
 *
 * This bundle provides only a couple of base modules that we want to make
 * sure are loaded before anything else.
 *
 * This will require a combination of CommonJS and ES6 modules, coming from
 * node_modules.
 */
const thirdPartyBaseConfig = {
    output: commonRollupConfig.output,
    plugins: [
        /* This must take place before babel(). */
        commonjs(commonRollupConfig.plugins.commonjs),

        /* Configure rollup to use Babel to compile files. */
        babel(commonRollupConfig.plugins.babel),

        /* Specify where modules should be looked up from. */
        resolve(commonRollupConfig.plugins.resolve),
    ],
    treeshake: commonRollupConfig.treeshake,
};


/**
 * Configuration for all other lib bundles (3rdparty and others).
 *
 * These are dependent on 3rdparty-base.
 */
function makeThirdPartyConfig(input) {
    return {
        ...thirdPartyBaseConfig,

        external: commonRollupConfig.external,
        input: input,
        output: {
            ...thirdPartyBaseConfig.output,

            globals: commonRollupConfig.globals,
        },
    };
}


/**
 * Configuration for the rest of the Review Board (and Djblets) codebases.
 *
 * These are set up to reference the external libraries from the lib bundles
 * as globals, ensuring we don't end up bundling them unintentionally.
 */
const rbConfig = makeReviewBoardRollupConfig({
    output: {
        /*
         * Anything exported from a top-level index.* file (as specified in
         * the Pipeline bundle configuration) will be placed in this top-level
         * variable.
         */
        name: 'RB',
    },
    modulePaths: [
        'reviewboard/static/lib/js',
        'reviewboard/static/rb/js',
        '.npm-workspaces/djblets/static/djblets/js',
    ],
});


export default args => {
    const input = (args.input || [''])[0];

    if (input.includes('reviewboard/static/lib/js/3rdparty-base/')) {
        return thirdPartyBaseConfig;
    } else if (input.includes('reviewboard/static/lib/')) {
        return makeThirdPartyConfig(input);
    } else {
        return rbConfig;
    }
};
