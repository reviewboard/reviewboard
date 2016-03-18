RB.JSONSerializers = {
    onlyIfUnloaded(value, state) {
        return state.loaded ? undefined : value;
    },

    onlyIfUnloadedAndValue(value, state) {
        return !state.loaded && value ? value : undefined;
    },

    onlyIfValue(value) {
        return value || undefined;
    },

    onlyIfNew(value, state) {
        return state.isNew ? value : undefined;
    },

    textType(value) {
        return value ? 'markdown' : 'plain';
    }
};
