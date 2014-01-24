describe('configForms/models/ListItem', function() {
    describe('Default actions', function() {
        describe('showRemove', function() {
            it('true', function() {
                var listItem = new RB.Config.ListItem({
                    showRemove: true
                });

                expect(listItem.actions.length).toBe(1);
                expect(listItem.actions[0].id).toBe('delete');
            });

            it('false', function() {
                var listItem = new RB.Config.ListItem({
                    showRemove: false
                });

                expect(listItem.actions.length).toBe(0);
            });
        });
    });
});
