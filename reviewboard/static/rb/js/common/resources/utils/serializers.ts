/**
 * JSON serialization helpers for API resources.
 */

/** Resource state to use for serializer methods. */
export interface SerializerState {
    /** Whether the object has not yet been created on the server. */
    isNew: boolean;

    /** Whether the resource has been loaded from the server. */
    loaded: boolean;
}


/**
 * Serialize only if the resource is not loaded.
 *
 * Args:
 *     value (unknown):
 *         The value to serialize.
 *
 *     state (SerializerState):
 *         The resource state.
 */
export function onlyIfUnloaded(
    value: unknown,
    state: SerializerState,
): unknown {
    return state.loaded ? undefined : value;
}


/**
 * Serialize only if the resource is not loaded and the value exists.
 *
 * Args:
 *     value (unknown):
 *         The value to serialize.
 *
 *     state (SerializerState):
 *         The resource state.
 */
export function onlyIfUnloadedAndValue(
    value: unknown,
    state: SerializerState,
): unknown {
    if (!state.loaded && value) {
        return value;
    } else {
        return undefined;
    }
}


/**
 * Serialize only if the value exists.
 *
 * Args:
 *     value (unknown):
 *         The value to serialize.
 *
 *     state (SerializerState):
 *         The resource state.
 */
export function onlyIfValue(
    value: unknown,
): unknown {
    return value || undefined;
}


/**
 * Serialize only if the resource has not yet been created on the server.
 *
 * Args:
 *     value (unknown):
 *         The value to serialize.
 *
 *     state (SerializerState):
 *         The resource state.
 */
export function onlyIfNew(
    value: unknown,
    state: SerializerState,
): unknown {
    return state.isNew ? value : undefined;
}


/**
 * Serializer for text type fields.
 *
 * Args:
 *     value (unknown):
 *         The value to serialize.
 *
 *     state (SerializerState):
 *         The resource state.
 */
export function textType(
    value: unknown,
): string {
    return value ? 'markdown' : 'plain';
}
