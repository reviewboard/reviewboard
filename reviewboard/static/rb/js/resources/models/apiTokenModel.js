RB.APIToken = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            tokenValue: null,
            note: null,
            policy: {},
            userName: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'api_token',

    url: function() {
        var url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                  'api/users/' + this.get('userName') + '/api-tokens/';

        if (!this.isNew()) {
            url += this.id + '/';
        }

        return url;
    },

    toJSON: function() {
        return {
            note: this.get('note'),
            policy: JSON.stringify(this.get('policy'))
        };
    },

    parseResourceData: function(rsp) {
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
