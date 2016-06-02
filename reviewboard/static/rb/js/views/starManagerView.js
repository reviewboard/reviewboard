/**
 * A manager for star buttons, for both datagrids and individual buttons.
 *
 * This view manages the state of review request and review group star status
 * in datagrids, as well as the star status for review requests on their
 * individual pages.
 */
RB.StarManagerView = Backbone.View.extend({
    events: {
        'click .star': '_toggleStar'
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         View initialization options.
     *
     * Option Args:
     *     datagridMode (boolean):
     *         Whether or not the manager is managing a datagrid.
     */
    initialize: function(options) {
        var objects = this.model.get('objects'),
            starred = this.model.get('starred');

        options = options || {};

        this._datagridMode = options.datagridMode;

        this.$('div.star').each(function(idx, el) {
            var $el = $(el),
                objType = $el.attr('data-object-type'),
                objID = $el.attr('data-object-id'),
                objStarred = (parseInt($el.attr('data-starred'), 10) === 1),
                obj;

            if (objType === 'reviewrequests') {
                obj = new RB.ReviewRequest({
                    id: objID
                });
            } else if (objType === 'groups') {
                obj = new RB.ReviewGroup({
                    id: objID
                });
            } else if (objType !== undefined) {
                console.assert('Unknown star object type: %s', objType);
            } else {
                /* Skip any stars that don't have an object type. */
                return;
            }

            objects[objID] = obj;
            starred[objID] = objStarred;
        });

        /*
         * When the datagrid is in mobile mode, we have to keep track of any
         * objects whose star status changes so that we can update the datagrid
         * if it switches back to desktop mode.
         */
        this._watchUpdates = false;
        this._toUpdate = {};

        if (this._datagridMode) {
            this.$el.on(
                'datagridDisplayModeChanged',
                _.bind(function($grid, options) {
                    var objID;

                    if (options.mode === 'desktop') {
                        for (objID in this._toUpdate) {
                            if (this._toUpdate.hasOwnProperty(objID)) {
                                this._updateStarColumn(objID);
                            }
                        }

                        this._watchUpdates = false;
                        this._toUpdate = {};
                    } else if (options.mode === 'mobile') {
                        this._watchUpdates = true;
                    }
                }, this));

            if (this.$el.attr('data-datagrid-display-mode') === 'mobile') {
                this._watchUpdates = true;
            }
        }
    },

    /**
     * Update a star column.
     *
     * This function is called when the datagrid changes from mobile to desktop
     * model. Since datagrids copy the original DOM over the new one when the
     * mode is changed to desktop, we must copy over relevant star attributes
     * and classes when this happens.
     *
     * Args:
     *     objID (string):
     *         The object's unique ID, as a string.
     */
    _updateStarColumn: function(objID) {
        var $el = this.$('.star[data-object-id="' + objID + '"]'),
            starred = this.model.get('starred')[objID];

        $el
            .toggleClass('rb-icon-star-on', starred)
            .toggleClass('rb-icon-star-off', !starred)
            .attr('title',
                  starred ? gettext('Starred')
                          : gettext('Click to star'));
    },

    /**
     * Toggle an object being starred or unstarred.
     *
     * This function is called when a star icon is clicked.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    _toggleStar: function(e) {
        var $target = $(e.target),
            objID = $target.attr('data-object-id'),
            obj = this.model.get('objects')[objID],
            starred = this.model.get('starred'),
            objStarred = !starred[objID];

        e.preventDefault();
        e.stopPropagation();

        obj.setStarred(objStarred);
        starred[objID] = objStarred;

        if (this._watchUpdates) {
            if (this._toUpdate.hasOwnProperty(objID)) {
                delete this._toUpdate[objID];
            } else {
                this._toUpdate[objID] = true;
            }
        }

        $target
            .toggleClass('rb-icon-star-on', objStarred)
            .toggleClass('rb-icon-star-off', !objStarred)
            .attr('title',
                  objStarred ? gettext('Starred')
                             : gettext('Click to star'));
    }
});
