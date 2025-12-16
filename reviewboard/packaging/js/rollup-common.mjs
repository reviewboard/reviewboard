import babel from '@rollup/plugin-babel';
import externalGlobals from 'rollup-plugin-external-globals';
import resolve from '@rollup/plugin-node-resolve';


export const supportedJSExtensions = [
    '.es6.js',
    '.js',
    '.ts',
];


export const commonRollupConfig = {
    external: [
        '$',
        'babel-plugin-dedent',
        'babel-plugin-django-gettext',
        'jQuery',
        'jasmine-core',
        'jquery',
    ],
    globals: {
        '$': '$',
        jQuery: '$',
        jquery: '$',
        'jasmine-core': 'window',
    },
    output: {
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
            extensions: supportedJSExtensions,
        },

        commonjs: {
            ignoreTryCatch: false,
            transformMixedEsModules: true,
        },

        resolve: {
            browser: true,
            extensions: supportedJSExtensions,
            moduleDirectories: [],
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
    },
};


export function makeReviewBoardRollupConfig(options) {
    const externalConfig = options.external || [];
    const outputConfig = options.output || {};
    const globalsConfig = options.globals || {};
    const externalGlobalsFunc = options.externalGlobals;
    const modulePathsConfig = options.modulePaths || [];
    const pluginsConfig = options.plugins || [];
    const overrideConfig = options.overrideRollupConfig || {};

    return {
        external: [
            ...commonRollupConfig.external,

            '@beanbag/ink',
            '@beanbag/jasmine-suites',
            '@beanbag/spina',
            'backbone',
            'codemirror',
            'moment',
            'django',
            'djblets',
            'underscore',

            ...externalConfig,
        ],
        output: {
            ...commonRollupConfig.output,

            /*
             * If a namespace is provided (via ``name``), make sure that
             * namespace is extended, not replaced with each module.
             */
            extend: true,

            /*
             * Each of these globals will be assumed to exist when the module
             * is loaded. They won't have to be imported.
             */
            globals: {
                ...commonRollupConfig.globals,

                '@beanbag/ink': 'Ink',
                '@beanbag/jasmine-suites': 'window',
                '@beanbag/spina': 'Spina',
                RB: 'RB',
                backbone: 'Backbone',
                django: 'django',
                djblets: 'Djblets',
                underscore: '_',

                ...globalsConfig,
            },

            ...outputConfig,
        },
        plugins: [
            /* Configure rollup to use Babel to compile files. */
            babel(commonRollupConfig.plugins.babel),

            /*
             * Convert any module import paths from our projects to instead
             * look up in top-level namespace variables.
             */
            externalGlobals(id => {
                if (id.startsWith('djblets/')) {
                    return 'Djblets';
                }

                if (id.startsWith('reviewboard/')) {
                    return 'RB';
                }

                if (externalGlobalsFunc) {
                    return externalGlobalsFunc(id);
                }
            }),

            /* Specify where modules should be looked up from. */
            resolve({
                ...commonRollupConfig.plugins.resolve,

                modulePaths: [
                    ...modulePathsConfig,

                    'node_modules',
                ],
            }),

            ...pluginsConfig,
        ],
        treeshake: commonRollupConfig.treeshake,

        ...overrideConfig,
    };
}
