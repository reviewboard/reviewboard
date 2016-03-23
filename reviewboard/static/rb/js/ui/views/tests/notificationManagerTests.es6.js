suite('rb/ui/managers/NotificationManagerModel', () => {
    beforeEach(() => {
        RB.NotificationManager.instance.setup();
    });

    describe('Notification Manager', () => {
        it('Calls external API', () => {
            spyOn(RB.NotificationManager, 'Notification')
                .and.returnValue({
                    close: () => true
                });

            RB.NotificationManager.instance.notify({
                title: 'Test',
                body: 'This is a Test'
            });

            expect(RB.NotificationManager.Notification)
                .toHaveBeenCalled();
        });

        it('Should notify', () => {
            RB.NotificationManager.instance._canNotify = true;
            spyOn(RB.NotificationManager.instance,
                  '_haveNotificationPermissions').and.returnValue(true);

            expect(RB.NotificationManager.instance.shouldNotify()).toBe(true);
        });


        it('Should not notify due to user permissions', () => {
            RB.NotificationManager.instance._canNotify = false;
            spyOn(RB.NotificationManager.instance,
                  '_haveNotificationPermissions').and.returnValue(true);

            expect(RB.NotificationManager.instance.shouldNotify()).toBe(false);
        });

         it('Should not notify due to browser permissions', () => {
            RB.NotificationManager.instance._canNotify = true;
            spyOn(RB.NotificationManager.instance,
                  '_haveNotificationPermissions').and.returnValue(false);

            expect(RB.NotificationManager.instance.shouldNotify()).toBe(false);
        });
    });
});
