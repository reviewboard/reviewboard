import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { ServiceItemsView } from '../serviceItemsView';


suite('rb/admin/views/ServiceItemsView', () => {
    let el: HTMLElement;

    function createView(
        totalCount: number,
    ): ServiceItemsView {
        el = document.createElement('div');
        el.className = 'rb-c-admin-cs-service-items';
        el.dataset.serviceId = 'github';
        el.dataset.itemCount = String(totalCount);
        el.innerHTML = `
            <div class="rb-c-admin-cs-service-items__panel">
             <div class="rb-c-admin-cs-service-items__results-container"
              ><ul class="rb-c-admin-cs-service-items__results"
                ><li>repo1</li></ul></div>
            </div>
        `;
        document.body.appendChild(el);

        const view = new ServiceItemsView({
            el,
            itemsURLTemplate: '/items/__SERVICE_ID__/',
            perPage: 2,
            strings: {
                filterLabel: 'Filter',
                filterPlaceholder: 'Filter…',
                loadError: 'Error',
                loading: 'Loading',
                paginatorLabel: 'Pages',
            },
        });
        view.render();

        return view;
    }

    beforeEach(() => {
        spyOn(window, 'fetch').and.resolveTo(new Response(
            '<ul class="rb-c-admin-cs-service-items__results"></ul>',
            {
                headers: {
                    'X-Num-Pages': '1',
                    'X-Page-Number': '1',
                },
            }));
    });

    afterEach(() => {
        el.remove();
    });

    describe('Rendering', () => {
        it('Keeps the server-rendered list without fetching', () => {
            createView(1);

            expect(window.fetch).not.toHaveBeenCalled();
            expect(el.querySelector('.rb-c-admin-cs-service-items__results'))
                .not.toBeNull();
            expect(el.querySelector('.rb-c-admin-cs-service-items__filter'))
                .toBeNull();
            expect(el.querySelector(
                '.rb-c-admin-cs-service-items__paginator')).toBeNull();
        });

        it('Builds filter and paginator when paginated', () => {
            createView(5);

            const panelEl = el.querySelector(
                '.rb-c-admin-cs-service-items__panel');
            const children = Array.from(panelEl.children);

            expect(window.fetch).not.toHaveBeenCalled();
            expect(children.map(child => child.className)).toEqual([
                'rb-c-admin-cs-service-items__filter',
                'rb-c-admin-cs-service-items__results-container',
                'rb-c-admin-cs-service-items__paginator',
            ]);
            expect((children[2] as HTMLElement).hidden).toBeFalse();
        });
    });

    describe('Searching', () => {
        it('Fetches the first page with the search term', async () => {
            createView(5);

            const inputEl = el.querySelector<HTMLInputElement>(
                'input[type="search"]');
            inputEl.value = 'foo';
            inputEl.dispatchEvent(new Event('input'));

            /*
             * Underscore's debounce reads the real clock, so jasmine's mock
             * clock can't advance it. Wait out the debounce instead.
             */
            await new Promise(resolve => setTimeout(resolve, 400));

            expect(window.fetch).toHaveBeenCalledWith(
                '/items/github/?q=foo&page=1');
        });
    });
});
