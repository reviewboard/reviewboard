/**
 * Manages UI for the Add/Edit Webhook form.
 *
 * This will manage the visibility of different page elements, create a
 * CodeMirror for editing, and manage CodeMirror's properties.
 */
RB.WebhookFormView = Backbone.View.extend({
    events: {
        'change #id_apply_to': '_onApplyToChanged',
        'change #id_encoding': '_onEncodingChanged',
        'change #id_use_custom_content': '_onUseCustomContentToggled',
        'change #id_events_0': '_onAllEventsToggled',
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.WebhookFormView:
     *     This object, for chaining.
     */
    render() {
        this._$encoding = $('#id_encoding');
        this._$eventCheckboxes = $('#id_events').find('input');
        this._$allEventsCheckbox = this._$eventCheckboxes.filter('[value="*"]');
        this._$applyTo = $('#id_apply_to');
        this._$applyToSelected = this._$applyTo.find('[value="S"]');
        this._$customContentRow = this.$('.field-custom_content');
        this._$reposRow = this.$('.field-repositories');
        this._$useCustomContent = $('#id_use_custom_content');

        this._codeMirror = CodeMirror.fromTextArea($('#id_custom_content')[0], {
            matchBrackets: true,
            mode: 'application/json',
        });

        this._$customContentRow.find('p.help')
            .append('<br/>')
            .append(
                $('<a/>')
                    .attr('href', MANUAL_URL + 'admin/configuration/webhooks/'
                          + '#custom-payloads')
                    .text(gettext('Custom payload reference'))
                );

        /*
         * Activate these handlers so that the form will be in the correct
         * state.
         */
        this._onAllEventsToggled();
        this._onApplyToChanged();
        this._onEncodingChanged();
        this._onUseCustomContentToggled();

        return this;
    },

    /**
     * Handler for when the All Events checkbox is toggled.
     *
     * Sets the other events to be disabled if the checkbox is checked.
     */
    _onAllEventsToggled() {
        this._$eventCheckboxes.not(this._$allEventsCheckbox).prop(
            'disabled', this._$allEventsCheckbox[0].checked);
    },

    /**
     * Handler for when the Apply To radio buttons are changed.
     *
     * Toggles the visibility of the Repositories list, depending on the
     * selected radio button.
     */
    _onApplyToChanged() {
        this._$reposRow.setVisible(this._$applyToSelected[0].checked);
    },

    /**
     * Handler for when the Encoding drop-down is changed.
     *
     * Sets the CodeMirror mode based on the encoding value.
     */
    _onEncodingChanged() {
        this._codeMirror.setOption('mode', this._$encoding.val());
    },

    /**
     * Handler for when the Use Custom Content checkbox is toggled.
     *
     * Toggles the visibility of the text box to match the checkbox.
     */
    _onUseCustomContentToggled() {
        this._$customContentRow.setVisible(this._$useCustomContent[0].checked);
    },
});
