/**
 * Main configuration for Storybook.
 *
 * Version Added:
 *     7.0
 */

import { StorybookConfig } from '@storybook/html-vite';


const config: StorybookConfig = {
    addons: [
        '@storybook/addon-a11y',
        '@storybook/addon-docs',
        '@storybook/addon-links',
        '@storybook/addon-themes',
    ],
    core: {
        disableTelemetry: true,
    },
    framework: {
        name: '@storybook/html-vite',
        options: {},
    },
    stories: [
        '../docs/stories/**/*.mdx',
        '../docs/stories/**/*.stories.@(js|jsx|mjs|ts|tsx)',
    ],
};

export default config;
