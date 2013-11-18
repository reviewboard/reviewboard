describe('utils/textUtils', function() {
    describe('escapeMarkdown', function() {
        it('All standard characters', function() {
            expect(RB.escapeMarkdown('hello \\`*_{}[]()>#+-.! world.')).toBe(
                'hello \\\\\\`\\*\\_\\{\\}\\[\\]\\(\\)\\>#+-.\\! world.');
        });

        it("With '.' placement", function() {
            expect(RB.escapeMarkdown('Line. 1.\n' +
                                     '1. Line. 2.\n' +
                                     '1.2. Line. 3.\n' +
                                     '  1. Line. 4.'))
                .toBe(
                    'Line. 1.\n' +
                    '1\\. Line. 2.\n' +
                    '1\\.2\\. Line. 3.\n' +
                    '  1\\. Line. 4.');
        });

        it("With '#' placement", function() {
            expect(RB.escapeMarkdown('### Header\n' +
                                     '  ## Header ##\n' +
                                     'Not # a header'))
                .toBe(
                    '\\#\\#\\# Header\n' +
                    '  \\#\\# Header ##\n' +
                    'Not # a header');
        });

        it("With '-' placement", function() {
            expect(RB.escapeMarkdown('Header\n' +
                                     '------\n' +
                                     '\n' +
                                     '- List item\n' +
                                     '  - List item\n' +
                                     'Just hyp-henated'))
                .toBe(
                    'Header\n' +
                    '\\-\\-\\-\\-\\-\\-\n' +
                    '\n' +
                    '\\- List item\n' +
                    '  \\- List item\n' +
                    'Just hyp-henated');
        });

        it("With '+' placement", function() {
            expect(RB.escapeMarkdown('+ List item\n' +
                                     'a + b'))
                .toBe(
                    '\\+ List item\n' +
                    'a + b');
        });
    });
});
