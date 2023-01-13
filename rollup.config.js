import babel from '@rollup/plugin-babel';
import externalGlobals from 'rollup-plugin-external-globals';
import resolve from '@rollup/plugin-node-resolve';


const extensions = [
    '.es6.js',
    '.js',
    '.ts',
];


export default {
    output: {
        /*
         * Anything exported from a top-level index.* file (as specified in
         * the Pipeline bundle configuration) will be placed in this top-level
         * variable.
         */
        name: 'RB',

        esModule: false,
        exports: 'named',
        extend: true,
        format: 'umd',
        sourcemap: true,

        /*
         * Each of these globals will be assumed to exist when the module is
         * loaded. They won't have to be imported.
         */
        globals: {
            Backbone: 'Backbone',
            Djblets: 'Djblets',
            RB: 'RB',
            django: 'django',
            jquery: '$',
            underscore: '_',
        },
    },
    plugins: [
        /* Configure rollup to use Babel to compile files. */
        babel({
            babelHelpers: 'bundled',
            extensions: extensions,
        }),

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
            extensions: extensions,
            modulePaths: [
                'reviewboard/static/lib/js',
                'reviewboard/static/rb/js',
                '.djblets/static/djblets/js',
            ],
        }),
    ],
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
