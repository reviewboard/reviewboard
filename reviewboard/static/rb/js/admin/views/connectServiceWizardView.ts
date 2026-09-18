/**
 * Wizard for connecting a hosting service.
 *
 * Version Added:
 *     9.0
 */

import {
    type ButtonView,
    type ComponentChild,
    type DialogViewOptions,
    DialogView,
    craft,
    paint,
} from '@beanbag/ink';
import {
    type BaseModel,
    spina,
} from '@beanbag/spina';
import { dedent } from 'babel-plugin-dedent';


/**
 * Information about a hosting service available for connection.
 *
 * Version Added:
 *     9.0
 */
export interface ConnectServiceInfo {
    /** The unique ID of the hosting service. */
    id: string;

    /** The static URL to the service's logo, if any. */
    logo: string | null;

    /** The display name of the service. */
    name: string;

    /** The section IDs the service belongs to. */
    sections: string[];
}


/**
 * Options for ConnectServiceWizardView.
 *
 * Version Added:
 *     9.0
 */
export interface ConnectServiceWizardViewOptions extends DialogViewOptions {
    /**
     * A URL template for the per-service connect endpoint.
     *
     * This contains the placeholder ``__SERVICE_ID__``, which is replaced
     * with the selected service's ID.
     */
    connectURLTemplate: string;

    /** The CSRF token to send with form submissions. */
    csrfToken: string;

    /**
     * A connect page to open directly, skipping the service picker.
     *
     * This is used to deep-link to a specific step (such as the GitHub App
     * creation page) from outside the wizard. When set, the picker is not
     * shown and there is nothing to go "Back" to.
     */
    initialConnectURL?: string;

    /** The list of services available for connection. */
    services: ConnectServiceInfo[];
}


/**
 * A section of services shown in the picker.
 *
 * Version Added:
 *     9.0
 */
interface SectionInfo {
    /** The section ID, matching the values in ConnectServiceInfo.sections. */
    id: string;

    /** The localized label for the section. */
    label: string;
}


/**
 * The placeholder used in the connect URL template.
 *
 * Version Added:
 *     9.0
 */
const SERVICE_ID_PLACEHOLDER = '__SERVICE_ID__';


/**
 * Wizard for connecting a hosting service.
 *
 * This presents a searchable list of services grouped into sections. Once a
 * service is chosen, the service-specific connect UI is loaded from the
 * server and shown. Submitting that form creates the hosting service account.
 *
 * Version Added:
 *     9.0
 */
@spina
export class ConnectServiceWizardView extends DialogView<
    BaseModel,
    ConnectServiceWizardViewOptions
> {
    static className = 'ink-c-dialog rb-c-connect-wizard';
    static title = _`Connect a Service`;

    /** The ordered list of sections to show in the picker. */
    static SECTIONS: SectionInfo[] = [
        { id: 'popular', label: _`Popular` },
        { id: 'source_hosting', label: _`Source Hosting` },
        { id: 'issue_tracking', label: _`Issue Tracking` },
    ];

    /**********************
     * Instance variables *
     **********************/

    #bodyEl: HTMLElement;

    /** The element containing the wizard's step content. */
    #$body: JQuery<HTMLDivElement>;

    /**
     * The "Back" action in the footer.
     *
     * This is hidden on the service picker and shown on later steps.
     */
    #backButton: ButtonView;

    /**
     * The close action in the footer.
     *
     * This closes the dialog. Its label defaults to "Cancel", but a step can
     * relabel it (for example, to "Skip") by marking content with
     * ``data-wizard-cancel-label``.
     */
    #cancelButton: ButtonView;

    /**
     * The primary action in the footer.
     *
     * Each step that has a form to submit configures this button with its
     * own label, optional icon, and click handler. It is hidden on steps
     * that have no such action (such as the service picker).
     */
    #actionButton: ButtonView;

    /**
     * The handler to run when the primary action button is clicked.
     *
     * This is set by the current step and is ``null`` when no action is
     * available.
     */
    #currentAction: (() => void) | null = null;

    /**
     * A stack of actions that return to the previous step.
     *
     * Each navigation pushes an action that restores the prior view. The
     * "Back" button pops and runs the top action. It is shown only while the
     * stack is non-empty.
     */
    #backStack: (() => void)[] = [];

    /**
     * The options passed to the view.
     *
     * This is captured during the initial render, since Ink discards
     * ``initialComponentState`` once rendering completes.
     */
    #options: Partial<ConnectServiceWizardViewOptions>;

    /**
     * The URL of the connect page currently shown.
     *
     * Connect forms are submitted back to this URL, so that any error
     * re-render returns the same page.
     */
    #currentConnectURL: string;

    /**
     * The service currently being connected.
     *
     * This is set once a service is chosen and is used for the dialog title.
     * It is ``null`` while on the service picker.
     */
    #currentService: ConnectServiceInfo | null = null;

    /**
     * A title supplied by the current step.
     *
     * A connect page can override the dialog title and icon by marking
     * content with ``data-wizard-title`` and ``data-wizard-title-icon``. This
     * is used by deep-linked steps that are not reached through the picker,
     * where there is no selected service to derive the title from.
     */
    #titleOverride: ({
        /** The icon URL to show, if any. */
        icon: string | null;

        /** The title label to show. */
        label: string;
    } | null) = null;

    /**
     * Render the body for the dialog.
     *
     * Returns:
     *     ComponentChild:
     *     The element to add for the body.
     */
    protected renderBody(): ComponentChild {
        this.#options = this.initialComponentState.options;

        this.#$body = $('<div class="rb-c-connect-wizard__body">');
        this.#bodyEl = this.#$body[0];

        if (this.#options.initialConnectURL) {
            /*
             * Open directly at a specific connect page. There is no picker to
             * return to, so the back stack stays empty.
             */
            this.#loadConnectPage(this.#options.initialConnectURL);
        } else {
            this.#renderServicePicker();
        }

        return this.#$body[0];
    }

    /**
     * Render the primary actions.
     *
     * Returns:
     *     ComponentChild:
     *     The element to add for the primary actions.
     */
    protected renderPrimaryActions(): ComponentChild | ComponentChild[] {
        const cancelButton = craft<ButtonView>`
            <Ink.DialogAction action="close">
             ${_`Cancel`}
            </Ink.DialogAction>
        `;
        this.#cancelButton = cancelButton;

        this.#actionButton = craft<ButtonView>`
            <Ink.DialogAction type="primary"
                              callback=${() => this.#currentAction?.()}>
            </Ink.DialogAction>
        `;
        this.#actionButton.el.style.display = 'none';

        return [
            cancelButton,
            this.#actionButton,
        ];
    }

    /**
     * Render the secondary actions.
     *
     * This provides the "Back" action, which is hidden until the connect
     * step is shown.
     *
     * Returns:
     *     ComponentChild:
     *     The element to add for the secondary actions.
     */
    protected renderSecondaryActions(): ComponentChild | ComponentChild[] {
        this.#backButton = craft<ButtonView>`
            <Ink.Button onClick=${() => this.#goBack()}>
             ${_`Back`}
            </Ink.Button>
        `;
        this.#backButton.$el.hide();

        return this.#backButton;
    }

    /**
     * Push an action that returns to the current view.
     *
     * This is called before navigating to a new step, so that "Back" can
     * restore the prior view.
     *
     * Args:
     *     fn (function):
     *         The action that restores the prior view.
     */
    #pushBack(fn: () => void) {
        this.#backStack.push(fn);
        this.#updateBackVisibility();
    }

    /**
     * Return to the previous step.
     */
    #goBack() {
        const fn = this.#backStack.pop();

        if (fn) {
            fn();
        }

        this.#updateBackVisibility();
    }

    /**
     * Update whether the "Back" button is shown.
     *
     * It is shown only while there is somewhere to go back to.
     */
    #updateBackVisibility() {
        if (this.#backButton) {
            this.#backButton.$el.toggle(this.#backStack.length > 0);
        }
    }

    /**
     * Configure the footer's primary action button.
     *
     * Passing an action shows the button with the given label, optional
     * icon, and click handler. Passing ``null`` hides the button.
     *
     * Args:
     *     action (object):
     *         The action to show, or ``null`` to hide the button.
     */
    #setAction(
        action: {
            /** The label to show on the button. */
            label: string;

            /** The name of the icon to show, if any. */
            iconName?: string;

            /** The handler to run when the button is clicked. */
            onClick: () => void;
        } | null,
    ) {
        const button = this.#actionButton;

        if (!button) {
            return;
        }

        if (action) {
            this.#currentAction = action.onClick;
            button.label = action.label;
            button.iconName = action.iconName ?? null;
            button.$el.show();
        } else {
            this.#currentAction = null;
            button.$el.hide();
        }
    }

    /**
     * Render the service picker (step 1).
     *
     * This shows a search field followed by the services grouped into
     * sections.
     */
    #renderServicePicker() {
        const services = this.#options.services;
        const $body = this.#$body;

        /* The picker is the root view, so there is nowhere to go back to. */
        this.#backStack = [];
        this.#currentService = null;
        this.#updateTitle();

        $body.empty();

        const searchEl = paint<HTMLInputElement>`
            <input class="rb-c-search-field__input rb-c-connect-wizard__search"
                   aria-label="${_`Search services`}"
                   placeholder="${_`Search services`}"
                   type="search"
                   />
        `;
        searchEl.addEventListener(
            'input', () => this.#filterServices(searchEl.value));
        $body.append(paint`
            <div class="rb-c-search-field rb-c-connect-wizard__search-field">
             <span class="ink-i-search" aria-hidden="true"></span>
             ${searchEl}
            </div>
        `);

        const $sections = $('<div class="rb-c-connect-wizard__sections">');

        for (const section of ConnectServiceWizardView.SECTIONS) {
            const sectionServices = services
                .filter(service => service.sections.includes(section.id))
                .sort((a, b) => a.name.localeCompare(b.name));

            if (sectionServices.length === 0) {
                continue;
            }

            const $section = $(dedent`
                <section class="rb-c-connect-wizard__section">
                 <h3 class="rb-c-connect-wizard__section-title"></h3>
                 <ul class="rb-c-connect-wizard__options"></ul>
                </section>
            `);
            $section.find('.rb-c-connect-wizard__section-title')
                .text(section.label);

            const $list = $section.find('.rb-c-connect-wizard__options');

            for (const service of sectionServices) {
                $list.append(this.#buildServiceOption(service));
            }

            $sections.append($section);
        }

        $body.append($sections);
        searchEl.focus();

        this.#updateBackVisibility();
        this.#setAction(null);

        if (this.#cancelButton) {
            this.#cancelButton.label = _`Cancel`;
        }
    }

    /**
     * Build a clickable option for a service.
     *
     * Args:
     *     service (ConnectServiceInfo):
     *         The service to build a option for.
     *
     * Returns:
     *     HTMLElement:
     *     The option element.
     */
    #buildServiceOption(
        service: ConnectServiceInfo,
    ): HTMLElement {
        const logoEl = (
            service.logo
            ? paint`<img src=${service.logo} aria-hidden="true" />`
            : null
        );

        const linkEl = paint<HTMLAnchorElement>`
            <a href="#">
             ${logoEl}
             <h2>${service.name}</h2>
            </a>
        `;
        linkEl.addEventListener('click', e => {
            e.preventDefault();
            this.#selectService(service);
        });

        return paint<HTMLElement>`
            <li data-service-name="${service.name.toLowerCase()}">
             ${linkEl}
            </li>
        `;
    }

    /**
     * Filter the visible services by a search query.
     *
     * Args:
     *     query (string):
     *         The search query.
     */
    #filterServices(query: string) {
        const normalized = query.trim().toLowerCase();
        const $body = this.#$body;

        for (const el of $body.find('.rb-c-connect-wizard__options li')) {
            const name = el.getAttribute('data-service-name') || '';

            $(el).toggle(!normalized || name.includes(normalized));
        }

        /* Hide sections that have no visible services. */
        for (const sectionEl of $body.find('.rb-c-connect-wizard__section')) {
            const $section = $(sectionEl);
            const hasVisible = $section
                .find('.rb-c-connect-wizard__options li')
                .toArray()
                .some(el => el.style.display !== 'none');

            $section.toggle(hasVisible);
        }
    }

    /**
     * Select a service and load its connect page.
     *
     * Args:
     *     service (ConnectServiceInfo):
     *         The selected service.
     */
    async #selectService(service: ConnectServiceInfo) {
        const url = this.#options.connectURLTemplate
            .replace(SERVICE_ID_PLACEHOLDER, encodeURIComponent(service.id));

        this.#currentService = service;
        this.#updateTitle();

        this.#pushBack(() => this.#renderServicePicker());
        await this.#loadConnectPage(url);
    }

    /**
     * Render the dialog title.
     *
     * Returns:
     *     ComponentChild:
     *     The element to add for the title.
     */
    protected renderTitle(): ComponentChild {
        return this.#renderTitleContent();
    }

    /**
     * Update the dialog title for the current step.
     *
     * On the service picker the default title is shown. Once a service is
     * chosen, the title shows the service's icon and name.
     */
    #updateTitle() {
        const $title = this.$el.find('.ink-c-dialog__title');

        if ($title.length === 0) {
            /* The dialog has not been rendered into the DOM yet. */
            return;
        }

        $title.empty().append(this.#renderTitleContent());
    }

    /**
     * Render the contents of the dialog title.
     *
     * On the service picker this is the default label. Once a service is
     * chosen, it pairs the service's icon with a "Connect to <X>" label.
     *
     * Returns:
     *     HTMLElement:
     *     The title contents.
     */
    #renderTitleContent(): HTMLElement {
        const titleOverride = this.#titleOverride;

        if (titleOverride !== null) {
            return this.#renderTitleParts(titleOverride.label, titleOverride.icon);
        }

        const service = this.#currentService;

        if (service === null) {
            return paint`
                <span class="rb-c-connect-wizard__title">
                 ${ConnectServiceWizardView.title}
                </span>
            `;
        }

        return this.#renderTitleParts(
            _`Connect to ${service.name}`, service.logo);
    }

    /**
     * Render a title pairing an optional icon with a label.
     *
     * Args:
     *     label (string):
     *         The title label to show.
     *
     *     icon (string):
     *         The icon URL to show, or ``null`` for no icon.
     *
     * Returns:
     *     HTMLElement:
     *     The title contents.
     */
    #renderTitleParts(
        label: string,
        icon: string | null,
    ): HTMLElement {
        return paint`
            <span class="rb-c-connect-wizard__title">
            ${icon
              ? paint`<img class="rb-c-connect-wizard__title-icon"
                           src=${icon} aria-hidden="true" />`
              : null}
             <span>${label}</span>
            </span>
        `;
    }

    /**
     * Load and show a connect page.
     *
     * The page is fetched from the server and shown in place of the current
     * step. The URL is remembered so the form (if any) submits back to it.
     *
     * Args:
     *     url (string):
     *         The URL of the connect page to load.
     */
    async #loadConnectPage(url: string) {
        this.#currentConnectURL = url;

        this.#setAction(null);

        $(this.#bodyEl)
            .empty()
            .append($('<div class="rb-c-connect-wizard__loading">')
                .text(_`Loading…`));

        try {
            const response = await fetch(url, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });

            if (response.ok) {
                this.#showConnectUI(await response.text());
            } else {
                this.#showLoadError();
            }
        } catch (err) {
            this.#showLoadError();
        }
    }

    /**
     * Show a connect page's HTML.
     *
     * Args:
     *     html (string):
     *         The rendered connect page fragment.
     */
    #showConnectUI(html: string) {
        const $body = $(this.#bodyEl).empty();

        const $content = $('<div class="rb-c-connect-wizard__connect">')
            .html(html)
            .appendTo($body);

        this.#bindConnectContent($content);
        this.#focusConnectContent($content);
    }

    /**
     * Move focus to the start of a loaded connect page.
     *
     * Focus is placed on the content container itself rather than on a
     * specific field, so that the first Tab moves into the content instead of
     * starting on a particular field or on a footer action such as the close
     * button.
     *
     * The container is made focusable with ``tabindex="-1"`` for this, without
     * becoming a tab stop of its own. Its focus outline is suppressed, since
     * it is only an anchor for Tab entry; the interactive controls inside keep
     * their own focus indicators.
     *
     * The service picker focuses its search field through its own path, so it
     * does not go through here.
     *
     * Args:
     *     $content (jQuery):
     *         The element containing the connect UI.
     */
    #focusConnectContent($content: JQuery) {
        $content
            .attr('tabindex', '-1')
            .css('outline', 'none');
        $content[0].focus({ preventScroll: true });
    }

    /**
     * Bind interactive behavior to a loaded connect page.
     *
     * Args:
     *     $content (jQuery):
     *         The element containing the connect UI.
     */
    #bindConnectContent($content: JQuery) {
        this.#updateTitleFromContent($content);
        this.#updateCancelLabel($content);
        this.#bindConnectPageLinks($content);
        this.#bindStepAction($content);
    }

    /**
     * Update the dialog title from a loaded connect page.
     *
     * A step can set the title and icon by marking any element with
     * ``data-wizard-title`` (and optionally ``data-wizard-title-icon``). When
     * no such element is present, the title falls back to the selected service
     * or the default.
     *
     * Args:
     *     $content (jQuery):
     *         The element containing the connect UI.
     */
    #updateTitleFromContent($content: JQuery) {
        const titleEl = $content.find('[data-wizard-title]')[0];

        if (titleEl) {
            this.#titleOverride = {
                icon: titleEl.dataset.wizardTitleIcon || null,
                label: titleEl.dataset.wizardTitle || '',
            };
        } else {
            this.#titleOverride = null;
        }

        this.#updateTitle();
    }

    /**
     * Update the label of the close button for a loaded connect page.
     *
     * A step can relabel the close button by marking any element with
     * ``data-wizard-cancel-label`` (such as a "Skip" label on an optional
     * step). When no such label is present, the default "Cancel" is restored.
     *
     * Args:
     *     $content (jQuery):
     *         The element containing the connect UI.
     */
    #updateCancelLabel($content: JQuery) {
        const button = this.#cancelButton;

        if (!button) {
            return;
        }

        button.label = $content.find('[data-wizard-cancel-label]')
            .attr('data-wizard-cancel-label') || _`Cancel`;
    }

    /**
     * Bind links that navigate to another connect page.
     *
     * A link with a ``data-connect-page`` attribute loads its ``href`` as a
     * new connect page within the wizard, pushing a "Back" action that
     * returns to the current page.
     *
     * Args:
     *     $content (jQuery):
     *         The element containing the connect UI.
     */
    #bindConnectPageLinks($content: JQuery) {
        $content.find('a[data-connect-page]').on('click', e => {
            e.preventDefault();

            const url = (e.currentTarget as HTMLAnchorElement).href;
            const previousURL = this.#currentConnectURL;

            this.#pushBack(() => this.#loadConnectPage(previousURL));
            this.#loadConnectPage(url);
        });
    }

    /**
     * Configure the footer action for the current connect page.
     *
     * The connect page may carry a form to submit. An AJAX connect form
     * (marked with ``data-service-id``) is submitted in place. Any other
     * form marked with ``data-wizard-action-label`` is submitted natively,
     * which may navigate away from Review Board. The footer action button is
     * configured to match, or hidden when there is no such form.
     *
     * Args:
     *     $content (jQuery):
     *         The element containing the connect UI.
     */
    #bindStepAction($content: JQuery) {
        const $connectForm = $content.find('form[data-service-id]');

        if ($connectForm.length > 0) {
            $connectForm.on('submit', (e: JQuery.SubmitEvent) => {
                e.preventDefault();
                this.#submitConnectForm($connectForm);
            });

            this.#setAction({
                label: $connectForm.attr('data-wizard-action-label') ||
                       _`Connect`,
                iconName: $connectForm.attr('data-wizard-action-icon') ||
                          undefined,
                onClick: () => this.#submitConnectForm($connectForm),
            });

            return;
        }

        const $actionForm = $content.find('form[data-wizard-action-label]');

        if ($actionForm.length > 0) {
            const formEl = $actionForm[0] as HTMLFormElement;

            this.#setAction({
                label: $actionForm.attr('data-wizard-action-label'),
                iconName: $actionForm.attr('data-wizard-action-icon') ||
                          undefined,
                onClick: () => formEl.submit(),
            });

            return;
        }

        this.#setAction(null);
    }

    /**
     * Submit the connect form to the server.
     *
     * On success, the page is redirected to the connected services list. On
     * failure, the form is replaced with the re-rendered fragment showing the
     * errors.
     *
     * Args:
     *     $form (jQuery):
     *         The connect form being submitted.
     */
    async #submitConnectForm($form: JQuery) {
        try {
            const response = await fetch(this.#currentConnectURL, {
                body: new FormData($form[0] as HTMLFormElement),
                headers: {
                    'X-CSRFToken': this.#options.csrfToken,
                    'X-Requested-With': 'XMLHttpRequest',
                },
                method: 'POST',
            });

            if (response.ok) {
                const rsp = await response.json();

                if (rsp.success) {
                    window.location.href = rsp.redirect;
                } else {
                    const $content = $(this.#bodyEl)
                        .find('.rb-c-connect-wizard__connect')
                        .html(rsp.html);
                    this.#bindConnectContent($content);
                }
            } else {
                this.#showLoadError();
            }
        } catch (err) {
            this.#showLoadError();
        }
    }

    /**
     * Show a generic error when loading or submitting fails.
     */
    #showLoadError() {
        this.#setAction(null);

        $(this.#bodyEl)
            .empty()
            .append($('<div class="ink-c-alert -is-error" role="alert">')
                .append($('<div class="ink-c-alert__content">')
                    .text(_`
                        Something went wrong. Please try again.
                    `)));
    }
}
