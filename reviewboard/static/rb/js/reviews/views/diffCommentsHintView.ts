/**
 * A view which gives the user hints about comments in other revisions.
 */

import { paint, renderInto } from '@beanbag/ink';
import {
    type EventsHash,
    BaseView,
    spina,
} from '@beanbag/spina';

import { type DiffCommentsHint } from '../models/diffCommentsHintModel';


/**
 * A view which gives the user hints about comments in other revisions.
 */
@spina
export class DiffCommentsHintView extends BaseView<DiffCommentsHint> {
    static modelEvents: EventsHash = {
        'change': 'render',
    };

    /**
     * Render the view.
     */
    protected onRender() {
        const model = this.model;

        if (!model.get('hasOtherComments')) {
            this.$el.empty();

            return;
        }

        const headerText = _`
            You have unpublished comments on other revisions.
        `;
        const bodyText = _`
            Your review consists of comments on the following
            revisions:
        `;

        renderInto(
            this.el,
            paint`
                <Ink.Alert type="warning">
                 <Ink.Alert.Heading>
                  ${headerText}
                 </Ink.Alert.Heading>
                 <Ink.Alert.Content>
                  <p>${bodyText}</p>
                  <ul></ul>
                 </Ink.Alert.Content>
                </Ink.Alert>
            `,
            {empty: true});

        const $ul = this.$('ul');

        model.get('diffsetsWithComments').forEach(diffset => {
            const $li = $('<li>').appendTo($ul);
            const text = _`Revision ${diffset.revision}`;

            if (diffset.isCurrent) {
                $li
                    .text(text)
                    .addClass('-is-current');
            } else {
                $('<a href="#">')
                    .text(text)
                    .appendTo($li)
                    .on('click', (e: Event) => {
                        e.preventDefault();
                        e.stopPropagation();

                        this.trigger('revisionSelected',
                                     [0, diffset.revision]);
                    });
            }
        });

        model.get('commitsWithComments').forEach(commit => {
            const $li = $('<li>').appendTo($ul);
            let text: string;

            if (commit.baseCommitID === null ||
                commit.baseCommitID === commit.tipCommitID) {
                text = _`
                    Revision ${commit.revision},
                    commit ${commit.tipCommitID.substring(0, 8)}
                `;
            } else if (commit.tipCommitID === null) {
                text = _`
                    Revision ${commit.revision},
                    commit ${commit.baseCommitID.substring(0, 8)}
                `;
            } else {
                text = _`
                    Revision ${commit.revision},
                    commits ${commit.baseCommitID.substring(0, 8)} -
                    ${commit.tipCommitID.substring(0, 8)}
                `;
            }

            if (commit.isCurrent) {
                $li
                    .text(text)
                    .addClass('-is-current');
            } else {
                $('<a href="#">')
                    .text(text)
                    .appendTo($li)
                    .on('click', (e: Event) => {
                        e.preventDefault();
                        e.stopPropagation();

                        this.trigger('commitRangeSelected',
                                     commit.revision,
                                     commit.baseCommitPK,
                                     commit.tipCommitPK);
                    });
            }
        });

        model.get('interdiffsWithComments').forEach(interdiff => {
            const $li = $('<li>').appendTo($ul);
            const text = _`
                Interdiff revision ${interdiff.oldRevision} -
                ${interdiff.newRevision}
            `;

            if (interdiff.isCurrent) {
                $li
                    .text(text)
                    .addClass('-is-current');
            } else {
                $('<a href="#">')
                    .text(text)
                    .appendTo($li)
                    .on('click', (e: Event) => {
                        e.preventDefault();
                        e.stopPropagation();

                        this.trigger(
                            'revisionSelected',
                            [interdiff.oldRevision, interdiff.newRevision]);
                    });
            }
        });
    }
}
