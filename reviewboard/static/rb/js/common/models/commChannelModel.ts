/**
 * Communication channel to sync between tabs/windows.
 *
 * Version Added:
 *     6.0
 */

import { BaseModel, spina } from '@beanbag/spina';


/**
 * A message to send on the channel.
 *
 * Version Added:
 *     6.0.
 */
interface Message {
    /** The event name. */
    event: string;

    /** Any data sent by the caller. */
    data?: unknown;
}


/**
 * Communication channel to sync between tabs/windows.
 *
 * Version Added:
 *     6.0
 */
@spina
export class ClientCommChannel extends BaseModel {
    static instance: ClientCommChannel = null;

    /**
     * Return the ClientCommChannel instance.
     *
     * Returns:
     *     ClientCommChannel:
     *     The singleton instance.
     */
    static getInstance(): ClientCommChannel {
        return this.instance;
    }

    /**********************
     * Instance variables *
     **********************/

    /** The broadcast channel instance. */
    #channel: BroadcastChannel;

    /**
     * Initialize the model.
     */
    initialize() {
        console.assert(ClientCommChannel.instance === null);

        this.#channel = new BroadcastChannel('reviewboard');

        this.#channel.addEventListener('message', (event: MessageEvent) => {
            const message = event.data as Message;

            switch (message.event) {
                case 'reload':
                    this._onReload(message);
                    break;

                default:
                    console.warn(
                        'Received unknown event from BroadcastChannel',
                        message);
                    break;
            }
        });

        ClientCommChannel.instance = this;
    }

    /**
     * Close the communication channel.
     */
    close() {
        this.#channel.close();

        console.assert(ClientCommChannel.instance === this);
        ClientCommChannel.instance = null;
    }

    /**
     * Send a reload signal to other tabs.
     */
    reload() {
        const page = RB.PageManager.getPage();
        const pageData = page.getReloadData();

        if (pageData === null) {
            console.warn(dedent`
                Ignoring page reload request: No page data to send over the
                broadcast channel. This would have affected all tabs without
                reload data!
            `);
        } else {
            this.#channel.postMessage({
                data: pageData,
                event: 'reload',
            });
        }
    }

    /**
     * Handle a reload message from another tab.
     *
     * Args:
     *     message (Message):
     *         The message from the other tab.
     */
    private _onReload(message: Message) {
        const page = RB.PageManager.getPage();

        if (page) {
            const pageData = page.getReloadData();

            if (pageData !== null && _.isEqual(message.data, pageData)) {
                this.trigger('reload');
            }
        }
    }
}
