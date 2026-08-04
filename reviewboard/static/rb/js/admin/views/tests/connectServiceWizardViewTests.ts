import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    type ConnectServiceInfo,
    ConnectServiceWizardView,
} from 'reviewboard/admin';


suite('rb/admin/views/ConnectServiceWizardView', function() {
    const services: ConnectServiceInfo[] = [
        {
            id: 'github',
            logo: '/static/github.svg',
            name: 'GitHub',
            sections: ['popular', 'source_hosting'],
        },
        {
            id: 'jira',
            logo: null,
            name: 'JIRA',
            sections: ['issue_tracking'],
        },
    ];

    let wizard: ConnectServiceWizardView;

    function createWizard() {
        wizard = new ConnectServiceWizardView({
            connectURLTemplate:
                '/admin/connected-services/__SERVICE_ID__/connect/',
            csrfToken: 'test-csrf',
            services: services,
        });
        wizard.render();
    }

    afterEach(function() {
        if (wizard) {
            wizard.remove();
            wizard = null;
        }
    });

    describe('Service picker', function() {
        beforeEach(function() {
            createWizard();
        });

        it('Renders sections with services', function() {
            const $sections = wizard.$('.rb-c-connect-wizard__section');

            /* "Popular", "Source Hosting", and "Issue Tracking". */
            expect($sections.length).toBe(3);

            const $services = wizard.$('.rb-c-connect-wizard__options li');

            /* GitHub appears in Popular + Source Hosting; JIRA in Issue
             * Tracking. */
            expect($services.length).toBe(3);
        });

        it('Renders a logo when provided', function() {
            expect(wizard.$('.rb-c-connect-wizard__options img').length)
                .toBe(2);
        });

        it('Filters services by search query', function() {
            const searchEl = wizard.$('.rb-c-connect-wizard__search')[0] as
                HTMLInputElement;

            searchEl.value = 'jira';
            searchEl.dispatchEvent(new Event('input'));

            const $visible = wizard.$('.rb-c-connect-wizard__options li')
                .filter((_i, el) => el.style.display !== 'none');

            expect($visible.length).toBe(1);
            expect($visible.attr('data-service-name')).toBe('jira');
        });

        it('Hides sections with no matching services', function() {
            const searchEl = wizard.$('.rb-c-connect-wizard__search')[0] as
                HTMLInputElement;

            searchEl.value = 'jira';
            searchEl.dispatchEvent(new Event('input'));

            const visibleSections =
                wizard.$('.rb-c-connect-wizard__section')
                    .toArray()
                    .filter(el => el.style.display !== 'none');

            /* Only the "Issue Tracking" section (JIRA) remains. */
            expect(visibleSections.length).toBe(1);

            const li = visibleSections[0].querySelector(
                'li[data-service-name]');
            expect(li?.getAttribute('data-service-name')).toBe('jira');
        });
    });

    describe('Service selection', function() {
        beforeEach(function() {
            createWizard();
        });

        it('Fetches the connect UI for the selected service', function() {
            spyOn(window, 'fetch').and.returnValue(
                Promise.resolve(new Response('<form></form>')));

            wizard.$('.rb-c-connect-wizard__options a').eq(0).trigger('click');

            expect(window.fetch).toHaveBeenCalled();

            const url = (window.fetch as jasmine.Spy).calls.argsFor(0)[0];
            expect(url).toBe(
                '/admin/connected-services/github/connect/');
        });
    });
});
