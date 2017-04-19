/*
 * Renders an icon showing the general complexity of a diff.
 *
 * This icon is a pie graph showing the percentage of inserts vs deletes
 * vs replaces. The size of the white inner radius is a relative indicator
 * of how large the change is for the file, representing the unchanged lines.
 * Smaller inner radiuses indicate much larger changes, whereas larger
 * radiuses represent smaller changes.
 *
 * Callers are not required to supply the total number of lines or the number
 * of replaces, allowing this to be used when only the most basic insert and
 * delete counts are available.
 */
RB.DiffComplexityIconView = Backbone.View.extend({
    ICON_SIZE: 20,

    /*
     * Initializes the view.
     *
     * Each of the provided values will be normalized to something
     * the view expects.
     */
    initialize: function(options) {
        this.numInserts = options.numInserts || 0;
        this.numDeletes = options.numDeletes || 0;
        this.numReplaces = options.numReplaces || 0;
        this.totalLines = options.totalLines || null;
    },

    /*
     * Renders the icon.
     */
    render: function() {
        var numTotal = this.numInserts + this.numDeletes + this.numReplaces,
            numInsertsPct = this.numInserts / numTotal,
            numDeletesPct = this.numDeletes / numTotal,
            numReplacesPct = this.numReplaces / numTotal,
            minValue = 360 * 0.15,
            innerRadius = 0.5 *
                          (this.totalLines === null
                           ? 1
                           : (this.totalLines - numTotal) / this.totalLines),
            iconColors = RB.DiffComplexityIconView.getIconColors();

        this.$el
            .width(this.ICON_SIZE)
            .height(this.ICON_SIZE)
            .plot(
                [
                    {
                        color: iconColors.insertColor,
                        data: this._clampValue(numInsertsPct * 360, minValue)
                    },
                    {
                        color: iconColors.deleteColor,
                        data: this._clampValue(numDeletesPct * 360, minValue)
                    },
                    {
                        color: iconColors.replaceColor,
                        data: this._clampValue(numReplacesPct * 360, minValue)
                    }
                ],
                {
                    series: {
                        pie: {
                            show: true,
                            innerRadius: innerRadius,
                            radius: 0.8
                        }
                    }
                }
            );

        return this;
    },

    /*
     * Clamps the number to be, at minimum, minValue, unless it is 0.
     */
    _clampValue: function(val, minValue) {
        return val === 0 ? 0 : Math.max(val, minValue);
    }
}, {
    _iconColors: null,

    /*
     * Returns the colors used for the complexity icons.
     *
     * This will create a temporary icon on the DOM and apply the CSS
     * styles for each type of change the icon can show. It will then
     * copy these colors, caching them for all future icons, and return
     * them.
     */
    getIconColors: function() {
        var $iconColor;

        if (!this._iconColors) {
            this._iconColors = {};

            $iconColor = $('<div/>')
                .hide()
                .appendTo(document.body);

            $iconColor[0].className = 'diff-changes-icon-insert';
            this._iconColors.insertColor = $iconColor.css('color');

            $iconColor[0].className = 'diff-changes-icon-replace';
            this._iconColors.replaceColor = $iconColor.css('color');

            $iconColor[0].className = 'diff-changes-icon-delete';
            this._iconColors.deleteColor = $iconColor.css('color');

            $iconColor.remove();
        }

        return this._iconColors;
    }
});
