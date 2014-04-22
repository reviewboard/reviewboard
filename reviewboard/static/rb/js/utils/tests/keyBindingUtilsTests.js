suite('rb/utils/keyBindingUtils', function() {
    describe('KeyBindingsMixin', function() {
        var MyView,
            view;

        function sendKeyPress($el, keyCode, handled) {
            var evt = jQuery.Event('keypress');
            evt.which = keyCode.charCodeAt(0);
            $el.trigger(evt);

            expect(evt.isDefaultPrevented()).toBe(handled);
            expect(evt.isPropagationStopped()).toBe(handled);
        }

        it('Registered on create', function() {
            MyView = Backbone.View.extend({
                keyBindings: {}
            });
            _.extend(MyView.prototype, RB.KeyBindingsMixin);

            spyOn(MyView.prototype, 'delegateKeyBindings');

            view = new MyView();
            expect(MyView.prototype.delegateKeyBindings).toHaveBeenCalled();
        });

        it('Unregistered on undelegateEvents', function() {
            MyView = Backbone.View.extend({
                keyBindings: {}
            });
            _.extend(MyView.prototype, RB.KeyBindingsMixin);

            view = new MyView();
            spyOn(MyView.prototype, 'undelegateKeyBindings');

            view.undelegateEvents();
            expect(MyView.prototype.undelegateKeyBindings).toHaveBeenCalled();
        });

        it('Keys to function name', function() {
            MyView = Backbone.View.extend({
                keyBindings: {
                    'abc': 'myFunc1',
                    'def': 'myFunc2'
                },

                myFunc1: function() {},
                myFunc2: function() {}
            });
            _.extend(MyView.prototype, RB.KeyBindingsMixin);

            view = new MyView();
            view.render().$el.appendTo($testsScratch);

            spyOn(view, 'myFunc1');
            spyOn(view, 'myFunc2');

            sendKeyPress(view.$el, 'e', true);

            expect(view.myFunc1).not.toHaveBeenCalled();
            expect(view.myFunc2).toHaveBeenCalled();
        });

        it('Keys to function', function() {
            MyView = Backbone.View.extend({
                keyBindings: {
                    'abc': function() {},
                    'def': function() {}
                }
            });
            _.extend(MyView.prototype, RB.KeyBindingsMixin);

            view = new MyView();
            view.render().$el.appendTo($testsScratch);

            spyOn(view.keyBindings, 'abc');
            spyOn(view.keyBindings, 'def');

            sendKeyPress(view.$el, 'b', true);

            expect(view.keyBindings.abc).toHaveBeenCalled();
            expect(view.keyBindings.def).not.toHaveBeenCalled();
        });

        it('Unmatched keys', function() {
            MyView = Backbone.View.extend({
                keyBindings: {
                    'abc': function() {},
                    'def': function() {}
                }
            });
            _.extend(MyView.prototype, RB.KeyBindingsMixin);

            view = new MyView();
            view.render().$el.appendTo($testsScratch);

            spyOn(view.keyBindings, 'abc');
            spyOn(view.keyBindings, 'def');

            sendKeyPress(view.$el, '!', false);

            expect(view.keyBindings.abc).not.toHaveBeenCalled();
            expect(view.keyBindings.def).not.toHaveBeenCalled();
        });
    });
});
