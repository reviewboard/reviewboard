import { suite } from '@beanbag/jasmine-suites';
import {
    describe,
    expect,
    it,
} from 'jasmine-core';

import { DataUtils } from 'reviewboard/common';


suite('rb/utils/dataUtils', () => {
    describe('With callbacks', () => {
        it('readBlobAsArrayBuffer', (done: () => void) => {
            const str = 'abc123';
            const blob = new Blob([str]);

            spyOn(console, 'warn');

            DataUtils.readBlobAsArrayBuffer(blob, result => {
                expect(result.byteLength).toBe(6);

                const dataView = new DataView(result);

                for (let i = 0; i < result.byteLength; i++) {
                    expect(dataView.getUint8(i)).toBe(str.charCodeAt(i));
                }

                expect(console.warn).toHaveBeenCalled();

                done();
            });
        });

        it('readBlobAsString', (done: () => void) => {
            const blob = new Blob(['This is a test.']);

            spyOn(console, 'warn');

            DataUtils.readBlobAsString(blob, result => {
                expect(typeof result).toBe('string');
                expect(result).toBe('This is a test.');

                expect(console.warn).toHaveBeenCalled();

                done();
            });
        });

        it('readManyBlobsAsArrayBuffers', (done: () => void) => {
            const str1 = 'abc123';
            const str2 = 'foo';

            const blob1 = new Blob([str1]);
            const blob2 = new Blob([str2]);

            spyOn(console, 'warn');

            DataUtils.readManyBlobsAsArrayBuffers(
                [blob1, blob2],
                (result1, result2) => {
                    expect(result1.byteLength).toBe(6);
                    expect(result2.byteLength).toBe(3);

                    const dataView1 = new DataView(result1);

                    for (let i = 0; i < result1.byteLength; i++) {
                        expect(dataView1.getUint8(i)).toBe(str1.charCodeAt(i));
                    }

                    const dataView2 = new DataView(result2);

                    for (let i = 0; i < result2.byteLength; i++) {
                        expect(dataView2.getUint8(i)).toBe(str2.charCodeAt(i));
                    }

                    expect(console.warn).toHaveBeenCalled();

                    done();
                });
        });

        it('readManyBlobsAsStrings', (done: () => void) => {
            const blob1 = new Blob(['This is a test.']);
            const blob2 = new Blob(['hello world']);

            spyOn(console, 'warn');

            DataUtils.readManyBlobsAsStrings(
                [blob1, blob2],
                (result1, result2) => {
                    expect(typeof result1).toBe('string');
                    expect(typeof result2).toBe('string');
                    expect(result1).toBe('This is a test.');
                    expect(result2).toBe('hello world');

                    expect(console.warn).toHaveBeenCalled();

                    done();
                });
        });

        it('buildBlob', (done: () => void) => {
            const blob = DataUtils.buildBlob([
                'abc',
                [
                    {
                        type: 'uint8',
                        values: [1, 2],
                    },
                    {
                        type: 'uint32',
                        values: [100],
                    },
                ],
                new Blob(['def']),
            ]);

            spyOn(console, 'warn');

            DataUtils.readBlobAsArrayBuffer(blob, arrayBuffer => {
                expect(arrayBuffer.byteLength).toBe(12);

                const dataView = new DataView(arrayBuffer);
                expect(dataView.getUint8(0)).toBe('a'.charCodeAt(0));
                expect(dataView.getUint8(1)).toBe('b'.charCodeAt(0));
                expect(dataView.getUint8(2)).toBe('c'.charCodeAt(0));
                expect(dataView.getUint8(3)).toBe(1);
                expect(dataView.getUint8(4)).toBe(2);
                expect(dataView.getUint32(5, true)).toBe(100);
                expect(dataView.getUint8(9)).toBe('d'.charCodeAt(0));
                expect(dataView.getUint8(10)).toBe('e'.charCodeAt(0));
                expect(dataView.getUint8(11)).toBe('f'.charCodeAt(0));

                expect(console.warn).toHaveBeenCalled();

                done();
            });
        });
    });

    describe('With promises', () => {
        it('readBlobAsArrayBuffer', async () => {
            const str = 'abc123';
            const blob = new Blob([str]);
            const result = await DataUtils.readBlobAsArrayBuffer(blob);

            expect(result.byteLength).toBe(6);

            const dataView = new DataView(result);

            for (let i = 0; i < result.byteLength; i++) {
                expect(dataView.getUint8(i)).toBe(str.charCodeAt(i));
            }
        });

        it('readBlobAsString', async () => {
            const blob = new Blob(['This is a test.']);
            const result = await DataUtils.readBlobAsString(blob);

            expect(typeof result).toBe('string');
            expect(result).toBe('This is a test.');
        });

        it('readManyBlobsAsArrayBuffers', async () => {
            const str1 = 'abc123';
            const str2 = 'foo';

            const blob1 = new Blob([str1]);
            const blob2 = new Blob([str2]);

            const results = await DataUtils.readManyBlobsAsArrayBuffers(
                [blob1, blob2]);
            const [result1, result2] = results;

            expect(result1.byteLength).toBe(6);
            expect(result2.byteLength).toBe(3);

            const dataView1 = new DataView(result1);

            for (let i = 0; i < result1.byteLength; i++) {
                expect(dataView1.getUint8(i)).toBe(str1.charCodeAt(i));
            }

            const dataView2 = new DataView(result2);

            for (let i = 0; i < result2.byteLength; i++) {
                expect(dataView2.getUint8(i)).toBe(str2.charCodeAt(i));
            }
        });

        it('readManyBlobsAsStrings', async () => {
            const blob1 = new Blob(['This is a test.']);
            const blob2 = new Blob(['hello world']);

            const results = await DataUtils.readManyBlobsAsStrings(
                [blob1, blob2]);
            const [result1, result2] = results;

            expect(typeof result1).toBe('string');
            expect(typeof result2).toBe('string');
            expect(result1).toBe('This is a test.');
            expect(result2).toBe('hello world');
        });

        it('buildBlob', async () => {
            const blob = DataUtils.buildBlob([
                'abc',
                [
                    {
                        type: 'uint8',
                        values: [1, 2],
                    },
                    {
                        type: 'uint32',
                        values: [100],
                    },
                ],
                new Blob(['def']),
            ]);

            const arrayBuffer = await DataUtils.readBlobAsArrayBuffer(blob);

            expect(arrayBuffer.byteLength).toBe(12);

            const dataView = new DataView(arrayBuffer);
            expect(dataView.getUint8(0)).toBe('a'.charCodeAt(0));
            expect(dataView.getUint8(1)).toBe('b'.charCodeAt(0));
            expect(dataView.getUint8(2)).toBe('c'.charCodeAt(0));
            expect(dataView.getUint8(3)).toBe(1);
            expect(dataView.getUint8(4)).toBe(2);
            expect(dataView.getUint32(5, true)).toBe(100);
            expect(dataView.getUint8(9)).toBe('d'.charCodeAt(0));
            expect(dataView.getUint8(10)).toBe('e'.charCodeAt(0));
            expect(dataView.getUint8(11)).toBe('f'.charCodeAt(0));
        });
    });

    describe('buildArrayBuffer', () => {
        it('With int8', () => {
            const values = [-1, 0, 1];
            const arrayBuffer = DataUtils.buildArrayBuffer([
                {
                    type: 'int8',
                    values: values,
                },
            ]);
            expect(arrayBuffer.byteLength).toBe(3);

            const dataView = new DataView(arrayBuffer);

            for (let i = 0; i < values.length; i++) {
                expect(dataView.getInt8(i)).toBe(values[i]);
            }
        });

        it('With uint8', () => {
            const values = [1, 2, 3];
            const arrayBuffer = DataUtils.buildArrayBuffer([
                {
                    type: 'uint8',
                    values: values,
                },
            ]);
            expect(arrayBuffer.byteLength).toBe(3);

            const dataView = new DataView(arrayBuffer);

            for (let i = 0; i < values.length; i++) {
                expect(dataView.getUint8(i)).toBe(values[i]);
            }
        });

        describe('With int16', () => {
            const values = [-1, 0, 1];

            it('Little endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        type: 'int16',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(6);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getInt16(i * 2, true)).toBe(values[i]);
                }
            });

            it('Big endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        bigEndian: true,
                        type: 'int16',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(6);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getInt16(i * 2)).toBe(values[i]);
                }
            });
        });

        describe('With uint16', () => {
            const values = [1, 2, 3];

            it('Little endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        type: 'uint16',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(6);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getUint16(i * 2, true)).toBe(values[i]);
                }
            });

            it('Big endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        bigEndian: true,
                        type: 'uint16',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(6);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getUint16(i * 2)).toBe(values[i]);
                }
            });
        });

        describe('With int32', () => {
            const values = [-1, 0, 1];

            it('Little endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        type: 'int32',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(12);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getInt32(i * 4, true)).toBe(values[i]);
                }
            });

            it('Big endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        bigEndian: true,
                        type: 'int32',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(12);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getInt32(i * 4)).toBe(values[i]);
                }
            });
        });

        describe('With uint32', () => {
            const values = [1, 2, 3];

            it('Little endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        type: 'uint32',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(12);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getUint32(i * 4, true))
                        .toBe(values[i]);
                }
            });

            it('Big endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        bigEndian: true,
                        type: 'uint32',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(12);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getUint32(i * 4)).toBe(values[i]);
                }
            });
        });

        describe('With float32', () => {
            const values = [1, 2, 3];

            it('Little endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        type: 'float32',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(12);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getFloat32(i * 4, true))
                        .toBe(values[i]);
                }
            });

            it('Big endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        bigEndian: true,
                        type: 'float32',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(12);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getFloat32(i * 4)).toBe(values[i]);
                }
            });
        });

        describe('With float64', () => {
            const values = [1, 2, 3];

            it('Little endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        type: 'float64',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(24);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getFloat64(i * 8, true)).toBe(values[i]);
                }
            });

            it('Big endian', () => {
                const arrayBuffer = DataUtils.buildArrayBuffer([
                    {
                        bigEndian: true,
                        type: 'float64',
                        values: values,
                    },
                ]);
                expect(arrayBuffer.byteLength).toBe(24);

                const dataView = new DataView(arrayBuffer);

                for (let i = 0; i < values.length; i++) {
                    expect(dataView.getFloat64(i * 8)).toBe(values[i]);
                }
            });
        });

        it('With complex schema', () => {
            const arrayBuffer = DataUtils.buildArrayBuffer([
                {
                    bigEndian: true,
                    type: 'int32',
                    values: [10, 20],
                },
                {
                    type: 'uint8',
                    values: [100],
                },
                {
                    type: 'uint16',
                    values: [64],
                },
                {
                    type: 'float64',
                    values: [1.234],
                },
            ]);
            expect(arrayBuffer.byteLength).toBe(19);

            const dataView = new DataView(arrayBuffer);
            expect(dataView.getInt32(0)).toBe(10);
            expect(dataView.getInt32(4)).toBe(20);
            expect(dataView.getUint8(8)).toBe(100);
            expect(dataView.getUint16(9, true)).toBe(64);
            expect(dataView.getFloat64(11, true)).toEqual(1.234);
        });
    });
});
