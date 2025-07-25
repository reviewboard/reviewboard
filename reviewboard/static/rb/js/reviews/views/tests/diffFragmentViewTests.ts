import { suite } from '@beanbag/jasmine-suites';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { DiffFragmentView } from 'reviewboard/reviews';
import { CenteredElementManager } from 'reviewboard/ui';


suite('rb/views/DiffFragmentView', function() {
    const fragmentTemplate = _.template(dedent`
        <table>
         <thead>
         </thead>
         <tbody class="diff-header diff-header-above">
          <tr>
           <td>
            <div>
             <a href="#" class="diff-expand-btn"
                data-lines-of-context="20,0"></a>
            </div>
           </td>
          </tr>
         </tbody>
         <tbody class="insert"></tbody>
         <tbody class="insert">
          <tr>
           <td>
            <div class="rb-c-diff-collapse-button" role="button" tabindex="0"
                 data-lines-of-context="0,0"></div>
           </td>
          </tr>
         </tbody>
         <tbody class="diff-header diff-header-below">
          <tr>
           <td>
            <div>
             <a href="#" class="diff-expand-btn"
                data-lines-of-context="0,20"></a>
            </div>
           </td>
          </tr>
         </tbody>
        </table>
    `);

    let view: DiffFragmentView;
    let loadDiff: jasmine.Spy;

    beforeEach(function() {
        loadDiff = jasmine.createSpy('loadDiff').and.resolveTo(undefined);

        view = new DiffFragmentView({
            collapsible: true,
            loadDiff: loadDiff,
        });
        view.$el.html(fragmentTemplate());
        $testsScratch.append(view.$el);

        /* Make all the deferred/delayed functions run immediately. */
        spyOn(_, 'defer').and.callFake(cb => cb());
        spyOn(_, 'delay').and.callFake(cb => cb());
        spyOn(CenteredElementManager.prototype, 'updatePosition');
    });

    afterEach(() => {
        view.remove();
    });

    describe('render', function() {
        it('With visible and collapsible === true', function() {
            view.render();

            expect(view.$el.hasClass('allow-transitions')).toBe(true);
            expect(view._$table.hasClass('expanded')).toBe(false);
            expect(view._$table.hasClass('collapsed')).toBe(true);

            /*
             * Ideally we'd check for the proper transform values we're setting
             * (or part of them anyway), but browsers may turn those into
             * "matrix(...)" values. So this is better than nothing.
             */
            expect(view._$thead.css('transform')).not.toBe('none');

            view._$diffHeaders.each((i, headerEl) => {
                expect($(headerEl).css('transform')).not.toBe('none');
            });
        });

        it('With hidden and collapsible === true', function() {
            view.$el.hide();
            view.render();

            expect(view.$el.hasClass('allow-transitions')).toBe(true);
            expect(view._$table.hasClass('expanded')).toBe(true);
            expect(view._$table.hasClass('collapsed')).toBe(false);

            /*
             * Ideally we'd check for the proper transform values we're setting
             * (or part of them anyway), but browsers may turn those into
             * "matrix(...)" values. So this is better than nothing.
             */
            expect(view._$thead.css('transform')).toBe('none');

            view._$diffHeaders.each((i, headerEl) => {
                expect($(headerEl).css('transform')).toBe('none');
            });
        });

        it('With collapsible === false', function() {
            view._collapsible = false;
            view.render();

            expect(view.$el.hasClass('allow-transitions')).toBe(false);
            expect(view._$table.hasClass('expanded')).toBe(true);
            expect(view._$table.hasClass('collapsed')).toBe(false);

            /*
             * Ideally we'd check for the proper transform values we're setting
             * (or part of them anyway), but browsers may turn those into
             * "matrix(...)" values. So this is better than nothing.
             */
            expect(view._$thead.css('transform')).toBe('none');

            view._$diffHeaders.each((i, headerEl) => {
                expect($(headerEl).css('transform')).toBe('none');
            });
        });
    });

    describe('Events', function() {
        it('click expansion button', async () => {
            view.render();

            await view._expandOrCollapse(view.$('.diff-expand-btn'));

            expect(loadDiff).toHaveBeenCalled();
            expect(loadDiff.calls.mostRecent().args[0].linesOfContext)
                .toBe('20,0');
        });

        it('click collapse button', async () => {
            view.render();

            await view._expandOrCollapse(view.$('.rb-c-diff-collapse-button'));

            expect(loadDiff).toHaveBeenCalled();
            expect(loadDiff.calls.mostRecent().args[0].linesOfContext)
                .toBe('0,0');
        });

        describe('mouseenter', function() {
            it('With collapsible === true', function() {
                view.render();

                spyOn(view.$el, 'is').and.callFake(sel => {
                    expect(sel).toBe(':hover');

                    return true;
                });
                view.$el.trigger('mouseenter');

                expect(view._$table.hasClass('collapsed')).toBe(false);
                expect(view._$table.hasClass('expanded')).toBe(true);
                expect(view._$thead.css('transform')).toBe('none');

                view._$diffHeaders.each((i, headerEl) => {
                    expect($(headerEl).css('transform')).toBe('none');
                });
            });

            it('With collapsible === false', function() {
                view._collapsible = false;
                view.render();

                spyOn(view.$el, 'is').and.callFake(sel => {
                    expect(sel).toBe(':hover');

                    return true;
                });
                view.$el.trigger('mouseenter');

                expect(view._$table.hasClass('collapsed')).toBe(false);
                expect(view._$table.hasClass('expanded')).toBe(true);
                expect(view._$thead.css('transform')).toBe('none');

                view._$diffHeaders.each((i, headerEl) => {
                    expect($(headerEl).css('transform')).toBe('none');
                });
            });
        });

        describe('mouseleave', function() {
            it('With collapsible === true', function() {
                let isHovering = true;

                view.render();

                /* First, trigger a mouseenter. */
                spyOn(view.$el, 'is').and.callFake((sel: string) => {
                    expect(sel).toBe(':hover');

                    return isHovering;
                });
                view.$el.trigger('mouseenter');

                /* Now the mouse leave. */
                isHovering = false;
                view.$el.trigger('mouseleave');

                expect(view._$table.hasClass('collapsed')).toBe(true);
                expect(view._$table.hasClass('expanded')).toBe(false);
                expect(view._$thead.css('transform')).not.toBe('none');

                view._$diffHeaders.each((i, headerEl) => {
                    expect($(headerEl).css('transform')).not.toBe('none');
                });
            });

            it('With collapsible === false', function() {
                let isHovering = true;

                view._collapsible = false;
                view.render();

                /* First, trigger a mouseenter. */
                spyOn(view.$el, 'is').and.callFake((sel: string) => {
                    expect(sel).toBe(':hover');

                    return isHovering;
                });
                view.$el.trigger('mouseenter');

                /* Now the mouse leave. */
                isHovering = false;
                view.$el.trigger('mouseleave');

                expect(view._$table.hasClass('collapsed')).toBe(false);
                expect(view._$table.hasClass('expanded')).toBe(true);
                expect(view._$thead.css('transform')).toBe('none');

                view._$diffHeaders.each((i, headerEl) => {
                    expect($(headerEl).css('transform')).toBe('none');
                });
            });
        });
    });
});
