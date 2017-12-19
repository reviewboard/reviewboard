/**
 * A manager for desktop notifications.
 *
 * Manages the sending of desktop notifications to the user, including
 * checking if certain user conditions are met and deciding which form
 * of notification to send depending on the user's browser.
 *
 * For desktop notifications to be sent to the user, the user must have
 * allowed notifications in their browser and account settings.
 */
RB.NotificationManager = Backbone.View.extend({
    /**
     * Initialize the notification manager.
     *
     * Sets the initial values used by the notification manager.
     *
     */
    initialize() {
        this._canNotify = false;
        this._notification = null;
    },

    /**
     * Set up the notification manager.
     *
     * This function will request permission to send desktop notifications
     * if notifications are allowed in the users preferences, and the
     * browser supports notifications.
     *
     * It must be called before attempting to send notifications.
     */
    setup() {
       const Notification = RB.NotificationManager.Notification;

       this._canNotify = (
           Notification !== undefined &&
           RB.UserSession.instance.get('enableDesktopNotifications'));

       if (this._canNotify && !this._haveNotificationPermissions()) {
           Notification.requestPermission();
       }
    },

    /**
     * Return whether we have permission to send notifications to the user.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the user has enabled notifications in their browser
     *     Otherwise, ``false`` will be returned.
     */
    _haveNotificationPermissions() {
        return this._canNotify &&
               RB.NotificationManager.Notification.permission === 'granted';
    },

    /**
     * Return whether or not we should send notifications to the user.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the user has enabled notifications in their user
     *     settings, the users current browser supports notifications, and
     *     the user has granted permission for notifications to the
     *     browser. Otherwise, ``false`` will be returned.
     */
    shouldNotify() {
        return this._canNotify && this._haveNotificationPermissions();
    },

    /**
     * Send a notification with the options specified.
     *
     * Args:
     *     options (object):
     *         The notification options.
     *
     * Option Args:
     *     title (string):
     *         The title of the notification.
     *
     *     body (string):
     *         The body of the notification.
     *
     *     iconURL (string):
     *         The URL of the icon to be used in the notification. Icons are
     *         only supported in some browsers.
     *
     *     onClick (function):
     *         The callback for when a user clicks the notification. The caller
     *         needn't close the notification with this
     */
    notify(options) {
        if (!this._canNotify) {
            return;
        }

        if (this._notification) {
            this._notification.close();
        }

        console.assert(
            options.hasOwnProperty('title'),
            'RB.NotificationManager.notify requires "title" property');

        const notification = new RB.NotificationManager.Notification(
            options.title,
            {
                body: options.body,
                icon: options.iconURL,
            });

        this._notification = notification;

        notification.onclick = function() {
            if (_.isFunction(options.onClick)) {
                options.onClick();
            }

            notification.close();
        };

        _.delay(() => notification.close(),
                RB.NotificationManager.NOTIFICATION_LIFETIME_MSECS);
     }
}, {
    instance: null,

    NOTIFICATION_LIFETIME_MSECS: 10000,
    Notification: window.Notification ||
                  window.mozNotification ||
                  window.webkitNotification,
});


RB.NotificationManager.instance = new RB.NotificationManager();
