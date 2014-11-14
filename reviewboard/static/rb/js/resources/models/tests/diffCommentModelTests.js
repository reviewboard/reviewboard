suite('rb/resources/models/DiffComment', function() {
    var model;

    beforeEach(function() {
        /* Set some sane defaults needed to pass validation. */
        model = new RB.DiffComment({
            fileDiffID: 16,
            parentObject: new RB.BaseResource({
                'public': true
            })
        });
    });

    it('getNumLines', function() {
        model.set({
            beginLineNum: 5,
            endLineNum: 10
        });

        expect(model.getNumLines()).toBe(6);
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                diff_comment: {
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    text_type: 'markdown',
                    text: 'foo',
                    first_line: 10,
                    num_lines: 5,
                    filediff: {
                        id: 1,
                        source_file: 'my-file'
                    },
                    interfilediff: {
                        id: 2,
                        source_file: 'my-file'
                    }
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.issueOpened).toBe(true);
            expect(data.issueStatus).toBe(RB.BaseComment.STATE_RESOLVED);
            expect(data.richText).toBe(true);
            expect(data.text).toBe('foo');
            expect(data.beginLineNum).toBe(10);
            expect(data.endLineNum).toBe(14);
            expect(data.fileDiff).not.toBe(undefined);
            expect(data.fileDiff.id).toBe(1);
            expect(data.fileDiff.get('sourceFilename')).toBe('my-file');
            expect(data.interFileDiff).not.toBe(undefined);
            expect(data.interFileDiff.id).toBe(2);
            expect(data.interFileDiff.get('sourceFilename')).toBe('my-file');
        });
    });

    describe('toJSON', function() {
        it('BaseComment.toJSON called', function() {
            spyOn(RB.BaseComment.prototype, 'toJSON').andCallThrough();
            model.toJSON();
            expect(RB.BaseComment.prototype.toJSON).toHaveBeenCalled();
        });

        it('first_line field', function() {
            var data;

            model.set({
                beginLineNum: 100,
                endLineNum: 100
            });

            data = model.toJSON();
            expect(data.first_line).toBe(100);
        });

        it('num_lines field', function() {
            var data;

            model.set({
                beginLineNum: 100,
                endLineNum: 105
            });

            data = model.toJSON();
            expect(data.num_lines).toBe(6);
        });

        describe('force_text_type field', function() {
            it('With value', function() {
                var data;

                model.set('forceTextType', 'html');
                data = model.toJSON();
                expect(data.force_text_type).toBe('html');
            });

            it('Without value', function() {
                var data = model.toJSON();

                expect(data.force_text_type).toBe(undefined);
            });
        });

        describe('include_text_types field', function() {
            it('With value', function() {
                var data;

                model.set('includeTextTypes', 'html');
                data = model.toJSON();
                expect(data.include_text_types).toBe('html');
            });

            it('Without value', function() {
                var data = model.toJSON();

                expect(data.include_text_types).toBe(undefined);
            });
        });

        describe('filediff_id field', function() {
            it('When loaded', function() {
                var data;

                model.set('loaded', true);

                data = model.toJSON();
                expect(data.filediff_id).toBe(undefined);
            });

            it('When not loaded', function() {
                var data = model.toJSON();
                expect(data.filediff_id).toBe(16);
            });
        });

        describe('interfilediff_id field', function() {
            it('When loaded', function() {
                var data;

                model.set('loaded', true);

                data = model.toJSON();
                expect(data.interfilediff_id).toBe(undefined);
            });

            it('When not loaded', function() {
                var data;

                model.set('interFileDiffID', 50);
                data = model.toJSON();
                expect(data.interfilediff_id).toBe(50);
            });

            it('When not loaded and unset', function() {
                var data;

                data = model.toJSON();
                expect(data.interfilediff_id).toBe(undefined);
            });
        });
    });

    describe('validate', function() {
        it('Inherited behavior', function() {
            spyOn(RB.BaseComment.prototype, 'validate');
            model.validate({});
            expect(RB.BaseComment.prototype.validate).toHaveBeenCalled();
        });

        describe('beginLineNum/endLineNum', function() {
            describe('Valid values', function() {
                it('beginLineNum == 0, endLineNum == 0', function() {
                    expect(model.validate({
                        beginLineNum: 0,
                        endLineNum: 0
                    })).toBe(undefined);
                });

                it('beginLineNum > 0, endLineNum == beginLineNum', function() {
                    expect(model.validate({
                        beginLineNum: 10,
                        endLineNum: 10
                    })).toBe(undefined);
                });

                it('beginLineNum > 0, endLineNum > 0', function() {
                    expect(model.validate({
                        beginLineNum: 10,
                        endLineNum: 11
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('beginLineNum < 0', function() {
                    expect(model.validate({
                        beginLineNum: -1
                    })).toBe(RB.DiffComment.strings.BEGINLINENUM_GTE_0);
                });

                it('endLineNum < 0', function() {
                    expect(model.validate({
                        endLineNum: -1
                    })).toBe(RB.DiffComment.strings.ENDLINENUM_GTE_0);
                });

                it('endLineNum < beginLineNum', function() {
                    expect(model.validate({
                        beginLineNum: 20,
                        endLineNum: 10
                    })).toBe(
                        RB.DiffComment.strings.BEGINLINENUM_LTE_ENDLINENUM);
                });
            });
        });

        describe('fileDiffID', function() {
            it('With value', function() {
                expect(model.validate({
                    fileDiffID: 42
                })).toBe(undefined);
            });

            it('Unset', function() {
                expect(model.validate({
                    fileDiffID: null
                })).toBe(RB.DiffComment.strings.INVALID_FILEDIFF_ID);
            });
        });
    });
});
