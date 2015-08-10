suite('djblets/gravy/backboneUtils', function() {
    var model;

    beforeEach(function() {
        model = new Backbone.Model();
    });

    describe('$.fn.bindClass', function() {
        var $el;

        beforeEach(function() {
            $el = $('<div/>').appendTo(document.body);
        });

        describe('Initial class value', function() {
            it('Adds class when true', function() {
                model.set('mybool', true);
                $el.bindClass(model, 'mybool', 'myclass');
                expect($el.hasClass('myclass')).toBe(true);
            });

            it('No class when false', function() {
                model.set('mybool', false);
                $el.bindClass(model, 'mybool', 'myclass');
                expect($el.hasClass('myclass')).toBe(false);
            });

            describe('With inverse', function() {
                it('No class when true', function() {
                    model.set('mybool', true);
                    $el.bindClass(model, 'mybool', 'myclass', {
                        inverse: true
                    });
                    expect($el.hasClass('myclass')).toBe(false);
                });

                it('Adds class when false', function() {
                    model.set('mybool', false);
                    $el.bindClass(model, 'mybool', 'myclass', {
                        inverse: true
                    });
                    expect($el.hasClass('myclass')).toBe(true);
                });
            });
        });

        describe('Model property changes', function() {
            it('Removes class when true -> false', function() {
                model.set('mybool', true);
                $el.bindClass(model, 'mybool', 'myclass');
                model.set('mybool', false);
                expect($el.hasClass('myclass')).toBe(false);
            });

            it('Adds class when false -> true', function() {
                model.set('mybool', false);
                $el.bindClass(model, 'mybool', 'myclass');
                model.set('mybool', true);
                expect($el.hasClass('myclass')).toBe(true);
            });

            describe('With inverse', function() {
                it('Adds class when true -> false', function() {
                    model.set('mybool', true);
                    $el.bindClass(model, 'mybool', 'myclass', {
                        inverse: true
                    });
                    model.set('mybool', false);
                    expect($el.hasClass('myclass')).toBe(true);
                });

                it('Removes class when false -> true', function() {
                    model.set('mybool', false);
                    $el.bindClass(model, 'mybool', 'myclass', {
                        inverse: true
                    });
                    model.set('mybool', true);
                    expect($el.hasClass('myclass')).toBe(false);
                });
            });
        });
    });

    describe('$.fn.bindProperty', function() {
        var $el,
            $radio1,
            $radio2;

        beforeEach(function() {
            $el = $("<input type='checkbox'/>").appendTo(document.body);
            $radio1 = $('<input type="radio" name="my-radio" value="one" />')
                .appendTo(document.body);
            $radio2 = $('<input type="radio" name="my-radio" value="two" />')
                .appendTo(document.body);
        });

        afterEach(function() {
            $el.remove();
            $radio1.remove();
            $radio2.remove();
        });

        describe("Initial property values", function() {
            it("Setting element's property from model property's", function() {
                model.set('mybool', true);
                $el.bindProperty('checked', model, 'mybool');
                expect($el.prop('checked')).toBe(true);
            });

            it("Setting element's property from model property's with " +
               "inverse=true",
               function() {
                model.set('mybool', false);
                $el.bindProperty('checked', model, 'mybool', {
                    inverse: true
                });
                expect($el.prop('checked')).toBe(true);
                expect(model.get('mybool')).toBe(false);
            });

            it("Setting element's property from model property with radioValue",
               function() {
                model.set('myvalue', 'one');

                $radio1.bindProperty('checked', model, 'myvalue', {
                    radioValue: 'one'
                });
                $radio2.bindProperty('checked', model, 'myvalue', {
                    radioValue: 'two'
                });

                expect($radio1.prop('checked')).toBe(true);
                expect($radio2.prop('checked')).toBe(false);
                expect(model.get('myvalue')).toBe('one');
            });

            it('No element changes with modelToElement=false', function() {
                model.set('mybool', true);
                $el.bindProperty('checked', model, 'mybool', {
                    modelToElement: false
                });

                expect($el.prop('checked')).toBe(false);
            });
        });

        describe("Model property changes", function() {
            it("Setting element's property", function() {
                model.set('mybool', false);
                $el.bindProperty('checked', model, 'mybool');
                expect($el.prop('checked')).toBe(false);

                model.set('mybool', true);
                expect($el.prop('checked')).toBe(true);
            });

            it("Setting element's property with inverse=true", function() {
                model.set('mybool', false);
                $el.bindProperty('checked', model, 'mybool', {
                    inverse: true
                });
                expect($el.prop('checked')).toBe(true);

                model.set('mybool', true);
                expect($el.prop('checked')).toBe(false);
                expect(model.get('mybool')).toBe(true);
            });

            it("Setting element's property with radioValue", function() {
                model.set('myvalue', 'one');

                $radio1.bindProperty('checked', model, 'myvalue', {
                    radioValue: 'one'
                });
                $radio2.bindProperty('checked', model, 'myvalue', {
                    radioValue: 'two'
                });

                expect($radio1.prop('checked')).toBe(true);
                expect($radio2.prop('checked')).toBe(false);

                model.set('myvalue', 'two');
                expect($radio1.prop('checked')).toBe(false);
                expect($radio2.prop('checked')).toBe(true);
                expect(model.get('myvalue')).toBe('two');
            });

            it('No element changes with modelToElement=false', function() {
                model.set('mybool', false);
                $el.bindProperty('checked', model, 'mybool', {
                    modelToElement: false
                });

                model.set('mybool', true);
                expect($el.prop('checked')).toBe(false);
            });
        });

        describe("Element property changes", function() {
            it("Setting model's property", function() {
                model.set('mybool', false);
                $el.bindProperty('checked', model, 'mybool');

                $el.click();
                expect($el.prop('checked')).toBe(true);
                expect(model.get('mybool')).toBe(true);
            });

            it("Setting model's property with inverse=true", function() {
                model.set('mybool', false);
                $el.bindProperty('checked', model, 'mybool', {
                    inverse: true
                });

                $el.prop('checked', false);
                $el.click();

                expect($el.prop('checked')).toBe(true);
                expect(model.get('mybool')).toBe(false);
            });

            it("Setting model's property with radioValue", function() {
                model.set('myvalue', 'one');

                $radio1.bindProperty('checked', model, 'myvalue', {
                    radioValue: 'one'
                });
                $radio2.bindProperty('checked', model, 'myvalue', {
                    radioValue: 'two'
                });

                $radio2.click();

                expect($radio1.prop('checked')).toBe(false);
                expect($radio2.prop('checked')).toBe(true);
                expect(model.get('myvalue')).toBe('two');
            });

            it("No model changes with elementToModel=false", function() {
                model.set('mybool', false);
                $el.bindProperty('checked', model, 'mybool', {
                    elementToModel: false
                });

                $el.click();
                expect($el.prop('checked')).toBe(true);
                expect(model.get('mybool')).toBe(false);
            });
        });

        describe("Special properties", function() {
            it('text', function() {
                var $el = $('<p/>');

                $el.bindProperty('text', model, 'text', {
                    elementToModel: false
                });

                model.set('text', 'hello world!');
                expect($el.text()).toBe('hello world!');
            });

            it('html', function() {
                var $el = $('<p/>');

                $el.bindProperty('html', model, 'html', {
                    elementToModel: false
                });

                model.set('html', '<b>hello world!</b>');
                expect($el.html()).toBe('<b>hello world!</b>');
            });
        });
    });

    describe('$.fn.bindVisibility', function() {
        var $el;

        beforeEach(function() {
            $el = $('<div/>').appendTo(document.body);
        });

        afterEach(function() {
            $el.remove();
        });

        describe('Showing elements', function() {
            it('When property is initially true', function() {
                $el.hide();

                model.set('mybool', true);
                $el.bindVisibility(model, 'mybool');
                expect($el.is(':visible')).toBe(true);
            });

            it('When property is initially false with inverse=true',
               function() {
                $el.hide();

                model.set('mybool', false);
                $el.bindVisibility(model, 'mybool', {
                    inverse: true
                });
                expect($el.is(':visible')).toBe(true);
            });

            it('When property is changed to true', function() {
                expect($el.is(':visible')).toBe(true);

                model.set('mybool', false);
                $el.bindVisibility(model, 'mybool');
                model.set('mybool', true);
                expect($el.is(':visible')).toBe(true);
            });

            it('When property is changed to false with inverse=true',
               function() {
                $el.hide();

                model.set('mybool', true);
                $el.bindVisibility(model, 'mybool', {
                    inverse: true
                });
                model.set('mybool', false);
                expect($el.is(':visible')).toBe(true);
            });
        });

        describe('Hiding elements', function() {
            it('When property is initially false', function() {
                expect($el.is(':visible')).toBe(true);

                model.set('mybool', false);
                $el.bindVisibility(model, 'mybool');
                expect($el.is(':visible')).toBe(false);
            });

            it('When property is initially true with inverse=true',
               function() {
                expect($el.is(':visible')).toBe(true);

                model.set('mybool', true);
                $el.bindVisibility(model, 'mybool', {
                    inverse: true
                });
                expect($el.is(':visible')).toBe(false);
            });

            it('When property is changed to false', function() {
                $el.hide();

                model.set('mybool', true);
                $el.bindVisibility(model, 'mybool');
                model.set('mybool', false);
                expect($el.is(':visible')).toBe(false);
            });

            it('When property is changed to true with inverse=true',
               function() {
                expect($el.is(':visible')).toBe(true);

                model.set('mybool', false);
                $el.bindVisibility(model, 'mybool', {
                    inverse: true
                });
                model.set('mybool', true);
                expect($el.is(':visible')).toBe(false);
            });
        });
    });
});
