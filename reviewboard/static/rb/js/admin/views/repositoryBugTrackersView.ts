/**
 * View for the repository form's bug trackers widget.
 *
 * Version Added:
 *     9.0
 */

import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';
import { dedent } from 'babel-plugin-dedent';
import _ from 'underscore';


/**
 * Serialized information on a bug tracker configuration.
 *
 * Version Added:
 *     9.0
 */
export interface BugTrackerConfigInfo {
    /** Whether the configuration is enabled. */
    enabled: boolean;

    /** The configuration's primary key. */
    id: number;

    /** Whether the configuration limits access by user conditions. */
    limitedAccess: boolean;

    /** The URL of the service's logo, if any. */
    logoURL: string | null;

    /** The configuration's display name. */
    name: string;

    /** The display name of the backing service. */
    serviceLabel: string;
}


/**
 * Bug tracker information on a hosting service.
 *
 * Version Added:
 *     9.0
 */
export interface ServiceBugTrackerInfo {
    /** The display name of the service's own bug tracker. */
    bugTrackerName: string;

    /** The URL of the service's logo, if any. */
    logoURL: string | null;
}


/**
 * Options for RepositoryBugTrackersView.
 *
 * Version Added:
 *     9.0
 */
export interface RepositoryBugTrackersViewOptions {
    /** The hidden input holding the attached configuration IDs. */
    $input: JQuery;

    /** Configurations applying to all review requests. */
    allConfigs: BugTrackerConfigInfo[];

    /** Configurations attached to this repository. */
    attachedConfigs: BugTrackerConfigInfo[];

    /** Configurations available for attaching. */
    availableConfigs: BugTrackerConfigInfo[];

    /** The materialized built-in tracker configuration, if any. */
    builtinConfig: BugTrackerConfigInfo | null;

    /** The ID of the form's default bug tracker select. */
    defaultFieldID: string;

    /** The primary key of the current default bug tracker. */
    defaultID: number | null;

    /** The ID of the form's hosting type select. */
    hostingTypeFieldID: string;

    /** Bug tracker information, keyed by hosting service ID. */
    services: Record<string, ServiceBugTrackerInfo>;

    /** Whether the repository uses its hosting service's bug tracker. */
    useHosting: boolean;

    /** The ID of the form's legacy use-hosting checkbox. */
    useHostingFieldID: string;
}


/**
 * Per-service metadata provided by the repository form page.
 *
 * Version Added:
 *     9.0
 */
interface HostingServiceInfo {
    fake?: boolean;
    supports_bug_trackers: boolean;
}

declare const HOSTING_SERVICES: Record<string, HostingServiceInfo>;


/**
 * A key identifying a tracker row.
 *
 * Attached configurations are keyed by primary key. The built-in
 * tracker is keyed as ``builtin`` until it has a materialized
 * configuration.
 *
 * Version Added:
 *     9.0
 */
type TrackerKey = number | 'builtin';


/**
 * View for the repository form's bug trackers widget.
 *
 * This renders the trackers for a repository: the built-in hosting
 * service tracker, configurations applying to all review requests
 * (locked), and configurations attached to the repository, along with
 * a radio for choosing the default tracker for bare bug IDs and a
 * picker for attaching more.
 *
 * The view drives the form's hidden fields: the attached configuration
 * IDs input, the legacy use-hosting checkbox, and the default bug
 * tracker select.
 *
 * Version Added:
 *     9.0
 */
@spina
export class RepositoryBugTrackersView extends BaseView<
    undefined,
    HTMLElement,
    RepositoryBugTrackersViewOptions
> {
    static events: EventsHash = {
        'change .rb-c-repo-bug-trackers__attach-select': '_onAttachSelected',
        'change .rb-c-repo-bug-trackers__radio': '_onDefaultSelected',
        'click .rb-c-repo-bug-trackers__remove': '_onRemoveClicked',
    };

    /**********************
     * Instance variables *
     **********************/

    /** The hidden input holding the attached configuration IDs. */
    #$input: JQuery;

    /** The form's default bug tracker select. */
    #$defaultField: JQuery;

    /** The form's hosting type select. */
    #$hostingType: JQuery;

    /** The form's legacy use-hosting checkbox. */
    #$useHostingField: JQuery;

    /** Configurations applying to all review requests. */
    #allConfigs: BugTrackerConfigInfo[];

    /** Configurations attached to this repository, in display order. */
    #attached: BugTrackerConfigInfo[];

    /** Configurations available for attaching, in display order. */
    #available: BugTrackerConfigInfo[];

    /** The materialized built-in tracker configuration, if any. */
    #builtinConfig: BugTrackerConfigInfo | null;

    /** Whether the selected hosting service offers a built-in tracker. */
    #builtinSupported = false;

    /** The key of the current default tracker, if any. */
    #defaultKey: TrackerKey | null;

    /** Bug tracker information, keyed by hosting service ID. */
    #services: Record<string, ServiceBugTrackerInfo>;

    /** Whether the built-in tracker is in use. */
    #useHosting: boolean;

    /**
     * Initialize the view.
     *
     * Args:
     *     options (RepositoryBugTrackersViewOptions):
     *         Options for the view.
     */
    initialize(options: RepositoryBugTrackersViewOptions) {
        this.#$input = options.$input;
        this.#$defaultField = $(`#${options.defaultFieldID}`);
        this.#$hostingType = $(`#${options.hostingTypeFieldID}`);
        this.#$useHostingField = $(`#${options.useHostingFieldID}`);
        this.#allConfigs = options.allConfigs;
        this.#attached = [...options.attachedConfigs];
        this.#available = [...options.availableConfigs];
        this.#builtinConfig = options.builtinConfig;
        this.#services = options.services || {};
        this.#useHosting = options.useHosting;

        const defaultID = options.defaultID;

        if (defaultID === null) {
            this.#defaultKey = null;
        } else {
            this.#defaultKey = defaultID;
        }
    }

    /**
     * Render the view.
     */
    protected onInitialRender() {
        this.#$hostingType.on(
            'change.repositoryBugTrackers',
            () => this.#onHostingTypeChanged());
        this.#onHostingTypeChanged();
    }

    /**
     * Remove the view.
     *
     * Returns:
     *     RepositoryBugTrackersView:
     *     This view.
     */
    protected onRemove() {
        this.#$hostingType.off('change.repositoryBugTrackers');
    }

    /**
     * Handle a change to the form's hosting service.
     *
     * The built-in tracker row is only offered when the selected
     * hosting service supports bug trackers. Switching to a hosting
     * service without support turns the built-in tracker off.
     */
    #onHostingTypeChanged() {
        const hostingType = this.#$hostingType.val() as string;
        const serviceInfo =
            (typeof HOSTING_SERVICES !== 'undefined' &&
             HOSTING_SERVICES[hostingType]) ||
            null;

        this.#builtinSupported = !!(
            serviceInfo &&
            serviceInfo.fake !== true &&
            serviceInfo.supports_bug_trackers);

        if (!this.#builtinSupported && this.#useHosting) {
            this.#setUseHosting(false);
        }

        this.#paint();
    }

    /**
     * Return the display label for the built-in tracker.
     *
     * Returns:
     *     string:
     *     The label to show on the built-in tracker row.
     */
    #getBuiltinLabel(): string {
        if (this.#builtinConfig !== null) {
            return this.#builtinConfig.name;
        }

        const hostingType = this.#$hostingType.val() as string;
        const serviceInfo = this.#services[hostingType];

        if (serviceInfo) {
            return serviceInfo.bugTrackerName;
        }

        const serviceName =
            this.#$hostingType.find('option:selected').text().trim();

        return interpolate(
            gettext('%(serviceName)s bug tracker'),
            { serviceName: serviceName },
            true);
    }

    /**
     * Return the key of the built-in tracker.
     *
     * Returns:
     *     TrackerKey:
     *     The built-in configuration's ID, or ``builtin`` when no
     *     configuration has been created yet.
     */
    #getBuiltinKey(): TrackerKey {
        return (this.#builtinConfig !== null
                ? this.#builtinConfig.id
                : 'builtin');
    }

    /**
     * Set whether the built-in tracker is in use.
     *
     * This drives the form's hidden legacy use-hosting checkbox, and
     * clears the default tracker if it pointed to the built-in tracker.
     *
     * Args:
     *     useHosting (boolean):
     *         Whether the built-in tracker is in use.
     */
    #setUseHosting(useHosting: boolean) {
        this.#useHosting = useHosting;
        this.#$useHostingField.prop('checked', useHosting);

        if (!useHosting && this.#defaultKey === this.#getBuiltinKey()) {
            this.#setDefault(null);
        }
    }

    /**
     * Set the default tracker.
     *
     * This drives the form's hidden default bug tracker select. The
     * unmaterialized built-in tracker has no selectable value; saving
     * the form assigns it as the default when one isn't set.
     *
     * Args:
     *     key (TrackerKey):
     *         The key of the new default tracker, or ``null`` to clear
     *         it.
     */
    #setDefault(key: TrackerKey | null) {
        this.#defaultKey = key;

        if (key === null || key === 'builtin') {
            this.#$defaultField.val('');
        } else {
            this.#$defaultField.val(String(key));
        }
    }

    /**
     * Write the attached configuration IDs to the hidden input.
     */
    #syncInput() {
        this.#$input.val(
            this.#attached
                .map(config => config.id)
                .join(','));
    }

    /**
     * Handle the default radio changing.
     *
     * Args:
     *     e (Event):
     *         The change event.
     */
    private _onDefaultSelected(e: Event) {
        const value = (e.target as HTMLInputElement).value;

        this.#setDefault(value === 'builtin'
                         ? 'builtin'
                         : parseInt(value, 10));
        this.#paint();
    }

    /**
     * Handle a remove button being clicked.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    private _onRemoveClicked(e: Event) {
        e.preventDefault();

        const key = $(e.currentTarget).data('tracker-key');

        if (key === 'builtin' || key === this.#getBuiltinKey()) {
            this.#setUseHosting(false);
        } else {
            const index = this.#attached.findIndex(
                config => config.id === key);

            if (index !== -1) {
                const [config] = this.#attached.splice(index, 1);
                this.#available.push(config);
                this.#syncInput();

                if (this.#defaultKey === config.id) {
                    this.#setDefault(null);
                }
            }
        }

        this.#paint();
    }

    /**
     * Handle a tracker being chosen in the attach picker.
     *
     * If no default tracker is set, the new tracker becomes the default.
     *
     * Args:
     *     e (Event):
     *         The change event.
     */
    private _onAttachSelected(e: Event) {
        const value = (e.target as HTMLSelectElement).value;

        if (!value) {
            return;
        }

        let attachedKey: TrackerKey | null = null;

        if (value === 'builtin') {
            this.#setUseHosting(true);
            attachedKey = this.#getBuiltinKey();
        } else {
            const id = parseInt(value, 10);
            const index = this.#available.findIndex(
                config => config.id === id);

            if (index !== -1) {
                const [config] = this.#available.splice(index, 1);
                this.#attached.push(config);
                this.#syncInput();
                attachedKey = config.id;
            }
        }

        if (attachedKey !== null && this.#defaultKey === null) {
            this.#setDefault(attachedKey);
        }

        this.#paint();
    }

    /**
     * Render a tracker row.
     *
     * Args:
     *     options (object):
     *         Options describing the row.
     *
     * Returns:
     *     string:
     *     The row's HTML.
     */
    #renderRow(
        options: {
            badges?: string[];
            key: TrackerKey;
            locked?: boolean;
            logoURL?: string | null;
            meta: string;
            name: string;
        },
    ): string {
        const key = options.key;
        const isDefault = (this.#defaultKey === key);
        const badges: string[] = [];

        if (isDefault) {
            badges.push(this.#renderBadge(gettext('Default'), {
                type: 'primary',
            }));
        }

        for (const chip of options.badges || []) {
            badges.push(chip);
        }

        let logoHTML: string;

        if (options.logoURL) {
            logoHTML = dedent`
                <img class="rb-c-repo-bug-trackers__logo" alt=""
                     src="${_.escape(options.logoURL)}">
            `;
        } else {
            const initials = options.name
                .split(/\s+/, 2)
                .map(word => word.charAt(0).toUpperCase())
                .join('');

            logoHTML = dedent`
                <span class="rb-c-repo-bug-trackers__logo" aria-hidden="true">
                 ${_.escape(initials)}
                </span>
            `;
        }

        let actionHTML: string;

        if (options.locked) {
            actionHTML = dedent`
                <span class="rb-c-repo-bug-trackers__lock"
                      title="${gettext('This bug tracker configuration applies to all review requests. Edit this in the tracker\'s administration page.')}"
                      aria-hidden="true">
                 <span class="rb-icon-lock"></span>
                </span>
            `;
        } else {
            actionHTML = dedent`
                <button class="rb-c-repo-bug-trackers__remove" type="button"
                        data-tracker-key="${key}"
                        title="${gettext('Remove from this repository')}">
                 <span class="ink-i-close" aria-hidden="true"></span>
                </button>
            `;
        }

        return dedent`
            <div class="rb-c-repo-bug-trackers__row">
             <input class="rb-c-repo-bug-trackers__radio" type="radio"
                    name="_bug_tracker_default_choice"
                    value="${key}"
                    ${isDefault ? 'checked' : ''}
                    title="${gettext('Make this the default tracker for bare bug IDs')}">
             ${logoHTML}
             <div class="rb-c-repo-bug-trackers__info">
              <div class="rb-c-repo-bug-trackers__name">
               ${_.escape(options.name)}
               ${badges.join('')}
              </div>
              <div class="rb-c-repo-bug-trackers__meta">
               ${_.escape(options.meta)}
              </div>
             </div>
             ${actionHTML}
            </div>
        `;
    }

    /**
     * Render a badge.
     *
     * Args:
     *     label (string):
     *         The badge's label.
     *
     *     options (object, optional):
     *         Options controlling the badge's appearance.
     *
     * Returns:
     *     string:
     *     The badge's HTML.
     */
    #renderBadge(
        label: string,
        options: {
            iconClass?: string;
            type?: string;
        } = {},
    ): string {
        const typeHTML = (options.type
                          ? ` data-type="${options.type}"`
                          : '');
        const iconHTML = (options.iconClass
                          ? `<span class="ink-c-badge__icon ` +
                            `${options.iconClass}" aria-hidden="true">` +
                            `</span>`
                          : '');

        return dedent`
            <span class="ink-c-badge"${typeHTML}>
             ${iconHTML}
             <span class="ink-c-badge__label">${_.escape(label)}</span>
            </span>
        `;
    }

    /**
     * Return the badges for a configuration.
     *
     * Args:
     *     config (BugTrackerConfigInfo):
     *         The configuration.
     *
     * Returns:
     *     Array of string:
     *     The HTML for each chip.
     */
    #getConfigBadges(config: BugTrackerConfigInfo): string[] {
        const badges: string[] = [];

        if (config.limitedAccess) {
            badges.push(this.#renderBadge(gettext('Private'), {
                iconClass: 'rb-icon-lock',
                type: 'warning',
            }));
        }

        if (!config.enabled) {
            badges.push(this.#renderBadge(gettext('Disabled')));
        }

        return badges;
    }

    /**
     * Paint the widget from the current state.
     */
    #paint() {
        const rows: string[] = [];

        if (this.#useHosting && this.#builtinSupported) {
            const hostingType = this.#$hostingType.val() as string;
            const serviceName =
                this.#$hostingType.find('option:selected').text().trim();

            rows.push(this.#renderRow({
                key: this.#getBuiltinKey(),
                logoURL: (this.#builtinConfig?.logoURL ??
                          this.#services[hostingType]?.logoURL ??
                          null),
                meta: interpolate(
                    gettext('Built-in tracker for this repository'),
                    { serviceName: serviceName },
                    true),
                name: this.#getBuiltinLabel(),
            }));
        }

        for (const config of this.#allConfigs) {
            rows.push(this.#renderRow({
                badges: [
                    this.#renderBadge(gettext('All review requests')),
                    ...this.#getConfigBadges(config),
                ],
                key: config.id,
                locked: true,
                logoURL: config.logoURL,
                meta: config.serviceLabel,
                name: config.name,
            }));
        }

        for (const config of this.#attached) {
            rows.push(this.#renderRow({
                badges: this.#getConfigBadges(config),
                key: config.id,
                logoURL: config.logoURL,
                meta: config.serviceLabel,
                name: config.name,
            }));
        }

        const attachOptions: string[] = [];

        if (this.#builtinSupported && !this.#useHosting) {
            attachOptions.push(dedent`
                <option value="builtin">
                 ${_.escape(interpolate(
                     gettext('%(label)s (built-in)'),
                     { label: this.#getBuiltinLabel() },
                     true))}
                </option>
            `);
        }

        for (const config of this.#available) {
            attachOptions.push(dedent`
                <option value="${config.id}">
                 ${_.escape(interpolate(
                     gettext('%(name)s (%(serviceLabel)s)'),
                     {
                         name: config.name,
                         serviceLabel: config.serviceLabel,
                     },
                     true))}
                </option>
            `);
        }

        const footerParts: string[] = [];

        if (attachOptions.length > 0) {
            footerParts.push(dedent`
                <select class="rb-c-repo-bug-trackers__attach-select">
                 <option value="">
                  ${gettext('+ Attach a tracker...')}
                 </option>
                 ${attachOptions.join('')}
                </select>
            `);
        }

        let listHTML: string;

        if (rows.length > 0) {
            listHTML = dedent`
                <div class="rb-c-repo-bug-trackers__list">
                 ${rows.join('')}
                </div>
            `;

            footerParts.push(dedent`
                <span class="rb-c-repo-bug-trackers__hint">
                 ${gettext('The <b>default tracker</b> is used for bug links in descriptions and comments.')}
                </span>
            `);
        } else {
            listHTML = dedent`
                <div class="rb-c-repo-bug-trackers__empty">
                 ${gettext('No bug trackers are attached to this repository.')}
                </div>
            `;
        }

        let footerHTML = '';

        if (footerParts.length > 0) {
            footerHTML = dedent`
                <div class="rb-c-repo-bug-trackers__footer">
                 ${footerParts.join('')}
                </div>
            `;
        }

        this.el.innerHTML = dedent`
            ${listHTML}
            ${footerHTML}
        `;
    }
}
