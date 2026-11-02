import { suite } from '@beanbag/jasmine-suites';
import { spina } from '@beanbag/spina';
import { dedent } from 'babel-plugin-dedent';
import {
    afterEach,
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    type RepositoryFormHostingAccount,
    type RepositoryFormHostingServiceInfo,
    type RepositoryFormPlan,
    type RepositoryFormViewOptions,
    HostingServiceRepositoryFormView,
    RepositoryForm,
    RepositoryFormView,
    SCMToolRepositoryFormView,
} from 'reviewboard/admin';


suite('rb/admin/views/RepositoryFormView', () => {
    const template = dedent`
        <form id="repository_form">
         <fieldset>
          <div class="form-row" id="row-hosting_type">
           <select id="id_hosting_type">
            <option value="custom">(None)</option>
            <option value="github">GitHub</option>
            <option value="gitlab">GitLab</option>
            <option value="fakesvc">Fake</option>
           </select>
          </div>
          <div class="form-row" id="row-hosting_account">
           <select id="id_hosting_account">
            <option value="">Link new account</option>
           </select>
           <a href="#" id="repo-edit-hosting-credentials">
            <span id="repo-edit-hosting-credentials-label"></span>
           </a>
          </div>
          <input type="hidden" id="id_force_authorize" value="false">
          <div class="hosting-auth-form" id="hosting-auth-form-github">
           <div class="form-row" id="row-2fa">
            <input data-required-for-2fa>
           </div>
          </div>
          <div class="hosting-auth-form" id="hosting-auth-form-gitlab">
          </div>
         </fieldset>
         <fieldset>
          <div class="form-row" id="row-tool">
           <select id="id_tool">
            <option value="git">Git</option>
            <option value="svn">Subversion</option>
            <option value="fake">FakeSCM</option>
           </select>
          </div>
          <div class="form-row" id="row-repository_plan">
           <select id="id_repository_plan"></select>
          </div>
          <div class="hosting-repo-form" id="repo-form-hosting-github-public">
          </div>
          <div class="hosting-repo-form" id="repo-form-hosting-github-private">
          </div>
          <div class="hosting-repo-form" id="repo-form-hosting-gitlab-default">
          </div>
          <div class="scmtool-repo-form" id="repo-form-scm-git"></div>
          <div class="scmtool-auth-form" id="auth-form-scm-git"></div>
          <div class="scmtool-repo-form" id="repo-form-scm-svn"></div>
          <div class="scmtool-auth-form" id="auth-form-scm-svn"></div>
         </fieldset>
         <fieldset>
          <div class="form-row" id="row-associate_ssh_key">
           <input type="checkbox" id="id_associate_ssh_key">
          </div>
         </fieldset>
         <fieldset>
          <input type="checkbox" id="id_public" checked>
          <div class="form-row" id="row-users"></div>
          <div class="form-row" id="row-review_groups"></div>
         </fieldset>
         <input type="submit">
        </form>
    `;

    let $form: JQuery;
    let hostingServices: Record<string, RepositoryFormHostingServiceInfo>;
    let view: RepositoryFormView | null;

    function createView(options: RepositoryFormViewOptions = {}) {
        view = new RepositoryFormView({
            ...options,
            el: $form[0] as HTMLFormElement,
            model: new RepositoryForm({
                hostingServices: hostingServices,
                tools: {
                    fake: {
                        fake: true,
                        name: 'FakeSCM',
                    },
                    git: {name: 'Git'},
                    svn: {name: 'Subversion'},
                },
            }),
        });
        view.render();
    }

    function selectField(
        id: string,
        value: string,
    ) {
        $form.find(id).val(value).trigger('change');
    }

    function optionLabels(
        id: string,
    ): string[] {
        return $form.find(`${id} option`).toArray()
            .map(el => el.textContent);
    }

    function isShown(
        selector: string,
    ): boolean {
        return $form.find(selector).is(':visible');
    }

    beforeEach(() => {
        $form = $(template).appendTo(document.body);

        hostingServices = {
            fakesvc: {
                accounts: [],
                fake: true,
                js_view_data: {},
                needs_two_factor_auth_code: false,
                plans: [],
                scmtools: [],
                supports_ssh_key_association: false,
            },
            github: {
                accounts: [
                    {
                        hosting_url: null,
                        is_authorized: true,
                        pk: 1,
                        username: 'octocat',
                    },
                    {
                        hosting_url: null,
                        is_authorized: false,
                        pk: 2,
                        username: 'hubot',
                    },
                ],
                js_view_data: {},
                needs_two_factor_auth_code: false,
                plans: [
                    {id: 'public', label: 'Public'},
                    {id: 'private', label: 'Private'},
                ],
                scmtools: ['git'],
                supports_ssh_key_association: true,
            },
            gitlab: {
                accounts: [
                    {
                        hosting_url: 'https://gitlab.example.com',
                        is_authorized: true,
                        pk: 3,
                        username: 'tanuki',
                    },
                ],
                js_view_data: {},
                needs_two_factor_auth_code: false,
                plans: [],
                scmtools: ['Git'],
                supports_ssh_key_association: false,
            },
        };
    });

    afterEach(() => {
        if (view) {
            view.remove();
            view = null;
        }

        $form.remove();
    });

    describe('No hosting service', () => {
        it('Shows all SCMTools and their forms', () => {
            createView();

            expect($form.find('#id_tool option').length).toBe(3);
            expect(isShown('#row-hosting_account')).toBe(false);
            expect(isShown('#row-repository_plan')).toBe(false);
            expect(isShown('#repo-form-scm-git')).toBe(true);
            expect(isShown('#auth-form-scm-git')).toBe(true);
            expect(isShown('#repo-form-scm-svn')).toBe(false);
            expect(isShown('.hosting-repo-form')).toBe(false);
            expect(isShown('.hosting-auth-form')).toBe(false);
            expect(isShown('#row-associate_ssh_key')).toBe(false);
        });

        it('Switching SCMTools', () => {
            createView();
            selectField('#id_tool', 'svn');

            expect(view.model.get('tool')).toBe('svn');
            expect(isShown('#repo-form-scm-git')).toBe(false);
            expect(isShown('#repo-form-scm-svn')).toBe(true);
            expect(isShown('#auth-form-scm-svn')).toBe(true);
        });

        it('With an SCMTool that is not installed', () => {
            createView();
            selectField('#id_tool', 'fake');

            const $advert = $form.find('#row-tool')
                .closest('fieldset')
                .children('.powerpack-advert');

            expect($advert.is(':visible')).toBe(true);
            expect($advert.text()).toContain('FakeSCM');
            expect(isShown('.scmtool-repo-form')).toBe(false);
            expect($form.find('input[type="submit"]').prop('disabled'))
                .toBe(true);
        });
    });

    describe('Hosting service', () => {
        it('Filters SCMTools by ID', () => {
            $form.find('#id_hosting_type').val('github');
            createView();

            expect(optionLabels('#id_tool'))
                .toEqual(['Git']);
            expect(isShown('.scmtool-repo-form')).toBe(false);
        });

        it('Filters SCMTools by name', () => {
            $form.find('#id_hosting_type').val('gitlab');
            createView();

            expect(optionLabels('#id_tool'))
                .toEqual(['Git']);
        });

        it('Lists and selects accounts', () => {
            $form.find('#id_hosting_type').val('github');
            createView();

            expect(optionLabels('#id_hosting_account'))
                .toEqual(['Link new account', 'octocat', 'hubot']);
            expect($form.find('#id_hosting_account').val()).toBe('1');
            expect(view.model.get('hostingAccountID')).toBe(1);
        });

        it('Includes the hosting URL in account labels', () => {
            $form.find('#id_hosting_type').val('gitlab');
            createView();

            expect($form.find('#id_hosting_account option:last').text())
                .toBe('tanuki (https://gitlab.example.com)');
        });

        it('Keeps the account empty when a 2FA code is needed', () => {
            hostingServices.github.needs_two_factor_auth_code = true;
            $form.find('#id_hosting_type').val('github');
            createView();

            expect($form.find('#id_hosting_account').val()).toBe('');
            expect(isShown('#hosting-auth-form-github')).toBe(true);
            expect(isShown('#row-2fa')).toBe(true);
        });

        it('Shows plans and the selected plan form', () => {
            $form.find('#id_hosting_type').val('github');
            createView();

            expect(isShown('#row-repository_plan')).toBe(true);
            expect($form.find('#id_repository_plan option').length).toBe(2);
            expect(isShown('#repo-form-hosting-github-public')).toBe(true);

            selectField('#id_repository_plan', 'private');

            expect(isShown('#repo-form-hosting-github-public')).toBe(false);
            expect(isShown('#repo-form-hosting-github-private')).toBe(true);
        });

        it('Hides plans for services without plans', () => {
            $form.find('#id_hosting_type').val('gitlab');
            createView();

            expect(isShown('#row-repository_plan')).toBe(false);
            expect(isShown('#repo-form-hosting-gitlab-default')).toBe(true);
        });

        it('Shows SSH key association when supported', () => {
            $form.find('#id_hosting_type').val('github');
            createView();

            expect(isShown('#row-associate_ssh_key')).toBe(true);

            selectField('#id_hosting_type', 'gitlab');

            expect(isShown('#row-associate_ssh_key')).toBe(false);
            expect($form.find('#id_associate_ssh_key').prop('disabled'))
                .toBe(true);
        });

        it('Switching services', () => {
            $form.find('#id_hosting_type').val('github');
            createView();
            selectField('#id_hosting_type', 'gitlab');

            expect(view.model.get('hostingType')).toBe('gitlab');
            expect(view.model.get('hostingAccountID')).toBe(3);
            expect(isShown('#repo-form-hosting-github-public')).toBe(false);
            expect(isShown('#repo-form-hosting-gitlab-default')).toBe(true);
        });

        it('With a service that is not installed', () => {
            createView();
            selectField('#id_hosting_type', 'fakesvc');

            const $advert = $form.find('#row-hosting_type')
                .closest('fieldset')
                .children('.powerpack-advert');

            expect($advert.is(':visible')).toBe(true);
            expect($advert.text()).toContain('Fake');
            expect(isShown('#row-hosting_account')).toBe(false);
            expect(isShown('#row-tool')).toBe(false);
            expect($form.find('input[type="submit"]').prop('disabled'))
                .toBe(true);
        });

        it('With Gerrit', () => {
            hostingServices['gerrit'] = hostingServices.gitlab;
            $form.find('#id_hosting_type')
                .append('<option value="gerrit">Gerrit</option>')
                .val('gerrit');
            createView();

            expect(isShown('.gerrit-plugin-advert')).toBe(true);
        });
    });

    describe('Hosting accounts', () => {
        beforeEach(() => {
            $form.find('#id_hosting_type').val('github');
        });

        it('Authorized account', () => {
            createView();

            expect(isShown('#hosting-auth-form-github')).toBe(false);
            expect(isShown('#repo-edit-hosting-credentials')).toBe(true);
            expect(isShown('.errornote')).toBe(false);
        });

        it('Account needing re-authorization', () => {
            createView();
            selectField('#id_hosting_account', '2');

            expect(isShown('#hosting-auth-form-github')).toBe(true);
            expect(isShown('#repo-edit-hosting-credentials')).toBe(false);
            expect(isShown('.errornote')).toBe(true);
        });

        it('Linking a new account', () => {
            createView();
            selectField('#id_hosting_account', '');

            expect(view.model.get('hostingAccountID')).toBe(null);
            expect(isShown('#hosting-auth-form-github')).toBe(true);
            expect(isShown('#row-2fa')).toBe(false);
            expect(isShown('.errornote')).toBe(false);
        });

        it('Editing credentials', () => {
            createView();

            const $link = $form.find('#repo-edit-hosting-credentials');

            $link.trigger('click');

            expect(isShown('#hosting-auth-form-github')).toBe(true);
            expect($form.find('#id_force_authorize').val()).toBe('true');
            expect($link.text().trim()).toBe('Cancel editing credentials');

            $link.trigger('click');

            expect(isShown('#hosting-auth-form-github')).toBe(false);
            expect($form.find('#id_force_authorize').val()).toBe('false');
            expect($link.text().trim()).toBe('Edit credentials');
        });
    });

    describe('Hosting service views', () => {
        /* Offers only private plans to the unauthorized account. */
        @spina
        class TestHostingServiceView extends HostingServiceRepositoryFormView {
            getAccountLabel(account: RepositoryFormHostingAccount): string {
                return `${this.data['prefix']}${account.username}`;
            }

            getRepositoryPlans(
                plans: RepositoryFormPlan[],
                account: RepositoryFormHostingAccount | null,
            ): RepositoryFormPlan[] {
                if (account !== null && !account.is_authorized) {
                    return plans.filter(plan => plan.id === 'private');
                }

                return plans;
            }
        }

        beforeEach(() => {
            hostingServices.github.js_view_data = {prefix: '@'};
            $form.find('#id_hosting_type').val('github');
        });

        it('Uses the hosting service view for account labels', () => {
            createView({
                hostingServiceViews: {github: TestHostingServiceView},
            });

            expect(optionLabels('#id_hosting_account'))
                .toEqual(['Link new account', '@octocat', '@hubot']);
        });

        it('Rebuilds plans when the account changes', () => {
            createView({
                hostingServiceViews: {github: TestHostingServiceView},
            });

            expect(optionLabels('#id_repository_plan'))
                .toEqual(['Public', 'Private']);
            expect(isShown('#row-repository_plan')).toBe(true);

            selectField('#id_hosting_account', '2');

            expect(optionLabels('#id_repository_plan')).toEqual(['Private']);
            expect(view.model.get('repositoryPlan')).toBe('private');
            expect(isShown('#row-repository_plan')).toBe(false);
            expect(isShown('#repo-form-hosting-github-public')).toBe(false);
            expect(isShown('#repo-form-hosting-github-private')).toBe(true);
        });

        it('Removes the view when switching services', () => {
            spyOn(TestHostingServiceView.prototype, 'getAccountLabel')
                .and.callThrough();

            createView({
                hostingServiceViews: {github: TestHostingServiceView},
            });
            selectField('#id_hosting_type', 'gitlab');

            expect(TestHostingServiceView.prototype.getAccountLabel)
                .toHaveBeenCalledTimes(2);
            expect(optionLabels('#id_hosting_account'))
                .toEqual(['Link new account',
                          'tanuki (https://gitlab.example.com)']);
            expect($.contains(document.body, $form[0])).toBe(true);
        });
    });

    describe('SCMTool views', () => {
        it('Creates a view for the selected SCMTool', () => {
            const renderSpy = spyOn(SCMToolRepositoryFormView.prototype,
                                    'render').and.callThrough();
            const removeSpy = spyOn(SCMToolRepositoryFormView.prototype,
                                    'remove').and.callThrough();

            createView();

            expect(renderSpy).toHaveBeenCalledTimes(1);
            expect(removeSpy).not.toHaveBeenCalled();

            selectField('#id_hosting_type', 'github');

            expect(removeSpy).toHaveBeenCalledTimes(1);
            expect(renderSpy).toHaveBeenCalledTimes(1);
            expect($.contains(document.body, $form[0])).toBe(true);
        });
    });

    it('Public access', () => {
        createView();

        expect(isShown('#row-users')).toBe(false);
        expect(isShown('#row-review_groups')).toBe(false);

        $form.find('#id_public').prop('checked', false).trigger('change');

        expect(isShown('#row-users')).toBe(true);
        expect(isShown('#row-review_groups')).toBe(true);
    });
});
