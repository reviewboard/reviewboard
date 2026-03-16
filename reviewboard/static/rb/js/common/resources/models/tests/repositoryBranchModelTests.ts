import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import { RepositoryBranch } from 'reviewboard/common';


suite('rb/resources/models/RepositoryBranch', function() {
    let model: RepositoryBranch;

    beforeEach(function() {
        model = new RepositoryBranch();
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                commit: 'c8ffef025488802a77f499d7f0d24579d858b07e',
                default: true,
                name: 'master',
            });

            expect(data).not.toBe(undefined);
            expect(data.name).toBe('master');
            expect(data.commit)
                .toBe('c8ffef025488802a77f499d7f0d24579d858b07e');
            expect(data.isDefault).toBe(true);
        });
    });
});
