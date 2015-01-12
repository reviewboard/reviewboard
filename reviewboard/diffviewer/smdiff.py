from __future__ import unicode_literals

from difflib import SequenceMatcher

from reviewboard.diffviewer.differ import Differ


class SMDiffer(Differ):
    """Wrapper around SequenceMatcher.

    This class works around bugs in how SequenceMatcher does its matching.
    """
    def __init__(self, *args, **kwargs):
        super(SMDiffer, self).__init__(*args, **kwargs)

    def get_opcodes(self):
        sequence_matcher = SequenceMatcher(None, self.a, self.b)

        for tag, i1, i2, j1, j2 in sequence_matcher.get_opcodes():
            if tag == 'replace':
                oldlines = self.a[i1:i2]
                newlines = self.b[j1:j2]

                i = i_start = 0
                j = j_start = 0

                while i < len(oldlines) and j < len(newlines):
                    new_tag = None
                    new_i, new_j = i, j

                    if oldlines[i] == "" and newlines[j] == "":
                        new_tag = "equal"
                        new_i += 1
                        new_j += 1
                    elif oldlines[i] == "":
                        new_tag = "insert"
                        new_j += 1
                    elif newlines[j] == "":
                        new_tag = "delete"
                        new_i += 1
                    else:
                        new_tag = "replace"
                        new_i += 1
                        new_j += 1

                    if new_tag != tag:
                        if i > i_start or j > j_start:
                            yield (tag, i1 + i_start, i1 + i,
                                   j1 + j_start, j1 + j)

                        tag = new_tag
                        i_start, j_start = i, j

                    i, j = new_i, new_j

                yield tag, i1 + i_start, i1 + i, j1 + j_start, j1 + j
                i_start = i
                j_start = j

                if i2 > i1 + i_start or j2 > j1 + j_start:
                    tag = None

                    if len(oldlines) > len(newlines):
                        tag = "delete"
                    elif len(oldlines) < len(newlines):
                        tag = "insert"

                    if tag is not None:
                        yield tag, i1 + i_start, i2, j1 + j_start, j2
            else:
                yield tag, i1, i2, j1, j2
