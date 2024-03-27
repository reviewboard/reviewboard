/**
 * A view which gives the user hints about comments in other revisions.
 */

import {
    BaseView,
    type EventsHash,
    spina,
} from '@beanbag/spina';

import type { DiffCommentsHint } from '../models/diffCommentsHintModel';


/**
 * A view which gives the user hints about comments in other revisions.
 */
@spina
export class DiffCommentsHintView extends BaseView<DiffCommentsHint> {
    static modelEvents: EventsHash = {
        'change': 'render',
    };

    static template = _.template(dedent`
        <div class="box-container">
         <div class="box important">
          <div class="box-inner comments-hint">
           <h1><%- unpublishedCommentsHeader %></h1>
           <p><%- unpublishedCommentsText %></p>
           <ul>
           </ul>
          </div>
         </div>
        </div>
    `);

    /**
     * Render the view.
     */
    onRender() {
        const model = this.model;

        if (model.get('hasOtherComments')) {
            this.$el.html(DiffCommentsHintView.template({
                unpublishedCommentsHeader: _`
                    You have unpublished comments on other revisions.
                `,
                unpublishedCommentsText: _`
                    Your review consists of comments on the following
                    revisions:
                `,
            }));

            const $ul = this.$('ul');

            model.get('diffsetsWithComments').forEach(diffset => {
                const $li = $('<li>')
                    .addClass('revision')
                    .text(_`Revision ${diffset.revision}`)
                    .appendTo($ul);

                if (diffset.isCurrent) {
                    $li.addClass('current');
                } else {
                    $li.on('click', () => {
                        this.trigger('revisionSelected',
                                     [0, diffset.revision]);
                    });
                }
            });

            model.get('commitsWithComments').forEach(commit => {
                const $li = $('<li>')
                    .addClass('commit')
                    .appendTo($ul);

                if (commit.baseCommitID === null ||
                    commit.baseCommitID === commit.tipCommitID) {
                    $li.text(_`
                        Revision ${commit.revision},
                        commit ${commit.tipCommitID.substring(0, 8)}
                    `);
                } else {
                    $li.text(_`
                        Revision ${commit.revision},
                        commits ${commit.baseCommitID.substring(0, 8)} -
                        ${commit.tipCommitID.substring(0, 8)}
                    `);
                }

                if (commit.isCurrent) {
                    $li.addClass('current');
                } else {
                    $li.on('click', () => {
                        this.trigger('commitRangeSelected',
                                     commit.revision,
                                     commit.baseCommitPK,
                                     commit.tipCommitPK);
                    });
                }
            });

            model.get('interdiffsWithComments').forEach(interdiff => {
                const $li = $('<li>')
                    .addClass('interdiff')
                    .text(_`
                        Interdiff revision ${interdiff.oldRevision} -
                        ${interdiff.newRevision}
                    `)
                    .appendTo($ul);

                if (interdiff.isCurrent) {
                    $li.addClass('current');
                } else {
                    $li.on('click', () => {
                        this.trigger(
                            'revisionSelected',
                            [interdiff.oldRevision, interdiff.newRevision]);
                    });
                }
            });
        } else {
            this.$el.empty();
        }
    }
}
