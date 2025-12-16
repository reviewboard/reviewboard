/**
 * ESLint configuration.
 *
 * Version Added:
 *     7.1
 */

import beanbag from '@beanbag/eslint-plugin';
import {
    defineConfig,
    globalIgnores,
} from 'eslint/config';
import storybook from 'eslint-plugin-storybook';
import globals from 'globals';


export default defineConfig([
    globalIgnores([
        'reviewboard/htdocs/**/*',
        'reviewboard/static/lib/js/**/*',
    ]),
    beanbag.configs.recommended,
    ...storybook.configs['flat/recommended'],
    {
        languageOptions: {
            globals: {
                ...beanbag.globals.backbone,
                ...beanbag.globals.django,
                ...beanbag.globals.djblets,
                ...globals.browser,
                ...globals.jquery,
                MANUAL_URL: 'readonly',
                RB: 'writable',
                SITE_ROOT: 'readonly',
                _super: 'readonly',
                dedent: false,
            },
            sourceType: 'module',
        },
        plugins: {
            '@beanbag': beanbag,
        },
    },
]);
