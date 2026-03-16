/**
 * A collection of branches in a repository.
 */

import { spina } from '@beanbag/spina';

import { BaseCollection } from '../../collections/baseCollection';
import {
    type RepositoryBranchAttrs,
    RepositoryBranch,
} from '../models/repositoryBranchModel';


/**
 * A collection of branches in a repository.
 */
@spina
export class RepositoryBranches extends BaseCollection<RepositoryBranch> {
    static model = RepositoryBranch;

    /**
     * Parse the response from the server.
     *
     * Args:
     *     response (object):
     *         Response, parsed from the JSON returned by the server.
     *
     * Returns:
     *     Array of object:
     *     An array of objects parsed that will be parsed to create each model.
     */
    parse(
        response: {
            branches: RepositoryBranchAttrs[];
        },
    ): RepositoryBranchAttrs[] {
        return response.branches;
    }
}
