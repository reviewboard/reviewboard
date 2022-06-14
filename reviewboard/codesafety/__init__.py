"""Code safety support.

These modules are used to help ensure code going up for review passes certain
safety checks.

Version Added:
    5.0
"""

from djblets.registries.importer import lazy_import_registry


code_safety_checker_registry = \
    lazy_import_registry('reviewboard.codesafety.checkers.registry',
                         'CodeSafetyCheckerRegistry')
