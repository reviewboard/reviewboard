import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    expect,
    it,
} from 'jasmine-core';

import {
    type RepositoryFormHostingAccount,
    type RepositoryFormPlan,
    GitHubRepositoryFormView,
    RepositoryForm,
} from 'reviewboard/admin';


suite('rb/admin/views/GitHubRepositoryFormView', function() {
    const plans: RepositoryFormPlan[] = [
        {id: 'public', label: 'Public'},
        {id: 'private', label: 'Private'},
        {id: 'app', label: 'GitHub App'},
    ];
    const patAccount: RepositoryFormHostingAccount = {
        hosting_url: null,
        is_authorized: true,
        pk: 1,
        username: 'myuser',
    };
    const appAccount: RepositoryFormHostingAccount = {
        hosting_url: null,
        is_authorized: true,
        pk: 2,
        username: 'myorg',
    };

    let view: GitHubRepositoryFormView;

    beforeEach(function() {
        view = new GitHubRepositoryFormView({
            data: {
                accountLabels: {
                    '1': 'myuser (PAT)',
                    '2': 'myorg',
                },
                appAccountIDs: [2],
            },
            model: new RepositoryForm(),
        });
    });

    it('getAccountLabel', function() {
        expect(view.getAccountLabel(patAccount)).toBe('myuser (PAT)');
        expect(view.getAccountLabel(appAccount)).toBe('myorg');
        expect(view.getAccountLabel({
            hosting_url: null,
            is_authorized: true,
            pk: 3,
            username: 'unlisted',
        })).toBe('unlisted');
    });

    it('getRepositoryPlans with an app installation', function() {
        expect(view.getRepositoryPlans(plans, appAccount).map(p => p.id))
            .toEqual(['app']);
    });

    it('getRepositoryPlans with a Personal Access Token', function() {
        expect(view.getRepositoryPlans(plans, patAccount).map(p => p.id))
            .toEqual(['public', 'private']);
    });

    it('getRepositoryPlans when linking a new account', function() {
        expect(view.getRepositoryPlans(plans, null).map(p => p.id))
            .toEqual(['public', 'private']);
    });
});
