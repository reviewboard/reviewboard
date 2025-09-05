"""Differ implementation using the Myers diff algorithm."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.diffviewer.differ import Differ, DiffCompatVersion


if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Sequence

    from reviewboard.diffviewer.differ import DiffOpcode, DiffOpcodeTag


class _DiffData:
    """Storage class for data used in the Myers diff algorithm.

    Version Changed:
        8.0:
        Moved out of the MyersDiffer class.
    """

    ######################
    # Instance variables #
    ######################

    #: The data to operate on.
    data: Sequence[int]

    #: The length of the data.
    length: int

    #: A set of line numbers which have been modified.
    #:
    #: Version Changed:
    #:     8.0:
    #:     Changed from a dict[int, bool] to a set.
    modified: set[int]

    #: Lines which have not been discarded from the diff.
    undiscarded: list[int]

    #: The number of lines which have not been discarded.
    undiscarded_lines: int

    #: A list which maps undiscarded lines to line number.
    real_indexes: list[int]

    def __init__(
        self,
        data: Sequence[int],
    ) -> None:
        """Initialize the object.

        Args:
            data (list of int):
                The data in the diff.
        """
        self.data = data
        self.length = len(data)
        self.modified = set()
        self.undiscarded = []
        self.undiscarded_lines = 0
        self.real_indexes = []


class MyersDiffer(Differ):
    """Differ implementation that users the Myers diff algorithm.

    This uses Eugene Myers's O(ND) Diff algorithm, with some additional
    heuristics. This effectively turns the diff problem into a graph search.
    It works by finding the "shortest middle snake," which

    [ this area intentionally left in suspense ]
    """

    SNAKE_LIMIT = 20

    DISCARD_NONE = 0
    DISCARD_FOUND = 1
    DISCARD_CANCEL = 2

    ######################
    # Instance variables #
    ######################

    #: The data for the original side of the diff.
    a_data: _DiffData

    #: The data for the modified side of the diff.
    b_data: _DiffData

    #: Storage for computing the backward diagonal.
    bdiag: list[int]

    #: A mapping from line content to unique integers.
    code_table: dict[str, int]

    #: The current offset for the down search.
    downoff: int

    #: Storage for computing the forward diagonal.
    fdiag: list[int]

    #: The most recent code used.
    last_code: int

    #: The maximum number of changed lines that could be in the diff.
    max_lines: int

    #: The current offset for the up search.
    upoff: int

    #: Whether the data has been initialized.
    _initialized: bool

    def __init__(self, *args, **kwargs) -> None:
        """Initialize the differ.

        Args:
            *args (tuple):
                Positional arguments to pass through to the parent class.

            **kwargs (dict):
                Keyword arguments to pass through to the parent class.
        """
        super().__init__(*args, **kwargs)

        self._initialized = False

        self.code_table = {}
        self.last_code = 0
        self.interesting_line_table = {}

    def ratio(self) -> float:
        """Return the diff ratio.

        Returns:
            float:
            The ratio of unmodified lines to total lines.
        """
        self._gen_diff_data()

        a_data = self.a_data
        b_data = self.b_data

        a_equals = a_data.length - len(a_data.modified)
        b_equals = b_data.length - len(b_data.modified)

        return ((a_equals + b_equals) /
                (a_data.length + b_data.length))

    def get_opcodes(self) -> Iterator[DiffOpcode]:
        """Yield the opcodes for the diff.

        Yields:
            reviewboard.diffviewer.differ.DiffOpcode:
            The opcodes for the diff.
        """
        self._gen_diff_data()

        a_data = self.a_data
        b_data = self.b_data

        assert a_data is not None
        assert b_data is not None

        if a_data.length == 0 and b_data.length == 0:
            # There's nothing to process or yield. Bail.
            return

        a_line = b_line = 0
        last_group: (DiffOpcode | None) = None

        # Go through the entire set of lines on both the old and new files
        while a_line < a_data.length or b_line < b_data.length:
            a_start = a_line
            b_start = b_line

            tag: (DiffOpcodeTag | None) = None

            if (a_line < a_data.length and
                a_line not in a_data.modified and
                b_line < b_data.length and
                b_line not in b_data.modified):
                # Equal
                a_changed = b_changed = 1
                tag = 'equal'
                a_line += 1
                b_line += 1
            else:
                # Deleted, inserted or replaced

                # Count every old line that's been modified, and the
                # remainder of old lines if we've reached the end of the new
                # file.
                while (a_line < a_data.length and
                       (b_line >= b_data.length or
                        a_line in a_data.modified)):
                    a_line += 1

                # Count every new line that's been modified, and the
                # remainder of new lines if we've reached the end of the old
                # file.
                while (b_line < b_data.length and
                       (a_line >= a_data.length or
                        b_line in b_data.modified)):
                    b_line += 1

                a_changed = a_line - a_start
                b_changed = b_line - b_start

                assert a_start < a_line or b_start < b_line
                assert a_changed != 0 or b_changed != 0

                if a_changed == 0 and b_changed > 0:
                    tag = 'insert'
                elif a_changed > 0 and b_changed == 0:
                    tag = 'delete'
                elif a_changed > 0 and b_changed > 0:
                    tag = 'replace'

                    if a_changed != b_changed:
                        if a_changed > b_changed:
                            a_line -= a_changed - b_changed
                        elif a_changed < b_changed:
                            b_line -= b_changed - a_changed

                        a_changed = b_changed = min(a_changed, b_changed)

            assert tag is not None

            if last_group and last_group[0] == tag:
                last_group = (
                    tag,
                    last_group[1],
                    last_group[2] + a_changed,
                    last_group[3],
                    last_group[4] + b_changed,
                )
            else:
                if last_group:
                    yield last_group

                last_group = (
                    tag,
                    a_start,
                    a_start + a_changed,
                    b_start,
                    b_start + b_changed,
                )

        if not last_group:
            last_group = (
                'equal',
                0,
                a_data.length,
                0,
                b_data.length,
            )

        yield last_group

    def _gen_diff_data(self) -> None:
        """Generate all the data needed for the opcodes or the diff ratio."""
        if self._initialized:
            return

        a_data = _DiffData(self._gen_diff_codes(self.a, False))
        b_data = _DiffData(self._gen_diff_codes(self.b, True))

        self.a_data = a_data
        self.b_data = b_data

        self._discard_confusing_lines()

        self.max_lines = (a_data.undiscarded_lines +
                          b_data.undiscarded_lines + 3)

        vector_size = (a_data.undiscarded_lines +
                       b_data.undiscarded_lines + 3)
        self.fdiag = [0] * vector_size
        self.bdiag = [0] * vector_size
        self.downoff = self.upoff = b_data.undiscarded_lines + 1

        self._lcs(0, a_data.undiscarded_lines,
                  0, b_data.undiscarded_lines,
                  find_minimal=False)
        self._shift_chunks(a_data, b_data)
        self._shift_chunks(b_data, a_data)

        self._initialized = True

    def _gen_diff_codes(
        self,
        lines: Sequence[str],
        is_modified_file: bool,
    ) -> list[int]:
        """Convert all unique lines of text into unique numbers.

        We do this because comparing lists of numbers is faster than comparing
        lists of strings.

        Args:
            lines (list of str):
                The lines in a file.

            is_modified_file (bool):
                Whether this is operating on the modified version of the file.

        Returns:
            list of int:
            A list of unique numbers corresponding to the lines of text.
        """
        codes: list[int] = []

        if is_modified_file:
            interesting_lines = self.interesting_lines[1]
        else:
            interesting_lines = self.interesting_lines[0]

        ignore_space = self.ignore_space
        code_table = self.code_table
        interesting_line_table = self.interesting_line_table
        interesting_line_regexes = self.interesting_line_regexes
        last_code = self.last_code

        for linenum, line in enumerate(lines):
            # TODO: Handle ignoring/trimming spaces, ignoring casing, and
            #       special hooks

            raw_line = line
            stripped_line = line.lstrip()

            # We still want to show lines that contain only whitespace.
            if ignore_space and len(stripped_line) > 0:
                line = stripped_line

            interesting_line_name = None

            try:
                code = code_table[line]
                interesting_line_name = \
                    interesting_line_table.get(code, None)
            except KeyError:
                # This is a new, unrecorded line, so mark it and store it.
                last_code += 1
                code = last_code
                code_table[line] = code

                # Check to see if this is an interesting line that the caller
                # wants recorded.
                if stripped_line:
                    for name, regex in interesting_line_regexes:
                        if regex.match(raw_line):
                            interesting_line_name = name
                            interesting_line_table[code] = name
                            break

            if interesting_line_name:
                interesting_lines[interesting_line_name].append(
                    (linenum, raw_line))

            codes.append(code)

        self.last_code = last_code

        return codes

    def _find_sms(
        self,
        a_lower: int,
        a_upper: int,
        b_lower: int,
        b_upper: int,
        find_minimal: bool,
    ) -> tuple[int, int, bool, bool]:
        """Find the Shortest Middle Snake within given bounds.

        Args:
            a_lower (int):
                The lower bound on the original data.

            a_upper (int):
                The upper bound on the original data.

            b_lower (int):
                The lower bound on the modified data.

            b_upper (int):
                The upper bound on the modified data.

            find_minimal (bool):
                Whether to iterate until a minimal diff is found.

        Returns:
            tuple:
            A 4-tuple of:

            Tuple:
                0 (int):
                    The best dividing point for the original data to use for
                    the next step.

                1 (int):
                    The best dividing point for the modified data to use for
                    the next step.

                2 (bool):
                    Whether to search for a minimal diff in the lower half for
                    the next step.

                3 (bool):
                    Whether to search for a minimal diff in the upper half for
                    the next step.
        """
        down_vector = self.fdiag  # The vector for the (0, 0) to (x, y) search
        up_vector = self.bdiag    # The vector for the (u, v) to (N, M) search

        down_k = a_lower - b_lower  # The k-line to start the forward search
        up_k = a_upper - b_upper    # The k-line to start the reverse search
        odd_delta = (down_k - up_k) % 2 != 0

        down_vector[self.downoff + down_k] = a_lower
        up_vector[self.upoff + up_k] = a_upper

        dmin = a_lower - b_upper
        dmax = a_upper - b_lower

        down_min = down_max = down_k
        up_min = up_max = up_k

        cost = 0
        max_cost = max(256, self._very_approx_sqrt(self.max_lines * 4))

        while True:
            cost += 1
            big_snake = False

            if down_min > dmin:
                down_min -= 1
                down_vector[self.downoff + down_min - 1] = -1
            else:
                down_min += 1

            if down_max < dmax:
                down_max += 1
                down_vector[self.downoff + down_max + 1] = -1
            else:
                down_max -= 1

            # Extend the forward path
            for k in range(down_max, down_min - 1, -2):
                tlo = down_vector[self.downoff + k - 1]
                thi = down_vector[self.downoff + k + 1]

                if tlo >= thi:
                    x = tlo + 1
                else:
                    x = thi

                y = x - k
                old_x = x

                # Find the end of the furthest reaching forward D-path in
                # diagonal k
                while (x < a_upper and y < b_upper and
                       (self.a_data.undiscarded[x] ==
                        self.b_data.undiscarded[y])):
                    x += 1
                    y += 1

                if odd_delta and up_min <= k <= up_max and \
                   up_vector[self.upoff + k] <= x:
                    return x, y, True, True

                if x - old_x > self.SNAKE_LIMIT:
                    big_snake = True

                down_vector[self.downoff + k] = x

            # Extend the reverse path
            if up_min > dmin:
                up_min -= 1
                up_vector[self.upoff + up_min - 1] = self.max_lines
            else:
                up_min += 1

            if up_max < dmax:
                up_max += 1
                up_vector[self.upoff + up_max + 1] = self.max_lines
            else:
                up_max -= 1

            for k in range(up_max, up_min - 1, -2):
                tlo = up_vector[self.upoff + k - 1]
                thi = up_vector[self.upoff + k + 1]

                if tlo < thi:
                    x = tlo
                else:
                    x = thi - 1

                y = x - k
                old_x = x

                while (x > a_lower and y > b_lower and
                       (self.a_data.undiscarded[x - 1] ==
                        self.b_data.undiscarded[y - 1])):
                    x -= 1
                    y -= 1

                if (not odd_delta and down_min <= k <= down_max and
                        x <= down_vector[self.downoff + k]):
                    return x, y, True, True

                if old_x - x > self.SNAKE_LIMIT:
                    big_snake = True

                up_vector[self.upoff + k] = x

            if find_minimal:
                continue

            # Heuristics to improve diff results.
            #
            # We check occasionally for a diagonal that made lots of progress
            # compared with the edit distance. If we have one, find the one
            # that made the most progress and return it.
            #
            # This gives us better, more dense chunks, instead of lots of
            # small ones often starting with replaces.

            if cost > 200 and big_snake:
                ret_x, ret_y, best = self._find_diagonal(
                    down_min, down_max, down_k, 0,
                    self.downoff, down_vector,
                    lambda x: x - a_lower,
                    lambda x: a_lower + self.SNAKE_LIMIT <= x < a_upper,
                    lambda y: b_lower + self.SNAKE_LIMIT <= y < b_upper,
                    lambda i, k: i - k,
                    1, cost)

                if best > 0:
                    return ret_x, ret_y, True, False

                ret_x, ret_y, best = self._find_diagonal(
                    up_min, up_max, up_k, best, self.upoff,
                    up_vector,
                    lambda x: a_upper - x,
                    lambda x: a_lower < x <= a_upper - self.SNAKE_LIMIT,
                    lambda y: b_lower < y <= b_upper - self.SNAKE_LIMIT,
                    lambda i, k: i + k,
                    0, cost)

                if best > 0:
                    return ret_x, ret_y, False, True

            if (cost >= max_cost and
                self.compat_version >= DiffCompatVersion.MYERS_SMS_COST_BAIL):
                # We've reached or gone past the max cost. Just give up now
                # and report the halfway point between our best results.
                fx_best = bx_best = 0

                # Find the forward diagonal that maximized x + y
                fxy_best = -1
                for d in range(down_max, down_min - 1, -2):
                    x = min(down_vector[self.downoff + d], a_upper)
                    y = x - d

                    if b_upper < y:
                        x = b_upper + d
                        y = b_upper

                    if fxy_best < x + y:
                        fxy_best = x + y
                        fx_best = x

                # Find the backward diagonal that minimizes x + y
                bxy_best = self.max_lines
                for d in range(up_max, up_min - 1, -2):
                    x = max(a_lower, up_vector[self.upoff + d])
                    y = x - d

                    if y < b_lower:
                        x = b_lower + d
                        y = b_lower

                    if x + y < bxy_best:
                        bxy_best = x + y
                        bx_best = x

                # Use the better of the two diagonals
                if a_upper + b_upper - bxy_best < \
                   fxy_best - (a_lower + b_lower):
                    return fx_best, fxy_best - fx_best, True, False
                else:
                    return bx_best, bxy_best - bx_best, False, True

        raise Exception(
            'The function should not have reached here.',
        )

    def _find_diagonal(
        self,
        minimum: int,
        maximum: int,
        k: int,
        best: int,
        diagoff: int,
        vector: Sequence[int],
        vdiff_func: Callable[[int], int],
        check_x_range: Callable[[int], bool],
        check_y_range: Callable[[int], bool],
        discard_index: Callable[[int, int], int],
        k_offset: int,
        cost: int,
    ) -> tuple[int, int, int]:
        """Find the best diagonal in a region of the graph.

        Args:
            minimum (int):
                The lower bound to search within the vector.

            maximum (int):
                The upper bound to search within the vector.

            k (int):
                The k-line to start the search.

            best (int):
                The best number of steps of progress discovered so far.

            diagoff (int):
                The offset of the diagonal found so far.

            vector (list of int):
                The vector to search.

            vdiff_func (callable):
                A callable to compute an offset within the vector. This is used
                so we can search both forward and backward.

            check_x_range (callable):
                A callable to check if a value is within bounds.

            check_y_range (callable):
                A callable to check if a value is within bounds.

            discard_index (callable):
                A callable to determine the index into the discards list.

            k_offset (int):
                The offset to apply to the ``k`` parameter.

            cost (int):
                The current edit cost.

        Returns:
            tuple:
            A 3-tuple of:

            Tuple:
                 0 (int):
                    The number of steps in the X direction.

                 1 (int):
                    The number of steps in the Y direction.

                 2 (int):
                    The new best number of steps of progress.
        """
        a_data = self.a_data
        b_data = self.b_data
        snake_limit = self.SNAKE_LIMIT

        for d in range(maximum, minimum - 1, -2):
            dd = d - k
            x = vector[diagoff + d]
            y = x - d
            v = vdiff_func(x) * 2 + dd

            if (v > best and
                v > 12 * (cost + abs(dd)) and
               check_x_range(x) and
               check_y_range(y)):
                # We found a sufficient diagonal.
                k = k_offset
                x_index = discard_index(x, k)
                y_index = discard_index(y, k)

                while (a_data.undiscarded[x_index] ==
                       b_data.undiscarded[y_index]):
                    if k == snake_limit - 1 + k_offset:
                        return x, y, v

                    k += 1

        return 0, 0, 0

    def _lcs(
        self,
        a_lower: int,
        a_upper: int,
        b_lower: int,
        b_upper: int,
        find_minimal: bool,
    ) -> None:
        """Perform a step of finding the longest common subsequence (LCS).

        This does a divide-and-conquer to find the longest subsequence within
        the given ranges.

        Args:
            a_lower (int):
                The lower bound on the original data.

            a_upper (int):
                The upper bound on the original data.

            b_lower (int):
                The lower bound on the modified data.

            b_upper (int):
                The upper bound on the modified data.

            find_minimal (bool):
                Whether to iterate until a minimal diff is found.
        """
        # Fast walkthrough equal lines at the start.
        while (a_lower < a_upper and b_lower < b_upper and
               (self.a_data.undiscarded[a_lower] ==
                self.b_data.undiscarded[b_lower])):
            a_lower += 1
            b_lower += 1

        # Fast walkthrough equal lines at the end.
        while (a_upper > a_lower and b_upper > b_lower and
               (self.a_data.undiscarded[a_upper - 1] ==
                self.b_data.undiscarded[b_upper - 1])):
            a_upper -= 1
            b_upper -= 1

        if a_lower == a_upper:
            # Purely inserted lines.
            while b_lower < b_upper:
                self.b_data.modified.add(self.b_data.real_indexes[b_lower])
                b_lower += 1
        elif b_lower == b_upper:
            # Purely deleted lines.
            while a_lower < a_upper:
                self.a_data.modified.add(self.a_data.real_indexes[a_lower])
                a_lower += 1
        else:
            # Find the middle snake and length of an optimal path for A and B.
            x, y, low_minimal, high_minimal = \
                self._find_sms(a_lower, a_upper, b_lower, b_upper,
                               find_minimal)

            self._lcs(a_lower, x, b_lower, y, low_minimal)
            self._lcs(x, a_upper, y, b_upper, high_minimal)

    def _shift_chunks(
        self,
        data: _DiffData,
        other_data: _DiffData,
    ) -> None:
        """Shift chunks to improve alignment.

        This shifts the inserts/deletes of identical lines in order to join the
        changes together a bit more. This has the effect of cleaning up the
        diff.

        Often times, a generated diff will have two identical lines before
        and after a chunk (say, a blank line). The default algorithm will
        insert at the front of that range and include two blank lines at the
        end, but that does not always produce the best looking diff. Since
        the two lines are identical, we can shift the chunk so that the line
        appears both before and after the line, rather than only after.

        Args:
            data (_DiffData):
                One side of the diff.

            other_data (_DiffData):
                The other side of the diff.
        """
        i = j = 0
        i_end = data.length

        while True:
            # Scan forward in order to find the start of a run of changes.
            while i < i_end and i not in data.modified:
                i += 1

                while j in other_data.modified:
                    j += 1

            if i == i_end:
                return

            start = i

            # Find the end of these changes
            i += 1
            while i in data.modified:
                i += 1

            while j in other_data.modified:
                j += 1

            while True:
                run_length = i - start

                # Move the changed chunks back as long as the previous
                # unchanged line matches the last changed line.
                # This merges with the previous changed chunks.
                while start != 0 and data.data[start - 1] == data.data[i - 1]:
                    start -= 1
                    i -= 1

                    data.modified.add(start)
                    data.modified.remove(i)

                    while (start - 1) in data.modified:
                        start -= 1

                    j -= 1

                    while j in other_data.modified:
                        j -= 1

                # The end of the changed run at the last point where it
                # corresponds to the changed run in the other data set.
                # If it's equal to i_end, then we didn't find a corresponding
                # point.
                if (j - 1) in other_data.modified:
                    corresponding = i
                else:
                    corresponding = i_end

                # Move the changed region forward as long as the first
                # changed line is the same as the following unchanged line.
                while i != i_end and data.data[start] == data.data[i]:
                    data.modified.remove(start)
                    data.modified.add(i)

                    start += 1
                    i += 1

                    while i in data.modified:
                        i += 1

                    j += 1

                    while j in other_data.modified:
                        j += 1
                        corresponding = i

                if run_length == i - start:
                    break

            # Move the fully-merged run back to a corresponding run in the
            # other data set, if we can.
            while corresponding < i:
                start -= 1
                i -= 1

                data.modified.add(start)
                data.modified.remove(i)

                j -= 1

                while j in other_data.modified:
                    j -= 1

    def _discard_confusing_lines(self) -> None:
        """Discard lines that may make the diff confusing."""
        def build_discard_list(
            data: _DiffData,
            discards: list[int],
            counts: Sequence[int],
        ) -> None:
            """Populate the discard list.

            Args:
                data (_DiffData):
                    The data to operate on.

                discards (list of int):
                    The discards. This will be modified.

                counts (list of int):
                    The number of times each unique line appears in the data.
            """
            many = 5 * self._very_approx_sqrt(data.length // 64)

            for i, item in enumerate(data.data):
                if item != 0:
                    num_matches = counts[item]

                    if num_matches == 0:
                        discards[i] = self.DISCARD_FOUND
                    elif num_matches > many:
                        discards[i] = self.DISCARD_CANCEL

        def scan_run(
            discards: list[int],
            i: int,
            length: int,
            index_func: Callable[[int, int], int],
        ) -> None:
            """Scan a run of discarded lines.

            Args:
                discards (list of int):
                    The discards. This will be modified.

                i (int):
                    The index to start at.

                length (int):
                    The length of the run to scan.

                index_func (callable):
                    A function to create an index into the ``discards`` list.
            """
            consec = 0

            for j in range(length):
                index = index_func(i, j)
                discard = discards[index]

                if j >= 8 and discard == self.DISCARD_FOUND:
                    break

                if discard == self.DISCARD_FOUND:
                    consec += 1
                else:
                    consec = 0

                    if discard == self.DISCARD_CANCEL:
                        discards[index] = self.DISCARD_NONE

                if consec == 3:
                    break

        def check_discard_runs(
            data: _DiffData,
            discards: list[int],
        ) -> None:
            """Check runs of discarded lines.

            Args:
                data (_DiffData):
                    The data to operate on.

                discards (list of int):
                    The discards. This will be modified.
            """
            i = 0
            while i < data.length:
                # Cancel the provisional discards that are not in the middle
                # of a run of discards
                if discards[i] == self.DISCARD_CANCEL:
                    discards[i] = self.DISCARD_NONE
                elif discards[i] == self.DISCARD_FOUND:
                    # We found a provisional discard
                    provisional = 0

                    # Find the end of this run of discardable lines and count
                    # how many are provisionally discardable.
                    j = i
                    while j < data.length:
                        if discards[j] == self.DISCARD_NONE:
                            break
                        elif discards[j] == self.DISCARD_CANCEL:
                            provisional += 1
                        j += 1

                    # Cancel the provisional discards at the end and shrink
                    # the run.
                    while j > i and discards[j - 1] == self.DISCARD_CANCEL:
                        j -= 1
                        discards[j] = 0
                        provisional -= 1

                    length = j - i

                    # If 1/4 of the lines are provisional, cancel discarding
                    # all the provisional lines in the run.
                    if provisional * 4 > length:
                        while j > i:
                            j -= 1
                            if discards[j] == self.DISCARD_CANCEL:
                                discards[j] = self.DISCARD_NONE
                    else:
                        minimum = 1 + self._very_approx_sqrt(length // 4)
                        j = 0
                        consec = 0
                        while j < length:
                            if discards[i + j] != self.DISCARD_CANCEL:
                                consec = 0
                            else:
                                consec += 1
                                if minimum == consec:
                                    j -= consec
                                elif minimum < consec:
                                    discards[i + j] = self.DISCARD_NONE

                            j += 1

                        scan_run(discards, i, length, lambda x, y: x + y)
                        i += length - 1
                        scan_run(discards, i, length, lambda x, y: x - y)

                i += 1

        def discard_lines(
            data: _DiffData,
            discards: Sequence[int],
        ) -> None:
            """Perform the actual discard.

            Args:
                data (_DiffData):
                    The data for the file. This will be modified.

                discards (list of int):
                    The discard information.
            """
            j = 0

            for i, item in enumerate(data.data):
                if discards[i] == self.DISCARD_NONE:
                    data.undiscarded[j] = item
                    data.real_indexes[j] = i
                    j += 1
                else:
                    data.modified.add(i)

            data.undiscarded_lines = j

        a_data = self.a_data
        b_data = self.b_data
        a_length = a_data.length
        b_length = b_data.length
        last_code = self.last_code

        a_data.undiscarded = [0] * a_length
        b_data.undiscarded = [0] * b_length
        a_data.real_indexes = [0] * a_length
        b_data.real_indexes = [0] * b_length
        a_discarded = [0] * a_length
        b_discarded = [0] * b_length
        a_code_counts = [0] * (1 + last_code)
        b_code_counts = [0] * (1 + last_code)

        for item in a_data.data:
            a_code_counts[item] += 1

        for item in b_data.data:
            b_code_counts[item] += 1

        build_discard_list(a_data, a_discarded, b_code_counts)
        build_discard_list(b_data, b_discarded, a_code_counts)

        check_discard_runs(a_data, a_discarded)
        check_discard_runs(b_data, b_discarded)

        discard_lines(a_data, a_discarded)
        discard_lines(b_data, b_discarded)

    def _very_approx_sqrt(
        self,
        i: int,
    ) -> int:
        """Perform an extremely inaccurate square root.

        Args:
            i (int):
                The number to operate on.

        Returns:
            int:
            Something vaguely square-root like.
        """
        result = 1
        i //= 4

        while i > 0:
            i //= 4
            result *= 2

        return result
