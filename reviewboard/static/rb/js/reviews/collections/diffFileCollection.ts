/**
 * A collection of files.
 */
import { BaseCollection, spina } from '@beanbag/spina';

import { DiffFile } from '../models/diffFileModel';


/**
 * A collection of files.
 */
@spina
export class DiffFileCollection extends BaseCollection<DiffFile> {
    static model = DiffFile;
}
