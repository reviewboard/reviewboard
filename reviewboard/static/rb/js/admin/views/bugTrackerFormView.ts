/**
 * View for the bug tracker configuration form.
 *
 * Version Added:
 *     9.0
 */

import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';


/**
 * View for the bug tracker configuration form.
 *
 * This manages the visibility of fields that only apply to some of the
 * form's choices, and limits the accounts to the selected service.
 *
 * Version Added:
 *     9.0
 */
@spina
export class BugTrackerFormView extends BaseView {
    static events: EventsHash = {
        'change [name="accessible_to_everyone"]': '_onAccessibilityChanged',
        'change [name="apply_to"]': '_onApplyToChanged',
        'change [name="service_name"]': '_onServiceChanged',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The form's Account field. */
    #$account: JQuery;

    /** Every account option the form was rendered with. */
    #$accountOptions: JQuery;

    /** The form's Accessible To Everyone checkbox. */
    #$accessibleToEveryone: JQuery;

    /** The form's Users Who Have Access row. */
    #$conditionsRow: JQuery;

    /** The form's Repositories row. */
    #$reposRow: JQuery;

    /** The per-service settings blocks. */
    #$settingsBlocks: JQuery;

    /**
     * Render the view.
     */
    protected onInitialRender() {
        this.#$reposRow = this.$('.field-repositories');
        this.#$conditionsRow = this.$('.field-user_conditions');
        this.#$accessibleToEveryone =
            this.$('[name="accessible_to_everyone"]');
        this.#$account = this.$('[name="hosting_account"]');
        this.#$accountOptions = this.#$account.children();
        this.#$settingsBlocks = this.$('.rb-c-admin-bug-tracker-settings');

        this._onAccessibilityChanged();
        this._onApplyToChanged();
        this._onServiceChanged();
    }

    /**
     * Handler for when the Accessible To Everyone checkbox is toggled.
     *
     * This shows the conditions limiting access only when the bug tracker
     * isn't accessible to everyone.
     */
    private _onAccessibilityChanged() {
        this.#$conditionsRow.toggle(
            !this.#$accessibleToEveryone.prop('checked'));
    }

    /**
     * Handler for when the Apply To radio buttons are changed.
     *
     * This shows the Repositories field only when the configuration
     * applies to selected repositories.
     */
    private _onApplyToChanged() {
        this.#$reposRow.toggle(
            this.$('[name="apply_to"]:checked').val() === 'S');
    }

    /**
     * Handler for when the Service field is changed.
     *
     * This limits the Account field to the accounts on the selected
     * service, and shows that service's settings. Options without a
     * service, such as the empty choice, are always kept.
     *
     * The selection is cleared when the account is not on the service, so
     * that the form doesn't submit a mismatched account.
     */
    private _onServiceChanged() {
        const serviceName = this.$('[name="service_name"]').val();

        this.#$settingsBlocks.each((_i, el) => {
            $(el).toggle(el.getAttribute('data-service-id') === serviceName);
        });
        const $account = this.#$account;
        const selected = String($account.val() ?? '');

        const $options = this.#$accountOptions.filter(function() {
            const service = this.getAttribute('data-service');

            return !service || service === serviceName;
        });

        const keepSelected = $options.toArray().some(
            el => (el as HTMLOptionElement).value === selected);

        $account
            .empty()
            .append($options)
            .val(keepSelected ? selected : '');
    }
}
