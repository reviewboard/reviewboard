/*
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
    NOTIFICATION_LIFETIME_MSECS: 10000,
    NOTIFICATION_TYPE: (window.Notification ||
                        window.mozNotification ||
                        window.webkitNotification),

    /*
     * Initialize the notification manager.
     *
     * Sets the initial values used by the notification manager.
     *
     */
    initialize: function() {
        this._notification = null;
    },

   /*
     * Set up the notification manager.
     *
     * This function will request permission to send desktop notifications
     * if notifications are allowed in the users preferences, and the
     * browser supports notifications.
     *
     * It must be called before attempting to send notifications.
     */
    setup: function() {
        this._canNotify = (
            this.NOTIFICATION_TYPE !== undefined &&
            RB.UserSession.instance.get('enableDesktopNotifications'));

        if (this._canNotify &&
            !this._haveNotificationPermissions()) {
            this.NOTIFICATION_TYPE.requestPermission();
        }
    },

    /*
     * Return whether we have permission to send notifications to the user.
     *
     * Returns:
     *     boolean:
     *         ``true`` if the user has enabled notifications in their browser
     *         Otherwise, ``false`` will be returned.
     */
    _haveNotificationPermissions: function() {
        return this.NOTIFICATION_TYPE.permission === "granted";
    },

    /*
     * Return whether we should send notifications to the user.
     *
     * Returns:
     *     boolean:
     *         ``true`` if the user has enabled notifications in their user
     *         settings, the users current browser supports notifications, and
     *         the user has granted permission for notifications to the
     *         browser. Otherwise, ``false`` will be returned.
     */
    shouldNotify: function() {
        return this._canNotify &&
               this._haveNotificationPermissions();
    },

    /*
     * Send a notification with the options specified in the data parameter.
     *
     * Args:
     *     data (Object):
     *         The last update information for the request. Contains the
     *         following keys:
     *
     *         * ``title`` (String): The title of the notification.
     *
     *         * ``body`` (String): The body text of the notification.
     *
     *         * ``iconURL`` (String): The URL of the icon to be used
     *             in the notification Icons are not supported in some
     *             browsers, and thus will only be show in supported
     *             browsers.
     *
     *         * ``onclick`` (function): The callback for when a user
     *             clicks the notification. By defualt this includes
     *             notification.close, so this does not need to be
     *             specified by the calling class.
     */
    notify: function(data) {
        var notification = null;

        if (this._notification) {
            this._notification.close();
        }

        this._notification = new this.NOTIFICATION_TYPE(
            data.title, {
                text: data.body,
                icon: data.iconURL
            });

        notification = this._notification;

        this._notification.onclick = function(){
            data.onclick();
            notification.close();
        };

        _.delay(_.bind(notification.close, notification),
                this.NOTIFICATION_LIFETIME_MSECS);
     }
}, {
    instance: null
});

RB.NotificationManager.instance = new RB.NotificationManager();