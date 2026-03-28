import {
    paint,
} from '@beanbag/ink';


export default {
    tags: ['autodocs'],
    title: 'Review Board/Components/Users/User',

    render: (options: {
        avatarSize: number,
        badges: string[],
        name: string,
        showAvatar: boolean,
        showBadges: boolean,
    }) => {
        /* Prepare the avatar element, if requested. */
        let avatarEl: HTMLElement = null;

        if (options.showAvatar) {
            const avatarSize = options.avatarSize;

            avatarEl = paint`
                <span class="rb-c-user__avatar">
                 <img class="avatar djblets-o-avatar"
                      src="https://cataas.com/cat?type=small"
                      width="${avatarSize}"
                      height="${avatarSize}"/>
                </span>
            `;
        }

        /* Prepare the badges element, if requested. */
        let badgesEl: HTMLElement = null;
        const badges = options.badges;

        if (options.showBadges && badges && badges.length > 0) {
            badgesEl = paint`
                <span class="rb-c-user-badges"
                      role="list"
                      aria-label="Badges">
                 ${badges.map(badge => paint`
                   <span class="rb-c-user-badge"
                         role="listitem">
                    ${badge}
                   </span>
                 `)}
                </span>
            `;
        }

        return paint`
            <span class="rb-c-user">
             <a class="user" href="#">
              ${avatarEl}
              <span>${options.name}</span>
             </a>
             ${badgesEl}
            </span>
        `;
    },

    argTypes: {
        avatarSize: {
            control: 'number',
        },
        badges: {
            control: 'object',
        },
        name: {
            control: 'text',
        },
        showAvatar: {
            control: 'boolean',
        },
        showBadges: {
            control: 'boolean',
        },
    },

    args: {
        avatarSize: 24,
        badges: [
            'Power User',
            'Janitor',
        ],
        name: 'Dopey Dwarf',
        showAvatar: false,
        showBadges: false,
    },
};


export const User = {
};


export const UserWithAvatar = {
    args: {
        showAvatar: true,
    },
};


export const UserWithBadges = {
    args: {
        showBadges: true,
    },
};


export const UserWithAvatarAndBadges = {
    args: {
        showAvatar: true,
        showBadges: true,
    },
};
