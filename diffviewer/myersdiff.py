import math

class MyersDiffer:
    """
    An implementation of Eugene Myers's O(ND) Diff algorithm based on GNU diff.
    """
    SNAKE_LIMIT = 20

    class DiffData:
        def __init__(self, data):
            self.data = data
            self.length = len(data)
            self.modified = {}
            self.undiscarded = []
            self.undiscarded_lines = 0
            self.real_indexes = []

        def is_modified(self, line):
            return self.modified.has_key(line) and self.modified[line]


    def __init__(self, a, b, ignore_space=False):
        if type(a) != type(b):
            raise TypeError

        self.a = a
        self.b = b
        self.code_table = {}
        self.last_code = 0
        self.a_data = self.b_data = None
        self.ignore_space = ignore_space
        self.minimal_diff = False

        # SMS State
        self.max_lines = 0
        self.fdiag = None
        self.bdiag = None

    def ratio(self):
        self._gen_diff_data()
        a_equals = self.a_data.length - len(self.a_data.modified)
        b_equals = self.b_data.length - len(self.b_data.modified)

        return 1.0 * (a_equals + b_equals) / \
                     (self.a_data.length + self.b_data.length)

    def get_opcodes(self):
        """
        Generator that returns opcodes representing the contents of the
        diff.

        The resulting opcodes are in the format of
        (tag, i1, i2, j1, j2)
        """
        self._gen_diff_data()

        a_line = b_line = 0
        last_group = None

        while a_line < self.a_data.length or b_line < self.b_data.length:
            a_start = a_line
            b_start = b_line

            if a_line < self.a_data.length and \
               not self.a_data.is_modified(a_line) and \
               b_line < self.b_data.length and \
               not self.b_data.is_modified(b_line):
                # Equal
                a_changed = b_changed = 1
                tag = "equal"
                a_line += 1
                b_line += 1
            else:
                # Deleted, inserted or replaced
                while a_line < self.a_data.length and \
                      (b_line >= self.b_data.length or \
                       self.a_data.is_modified(a_line)):
                    a_line += 1

                while b_line < self.b_data.length and \
                      (a_line >= self.a_data.length or \
                       self.b_data.is_modified(b_line)):
                    b_line += 1

                a_changed = a_line - a_start
                b_changed = b_line - b_start

                assert a_start < a_line or b_start < b_line
                assert a_changed != 0 or b_changed != 0

                if a_changed == 0 and b_changed > 0:
                    tag = "insert"
                elif a_changed > 0 and b_changed == 0:
                    tag = "delete"
                elif a_changed > 0 and b_changed > 0:
                    tag = "replace"

                    if a_changed != b_changed:
                        if a_changed > b_changed:
                            a_line -= a_changed - b_changed
                        elif a_changed < b_changed:
                            b_line -= b_changed - a_changed

                        a_changed = b_changed = min(a_changed, b_changed)

            if last_group and last_group[0] == tag:
                last_group = (tag,
                              last_group[1], last_group[2] + a_changed,
                              last_group[3], last_group[4] + b_changed)
            else:
                if last_group:
                    yield last_group

                last_group = (tag, a_start, a_start + a_changed,
                              b_start, b_start + b_changed)


        if not last_group:
            last_group = ("equal", 0, self.a_data.length, 0, self.b_data.length)

        yield last_group

    def _gen_diff_data(self):
        if self.a_data and self.b_data:
            return

        self.a_data = self.DiffData(self._gen_diff_codes(self.a))
        self.b_data = self.DiffData(self._gen_diff_codes(self.b))

        self._discard_confusing_lines()

        self.max_lines = self.a_data.undiscarded_lines + \
                         self.b_data.undiscarded_lines + 3

        vector_size = self.a_data.undiscarded_lines + \
                      self.b_data.undiscarded_lines + 3
        self.fdiag = [0] * vector_size
        self.bdiag = [0] * vector_size
        self.downoff = self.upoff = self.b_data.undiscarded_lines + 1

        self._lcs(0, self.a_data.undiscarded_lines,
                  0, self.b_data.undiscarded_lines,
                  self.minimal_diff)
        self._shift_chunks(self.a_data, self.b_data)
        self._shift_chunks(self.b_data, self.a_data)

    def _gen_diff_codes(self, lines):
        """
        Converts all unique lines of text into unique numbers. Comparing
        lists of numbers is faster than comparing lists of strings.
        """
        codes = []

        for line in lines:
            # TODO: Handle ignoring/triming spaces, ignoring casing, and
            #       special hooks

            if self.ignore_space:
                temp = line.lstrip()

                # We still want to show lines that contain only whitespace.
                if temp != "":
                    line = temp

            if self.code_table.has_key(line):
                code = self.code_table[line]
            else:
                self.last_code += 1
                code = self.last_code
                self.code_table[line] = code

            codes.append(code)

        return codes

    def _findSMS(self, a_lower, a_upper, b_lower, b_upper, find_minimal):
        """
        Finds the Shortest Middle Snake.
        """
        down_vector = self.fdiag # The vector for the (0, 0) to (x, y) search
        up_vector   = self.bdiag # The vector for the (u, v) to (N, M) search

        down_k = a_lower - b_lower # The k-line to start the forward search
        up_k   = a_upper - b_upper # The k-line to start the reverse search
        odd_delta = (down_k - up_k) % 2 != 0

        down_vector[self.downoff + down_k] = a_lower

        up_vector[self.upoff + up_k] = a_upper

        dmin = a_lower - b_upper
        dmax = a_upper - b_lower

        down_min = down_max = down_k
        up_min   = up_max   = up_k

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
            for k in xrange(down_max, down_min - 1, -2):
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
                while x < a_upper and y < b_upper and \
                      self.a_data.undiscarded[x] == self.b_data.undiscarded[y]:
                    x += 1
                    y += 1

                if x - old_x > self.SNAKE_LIMIT:
                    big_snake = True

                down_vector[self.downoff + k] = x

                if odd_delta and up_min <= k <= up_max and \
                   up_vector[self.upoff + k] <= x:
                    return x, y, True, True

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

            for k in xrange(up_max, up_min - 1, -2):
                tlo = up_vector[self.upoff + k - 1]
                thi = up_vector[self.upoff + k + 1]

                if tlo < thi:
                    x = tlo
                else:
                    x = thi - 1

                y = x - k
                old_x = x

                while x > a_lower and y > b_lower and \
                      self.a_data.undiscarded[x - 1] == \
                      self.b_data.undiscarded[y - 1]:
                    x -= 1
                    y -= 1

                if old_x - x > self.SNAKE_LIMIT:
                    big_snake = True

                up_vector[self.upoff + k] = x

                if not odd_delta and down_min <= k <= down_max and \
                   x <= down_vector[self.downoff + k]:
                    return x, y, True, True

            if find_minimal:
                continue

            # Heuristics courtesy of GNU diff.
            #
            # We check occasionally for a diagonal that made lots of progress
            # compared with the edit distance. If we have one, find the one
            # that made the most progress and return it.
            #
            # This gives us better, more dense chunks, instead of lots of
            # small ones often starting with replaces. It also makes the output
            # closer to that of GNU diff, which more people would expect.

            if cost > 200 and big_snake:
                def find_diagonal(minimum, maximum, k, diagoff, vector,
                                  vdiff_func, check_x_range, check_y_range,
                                  discard_index, k_offset):
                    for d in xrange(maximum, minimum - 1, -2):
                        dd = d - k
                        x = vector[diagoff + d]
                        y = x - d
                        v = vdiff_func(x) * 2 + dd

                        if v > 12 * (cost + abs(dd)):
                            if v > best and \
                               check_x_range(x) and check_y_range(y):
                                # We found a sufficient diagonal.
                                k = k_offset
                                x_index = discard_index(x, k)
                                y_index = discard_index(y, k)

                                while self.a_data.undiscarded[x_index] == \
                                      self.b_data.undiscarded[y_index]:
                                    if k == self.SNAKE_LIMIT - 1 + k_offset:
                                        return x, y, v

                                    k += 1
                    return 0, 0, 0

                ret_x, ret_y, best = \
                    find_diagonal(down_min, down_max, down_k, self.downoff,
                                  down_vector,
                                  lambda x: x - a_lower,
                                  lambda x: a_lower + self.SNAKE_LIMIT <=
                                            x < a_upper,
                                  lambda y: b_lower + self.SNAKE_LIMIT <=
                                            y < b_upper,
                                  lambda i,k: i - k,
                                  1)

                if best > 0:
                    return ret_x, ret_y, True, False

                ret_x, ret_y, best = \
                    find_diagonal(up_min, up_max, up_k, self.upoff,
                                  up_vector,
                                  lambda x: a_upper - x,
                                  lambda x: a_lower < x <= a_upper -
                                                           self.SNAKE_LIMIT,
                                  lambda y: b_lower < y <= b_upper -
                                                           self.SNAKE_LIMIT,
                                  lambda i,k: i + k,
                                  0)

                if best > 0:
                    return ret_x, ret_y, False, True

            continue # XXX

            # If we've reached or gone past the max cost, just give up now
            # and report the halfway point between our best results.
            if cost >= max_cost:
                fx_best = bx_best = 0

                # Find the forward diagonal that maximized x + y
                fxy_best = -1
                for d in xrange(down_max, down_min - 1, -2):
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
                for d in xrange(up_max, up_min - 1, -2):
                    x = max(a_lower, up_vector[self.upoff + d])
                    y = x - d

                    if y < b_lower:
                        x = b_lower + d
                        y = b_lower

                    if x + y < bxy_best:
                        bxy_best = x + y
                        bx_bet = x

                # Use the better of the two diagonals
                if a_upper + b_upper - bxy_best < \
                   fxy_best - (a_lower + b_lower):
                    return fx_best, fxy_best - fx_best, True, False
                else:
                    return bx_best, bxy_best - bx_best, False, True


        raise Exception("The function should not have reached here.")

    def _lcs(self, a_lower, a_upper, b_lower, b_upper, find_minimal):
        """
        The divide-and-conquer implementation of the Longest Common
        Subsequence (LCS) algorithm.
        """
        # Fast walkthrough equal lines at the start
        while a_lower < a_upper and b_lower < b_upper and \
              self.a_data.undiscarded[a_lower] == \
              self.b_data.undiscarded[b_lower]:
            a_lower += 1
            b_lower += 1

        while a_upper > a_lower and b_upper > b_lower and \
              self.a_data.undiscarded[a_upper - 1] == \
              self.b_data.undiscarded[b_upper - 1]:
            a_upper -= 1
            b_upper -= 1

        if a_lower == a_upper:
            # Inserted lines.
            while b_lower < b_upper:
                self.b_data.modified[self.b_data.real_indexes[b_lower]] = True
                b_lower += 1
        elif b_lower == b_upper:
            # Deleted lines
            while a_lower < a_upper:
                self.a_data.modified[self.a_data.real_indexes[a_lower]] = True
                a_lower += 1
        else:
            # Find the middle snake and length of an optimal path for A and B
            x, y, low_minimal, high_minimal = \
                self._findSMS(a_lower, a_upper, b_lower, b_upper, find_minimal)

            self._lcs(a_lower, x, b_lower, y, low_minimal)
            self._lcs(x, a_upper, y, b_upper, high_minimal)

    def _shift_chunks(self, data, other_data):
        """
        Shifts the inserts/deletes of identical lines in order to join
        the changes together a bit more. This has the effect of cleaning
        up the diff.

        Often times, a generated diff will have two identical lines before
        and after a chunk (say, a blank line). The default algorithm will
        insert at the front of that range and include two blank lines at the
        end, but that does not always produce the best looking diff. Since
        the two lines are identical, we can shift the chunk so that the line
        appears both before and after the line, rather than only after.
        """
        i = j = 0
        i_end = data.length

        while True:
            # Scan forward in order to find the start of a run of changes.
            while i < i_end and not data.is_modified(i):
                i += 1

                while other_data.is_modified(j):
                    j += 1

            if i == i_end:
                return;

            start = i

            # Find the end of these changes
            i += 1
            while data.is_modified(i):
                i += 1

            while other_data.is_modified(j):
                j += 1

            while True:
                run_length = i - start

                # Move the changed chunks back as long as the previous
                # unchanged line matches the last changed line.
                # This merges with the previous changed chunks.
                while start != 0 and data.data[start - 1] == data.data[i - 1]:
                    start -= 1
                    i -= 1

                    data.modified[start] = True
                    data.modified[i] = False

                    while data.is_modified(start - 1):
                        start -= 1

                    j -= 1
                    while other_data.is_modified(j):
                        j -= 1

                # The end of the changed run at the last point where it
                # corresponds to the changed run in the other data set.
                # If it's equal to i_end, then we didn't find a corresponding
                # point.
                if other_data.is_modified(j - 1):
                    corresponding = i
                else:
                    corresponding = i_end

                # Move the changed region forward as long as the first
                # changed line is the same as the following unchanged line.
                while i != i_end and data.data[start] == data.data[i]:
                    data.modified[start] = False
                    data.modified[i] = True

                    start += 1
                    i += 1

                    while data.is_modified(i):
                        i += 1

                    j += 1
                    while other_data.is_modified(j):
                        j += 1
                        corresponding = i

                if run_length == i - start:
                    break

            # Move the fully-merged run back to a corresponding run in the
            # other data set, if we can.
            while corresponding < i:
                start -= 1
                i -= 1

                data.modified[start] = True
                data.modified[i] = False

                j -= 1
                while other_data.is_modified(j):
                    j -= 1

    def _discard_confusing_lines(self):
        def build_discard_list(data, discards, counts):
            many = 5 * self._very_approx_sqrt(data.length / 64)

            for i, item in enumerate(data.data):
                if item != 0:
                    num_matches = counts[item]

                    if num_matches == 0:
                        discards[i] = 1
                    elif num_matches > many:
                        discards[i] = 2

        def scan_run(discards, i, length, index_func):
            consec = 0

            for j in xrange(length):
                index = index_func(i, j)
                discard = discards[index]

                if j >= 8 and discard == 1:
                    break

                if discard == 2:
                    consec = 0
                    discards[index] = 0
                elif discard == 0:
                    consec = 0
                else:
                    consec += 1

                if consec == 3:
                    break

        def check_discard_runs(data, discards):
            i = 0
            while i < data.length:
                # Cancel the provisional discards that are not in the middle
                # of a run of discards
                if discards[i] == 2:
                    discards[i] = 0
                elif discards[i] != 0:
                    # We found a provisional discard
                    provisional = 0

                    # Find the end of this run of discardable lines and count
                    # how many are provisionally discardable.
                    #for j in xrange(i, data.length):
                    j = i
                    while j < data.length:
                        if discards[j] == 0:
                            break
                        elif discards[j] == 2:
                            provisional += 1
                        j += 1

                    # Cancel the provisional discards at the end and shrink
                    # the run.
                    while j > i and discards[j - 1] == 2:
                        j -= 1
                        discards[j] = 0
                        provisional -= 1

                    length = j - i

                    # If 1/4 of the lines are provisional, cancel discarding
                    # all the provisional lines in the run.
                    if provisional * 4 > length:
                        while j > i:
                            j -= 1
                            if discards[j] == 2:
                                discards[j] = 0
                    else:
                        #minimum = 1 + self._very_approx_sqrt(length / 4)
                        minimum = 1
                        temp = length >> 2
                        temp >>= 2
                        while 0 < temp:
                            temp >>= 2
                            minimum <<= 1
                        minimum += 1
                        assert minimum == 1 + self._very_approx_sqrt(length / 4)

                        j = 0
                        consec = 0
                        while j < length:
                            if discards[i + j] != 2:
                                consec = 0
                            else:
                                consec += 1
                                if minimum == consec:
                                    j -= consec
                                elif minimum < consec:
                                    discards[i + j] = 0

                            j += 1

                        scan_run(discards, i, length, lambda x,y: x + y)
                        i += length - 1
                        scan_run(discards, i, length, lambda x,y: x - y)

                i += 1

        def discard_lines(data, discards):
            j = 0
            for i, item in enumerate(data.data):
                if self.minimal_diff or discards[i] == 0:
                    data.undiscarded[j] = item
                    data.real_indexes[j] = i
                    j += 1
                else:
                    data.modified[i] = True

            data.undiscarded_lines = j


        self.a_data.undiscarded = [0] * self.a_data.length
        self.b_data.undiscarded = [0] * self.b_data.length
        self.a_data.real_indexes = [0] * self.a_data.length
        self.b_data.real_indexes = [0] * self.b_data.length
        a_discarded = [0] * self.a_data.length
        b_discarded = [0] * self.b_data.length
        a_code_counts = [0] * (1 + self.last_code)
        b_code_counts = [0] * (1 + self.last_code)

        for item in self.a_data.data:
            a_code_counts[item] += 1

        for item in self.b_data.data:
            b_code_counts[item] += 1

        build_discard_list(self.a_data, a_discarded, b_code_counts)
        build_discard_list(self.b_data, b_discarded, a_code_counts)

        check_discard_runs(self.a_data, a_discarded)
        check_discard_runs(self.b_data, b_discarded)

        discard_lines(self.a_data, a_discarded)
        discard_lines(self.b_data, b_discarded)


    def _very_approx_sqrt(self, i):
        result = 1
        foo = i
        i /= 4
        while i > 0:
            i /= 4
            result *= 2

        return result
