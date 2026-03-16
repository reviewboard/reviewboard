/**
 * Utilities for working with array buffers and blobs.
 */

export const ArrayBufferTypes = {
    int8: {
        funcName: 'setInt8',
        size: 1,
    },
    uint8: {
        funcName: 'setUint8',
        size: 1,
    },
    int16: {
        funcName: 'setInt16',
        size: 2,
    },
    uint16: {
        funcName: 'setUint16',
        size: 2,
    },
    int32: {
        funcName: 'setInt32',
        size: 4,
    },
    uint32: {
        funcName: 'setUint32',
        size: 4,
    },
    float32: {
        funcName: 'setFloat32',
        size: 4,
    },
    float64: {
        funcName: 'setFloat64',
        size: 8,
    },
};


/**
 * Read a Blob as an ArrayBuffer.
 *
 * This is an asynchronous operation.
 *
 * Args:
 *     blob (Blob):
 *         The blob to read as an :js:class:`ArrayBuffer`.
 *
 *     onLoaded (function, optional):
 *         The function to call when the blob has loaded. This will take
 *         the resulting :js:class:`ArrayBuffer` as an argument.
 *
 *         Deprecated:
 *             8.0:
 *             Deprecated in favor of async/promise style usage.
 *
 * Returns:
 *     Promise:
 *     A promise which resolves to the array buffer.
 */
export function readBlobAsArrayBuffer(
    blob: Blob,
    onLoaded?: (data: ArrayBuffer) => void,
): Promise<ArrayBuffer> {
    if (onLoaded !== undefined) {
        console.warn(dedent`
            The onLoaded argument to DataUtils.readBlobAsArrayBuffer is
            deprecated and will be removed in Review Board 9. Callers
            should be updated to use the promise return value.
        `);
    }

    return _readBlobAs<ArrayBuffer>('readAsArrayBuffer', blob, onLoaded);
}


/**
 * Read a Blob as a text string.
 *
 * This is an asynchronous operation.
 *
 * Args:
 *     blob (Blob):
 *         The blob to read as text.
 *
 *     onLoaded (function, optional):
 *         The function to call when the blob has loaded. This will take
 *         the resulting string as an argument.
 *
 *         Deprecated:
 *             8.0:
 *             Deprecated in favor of async/promise style usage.
 *
 * Returns:
 *     Promise:
 *     A promise which resolves to the string.
 */
export function readBlobAsString(
    blob: Blob,
    onLoaded?: (data: string) => void,
): Promise<string> {
    if (onLoaded !== undefined) {
        console.warn(dedent`
            The onLoaded argument to DataUtils.readBlobAsString is deprecated
            and will be removed in Review Board 9. Callers should be updated
            to use the promise return value.
        `);
    }

    return _readBlobAs<string>('readAsText', blob, onLoaded);
}


/**
 * Read several Blobs as individual ArrayBuffers.
 *
 * This is an asynchronous operation.
 *
 * Args:
 *     blobs (Array):
 *         The array of :js:class:`Blob`s instances to read as
 *         :js:class:`ArrayBuffer`s
 *
 *     onLoaded (function, optional):
 *         The function to call when the blobs have loaded. This will take
 *         one parameter per loaded :js:class:`ArrayBuffer`, in the order
 *         provided for the blobs.
 *
 *         Deprecated:
 *             8.0:
 *             Deprecated in favor of async/promise style usage.
 */
export function readManyBlobsAsArrayBuffers(
    blobs: Blob[],
    onLoaded?: (...args: ArrayBuffer[]) => void,
): Promise<ArrayBuffer[]> {
    if (onLoaded !== undefined) {
        console.warn(dedent`
            The onLoaded argument to DataUtils.readManyBlobsAsArrayBuffers is
            deprecated and will be removed in Review Board 9. Callers should
            be updated to use the promise return value.
        `);
    }

    return _readManyBlobsAs<ArrayBuffer>(
        readBlobAsArrayBuffer, blobs, onLoaded);
}


/**
 * Read several Blobs as individual text strings.
 *
 * This is an asynchronous operation.
 *
 * Args:
 *     blobs (Array):
 *         The array of :js:class:`Blob`s to read as text.
 *
 *     onLoaded (function, optional):
 *         The function to call when the blobs have loaded. This will take
 *         one parameter per loaded string, in the order provided for the
 *         blobs.
 *
 *         Deprecated:
 *             8.0:
 *             Deprecated in favor of async/promise style usage.
 */
export function readManyBlobsAsStrings(
    blobs: Blob[],
    onLoaded?: (...args: string[]) => void,
): Promise<string[]> {
    if (onLoaded !== undefined) {
        console.warn(dedent`
            The onLoaded argument to DataUtils.readManyBlobsAsStrings is
            deprecated and will be removed in Review Board 9. Callers should
            be updated to use the promise return value.
        `);
    }

    return _readManyBlobsAs<string>(readBlobAsString, blobs, onLoaded);
}


/**
 * Schema for an array buffer.
 *
 * Version Added:
 *     8.0
 */
interface ArrayBufferSchema {
    /**
     * The type of the values.
     *
     * See :js:data:`RB.DataUtils.ArrayBufferTypes` for the supported types.
     */
    type: keyof ArrayBufferTypes;

    /** The array of values to store in the buffer. */
    values: unknown[];

    /** Whether the buffer byte order is big endian. */
    bigEndian?: boolean;
}


/**
 * Build an ArrayBuffer based on a schema.
 *
 * This takes a schema that specifies the data that should go into the
 * :js:class:`ArrayBuffer`. Each item in the schema is an object specifying
 * the type and the list of values of that type to add.
 *
 * Args:
 *     schema (Array of ArrayBufferSchema):
 *         The schema containing the data to load.
 *
 * Returns:
 *     ArrayBuffer:
 *     The resulting buffer built from the schema.
 */
export function buildArrayBuffer(
    schema: ArrayBufferSchema[],
): ArrayBuffer {
    let arrayLen = 0;

    for (let i = 0; i < schema.length; i++) {
        const item = schema[i];

        arrayLen += ArrayBufferTypes[item.type].size * item.values.length;
    }

    const arrayBuffer = new ArrayBuffer(arrayLen);
    const dataView = new DataView(arrayBuffer);
    let pos = 0;

    for (let i = 0; i < schema.length; i++) {
        const item = schema[i];
        const values = item.values;
        const littleEndian = !item.bigEndian;
        const typeInfo = ArrayBufferTypes[item.type];
        const func = dataView[typeInfo.funcName];
        const size = typeInfo.size;

        for (let j = 0; j < values.length; j++) {
            func.call(dataView, pos, values[j], littleEndian);
            pos += size;
        }
    }

    return arrayBuffer;
}


/**
 * Build a Blob based on a schema.
 *
 * This takes a schema that specifies the data that should go into the
 * :js:class:`Blob`. Each item in the schema is either an array of objects
 * specifying the type and the list of values of that type to add (see
 * :js:func:`RB.DataUtils.buildArrayBuffer` for details), a
 * :js:class:`Blob`, or string to add.
 *
 * Args:
 *     schema (Array):
 *         The schema containing the data to load. Each item in the array
 *         must be a :js:class:`Blob`, string, or an array of objects
 *         supported by :js:func:`RB.DataUtils.buildArrayBuffer`.
 *
 * Returns:
 *     Blob:
 *     The resulting blob built from the schema.
 */
export function buildBlob(
    schema: (Blob | string | ArrayBufferSchema[])[],
): Blob {
    const parts = [];

    for (let i = 0; i < schema.length; i++) {
        const schemaItem = schema[i];

        if (Array.isArray(schemaItem)) {
            parts.push(buildArrayBuffer(schemaItem));
        } else {
            parts.push(schemaItem);
        }
    }

    return new Blob(parts);
}


/**
 * Read a Blob using a specific FileReader function.
 *
 * This is a convenience function that wraps a :js:class:`FileReader`
 * function designed to load a blob as a certain type.
 *
 * Args:
 *     readFuncName (string):
 *         The function name on :js:class:`FileReader` to call.
 *
 *     blob (Blob):
 *         The blob to load.
 *
 *     onLoaded (function, optional):
 *         The function to call when the blob has loaded. This will take
 *         the resulting value as an argument.
 *
 *         Deprecated:
 *              8.0:
 *              Deprecated in favor of async/promise style usage.
 *
 * Returns:
 *     Promise:
 *     A promise which resolves to the loaded result.
 */
function _readBlobAs<T extends (ArrayBuffer | string)>(
    readFuncName: 'readAsArrayBuffer' | 'readAsText',
    blob: Blob,
    onLoaded?: (value: T) => void,
): Promise<T> {
    return new Promise(resolve => {
        const reader = new FileReader();

        reader.addEventListener('loadend', () => {
            const result = reader.result as T;

            if (typeof onLoaded === 'function') {
                onLoaded(result);
            }

            resolve(result);
        });
        reader[readFuncName](blob);
    });
}

/**
 * Read several Blobs using a specific FileReader function.
 *
 * This is a convenience function that wraps a :js:class:`FileReader`
 * function, chaining multiple results in order to asynchronously load
 * each of the blobs as a certain type.
 *
 * Args:
 *     readFuncName (string):
 *         The function name on :js:class:`FileReader` to call.
 *
 *     blobs (Array):
 *         The array of Blobs to load.
 *
 *     onLoaded (function, optional):
 *         The function to call when the blobs have loaded. This will take
 *         an argument per value loaded.
 *
 *         Deprecated:
 *              8.0:
 *              Deprecated in favor of async/promise style usage.
 *
 * Returns:
 *     Promise:
 *     A promise which resolves to the result.
 */
async function _readManyBlobsAs<T extends (ArrayBuffer | string)>(
    readFunc: (blob: Blob) => Promise<T>,
    blobs: Blob[],
    onLoaded?: (...values: T[]) => void,
): Promise<T[]> {
    const result: T[] = new Array(blobs.length);
    let i = 0;

    for (const blob of blobs) {
        result[i] = await readFunc(blob);
        i++;
    }

    if (typeof onLoaded === 'function') {
        onLoaded(...result);
    }

    return result;
}
