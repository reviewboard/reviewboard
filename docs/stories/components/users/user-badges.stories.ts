import {
    paint,
} from '@beanbag/ink';


export default {
    tags: ['autodocs'],
    title: 'Review Board/Components/Users/User Badges',

    render: (options: {
        badges: string[],
    }) => {
        return paint`
            <span class="rb-c-user-badges"
                  role="list"
                  aria-label="Badges">
             ${options.badges.map(badge => paint`
               <span class="rb-c-user-badge"
                     role="listitem">${badge}</span>
             `)}
            </span>
        `;
    },

    argTypes: {
        badges: {
            control: 'object',
        },
    },

    args: {
        badges: [
            'Badge 1',
            'Badge 2',
            'Badge 3',
            ("Very long badge with a long name that should help us test " +
             "some wrapping probably and we'll just keep going for a while " +
             "until we're seeing the wrap and this is probably enough."),
            'Badge 5',
        ],
    },
};


export const Badges = {};
