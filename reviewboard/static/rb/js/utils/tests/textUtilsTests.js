describe('utils/textUtils', function() {
    it('escapeMarkDown', function() {
        expect(RB.escapeMarkdown('hello \\`*_{}[]()>#+-.! world.')).toBe(
            'hello \\\\\\`\\*\\_\\{\\}\\[\\]\\(\\)\\>\\#\\+\\-\\.\\! world\\.');
    });
});
