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
            deprecated: false,
            expired: false,
            expires: null,
            invalidDate: null,
            invalidReason: null,
            lastUsed: null,
            note: null,
            policy: {},
            tokenValue: null,
            userName: null,
            valid: true,
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
            expires: this.get('expires'),
            note: this.get('note'),
            policy: JSON.stringify(this.get('policy')),
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
            deprecated: rsp.deprecated,
            expired: rsp.expired,
            expires: rsp.expires,
            invalidDate: rsp.invalid_date,
            invalidReason: rsp.invalid_reason,
            lastUsed: rsp.last_used,
            note: rsp.note,
            policy: rsp.policy,
            tokenValue: rsp.token,
            valid: rsp.valid,
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
