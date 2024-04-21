/**
 * Story file for DiffComplexityIconView.
 *
 * Version Added:
 *     7.0
 */

import {
    DiffComplexityIconView,
} from '@beanbag/reviewboard/static/rb/js/reviews';


export default {
    title: 'Review Board/Components/Diff Complexity Icon',
    tags: ['autodocs'],
    render: options => {
        const view = new DiffComplexityIconView({
            numDeletes: options.numDeletes,
            numInserts: options.numInserts,
            numReplaces: options.numReplaces,
            totalLines: Math.max(options.totalLines,
                                 options.numDeletes +
                                 options.numInserts +
                                 options.numReplaces),
        });
        view.render();

        return view.el;
    },
    argTypes: {
        numDeletes: {
            description: 'The number of deletes in the diff.',
            control: 'number',
        },
        numInserts: {
            description: 'The number of inserts in the diff.',
            control: 'number',
        },
        numReplaces: {
            description: 'The number of replaces in the diff.',
            control: 'number',
        },
        totalLines: {
            description: 'The total number of lines in the file.',
            control: 'number',
        },
    },
    args: {
        numDeletes: 50,
        numInserts: 100,
        numReplaces: 150,
        totalLines: 500,
    },
};


export const Standard = {
};


export const MinimumDonut = {
    args: {
        numDeletes: 50,
        numInserts: 100,
        numReplaces: 150,
        totalLines: 10000,
    }
};


export const MaximumDonut = {
    args: {
        numDeletes: 50,
        numInserts: 100,
        numReplaces: 150,
        totalLines: 300,
    }
};


export const NewFile = {
    args: {
        numDeletes: 0,
        numInserts: 100,
        numReplaces: 0,
        totalLines: 100,
    },
};


export const DeletedFile = {
    args: {
        numDeletes: 100,
        numInserts: 0,
        numReplaces: 0,
        totalLines: 100,
    },
};


export const ReplacedFile = {
    args: {
        numDeletes: 0,
        numInserts: 0,
        numReplaces: 100,
        totalLines: 100,
    },
};


export const HalfInsertDelete = {
    args: {
        numDeletes: 50,
        numInserts: 50,
        numReplaces: 0,
        totalLines: 100,
    },
};


export const NoChanges = {
    args: {
        numDeletes: 0,
        numInserts: 0,
        numReplaces: 0,
        totalLines: 100,
    },
};


export const OnlyInserts = {
    args: {
        numDeletes: 0,
        numInserts: 100,
        numReplaces: 0,
        totalLines: 500,
    },
};


export const OnlyDeletes = {
    args: {
        numDeletes: 100,
        numInserts: 0,
        numReplaces: 0,
        totalLines: 500,
    },
};


export const OnlyReplaces = {
    args: {
        numDeletes: 0,
        numInserts: 0,
        numReplaces: 100,
        totalLines: 500,
    },
};


export const OneMinimumSegment = {
    args: {
        numDeletes: 1,
        numInserts: 100,
        numReplaces: 100,
        totalLines: 100,
    },
};

export const OneMinimumSegmentDonut = {
    args: {
        numDeletes: 1,
        numInserts: 100,
        numReplaces: 100,
        totalLines: 1000,
    },
};

export const TwoMinimumSegments = {
    args: {
        numDeletes: 1,
        numInserts: 1,
        numReplaces: 100,
        totalLines: 100,
    },
};

export const TwoMinimumSegmentsDonut = {
    args: {
        numDeletes: 1,
        numInserts: 1,
        numReplaces: 100,
        totalLines: 1000,
    },
};
