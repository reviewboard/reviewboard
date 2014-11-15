RB.JSONSerializers = {
    onlyIfUnloaded: function(value, state) {
        return state.loaded ? undefined : value;
    },

    onlyIfUnloadedAndValue: function(value, state) {
        return !state.loaded && value ? value : undefined;
    },

    onlyIfValue: function(value) {
        return value || undefined;
    },

    onlyIfNew: function(value, state) {
        return state.isNew ? value : undefined;
    },

    textType: function(value) {
        return value ? 'markdown' : 'plain';
    }
};
