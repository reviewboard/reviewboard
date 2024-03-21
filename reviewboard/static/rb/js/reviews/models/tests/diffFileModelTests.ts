import { suite } from '@beanbag/jasmine-suites';
import {
    describe,
    expect,
    it,
} from 'jasmine-core';

import { DiffFile } from 'reviewboard/reviews';


suite('rb/diffviewer/models/DiffFile', function() {
    describe('parse', function() {
        it('API payloads', function() {
            const diffFile = new DiffFile({
                base_filediff_id: 12,
                binary: false,
                deleted: true,
                filediff: {
                    id: 38,
                    revision: 2,
                },
                id: 28,
                index: 3,
                interfilediff: {
                    id: 23,
                    revision: 4,
                },
                modified_filename: 'bar',
                modified_revision: '4',
                newfile: true,
                orig_filename: 'foo',
                orig_revision: '3',
                serialized_comment_blocks: {
                    '4-2': [
                        {
                            comment_id: 1,
                            issue_opened: false,
                            line: 4,
                            localdraft: false,
                            num_lines: 2,
                            review_id: 1,
                            text: 'Comment',
                            user: { name: 'testuser' },
                        },
                    ],
                },
            }, {
                parse: true,
            });

            const data = diffFile.attributes;

            expect(data).not.toBe(undefined);
            expect(data.baseFileDiffID).toBe(12);
            expect(data.binary).toBe(false);
            expect(data.serializedCommentBlocks).toEqual({
                '4-2': [
                    {
                        comment_id: 1,
                        issue_opened: false,
                        line: 4,
                        localdraft: false,
                        num_lines: 2,
                        review_id: 1,
                        text: 'Comment',
                        user: { name: 'testuser' },
                    },
                ],
            });
            expect(data.deleted).toBe(true);
            expect(data.filediff).not.toBe(undefined);
            expect(data.filediff.id).toBe(38);
            expect(data.filediff.revision).toBe(2);
            expect(data.id).toBe(28);
            expect(data.index).toBe(3);
            expect(data.interfilediff).not.toBe(undefined);
            expect(data.interfilediff.id).toBe(23);
            expect(data.interfilediff.revision).toBe(4);
            expect(data.modifiedFilename).toBe('bar');
            expect(data.modifiedRevision).toBe('4'),
            expect(data.newfile).toBe(true);
            expect(data.origFilename).toBe('foo');
            expect(data.origRevision).toBe('3');
        });
    });
});
