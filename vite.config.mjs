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


const node_modules_dir = path.resolve(__dirname, 'node_modules')
const djblets_static_dir = path.resolve(
    node_modules_dir, '@beanbag', 'djblets', 'static')
const rb_static_dir = path.resolve(__dirname, 'reviewboard', 'static')


export default defineConfig({
    build: {
        target: 'esnext',
    },
    css: {
        preprocessorOptions: {
            less: {
                javascriptEnabled: true,
                modifyVars: {
                    'tabler-path': path.resolve(node_modules_dir,
                                                '\\@tabler', 'icons'),
                },
                paths: [
                    rb_static_dir,
                    djblets_static_dir,
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
        alias: [
            {
                find: 'reviewboard',
                replacement: path.resolve(rb_static_dir, 'rb', 'js'),
            },
            {
                find: 'djblets/css',
                replacement: path.resolve(djblets_static_dir, 'djblets', 'css'),
            },
            {
                find: 'djblets/images',
                replacement: path.resolve(djblets_static_dir, 'djblets', 'images'),
            },
            {
                find: 'djblets',
                replacement: path.resolve(djblets_static_dir, 'djblets', 'js'),
            },
        ],
    },
    ssr: {
        noExternal: [
            '@beanbag/ink',
            '@beanbag/spina',
        ],
    }
});
