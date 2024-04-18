/**
 * Story preview customization.
 *
 * This is where we import the common modules and stylesheets we need for the
 * execution of stories, and customize the display and capabilities of
 * stories.
 *
 * Version Added:
 *     7.0
 */

import { withThemeByDataAttribute } from '@storybook/addon-themes';
import { HtmlRenderer, Preview } from '@storybook/html';

import './stubs.ts';
import './rb-imports.ts';
import './theme.css';


const preview: Preview = {
    decorators: [
        Story => {
            const el = document.createElement('div');
            el.setAttribute('class', 'bg-white dark:bg-black');
            el.appendChild(Story());

            return el;
        },

        withThemeByDataAttribute<HtmlRenderer>({
            themes: {
                light: 'light',
                dark: 'dark',
                system: 'system',
                'high-contrast': 'high-contrast',
            },
            defaultTheme: 'light',
            attributeName: 'data-ink-color-scheme',
        }),
    ],
    parameters: {
        actions: {
            argTypesRegex: '^on[A-Z].*',
        },
        controls: {
            matchers: {
                color: /(background|color)$/i,
                date: /Date$/i,
            },
        },
    },
};

export default preview;
