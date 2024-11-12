"""A builder for static media files for extension packages.

Version Added:
    7.1:
    This moved from the top-level :py:mod:`reviewboard.extensions.packaging`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from djblets.extensions.packaging.static_media import (
    StaticMediaBuilder,
    StaticMediaBuildContext,
)

import reviewboard
from reviewboard import VERSION

if TYPE_CHECKING:
    from djblets.extensions.packaging.static_media import (
        LessCSSVariables,
        NPMWorkspaceDirs,
    )


class RBStaticMediaBuildContext(StaticMediaBuildContext):
    """Context for performing a static media build for an extension.

    This will set up some default NPM workspace paths needed for building
    Review Board extensions.

    Version Changed:
        7.1:
        This moved from :py:mod:`reviewboard.extensions.packaging`.

    Version Added:
        7.0
    """

    def get_npm_workspace_dirs(self) -> NPMWorkspaceDirs:
        """Return NPM workspace directories and symlinks to set up.

        Subclasses can override this to return additional workspaces to
        include. The parent class should always be called and the results
        included.

        Returns:
            dict:
            A mapping of symlink names to target locations.
        """
        return {
            'reviewboard': Path(reviewboard.__file__).parent.absolute(),
            **super().get_npm_workspace_dirs(),
        }

    def get_lessc_global_vars(self) -> LessCSSVariables:
        """Return a dictionary of LessCSS global variables and their values.

        Subclasses can override this to return custom variables.

        The contents in here are considered deprecated, and should generally
        not be used for any production extensions.

        Returns:
            dict:
            A dictionary mapping variable names to values.
        """
        return {
            'RB_MAJOR_VERSION': VERSION[0],
            'RB_MINOR_VERSION': VERSION[1],
            'RB_MICRO_VERSION': VERSION[2],
            'RB_PATCH_VERSION': VERSION[3],
            'RB_IS_RELEASED': VERSION[5],
            **super().get_lessc_global_vars(),
        }


class RBStaticMediaBuilder(StaticMediaBuilder):
    """Static media builder for Review Board extensions.

    This will take care of building static media files. As part of this, it
    will set up Babel, Rollup, and TypeScript configuration files needed to
    compile against Review Board JavaScript/TypeScript modules.

    Version Changed:
        7.1:
        This moved from :py:mod:`reviewboard.extensions.packaging`.

    Version Added:
        7.0
    """

    def ensure_build_files(self) -> None:
        """Set up the build tree and configuration files.

        This will set up the NPM workspaces and a starting
        :file:`package.json` file that can be used to manage the build.

        If there are any changes to the :file:`package.json` in the tree,
        they will be reported to the user.
        """
        super().ensure_build_files()

        build_context = self.build_context
        source_dir = build_context.source_root_dir

        babel_config_path = source_dir / 'babel.config.json'
        rollup_config_path = source_dir / 'rollup.config.mjs'
        tsconfig_path = source_dir / 'tsconfig.json'
        rel_static_dir = build_context.static_dir.relative_to(source_dir)
        packaging_js_modpath = '@beanbag/reviewboard/packaging/js'

        if not babel_config_path.exists():
            with babel_config_path.open('w') as fp:
                json.dump(
                    {
                        'extends':
                            f'{packaging_js_modpath}/babel.base.config.json',
                    },
                    fp,
                    indent=2,
                    sort_keys=True)
                fp.write('\n')

        if not tsconfig_path.exists():
            with tsconfig_path.open('w') as fp:
                json.dump(
                    {
                        'extends': f'{packaging_js_modpath}/tsconfig.base',
                        'compilerOptions': {
                            'paths': {
                                'backbone': [
                                    'node_modules/@beanbag/spina/lib/@types/'
                                    'backbone',
                                ],
                                'djblets/*': [
                                    'node_modules/@beanbag/djblets/static/'
                                    'djblets/js/*',
                                ],
                                'reviewboard/*': [
                                    'node_modules/@beanbag/reviewboard/static/'
                                    'rb/js/*',
                                ]
                            },
                        },
                        'include': [
                            os.path.join(rel_static_dir, '*'),
                            os.path.join(rel_static_dir, '**', '*'),
                        ],
                    },
                    fp,
                    indent=2,
                    sort_keys=True)
                fp.write('\n')

        if not rollup_config_path.exists():
            with rollup_config_path.open('w') as fp:
                fp.write(
                    'import {\n'
                    '    buildReviewBoardExtensionConfig,\n'
                    '} from "%(parent_rollup_config)s"\n'
                    '\n'
                    '\n'
                    'export default buildReviewBoardExtensionConfig({\n'
                    '    output: {\n'
                    '        name: "%(package_id)s",\n'
                    '    },\n'
                    '    modulePaths: [\n'
                    '        "%(static_dir)s/js/",\n'
                    '    ],\n'
                    '});\n'
                    % {
                        'package_id': build_context.package_id,
                        'parent_rollup_config':
                            f'{packaging_js_modpath}/rollup-extensions.mjs',
                        'static_dir': rel_static_dir,
                    })
