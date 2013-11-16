from __future__ import unicode_literals

import unittest

from generate_extension import CamelCase, LowerCaseWithUnderscores


class NamingConventionTests(unittest.TestCase):
    def test_camel_case_test(self):
        convention = CamelCase()
        assert convention.formatted("NormalCamelCase")
        assert convention.formatted("HasNumericWord9")
        assert convention.formatted("HasAlphanumericWordF1")
        assert convention.formatted("ALLCAPS")
        assert not convention.formatted("9AsStartingCharacter")

    def test_camel_case_conversion(self):
        convention = CamelCase()
        assert "Punctuation" == convention.convert("Punctuation.?")
        assert "StringWithSpaces" == convention.convert("String with spaces")
        assert "LowerCase" == convention.convert("lower_case")
        assert "Numeric1" == convention.convert("numeric 1")
        assert "AlphanumericB4b4" == convention.convert("alphanumeric b4b4")
        assert "SpacesAtEnd" == convention.convert("spaces At_end    ")
        assert "SpaceAtStart" == convention.convert(" space at start")
        assert "IdempotentCase" == convention.convert("IdempotentCase")

    def test_lowercase_with_underscores_test(self):
        convention = LowerCaseWithUnderscores()
        assert convention.formatted("lower_case")
        assert convention.formatted("ab_c___")
        assert convention.formatted("a___b")
        assert not convention.formatted("123_abc")

    def test_lowercase_with_underscores_conversion(self):
        convention = LowerCaseWithUnderscores()
        assert "punctuation" == convention.convert("Punctuation.?")
        assert "string_with_spaces" == convention.convert("String with spaces")
        assert "camel_case" == convention.convert("CamelCase")
        assert "numeric_1" == convention.convert("numeric 1")
        assert "alphanumeric_b4b4" == convention.convert("alphanumeric b4b4")
        assert "space_at_start" == convention.convert(" space at start")
        assert "spaces_at_end" == convention.convert("spaces At_end    ")
        assert "idempotent_case" == convention.convert("idempotent_case")
