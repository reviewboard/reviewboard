/**
 * Unit tests for BugTrackerFormView.
 *
 * Version Added:
 *     9.0
 */

import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import { BugTrackerFormView } from 'reviewboard/admin';


suite('rb/admin/views/BugTrackerFormView', function() {
    let $fixture: JQuery;
    let $accessibleToEveryone: JQuery;
    let $conditionsRow: JQuery;
    let $reposRow: JQuery;
    let $service: JQuery;
    let $account: JQuery;
    let view: BugTrackerFormView | null;

    /**
     * Create the view.
     *
     * The form is given two accounts on ``splat`` and one on ``github``.
     *
     * Args:
     *     options (object):
     *         Options for the form's initial state.
     *
     * Option Args:
     *     accessibleToEveryone (boolean):
     *         Whether the Accessible To Everyone checkbox is checked.
     *
     *     applyTo (string):
     *         The value of the Apply To radio button to check.
     *
     *     account (string):
     *         The value of the account to select.
     *
     *     service (string):
     *         The value of the service to select.
     */
    function createView(
        options: {
            accessibleToEveryone?: boolean;
            account?: string;
            applyTo?: string;
            service?: string;
        } = {},
    ) {
        const accessibleToEveryone = options.accessibleToEveryone ?? true;
        const applyTo = options.applyTo ?? 'A';
        const service = options.service ?? 'splat';
        const account = options.account ?? '';

        const $form = $('<form>').appendTo($fixture);

        $service = $('<select name="service_name">')
            .append($('<option value="splat">'))
            .append($('<option value="github">'))
            .val(service)
            .appendTo($form);

        $account = $('<select name="hosting_account">')
            .append($('<option value="">'))
            .append($('<option value="1" data-service="splat">'))
            .append($('<option value="2" data-service="github">'))
            .append($('<option value="3" data-service="splat">'))
            .val(account)
            .appendTo($form);

        for (const value of ['A', 'S', 'N']) {
            $('<input type="radio" name="apply_to">')
                .val(value)
                .prop('checked', value === applyTo)
                .appendTo($form);
        }

        $reposRow = $('<div class="form-row field-repositories">')
            .appendTo($form);

        $accessibleToEveryone = $(
            '<input type="checkbox" name="accessible_to_everyone">')
            .prop('checked', accessibleToEveryone)
            .appendTo($form);

        $conditionsRow = $('<div class="form-row field-user_conditions">')
            .appendTo($form);

        view = new BugTrackerFormView({
            el: $form[0],
        });
        view.render();
    }

    /**
     * Return the values of the account field's options.
     *
     * Returns:
     *     Array of string:
     *     The value of each option currently in the account field.
     */
    function accountValues(): string[] {
        return $account.find('option').toArray()
            .map(el => (el as HTMLOptionElement).value);
    }

    beforeEach(function() {
        $fixture = $('<div>').appendTo(document.body);
    });

    afterEach(function() {
        if (view) {
            view.remove();
            view = null;
        }

        $fixture.remove();
    });

    describe('Repositories visibility', function() {
        it('With selected repositories', function() {
            createView({applyTo: 'S'});

            expect($reposRow.is(':visible')).toBeTrue();
        });

        it('With all review requests', function() {
            createView({applyTo: 'A'});

            expect($reposRow.is(':visible')).toBeFalse();
        });

        it('With no repositories', function() {
            createView({applyTo: 'N'});

            expect($reposRow.is(':visible')).toBeFalse();
        });

        it('Changing to selected repositories', function() {
            createView({applyTo: 'A'});

            view.$('[name="apply_to"]')
                .val(['S'])
                .trigger('change');

            expect($reposRow.is(':visible')).toBeTrue();
        });

        it('Changing away from selected repositories', function() {
            createView({applyTo: 'S'});

            view.$('[name="apply_to"]')
                .val(['N'])
                .trigger('change');

            expect($reposRow.is(':visible')).toBeFalse();
        });
    });

    describe('Conditions visibility', function() {
        it('With accessible to everyone', function() {
            createView({accessibleToEveryone: true});

            expect($conditionsRow.is(':visible')).toBeFalse();
        });

        it('With limited access', function() {
            createView({accessibleToEveryone: false});

            expect($conditionsRow.is(':visible')).toBeTrue();
        });

        it('Changing to limited access', function() {
            createView({accessibleToEveryone: true});

            $accessibleToEveryone
                .prop('checked', false)
                .trigger('change');

            expect($conditionsRow.is(':visible')).toBeTrue();
        });

        it('Changing to accessible to everyone', function() {
            createView({accessibleToEveryone: false});

            $accessibleToEveryone
                .prop('checked', true)
                .trigger('change');

            expect($conditionsRow.is(':visible')).toBeFalse();
        });
    });

    describe('Account choices', function() {
        it('On initial render', function() {
            createView({service: 'splat'});

            expect(accountValues()).toEqual(['', '1', '3']);
        });

        it('After changing the service', function() {
            createView({service: 'splat'});

            $service.val('github').trigger('change');

            expect(accountValues()).toEqual(['', '2']);
        });

        it('Keeps an account on the service', function() {
            createView({
                account: '1',
                service: 'splat',
            });

            $service.val('splat').trigger('change');

            expect($account.val()).toBe('1');
        });

        it('Clears an account on another service', function() {
            createView({
                account: '1',
                service: 'splat',
            });

            $service.val('github').trigger('change');

            expect($account.val()).toBe('');
        });

        it('Restores accounts when changing back', function() {
            createView({service: 'splat'});

            $service.val('github').trigger('change');
            $service.val('splat').trigger('change');

            expect(accountValues()).toEqual(['', '1', '3']);
        });
    });
});
