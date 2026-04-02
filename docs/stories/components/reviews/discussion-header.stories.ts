import {
    paint,
} from '@beanbag/ink';


export default {
    tags: ['autodocs'],
    title: 'Review Board/Components/Reviews/Discussion Header',

    render: (options: {
        showAvatar: boolean,
        showCompact: boolean,
        showIsNew: boolean,
        titleText: string,
        titleType: 'text' | 'user',
    }) => {
        /* Build the avatar element. */
        let avatarEl: (HTMLElement | null) = null;

        if (options.showAvatar) {
            avatarEl = paint`
                <span class="rb-c-discussion-header__avatar">
                 <img class="avatar djblets-o-avatar"
                      src="https://cataas.com/cat?type=small"
                      width="24"
                      height="24"/>
                </span>
            `;
        }

        /* Build the title element. */
        const titleType = options.titleType;
        let titleEl: HTMLElement;

        if (titleType === 'user') {
            titleEl = paint`
                <span class="rb-c-user">
                 <a class="user" href="#">
                  <span>Dopey Dwarf</span>
                 </a>
                 <span class="rb-c-user-badges"
                       role="list"
                       aria-label="Badges">
                  <span class="rb-c-user-badge"
                        role="listitem">
                   Cat Herder
                  </span>
                 </span>
                </span>
            `;
        } else {
            titleEl = paint`${options.titleText}`;
        }

        /* Build the resulting element. */
        let cssClass = 'rb-c-discussion-header';

        if (options.showAvatar) {
            cssClass += ' -has-avatar';
        }

        if (options.showCompact) {
            cssClass += ' -is-compact';
        }

        const el = paint`
            <div class="${cssClass}">
            ${avatarEl}
             ${options.showIsNew && paint`
              <div class="rb-c-discussion-header__status">
               <div class="rb-icon rb-icon-new-updates"
                    title="New Updates"></div>
              </div>
             `}
             <div class="rb-c-discussion-header__title">
              ${titleEl}
             </div>
             <div class="rb-c-discussion-header__timestamp">
              <a class="timestamp" href="#">
               <time class="timesince"
                     dateTime="2026-03-26T12:30:40.000000-07:00">
                March 26, 2026, 12:30PM
               </time>
              </a>
             </div>
            </div>
        `;

        $(el).find('time').timesince();

        return el;
    },

    argTypes: {
        showAvatar: {
            control: 'boolean',
        },
        showCompact: {
            control: 'boolean',
        },
        showIsNew: {
            control: 'boolean',
        },
        titleType: {
            control: 'radio',
            options: [
                'text',
                'user',
            ],
        },
        titleText: {
            control: 'text',
        },
    },

    args: {
        showAvatar: false,
        showCompact: false,
        showIsNew: false,
        titleText: 'Review request changed',
        titleType: 'user',
    },
};


export const Standard = {};

export const Review = {
    args: {
        showAvatar: false,
        showCompact: false,
        titleType: 'user',
    },
};

export const NewReview = {
    args: {
        showAvatar: false,
        showCompact: false,
        showIsNew: true,
        titleType: 'user',
    },
};


export const Reply = {
    args: {
        showAvatar: true,
        showCompact: true,
        showIsNew: false,
        titleType: 'user',
    },
};


export const NewReply = {
    args: {
        showAvatar: true,
        showCompact: true,
        showIsNew: true,
        titleType: 'user',
    },
};


export const ReviewRequestChanged = {
    args: {
        showAvatar: false,
        showCompact: false,
        showIsNew: false,
        titleType: 'text',
        titleText: 'Review request changed',
    },
};


export const NewReviewRequestChanged = {
    args: {
        showAvatar: false,
        showCompact: false,
        showIsNew: true,
        titleType: 'text',
        titleText: 'Review request changed',
    },
};
