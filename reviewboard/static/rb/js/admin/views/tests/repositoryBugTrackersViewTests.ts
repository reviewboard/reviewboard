import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import { RepositoryBugTrackersView } from 'reviewboard/admin';


/**
 * Set the page-level hosting services metadata global.
 *
 * Args:
 *     services (object):
 *         The per-service metadata, or ``undefined`` to remove it.
 */
function setHostingServices(services?: unknown) {
    const win = window as unknown as Record<string, unknown>;

    if (services === undefined) {
        delete win.HOSTING_SERVICES;
    } else {
        win.HOSTING_SERVICES = services;
    }
}


suite('rb/admin/views/RepositoryBugTrackersView', function() {
    let $fixture: JQuery;
    let $input: JQuery;
    let $defaultField: JQuery;
    let $useHostingField: JQuery;
    let view: RepositoryBugTrackersView | null;

    function createView(
        options: Partial<{
            allConfigs: unknown[];
            attachedConfigs: unknown[];
            availableConfigs: unknown[];
            builtinConfig: unknown;
            defaultID: number | null;
            services: Record<string, unknown>;
            useHosting: boolean;
        }> = {},
    ) {
        view = new RepositoryBugTrackersView(Object.assign(
            {
                $input: $input,
                allConfigs: [],
                attachedConfigs: [],
                availableConfigs: [],
                builtinConfig: null,
                defaultFieldID: 'test_default_bug_tracker',
                defaultID: null,
                el: $('<div>').appendTo($fixture)[0],
                hostingTypeFieldID: 'test_hosting_type',
                services: {},
                useHosting: false,
                useHostingFieldID: 'test_bug_tracker_use_hosting',
            },
            options));
        view.render();
    }

    beforeEach(function() {
        $fixture = $('<div>').appendTo(document.body);

        $input = $('<input id="test_bug_tracker_configs">')
            .appendTo($fixture);
        $defaultField = $(
            '<select id="test_default_bug_tracker">' +
            '<option value=""></option>' +
            '<option value="1"></option>' +
            '<option value="2"></option>' +
            '</select>')
            .appendTo($fixture);
        $useHostingField = $(
            '<input type="checkbox" id="test_bug_tracker_use_hosting">')
            .appendTo($fixture);
        $(
            '<select id="test_hosting_type">' +
            '<option value="github" selected>GitHub</option>' +
            '<option value="custom">(None)</option>' +
            '</select>')
            .appendTo($fixture);

        setHostingServices({
            github: {
                supports_bug_trackers: true,
            },
        });
    });

    afterEach(function() {
        if (view) {
            view.remove();
            view = null;
        }

        $fixture.remove();
        setHostingServices();
    });

    function makeConfig(id: number, name: string, options = {}) {
        return Object.assign(
            {
                enabled: true,
                id: id,
                limitedAccess: false,
                logoURL: null,
                name: name,
                serviceLabel: 'Splat',
            },
            options);
    }

    describe('Rendering', function() {
        it('With attached and all-review-requests configs', function() {
            createView({
                allConfigs: [makeConfig(1, 'Everything Tracker')],
                attachedConfigs: [makeConfig(2, 'My Tracker')],
            });

            const rows = view.$('.rb-c-repo-bug-trackers__row');
            expect(rows.length).toBe(2);
            expect(rows.eq(0).text()).toContain('Everything Tracker');
            expect(rows.eq(0).text()).toContain('All review requests');
            expect(rows.eq(0).find('.rb-c-repo-bug-trackers__lock').length)
                .toBe(1);
            expect(rows.eq(1).text()).toContain('My Tracker');
            expect(rows.eq(1).find('.rb-c-repo-bug-trackers__remove').length)
                .toBe(1);
        });

        it('With the built-in tracker in use', function() {
            createView({
                services: {
                    github: {
                        bugTrackerName: 'GitHub Issues',
                        logoURL: '/static/rb/images/services/github.svg',
                    },
                },
                useHosting: true,
            });

            const rows = view.$('.rb-c-repo-bug-trackers__row');
            expect(rows.length).toBe(1);
            expect(rows.eq(0).text()).toContain('GitHub Issues');

            /* The hosting service's logo is used before materializing. */
            expect(rows.eq(0).find('img.rb-c-repo-bug-trackers__logo')
                   .attr('src'))
                .toBe('/static/rb/images/services/github.svg');
        });

        it('With chips for access and state', function() {
            createView({
                attachedConfigs: [
                    makeConfig(2, 'My Tracker', {
                        enabled: false,
                        limitedAccess: true,
                    }),
                ],
            });

            const row = view.$('.rb-c-repo-bug-trackers__row');
            expect(row.text()).toContain('Private');
            expect(row.text()).toContain('Disabled');
        });

        it('With no trackers', function() {
            setHostingServices({});
            createView();

            expect(view.$('.rb-c-repo-bug-trackers__empty').length).toBe(1);
        });
    });

    describe('Interaction', function() {
        it('Choosing a default updates the hidden select', function() {
            createView({
                attachedConfigs: [makeConfig(2, 'My Tracker')],
            });

            view.$('.rb-c-repo-bug-trackers__radio[value="2"]')
                .prop('checked', true)
                .trigger('change');

            expect($defaultField.val()).toBe('2');
            expect(view.$('.rb-c-repo-bug-trackers__row .ink-c-badge').text())
                .toContain('Default');
        });

        it('Removing a tracker updates the hidden input', function() {
            createView({
                attachedConfigs: [
                    makeConfig(1, 'Tracker One'),
                    makeConfig(2, 'Tracker Two'),
                ],
                defaultID: 2,
            });

            expect($input.val()).toBe('');

            view.$('.rb-c-repo-bug-trackers__remove[data-tracker-key="2"]')
                .trigger('click');

            expect($input.val()).toBe('1');
            expect($defaultField.val()).toBe('');

            /* The removed tracker is offered for re-attaching. */
            expect(
                view.$('.rb-c-repo-bug-trackers__attach-select ' +
                       'option[value="2"]').length)
                .toBe(1);
        });

        it('Attaching a tracker updates the hidden input', function() {
            createView({
                availableConfigs: [makeConfig(2, 'My Tracker')],
            });

            /*
             * Dispatch a native event, like a real user interaction,
             * to cover the event delegation itself.
             */
            const selectEl = view.$(
                '.rb-c-repo-bug-trackers__attach-select',
            )[0] as HTMLSelectElement;
            selectEl.value = '2';
            selectEl.dispatchEvent(new Event('change', { bubbles: true }));

            expect($input.val()).toBe('2');
            expect(view.$('.rb-c-repo-bug-trackers__row').text())
                .toContain('My Tracker');
        });

        it('Removing the built-in tracker unchecks use-hosting', function() {
            $useHostingField.prop('checked', true);
            createView({
                useHosting: true,
            });

            view.$('.rb-c-repo-bug-trackers__remove').trigger('click');

            expect($useHostingField.prop('checked')).toBe(false);
            expect(view.$('.rb-c-repo-bug-trackers__row').length).toBe(0);
        });

        it('Attaching the built-in tracker checks use-hosting', function() {
            createView();

            view.$('.rb-c-repo-bug-trackers__attach-select')
                .val('builtin')
                .trigger('change');

            expect($useHostingField.prop('checked')).toBe(true);
            expect(view.$('.rb-c-repo-bug-trackers__row').text())
                .toContain('GitHub bug tracker');
        });

        it('Attaching a tracker with no default makes it the default',
           function() {
            createView({
                availableConfigs: [makeConfig(2, 'My Tracker')],
            });

            view.$('.rb-c-repo-bug-trackers__attach-select')
                .val('2')
                .trigger('change');

            expect($defaultField.val()).toBe('2');
            expect(view.$('.rb-c-repo-bug-trackers__row .ink-c-badge').text())
                .toContain('Default');
        });

        it('Attaching a tracker keeps an existing default', function() {
            createView({
                attachedConfigs: [makeConfig(1, 'Tracker One')],
                availableConfigs: [makeConfig(2, 'Tracker Two')],
                defaultID: 1,
            });
            $defaultField.val('1');

            view.$('.rb-c-repo-bug-trackers__attach-select')
                .val('2')
                .trigger('change');

            expect($input.val()).toBe('1,2');
            expect($defaultField.val()).toBe('1');
        });

        it('Attaching the built-in tracker with no default makes it the ' +
           'default',
           function() {
            createView();

            view.$('.rb-c-repo-bug-trackers__attach-select')
                .val('builtin')
                .trigger('change');

            /*
             * The unmaterialized built-in tracker has no select value.
             * Saving the form assigns it as the default.
             */
            expect($defaultField.val()).toBe('');
            expect(view.$('.rb-c-repo-bug-trackers__row .ink-c-badge').text())
                .toContain('Default');
        });

        it('Switching to a hosting service without bug tracker support',
           function() {
            $useHostingField.prop('checked', true);
            createView({
                useHosting: true,
            });

            $('#test_hosting_type').val('custom').trigger('change');

            expect($useHostingField.prop('checked')).toBe(false);
            expect(view.$('.rb-c-repo-bug-trackers__row').length).toBe(0);
            expect(
                view.$('.rb-c-repo-bug-trackers__attach-select ' +
                       'option[value="builtin"]').length)
                .toBe(0);
        });
    });
});
