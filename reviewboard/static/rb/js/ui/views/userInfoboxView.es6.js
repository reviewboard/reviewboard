/**
 * An infobox for displaying information on users.
 */
RB.UserInfoboxView = RB.BaseInfoboxView.extend({
    infoboxID: 'user-infobox',

    /**
     * Render the infobox.
     */
    render() {
        RB.BaseInfoboxView.prototype.render.call(this);

        const $localTime = this.$('.localtime').children('time');

        if ($localTime.length > 0) {
            const timezone = $localTime.data('timezone');
            const now = moment.tz(timezone);

            $localTime.text(now.format('LT'));
        }

        this.$('.timesince').timesince();

        return this;
    }
});


$.fn.user_infobox = RB.InfoboxManagerView.createJQueryFn(RB.UserInfoboxView);
