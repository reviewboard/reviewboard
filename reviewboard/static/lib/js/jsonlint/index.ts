import jsonlint from '@prantlf/jsonlint';


const origParse = jsonlint.parse;


/**
 * Adapter to match jsonlint to CodeMirror.
 *
 * jsonlint has changed their API to make it so it can use either the native
 * JSON parser or their internal one, but that ended up changing the way errors
 * were reported (raising an error rather calling parseError). CodeMirror still
 * relies on the old API.
 */
jsonlint.parse = function(...args): object {
    try {
        return origParse(...args);
    } catch (err) {
        const location = err.location.start;

        jsonlint.parseError(err.message, {
            loc: {
                first_column: location.column,
                first_line: location.line,
                last_column: location.column + 1,
                last_line: location.line,
            },
        });
    }
};


/* Export what's needed to the global namespace. */
const _global = typeof globalThis !== 'undefined' ? globalThis : self;
_global.jsonlint = jsonlint;
