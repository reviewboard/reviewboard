describe('utils/textUtils', function() {
    describe('escapeMarkdown', function() {
        it('All standard characters', function() {
            expect(RB.escapeMarkdown('hello \\`*_{}[]()>#+-.! world.')).toBe(
                'hello \\\\\\`\\*\\_\\{\\}\\[\\]\\(\\)\\>\\#\\+\\-.\\! world.');
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
    });
});
