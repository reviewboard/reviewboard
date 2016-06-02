/**
 * An API token.
 */
RB.APIToken = RB.BaseResource.extend({
    /**
     * Return defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     The default values for new model instances.
     */
    defaults() {
        return _.defaults({
            tokenValue: null,
            note: null,
            policy: {},
            userName: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'api_token',

    /**
     * Return the URL for syncing the model.
     *
     * Returns:
     *     string:
     *     The URL to use when making HTTP requests.
     */
    url() {
        const url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                    'api/users/' + this.get('userName') + '/api-tokens/';

        return this.isNew() ? url : `${url}${this.id}/`;
    },

    /**
     * Return a JSON-serializable representation of the model.
     *
     * Returns:
     *     object:
     *     An object suitable for passing into JSON.stringify.
     */
    toJSON() {
        return {
            note: this.get('note'),
            policy: JSON.stringify(this.get('policy'))
        };
    },

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *         The response from the server API endpoint.
     *
     * Returns:
     *     object:
     *     The parsed attribute values.
     */
    parseResourceData(rsp) {
        return {
            tokenValue: rsp.token,
            note: rsp.note,
            policy: rsp.policy
        };
    }
}, {
    defaultPolicies: {
        readWrite: {},
        readOnly: {
            resources: {
                '*': {
                    allow: ['GET', 'HEAD', 'OPTIONS'],
                    block: ['*']
                }
            }
        },
        custom: {
            resources: {
                '*': {
                    allow: ['*'],
                    block: []
                }
            }
        }
    }
});
