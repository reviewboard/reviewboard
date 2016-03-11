RB.MathUtils = {
    /**
     * Clip a value to be within a given range.
     *
     * Args:
     *     value (number):
     *         The value to clip.
     *
     *     minValue (number):
     *         The minimum for the clipped value.
     *
     *     maxValue (number):
     *         The maximum for the clipped value.
     *
     * Returns:
     *     number:
     *     The clipped value.
     */
    clip(value, minValue, maxValue) {
        return Math.min(maxValue, Math.max(minValue, value));
    }
};
