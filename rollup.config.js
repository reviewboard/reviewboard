import babel from '@rollup/plugin-babel';
import commonjs from '@rollup/plugin-commonjs';
import externalGlobals from 'rollup-plugin-external-globals';
import path from 'path';
import resolve from '@rollup/plugin-node-resolve';


const extensions = [
    '.es6.js',
    '.js',
    '.ts',
];


const commonConfigs = {
    external: [
        '$',
        'jQuery',
        'jquery',
    ],
    globals: {
        '$': '$',
        jQuery: '$',
        jquery: '$',
    },
    output: {
        //esModule: false,

        /* Enforce named exports, helping with CommonJS compatibility. */
        exports: 'named',

        /*
         * Don't freeze properties. We want to be able to mutate $, _,
         * Backbone, etc.
         */
        freeze: false,

        /* Generate sourcemaps for the bundle. */
        sourcemap: true,

        /*
         * Use the UMD format, letting us load these in outside a browser.
         *
         * This isn't used today but opens the doors to local unit testing or
         * other non-browser uses.
         */
        format: 'umd',

        generatedCode: 'es2015',
    },
    plugins: {
        babel: {
            babelHelpers: 'external',
            extensions: extensions,
        },

        commonjs: {
            ignoreTryCatch: false,
            transformMixedEsModules: true,
        },

        resolve: {
            browser: true,
            extensions: extensions,
            modulePaths: [
                'node_modules',
            ],
        },
    },
    treeshake: {
        /*
         * Make sure that any imported but unused modules are retained, not
         * ignored, as it's possible to import from a module and compile
         * before writing code to export anything in that module.
         *
         * In that particular case, if the imported module were ignored, the
         * Rollup compiler for Pipeline wouldn't know about it and wouldn't
         * check to see if a recompile is needed.
         *
         * This should be the default, but we want to be explicit here.
         */
        moduleSideEffects: true,
    }
};


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
    output: commonConfigs.output,
    plugins: [
        /* This must take place before babel(). */
        commonjs(commonConfigs.plugins.commonjs),

        /* Configure rollup to use Babel to compile files. */
        babel(commonConfigs.plugins.babel),

        /* Specify where modules should be looked up from. */
        resolve(commonConfigs.plugins.resolve),
    ],
    treeshake: commonConfigs.treeshake,
};


/**
 * Configuration for all other lib bundles (3rdparty and others).
 *
 * These are dependent on 3rdparty-base.
 */
function makeThirdPartyConfig(input) {
    return {
        external: commonConfigs.external,
        input: input,
        output: {
            ...commonConfigs.output,

            globals: commonConfigs.globals,
        },
        plugins: [
            /* This must take place before babel(). */
            commonjs(commonConfigs.plugins.commonjs),

            /* Configure rollup to use Babel to compile files. */
            babel(commonConfigs.plugins.babel),

            /* Specify where modules should be looked up from. */
            resolve(commonConfigs.plugins.resolve),
        ],
        treeshake: commonConfigs.treeshake,
    };
}


/**
 * Configuration for the rest of the Review Board (and Djblets) codebases.
 *
 * These are set up to reference the external libraries from the lib bundles
 * as globals, ensuring we don't end up bundling them unintentionally.
 */
const rbConfig = {
    external: [
        ...commonConfigs.external,

        '@beanbag/spina',
        'backbone',
        'django',
        'djblets',
        'underscore',
    ],
    output: {
        ...commonConfigs.output,

        /*
         * Anything exported from a top-level index.* file (as specified in
         * the Pipeline bundle configuration) will be placed in this top-level
         * variable.
         *
         * Ensure the namespace is extended, not replaced with each module.
         */
        name: 'RB',
        extend: true,

        /*
         * Each of these globals will be assumed to exist when the module is
         * loaded. They won't have to be imported.
         */
        globals: {
            ...commonConfigs.globals,

            '@beanbag/spina': 'Spina',
            RB: 'RB',
            backbone: 'Backbone',
            django: 'django',
            djblets: 'Djblets',
            underscore: '_',
        },
    },
    plugins: [
        /* Configure rollup to use Babel to compile files. */
        babel(commonConfigs.plugins.babel),

        /*
         * Convert any module import paths from our projects to instead look up
         * in top-level namespace variables.
         */
        externalGlobals(id => {
            if (id.startsWith('djblets/')) {
                return 'Djblets';
            }

            if (id.startsWith('reviewboard/')) {
                return 'RB';
            }
        }),

        /* Specify where modules should be looked up from. */
        resolve({
            ...commonConfigs.plugins.resolve,

            modulePaths: [
                'reviewboard/static/lib/js',
                'reviewboard/static/rb/js',
                '.djblets/static/djblets/js',
                'node_modules',
            ],
        }),
    ],
    treeshake: commonConfigs.treeshake,
};


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
