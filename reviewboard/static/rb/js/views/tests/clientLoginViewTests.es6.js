suite('rb/views/ClientLoginView', function() {
    let view;
    const pageTemplate = dedent`
        <div id="auth_container">
         <div class="auth-header">
         </div>
        </div>
    `;

    beforeEach(function() {
        view = new RB.ClientLoginView({
            el: $(pageTemplate),
            clientName: 'Client',
            clientURL: 'http%3A//localhost%3A1234',
            payload: {
                api_token: 'token',
            },
            redirectTo: '',
            username: 'User',
        });
    });

    describe('Rendering', function() {
        it('With failing to connect to the client server', async function() {
            spyOn(window, 'fetch').and.throwError('Test Error');
            await view.render();

            expect(view.$('h1').text()).toBe('Failed to log in for Client');
            expect(view.$('p').text()).toBe([
                'Could not connect to Client. Please contact your ',
                'administrator.'
            ].join(''));
            expect(view.$('#redirect-counter').text()).toBe('');

        });

        it('With successfully sending data to the client', async function() {
            const response = new Response(JSON.stringify({}), { status: 200 });
            spyOn(window, 'fetch').and.resolveTo(response);
            await view.render();

            expect(view.$('h1').text()).toBe('Logged in to Client');
            expect(view.$('p').text()).toBe([
                'You have successfully logged in to Client as User. ',
                'You can now close this page.'
            ].join(''));
            expect(view.$('#redirect-counter').text()).toBe('');
        });

        it('With sending data to the client and a redirect', async function() {
            view = new RB.ClientLoginView({
                el: $(pageTemplate),
                clientName: 'Client',
                clientURL: 'http%3A//localhost%3A1234',
                payload: {
                    api_token: 'token',
                },
                redirectTo: 'http%3A//localhost%3A1234/test/',
                username: 'User',
            });
            const response = new Response(JSON.stringify({}), { status: 200 });
            spyOn(window, 'fetch').and.resolveTo(response);
            spyOn(window, 'setInterval');
            await view.render();

            expect(view.$('h1').text()).toBe('Logged in to Client');
            expect(view.$('p').text()).toBe([
                'You have successfully logged in to Client as User. ',
                'Redirecting in 3...'
            ].join(''));
            expect(view.$('#redirect-counter').text()).toBe(' 3...');
            expect(setInterval).toHaveBeenCalled();
        });

        it('With failing to send data to the client', async function() {
            const response = new Response(JSON.stringify({}), { status: 400 });
            spyOn(window, 'fetch').and.resolveTo(response);
            await view.render();

            expect(view.$('h1').text())
                .toBe('Failed to log in for Client');
            expect(view.$('p').text()).toBe([
                'Failed to log in for Client as User. Please contact ',
                'your administrator.'
            ].join(''));
            expect(view.$('#redirect-counter').text()).toBe('');
        });
    });

    describe('_redirectCountDown', function() {
        beforeEach(function() {
            view = new RB.ClientLoginView({
                el: $(`<div><span id="redirect-counter"></span></div>`),
                clientName: 'Client',
                clientURL: 'http%3A//localhost%3A1234',
                payload: {
                    api_token: 'token',
                },
                redirectTo: 'http%3A//localhost%3A1234/test/',
                username: 'User',
            });
        });

        it('With a counter greater than 1', function() {
            view._$counter = view.$('#redirect-counter');

            expect(view._redirectCounter).toBe(3);

            view._redirectCountdown();

            expect(view._redirectCounter).toBe(2);
            expect(view._$counter.text()).toBe(' 2...');
        });

        it('With a counter at 1', function() {
            view._$counter = view.$('#redirect-counter');
            view._redirectCounter = 1;
            spyOn(RB, 'navigateTo');
            spyOn(window, 'clearInterval');

            view._redirectCountdown();

            expect(view._redirectCounter).toBe(0);
            expect(view._$counter.text()).toBe(' 0...');
            expect(RB.navigateTo).toHaveBeenCalledWith(
                'http://localhost:1234/test/'
            );
        });
    });
});
