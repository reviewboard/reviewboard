/*
 * issueSummaryTableView handles all interactions with * the issue summary
 * table.
 */
RB.IssueSummaryTableView = Backbone.View.extend({
    events: {
        'change .filter': '_onFilterChanged',
        'click thead th': '_onHeaderClicked',
        'click .summary-anchor': '_onAnchorClicked'
    },

    // Maps a status filter state to its corresponding selector
    stateToSelectorMap: {
        open: ".open",
        dropped: ".dropped",
        resolved: ".resolved",
        all: ""
    },

    initialize: function() {
        this.statusFilterState = "open";  // Default status is "open"
        this.reviewerFilterState = "all"; // Default reviewer is "all"

        // Maps a reviewer name to issues issued by the reviewer
        this.reviewerToSelectorMap = {
            all: ""
        };
    },

    render: function() {
        this._$table = this.$el.find('table');
        this._$thead = this._$table.find('thead');
        this._$tbody = this._$table.find('tbody');

        this._buildReviewerFilterMap();
        this._checkNoIssues();
        this._uncollapseTarget();

        this.model.on('issueStatusUpdated', this._onIssueStatusChanged, this);

        return this;
    },

    // Show or hide entry according to issue summary filter state.
    setVisibility: function(entry, status) {
        if (this.statusFilterState !== status &&
            this.statusFilterState !== 'all') {
            entry.addClass('hidden');
        } else {
            entry.removeClass('hidden');
        }
    },

    // Decrement old status counter and increment new status counter.
    updateCounters: function(old_status, new_status) {
        var old_counter = $('#' + old_status + '-counter'),
            new_counter = $('#' + new_status + '-counter');

        old_counter.text(parseInt(old_counter.text(), 10) - 1);
        new_counter.text(parseInt(new_counter.text(), 10) + 1);
    },

    // Replace old status class with new status class and update text.
    updateStatus: function(entry, old_status, new_status) {
        entry.removeClass(old_status)
            .addClass(new_status)
            .find('.status').text(new_status);

        this.setVisibility(entry, new_status);
        this._checkNoIssues();
    },

    // Replace old timestamp attirbute with new timestamp and update text.
    updateTimeStamp: function(entry, timestamp) {
        entry.find(".last-updated")
            .attr("timestamp", new Date(timestamp).getTime())
            .text(timestamp);
    },

    _onFilterChanged: function() {
        // Hide all visible rows
        $('.issue' + this.stateToSelectorMap[this.statusFilterState] +
          this.reviewerToSelectorMap[this.reviewerFilterState])
            .toggleClass("hidden");

        // Update filter states
        this.statusFilterState = $("#issue-state-filter").val();
        this.reviewerFilterState = $("#issue-reviewer-filter").val();

        // Show rows that match the intersection of the filters
        $('.issue' + this.stateToSelectorMap[this.statusFilterState] +
          this.reviewerToSelectorMap[this.reviewerFilterState])
            .toggleClass("hidden");

        this._checkNoIssues();
    },

    _onHeaderClicked: function(event) {
        if (this._$tbody.find('tr.issue:visible').length !== 0) {
            var $header = $(event.target);

            this._sortByCol(
                $header.parent().children().index(event.target) + 1);
        }

        return false;
    },

    _onAnchorClicked: function(event) {
        event.stopPropagation();

        /*
         *  Extract the comment's attirbutes from the issue element and trigger
         *  the issueClicked event so the page can navigate the user to the
         *  relevant issue comment.
         */
        var $el = $(event.target);

        this.trigger('issueClicked', {
            type: $el.attr('comment-type'),
            id: $el.attr('issue-id')
        });
    },

    // Check that there are no issues that match the selected filter(s).
    _checkNoIssues: function() {
        this._$tbody.find('tr.no-issues').remove();
        this._$thead.show();

        if (this._$tbody.find('tr.issue:visible').length === 0) {
            var text;

            if (this.reviewerFilterState !== 'all') {
                if (this.statusFilterState === "open") {
                    text = interpolate(
                        gettext('There are no open issues from %s'),
                        [this.reviewerFilterState]);
                } else if (this.statusFilterState === 'dropped') {
                    text = interpolate(
                        gettext('There are no dropped issues from %s'),
                        [this.reviewerFilterState]);
                } else if (this.statusFilterState === 'resolved') {
                    text = interpolate(
                        gettext('There are no resolved issues'),
                        [this.reviewerFilterState]);
                }
            } else {
                if (this.statusFilterState === "open") {
                    text = gettext('There are no open issues');
                } else if (this.statusFilterState === 'dropped') {
                    text = gettext('There are no dropped issues');
                } else if (this.statusFilterState === 'resolved') {
                    text = gettext('There are no resolved issues');
                }
            }

            this._$thead.hide();
            this._$tbody.append($('<tr>')
                .addClass('no-issues')
                .append($('<td>')
                    .attr("colspan", 5)
                    .append($('<i>')
                        .text(text))));
        }
    },

    /*
     * Sort the issue summary table entries by the selected column in ascending
     * order.
     *
     * Entries with timestamps will be sorted using the timestamp attribute.
     * Entries with comment ids will be sorted using the comment-id attribute.
     * All other entries will be sorted alphabetically.
     */
    _sortByCol: function(colIndex) {
        this._$tbody.html($('.issue').sort(function(a, b) {
            var firstElement = $(a).find('td:nth-child(' + colIndex + ')'),
                secondElement = $(b).find('td:nth-child(' + colIndex + ')'),
                firstElementText = firstElement.text().toLowerCase(),
                secondElementText = secondElement.text().toLowerCase(),
                firstText,
                secondText;

            if (firstElement.attr('timestamp')) {
                return parseInt(firstElement.attr('timestamp'), 10) -
                       parseInt(secondElement.attr('timestamp'), 10);
            } else if (firstElement.hasClass('comment-id')) {
                 firstText = firstElementText.split(" ");
                 secondText = secondElementText.split(" ");

                 if (firstText[0] > secondText[0]) {
                     return 1;
                 } else if (firstText[0] < secondText[0]) {
                    return -1;
                 } else {
                     return parseInt(firstText[1], 10) -
                            parseInt(secondText[1], 10);
                 }
            } else if (firstElementText > secondElementText) {
                return 1;
            } else if (firstElementText === secondElementText) {
                return 0;
            } else {
                return -1;
            }
        }));
    },

    // Add entries to the reviewerToSelectorMap
    _buildReviewerFilterMap: function() {
        var self = this;

        this._$tbody.find('.issue').each(function() {
            var reviewer = $(this).attr('reviewer');

            if (!_.has(self.reviewerToSelectorMap, reviewer)) {
                self.reviewerToSelectorMap[reviewer] =
                    '[reviewer="' + reviewer + '"]';
                $('#issue-reviewer-filter').append(
                    $('<option>').text(reviewer).val(reviewer));
            }
        });
    },

    _uncollapseTarget: function() {
        var hash = window.location.hash,
            commentName,
            targetBox;

        if (hash.indexOf("comment") > 0) {
            commentName = hash.toString().substring(1);
            targetBox = $('a[name=' + commentName + ']').closest(".box");

            if (targetBox.hasClass('collapsed')) {
                targetBox.removeClass('collapsed');
                // Scroll down to the targeted comment box
                window.location = window.location;
            }
        }
    },

    /*
     * Handler for when the issue status of a comment changes.
     *
     * Updates the display of the table to reflect the state of that issue.
     */
    _onIssueStatusChanged: function(comment, oldStatus, lastUpdated) {
        var entry = $('#summary-table-entry-' + comment.id),
            newStatus = comment.get('issueStatus'),
            oldHeight = this.$el.height();

        this.updateStatus(entry, oldStatus, newStatus);
        this.updateCounters(oldStatus, newStatus);
        this.updateTimeStamp(entry, lastUpdated);

        /*
         * Update the scroll position to counteract the addition/deletion
         * of the entry in the issue summary table, so the page doesn't
         * appear to jump.
         */
        $(window).scrollTop($(window).scrollTop() + this.$el.height() -
                            oldHeight);
    }
});
