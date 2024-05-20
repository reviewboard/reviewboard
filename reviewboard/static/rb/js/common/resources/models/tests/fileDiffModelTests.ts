import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import { FileDiff } from 'reviewboard/common';


suite('rb/resources/models/FileDiff', function() {
    let model: FileDiff;

    beforeEach(function() {
        model = new FileDiff({
            destFilename: 'dest-file',
            sourceFilename: 'source-file',
            sourceRevision: 'source-revision',
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                filediff: {
                    dest_file: 'my-dest-file',
                    id: 42,
                    source_file: 'my-source-file',
                    source_revision: 'my-source-revision',
                },
                stat: 'ok',
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.destFilename).toBe('my-dest-file');
            expect(data.sourceFilename).toBe('my-source-file');
            expect(data.sourceRevision).toBe('my-source-revision');
        });
    });
});
