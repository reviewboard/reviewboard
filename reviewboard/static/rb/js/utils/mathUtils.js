RB.MathUtils = {
    /* Clip value to [minValue, maxValue] range. */
    clip: function(value, minValue, maxValue) {
        return Math.min(maxValue, Math.max(minValue, value));
    }
};
