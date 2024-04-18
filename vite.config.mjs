/**
 * Configuration for Vite, used for Storybook.
 *
 * This configures the paths, plugins, and settings needed to serve up
 * Storybook with Review Board.
 *
 * Version Added:
 *     7.0
 */

import path from 'path';

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';


export default defineConfig({
    build: {
        target: 'esnext',
    },
    css: {
        preprocessorOptions: {
            less: {
                javascriptEnabled: true,
                modifyVars: {
                    'images-path': path.resolve(__dirname, 'src', 'ink',
                                                'images'),
                    'tabler-path': path.resolve(__dirname, 'node_modules',
                                                '\\@tabler', 'icons'),
                },
                paths: [
                    path.resolve(__dirname, 'reviewboard', 'static'),
                    path.resolve(__dirname, 'node_modules', '@beanbag',
                                 'djblets', 'static'),
                ],
            },
        },
    },
    esbuild: {
        target: 'esnext',
    },
    optimizeDeps: {
        esbuildOptions: {
            target: 'esnext',
        },
    },
    plugins: [
        react({
            babel: {
                /*
                 * This is strictly a subset of the plugins we use when
                 * building Review Board. We only want the ones we need for
                 * certain transforms and executions within the context of a
                 * Storybook Preview page. Anything else could lead to
                 * breakages.
                 */
                plugins: [
                    '@babel/plugin-external-helpers',
                    ['@babel/plugin-proposal-decorators', {
                        'version': 'legacy'
                    }],
                    'babel-plugin-dedent',
                    'babel-plugin-django-gettext',
                ],
            },

            /*
             * Limit this to our own code, so we don't run Storybook
             * through it.
             */
            include: /reviewboard\/static\/.*\.(js|jsx|ts|tsx)$/,
        }),
    ],
    resolve: {
        alias: {
            'reviewboard/common': path.resolve(
                __dirname,
                'reviewboard/static/rb/js/common/index.ts'),
            'reviewboard/reviews': path.resolve(
                __dirname,
                'reviewboard/static/rb/js/reviews/index.ts'),
            'reviewboard/ui': path.resolve(
                __dirname,
                'reviewboard/static/rb/js/ui/index.ts'),
        },
    },
    ssr: {
        noExternal: [
            '@beanbag/ink',
            '@beanbag/spina',
        ],
    }
});
