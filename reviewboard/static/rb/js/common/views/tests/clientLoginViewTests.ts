import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { ClientLoginPageView } from 'reviewboard/common';
import { HeaderView } from 'reviewboard/ui';


suite('rb/views/ClientLoginPageView', function() {
    let view: ClientLoginPageView;
    let $body: JQuery<HTMLBodyElement>;
    let $headerBar: JQuery;
    let $pageContainer: JQuery;
    let $pageContent: JQuery;

    const pageTemplate = dedent`
        <div id="page-container">
         <main id="content">
          <div id="auth_container">
           <div class="auth-header">
           </div>
          </div>
         </main>
        </div>
    `;

    beforeEach(function() {
        $body = <JQuery<HTMLBodyElement>>$('<body>')
            .appendTo($testsScratch);
        $headerBar = $('<div>')
            .appendTo($body);
        $pageContainer = $(pageTemplate)
            .appendTo($body);
        $pageContent = $pageContainer.find('#content');

        spyOn(HeaderView.prototype, '_ensureSingleton');
        spyOn(RB, 'navigateTo');

        view = new ClientLoginPageView({
            $body: $body,
            $headerBar: $headerBar,
            $pageContainer: $pageContainer,
            $pageContent: $pageContent,
            clientName: 'Client',
            clientURL: 'http%3A//localhost%3A1234',
            payload: {
                api_token: 'token',
            },
            redirectTo: '',
            username: 'User',
            waitToSend: true,
        });
        view.render();
    });

    afterEach(() => {
        view.remove();
    });

    describe('Rendering', function() {
        it('With failing to connect to the client server', async function() {
            spyOn(window, 'fetch').and.throwError('Test Error');

            await view.sendData();

            expect(view.$pageContent.find('h1').text())
                .toBe('Failed to log in for Client');
            expect(view.$pageContent.find('p').text()).toBe(
                'Could not connect to Client. Please contact your ' +
                'administrator.')
            expect(view.$pageContent.find('#redirect-counter').text())
                .toBe('');
        });

        it('With successfully sending data to the client', async function() {
            const response = new Response(JSON.stringify({}), { status: 200 });
            spyOn(window, 'fetch').and.resolveTo(response);
            view.render();

            await view.sendData();

            expect(view.$pageContent.find('h1').text())
                .toBe('Logged in to Client');
            expect(view.$pageContent.find('p').text()).toBe(
                'You have successfully logged in to Client as User. ' +
                'You can now close this page.');
            expect(view.$pageContent.find('#redirect-counter').text())
                .toBe('');
        });

        it('With sending data to the client and a redirect', async function() {
            view._redirectTo = 'http://localhost:1234/test/';

            const response = new Response(JSON.stringify({}), { status: 200 });
            spyOn(window, 'fetch').and.resolveTo(response);
            spyOn(window, 'setInterval');

            await view.sendData();

            expect(view.$pageContent.find('h1').text())
                .toBe('Logged in to Client');
            expect(view.$pageContent.find('p').text()).toBe(
                'You have successfully logged in to Client as User. ' +
                'Redirecting in 3...');
            expect(view.$pageContent.find('#redirect-counter').text())
                .toBe(' 3...');
            expect(setInterval).toHaveBeenCalled();
        });

        it('With failing to send data to the client', async function() {
            const response = new Response(JSON.stringify({}), { status: 400 });
            spyOn(window, 'fetch').and.resolveTo(response);

            await view.sendData();

            expect(view.$pageContent.find('h1').text())
                .toBe('Failed to log in for Client');
            expect(view.$pageContent.find('p').text()).toBe(
                'Failed to log in for Client as User. Please contact ' +
                'your administrator.');
            expect(view.$pageContent.find('#redirect-counter').text())
                .toBe('');
        });
    });

    describe('Redirect countdown', function() {
        beforeEach(function() {
            view._redirectTo = 'http://localhost:1234/test/';

            const response = new Response(JSON.stringify({}), { status: 200 });
            spyOn(window, 'fetch').and.resolveTo(response);
            spyOn(window, 'setInterval');
        });

        it('With a counter greater than 1', async function() {
            const $counter = $('<div id="redirect-counter">')
                .appendTo(view.$el);

            expect(view._redirectInSeconds).toBe(3);

            view._redirectCountdown();

            expect(view._redirectInSeconds).toBe(2);
            expect($counter.text()).toBe(' 2...');
        });

        it('With a counter at 1', async function() {
            const $counter = $('<div id="redirect-counter">')
                .appendTo(view.$el);

            view._redirectInSeconds = 1;
            spyOn(window, 'clearInterval');

            view._redirectCountdown();

            expect(view._redirectInSeconds).toBe(0);
            expect($counter.text()).toBe(' 0...');
            expect(RB.navigateTo).toHaveBeenCalledWith(
                'http://localhost:1234/test/'
            );
        });
    });
});
