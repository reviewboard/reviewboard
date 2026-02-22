/**
 * Main configuration for Storybook.
 *
 * Version Added:
 *     7.0
 */

import { StorybookConfig } from '@storybook/html-vite';
import { checkA11y, injectAxe } from 'axe-playwright';


const config: StorybookConfig = {
    addons: [
        '@storybook/addon-a11y',
        '@storybook/addon-essentials',
        '@storybook/addon-interactions',
        '@storybook/addon-links',
        '@storybook/addon-themes',
    ],
    core: {
        disableTelemetry: true,
    },
    docs: {
        autodocs: 'tag',
    },
    framework: {
        name: '@storybook/html-vite',
        options: {},
    },
    stories: [
        '../docs/stories/*/*.mdx',
        '../docs/stories/**/*.mdx',
        '../docs/stories/*/*.stories.@(js|jsx|mjs|ts|tsx)',
        '../docs/stories/**/*.stories.@(js|jsx|mjs|ts|tsx)',
    ],

    async preVisit(page) {
        await injectAxe(page);
    },

    async postVisit(page) {
        await checkA11y(page, '#storybook-root', {
            detailedReport: true,
            detailedReportOptions: {
                html: true,
            },
        });
    },
};

export default config;
