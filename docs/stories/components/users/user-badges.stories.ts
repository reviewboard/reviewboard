import {
    paint,
} from '@beanbag/ink';


export default {
    tags: ['autodocs'],
    title: 'Review Board/Components/Users/User Badges',

    render: attrs => {
        return paint`
            <div class="rb-c-user-badges">
             <span class="rb-c-user-badge">Badge 1</span>
             <span class="rb-c-user-badge">Badge 2</span>
             <span class="rb-c-user-badge">Badge 3</span>
             <span class="rb-c-user-badge">
              Very long badge with a long name that should help us test
              some wrapping probably and we'll just keep going for a while
              until we're seeing the wrap and this is probably enough.
             </span>
             <span class="rb-c-user-badge">Badge 5</span>
            </div>
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
