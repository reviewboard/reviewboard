"""Unit test for reviewboard.diffviewer.processors."""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.diffviewer.differ import get_differ
from reviewboard.diffviewer.processors import (filter_interdiff_opcodes,
                                               post_process_filtered_equals)
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence


class FilterInterdiffOpcodesTests(TestCase):
    """Unit tests for filter_interdiff_opcodes."""

    def test_filter_interdiff_opcodes(self) -> None:
        """Testing filter_interdiff_opcodes"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('insert', 0, 0, 0, 1),
                ('equal', 0, 5, 1, 6),
                ('delete', 5, 10, 6, 6),
                ('equal', 10, 25, 6, 21),
                ('replace', 25, 26, 21, 22),
                ('equal', 26, 40, 22, 36),
                ('insert', 40, 40, 36, 46),
            ],
            a_num_lines=50,
            b_num_lines=50,
            a_ranges=[
                (21, 31),
            ],
            b_ranges=[
                (1, 10),
                (21, 31),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 0, 0, 1),
                ('equal', 0, 5, 1, 6),
                ('filtered-equal', 5, 10, 6, 6),
                ('equal', 10, 25, 6, 21),
                ('replace', 25, 26, 21, 22),
                ('equal', 26, 35, 22, 31),
                ('filtered-equal', 35, 40, 31, 36),
                ('filtered-equal', 40, 40, 36, 46),
            ],
        )

    def test_filter_interdiff_opcodes_replace_after_valid_ranges(self) -> None:
        """Testing filter_interdiff_opcodes with replace after valid range"""
        # While developing the fix for replace lines in
        # https://reviews.reviewboard.org/r/6030/, an iteration of the fix
        # broke replace lines when one side exceeded its last range found in
        # the diff.
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('replace', 12, 13, 5, 6),
            ],
            a_num_lines=20,
            b_num_lines=20,
            a_ranges=[
                (1, 11),
            ],
            b_ranges=[
                (1, 11),
            ],
            expected_opcodes=[
                ('replace', 12, 13, 5, 6),
            ],
        )

    def test_filter_interdiff_opcodes_1_line(self) -> None:
        """Testing filter_interdiff_opcodes with a 1 line file"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('replace', 0, 1, 0, 1),
            ],
            a_num_lines=5,
            b_num_lines=5,
            a_ranges=[
                (0, 2),
            ],
            b_ranges=[
                (0, 2),
            ],
            expected_opcodes=[
                ('replace', 0, 1, 0, 1),
            ],
        )

    def test_filter_interdiff_opcodes_early_change(self) -> None:
        """Testing filter_interdiff_opcodes with a change early in the file"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('replace', 2, 3, 2, 3),
            ],
            a_num_lines=10,
            b_num_lines=10,
            a_ranges=[
                (0, 6),
            ],
            b_ranges=[
                (0, 6),
            ],
            expected_opcodes=[
                ('replace', 2, 3, 2, 3),
            ],
        )

    def test_filter_interdiff_opcodes_with_inserts_right(self) -> None:
        """Testing filter_interdiff_opcodes with inserts on the right"""
        # These opcodes were taken from the r1-r2 interdiff of
        # resourceCollection.js at http://reviews.reviewboard.org/r/4221/
        # (which is a newly-introduced file in both revisions).
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 141, 0, 141),
                ('replace', 141, 142, 141, 142),
                ('insert', 142, 142, 142, 144),
                ('equal', 142, 165, 144, 167),
                ('replace', 165, 166, 167, 168),
                ('insert', 166, 166, 168, 170),
                ('equal', 166, 190, 170, 194),
                ('insert', 190, 190, 194, 197),
                ('equal', 190, 232, 197, 239),
            ],
            a_num_lines=232,
            b_num_lines=239,
            a_ranges=[
                (0, 232),
            ],
            b_ranges=[
                (0, 239),
            ],
            expected_opcodes=[
                ('equal', 0, 141, 0, 141),
                ('replace', 141, 142, 141, 142),
                ('insert', 142, 142, 142, 144),
                ('equal', 142, 165, 144, 167),
                ('replace', 165, 166, 167, 168),
                ('insert', 166, 166, 168, 170),
                ('equal', 166, 190, 170, 194),
                ('insert', 190, 190, 194, 197),
                ('equal', 190, 232, 197, 239),
            ],
        )

    def test_filter_interdiff_opcodes_with_many_ignorable_ranges(self) -> None:
        """Testing filter_interdiff_opcodes with many ignorable ranges"""
        # These opcodes were taken from the r1-r2 interdiff of
        # diffReviewableView.js at http://reviews.reviewboard.org/r/4257/
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 631, 0, 631),
                ('replace', 631, 632, 631, 632),
                ('insert', 632, 632, 632, 633),
                ('equal', 632, 882, 633, 883),
            ],
            a_num_lines=882,
            b_num_lines=883,
            a_ranges=[
                (415, 417),
                (426, 428),
                (431, 433),
                (441, 443),
                (452, 454),
                (607, 806),
                (847, 877),
            ],
            b_ranges=[
                (415, 417),
                (426, 428),
                (431, 433),
                (441, 443),
                (452, 454),
                (607, 807),
                (848, 878),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 631, 0, 631),
                ('replace', 631, 632, 631, 632),
                ('insert', 632, 632, 632, 633),
                ('equal', 632, 806, 633, 807),
                ('filtered-equal', 806, 882, 807, 883),
            ],
        )

    def test_filter_interdiff_opcodes_with_replace_overflowing_range(
        self,
    ) -> None:
        """Testing filter_interdiff_opcodes with replace overflowing range"""
        # In the case where there's a replace chunk with i2 or j2 larger than
        # the end position of the current range, the chunk would get chopped,
        # and the two replace ranges could be unequal. This broke an assertion
        # check when generating opcode metadata, and would result in a
        # corrupt-looking diff.
        #
        # This is bug #3440
        #
        # Before the fix, the below opcodes and diff ranges would result
        # in the replace turning into (2, 6, 2, 15), instead of staying at
        # (2, 15, 2, 15).
        #
        # This only really tends to happen in early ranges (since the range
        # numbers are small), but could also happen further into the diff
        # if a replace range is huge on one side.
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 2, 0, 2),
                ('replace', 2, 100, 2, 100),
            ],
            a_num_lines=110,
            b_num_lines=110,
            a_ranges=[
                (0, 6),
            ],
            b_ranges=[
                (0, 15),
            ],
            expected_opcodes=[
                ('equal', 0, 2, 0, 2),
                ('replace', 2, 15, 2, 15),
                ('filtered-equal', 15, 100, 15, 100),
            ],
        )

    def test_filter_interdiff_opcodes_with_trailing_context(self) -> None:
        """Testing filter_interdiff_opcodes with trailing context"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('replace', 0, 13, 0, 13),
                ('insert', 13, 13, 13, 14),
                ('replace', 13, 20, 14, 21),
            ],
            a_num_lines=20,
            b_num_lines=21,
            a_ranges=[
                (12, 13),
            ],
            b_ranges=[
                (13, 14),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 13, 0, 13),
                ('insert', 13, 13, 13, 14),
                ('filtered-equal', 13, 20, 14, 21),
            ],
        )

    #
    # The following tests are built on real-world interdiffs that have had
    # regressions in the past, and have been confirmed to have been fixed
    # at the time of commit. Further details are available internally.
    #

    def test_filter_interdiff_opcodes_with_customer_dataset_1(self) -> None:
        """Testing filter_interdiff_opcodes with customer dataset 1"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 5, 0, 5),
                ('delete', 5, 7, 5, 5),
                ('equal', 7, 40, 5, 38),
                ('delete', 40, 41, 38, 38),
                ('equal', 41, 42, 38, 39),
            ],
            a_num_lines=42,
            b_num_lines=39,
            a_ranges=[
                (5, 34),
                (36, 40),
            ],
            b_ranges=[
                (5, 38),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 5, 0, 5),
                ('delete', 5, 7, 5, 5),
                ('equal', 7, 40, 5, 38),
                ('filtered-equal', 40, 41, 38, 38),
                ('filtered-equal', 41, 42, 38, 39),
            ],
        )

    def test_filter_interdiff_opcodes_with_customer_dataset_2(self) -> None:
        """Testing filter_interdiff_opcodes with customer dataset 2"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 1005, 0, 1005),
                ('delete', 1005, 1016, 1005, 1005),
                ('equal', 1016, 1157, 1005, 1146),
                ('replace', 1157, 1158, 1146, 1147),
                ('equal', 1158, 1173, 1147, 1162),
                ('replace', 1173, 1174, 1162, 1163),
                ('insert', 1174, 1174, 1163, 1165),
                ('equal', 1174, 1216, 1165, 1207),
                ('replace', 1216, 1217, 1207, 1208),
                ('equal', 1217, 1522, 1208, 1513),
                ('delete', 1522, 1523, 1513, 1513),
                ('equal', 1523, 1534, 1513, 1524),
                ('insert', 1534, 1534, 1524, 1528),
                ('equal', 1534, 1761, 1528, 1755),
                ('replace', 1761, 1762, 1755, 1756),
                ('insert', 1762, 1762, 1756, 1757),
                ('equal', 1762, 4825, 1757, 4820),
                ('insert', 4825, 4825, 4820, 4823),
                ('equal', 4825, 4839, 4823, 4837),
                ('delete', 4839, 4840, 4837, 4837),
                ('equal', 4840, 4841, 4837, 4838),
                ('insert', 4841, 4841, 4838, 4839),
                ('equal', 4841, 5144, 4839, 5142),
                ('replace', 5144, 5147, 5142, 5145),
                ('equal', 5147, 5151, 5145, 5149),
                ('delete', 5151, 5161, 5149, 5149),
                ('equal', 5161, 5164, 5149, 5152),
                ('replace', 5164, 5165, 5152, 5153),
                ('equal', 5165, 5624, 5153, 5612),
                ('insert', 5624, 5624, 5612, 5613),
                ('equal', 5624, 5653, 5613, 5642),
                ('delete', 5653, 5654, 5642, 5642),
                ('equal', 5654, 5790, 5642, 5778),
            ],
            a_num_lines=5790,
            b_num_lines=5778,
            a_ranges=[
                (131, 132),
                (345, 404),
                (533, 537),
                (572, 574),
                (611, 612),
                (660, 661),
                (705, 706),
                (750, 751),
                (884, 889),
                (891, 893),
                (905, 908),
                (909, 910),
                (923, 924),
                (926, 927),
                (928, 943),
                (944, 945),
                (946, 947),
                (949, 953),
                (969, 971),
                (972, 974),
                (975, 976),
                (977, 979),
                (986, 987),
                (993, 1016),
                (1192, 1199),
                (1210, 1215),
                (1218, 1220),
                (1221, 1228),
                (1230, 1238),
                (1243, 1244),
                (1480, 1488),
                (1490, 1492),
                (1562, 1564),
                (1611, 1614),
                (1619, 1621),
                (1643, 1645),
                (1653, 1658),
                (1663, 1665),
                (1684, 1686),
                (1692, 1701),
                (1703, 1712),
                (1714, 1723),
                (1731, 1733),
                (1783, 1784),
                (1808, 1811),
                (1830, 1831),
                (1833, 1834),
                (1855, 1859),
                (1867, 1869),
                (1889, 1891),
                (1900, 1904),
                (1911, 1913),
                (1933, 1935),
                (1985, 1986),
                (2846, 2848),
                (2954, 2955),
                (3068, 3070),
                (3359, 3360),
                (3700, 3752),
                (3870, 3871),
                (3872, 3874),
                (3875, 3876),
                (3885, 3886),
                (3887, 3888),
                (3927, 3928),
                (3943, 3944),
                (3953, 3956),
                (3959, 3968),
                (4023, 4027),
                (4032, 4033),
                (4037, 4041),
                (4047, 4048),
                (4076, 4081),
                (4082, 4083),
                (4091, 4100),
                (4103, 4104),
                (4106, 4111),
                (4113, 4161),
                (4275, 4277),
                (4295, 4301),
                (4324, 4326),
                (4328, 4336),
                (4340, 4341),
                (4345, 4347),
                (4348, 4349),
                (4350, 4353),
                (4361, 4362),
                (4373, 4374),
                (4378, 4379),
                (4388, 4389),
                (4425, 4438),
                (4440, 4441),
                (4447, 4448),
                (4458, 4472),
                (4475, 4476),
                (4481, 4485),
                (4491, 4492),
                (4495, 4496),
                (4505, 4506),
                (4509, 4510),
                (4521, 4522),
                (4583, 4584),
                (4740, 4741),
                (4773, 4774),
                (4775, 4778),
                (4779, 4784),
                (4785, 4790),
                (4791, 4793),
                (4794, 4798),
                (4799, 4807),
                (4810, 4840),
                (5100, 5119),
                (5121, 5125),
                (5132, 5133),
                (5145, 5151),
                (5155, 5156),
                (5157, 5160),
                (5176, 5180),
                (5181, 5185),
                (5193, 5197),
                (5207, 5213),
                (5223, 5224),
                (5226, 5230),
                (5266, 5270),
                (5285, 5289),
                (5307, 5339),
                (5344, 5345),
                (5359, 5367),
                (5370, 5395),
                (5412, 5428),
                (5439, 5440),
                (5447, 5448),
                (5453, 5486),
                (5487, 5488),
                (5511, 5515),
                (5521, 5525),
                (5536, 5537),
                (5549, 5577),
                (5578, 5587),
                (5588, 5590),
                (5591, 5603),
                (5604, 5652),
                (5653, 5654),
                (5668, 5672),
            ],
            b_ranges=[
                (131, 132),
                (345, 404),
                (533, 537),
                (572, 574),
                (611, 612),
                (660, 661),
                (705, 706),
                (750, 751),
                (884, 889),
                (891, 893),
                (905, 908),
                (909, 910),
                (923, 924),
                (926, 927),
                (928, 943),
                (944, 945),
                (946, 947),
                (948, 952),
                (969, 971),
                (972, 974),
                (975, 976),
                (977, 979),
                (986, 987),
                (993, 1005),
                (1143, 1147),
                (1162, 1165),
                (1183, 1190),
                (1202, 1208),
                (1209, 1211),
                (1212, 1219),
                (1220, 1228),
                (1234, 1235),
                (1471, 1479),
                (1481, 1483),
                (1509, 1513),
                (1524, 1528),
                (1556, 1558),
                (1605, 1608),
                (1613, 1615),
                (1637, 1639),
                (1647, 1652),
                (1657, 1659),
                (1678, 1680),
                (1686, 1695),
                (1697, 1706),
                (1708, 1717),
                (1725, 1727),
                (1755, 1757),
                (1778, 1779),
                (1803, 1806),
                (1825, 1826),
                (1828, 1829),
                (1850, 1854),
                (1862, 1864),
                (1884, 1886),
                (1895, 1899),
                (1906, 1908),
                (1928, 1930),
                (1980, 1981),
                (2841, 2843),
                (2949, 2950),
                (3063, 3065),
                (3354, 3355),
                (3694, 3746),
                (3865, 3866),
                (3867, 3869),
                (3870, 3871),
                (3880, 3881),
                (3882, 3883),
                (3922, 3923),
                (3938, 3939),
                (3948, 3951),
                (3954, 3963),
                (4018, 4022),
                (4027, 4028),
                (4032, 4036),
                (4042, 4043),
                (4071, 4076),
                (4077, 4078),
                (4086, 4095),
                (4098, 4099),
                (4101, 4106),
                (4108, 4156),
                (4270, 4272),
                (4290, 4296),
                (4319, 4321),
                (4323, 4331),
                (4335, 4336),
                (4340, 4342),
                (4343, 4344),
                (4345, 4348),
                (4356, 4357),
                (4368, 4369),
                (4373, 4374),
                (4383, 4384),
                (4420, 4433),
                (4435, 4436),
                (4442, 4443),
                (4453, 4467),
                (4470, 4471),
                (4476, 4480),
                (4486, 4487),
                (4490, 4491),
                (4500, 4501),
                (4504, 4505),
                (4516, 4517),
                (4578, 4579),
                (4735, 4736),
                (4768, 4808),
                (4809, 4816),
                (4824, 4826),
                (4827, 4828),
                (4829, 4830),
                (4834, 4835),
                (5098, 5117),
                (5119, 5123),
                (5130, 5131),
                (5143, 5146),
                (5147, 5148),
                (5152, 5153),
                (5164, 5168),
                (5169, 5173),
                (5181, 5185),
                (5195, 5201),
                (5211, 5212),
                (5214, 5218),
                (5254, 5258),
                (5273, 5277),
                (5295, 5327),
                (5332, 5333),
                (5347, 5355),
                (5358, 5383),
                (5400, 5416),
                (5427, 5428),
                (5435, 5436),
                (5441, 5474),
                (5475, 5476),
                (5499, 5503),
                (5509, 5513),
                (5524, 5525),
                (5537, 5565),
                (5566, 5575),
                (5576, 5578),
                (5579, 5591),
                (5592, 5641),
                (5656, 5660),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 1005, 0, 1005),
                ('delete', 1005, 1016, 1005, 1005),
                ('filtered-equal', 1016, 1157, 1005, 1146),
                ('replace', 1157, 1158, 1146, 1147),
                ('filtered-equal', 1158, 1173, 1147, 1162),
                ('replace', 1173, 1174, 1162, 1163),
                ('insert', 1174, 1174, 1163, 1165),
                ('filtered-equal', 1174, 1216, 1165, 1207),
                ('replace', 1216, 1217, 1207, 1208),
                ('filtered-equal', 1217, 1522, 1208, 1513),
                ('filtered-equal', 1522, 1523, 1513, 1513),
                ('filtered-equal', 1523, 1534, 1513, 1524),
                ('insert', 1534, 1534, 1524, 1528),
                ('filtered-equal', 1534, 1761, 1528, 1755),
                ('replace', 1761, 1762, 1755, 1756),
                ('insert', 1762, 1762, 1756, 1757),
                ('filtered-equal', 1762, 4825, 1757, 4820),
                ('filtered-equal', 4825, 4825, 4820, 4823),
                ('equal', 4825, 4839, 4823, 4837),
                ('delete', 4839, 4840, 4837, 4837),
                ('filtered-equal', 4840, 4841, 4837, 4838),
                ('filtered-equal', 4841, 4841, 4838, 4839),
                ('filtered-equal', 4841, 5144, 4839, 5142),
                ('filtered-equal', 5144, 5145, 5142, 5143),
                ('replace', 5145, 5147, 5143, 5145),
                ('equal', 5147, 5151, 5145, 5149),
                ('filtered-equal', 5151, 5155, 5149, 5149),
                ('delete', 5155, 5156, 5149, 5149),
                ('filtered-equal', 5156, 5157, 5149, 5149),
                ('delete', 5157, 5160, 5149, 5149),
                ('filtered-equal', 5160, 5161, 5149, 5149),
                ('filtered-equal', 5161, 5164, 5149, 5152),
                ('replace', 5164, 5165, 5152, 5153),
                ('filtered-equal', 5165, 5624, 5153, 5612),
                ('insert', 5624, 5624, 5612, 5613),
                ('equal', 5624, 5652, 5613, 5641),
                ('filtered-equal', 5652, 5653, 5641, 5642),
                ('delete', 5653, 5654, 5642, 5642),
                ('filtered-equal', 5654, 5790, 5642, 5778),
            ],
        )

    def test_filter_interdiff_opcodes_with_customer_dataset_3(self) -> None:
        """Testing filter_interdiff_opcodes with customer dataset 3"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 1740, 0, 1740),
                ('replace', 1740, 1741, 1740, 1741),
                ('delete', 1741, 1744, 1741, 1741),
                ('equal', 1744, 1746, 1741, 1743),
                ('insert', 1746, 1746, 1743, 1744),
                ('equal', 1746, 1748, 1744, 1746),
                ('insert', 1748, 1748, 1746, 1747),
                ('equal', 1748, 1749, 1747, 1748),
                ('delete', 1749, 1750, 1748, 1748),
                ('equal', 1750, 1792, 1748, 1790),
                ('replace', 1792, 1793, 1790, 1791),
                ('equal', 1793, 2031, 1791, 2029),
            ],
            a_num_lines=2031,
            b_num_lines=2029,
            a_ranges=[
                (79, 81),
                (141, 142),
                (1692, 1693),
                (1737, 1738),
                (1754, 1814),
            ],
            b_ranges=[
                (79, 81),
                (141, 142),
                (1692, 1693),
                (1737, 1738),
                (1740, 1742),
                (1743, 1744),
                (1745, 1747),
                (1748, 1749),
                (1752, 1812),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 1740, 0, 1740),
                ('replace', 1740, 1741, 1740, 1741),
                ('filtered-equal', 1741, 1744, 1741, 1741),
                ('equal', 1744, 1746, 1741, 1743),
                ('insert', 1746, 1746, 1743, 1744),
                ('filtered-equal', 1746, 1748, 1744, 1746),
                ('insert', 1748, 1748, 1746, 1747),
                ('filtered-equal', 1748, 1749, 1747, 1748),
                ('filtered-equal', 1749, 1750, 1748, 1748),
                ('equal', 1750, 1792, 1748, 1790),
                ('replace', 1792, 1793, 1790, 1791),
                ('equal', 1793, 1814, 1791, 1812),
                ('filtered-equal', 1814, 2031, 1812, 2029),
            ],
        )

    def test_filter_interdiff_opcodes_with_customer_dataset_4(self) -> None:
        """Testing filter_interdiff_opcodes with customer dataset 4"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 59, 0, 59),
                ('delete', 59, 77, 59, 59),
                ('equal', 77, 160, 59, 142),
                ('replace', 160, 161, 142, 143),
                ('insert', 161, 161, 143, 151),
                ('equal', 161, 193, 151, 183),
                ('replace', 193, 194, 183, 184),
                ('insert', 194, 194, 184, 192),
                ('equal', 194, 700, 192, 698),
            ],
            a_num_lines=700,
            b_num_lines=698,
            a_ranges=[
                (47, 48),
                (58, 77),
                (160, 162),
                (188, 220),
            ],
            b_ranges=[
                (47, 48),
                (58, 59),
                (145, 153),
                (178, 218),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 59, 0, 59),
                ('delete', 59, 77, 59, 59),
                ('filtered-equal', 77, 160, 59, 142),
                ('replace', 160, 161, 142, 143),
                ('filtered-equal', 161, 161, 143, 145),
                ('insert', 161, 161, 145, 151),
                ('equal', 161, 163, 151, 153),
                ('filtered-equal', 163, 193, 153, 183),
                ('replace', 193, 194, 183, 184),
                ('insert', 194, 194, 184, 192),
                ('equal', 194, 220, 192, 218),
                ('filtered-equal', 220, 700, 218, 698),
            ],
        )

    def test_filter_interdiff_opcodes_with_customer_dataset_5(self) -> None:
        """Testing filter_interdiff_opcodes with customer dataset 5"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 112, 0, 112),
                ('insert', 112, 112, 112, 353),
                ('equal', 112, 310, 353, 551),
                ('insert', 310, 310, 551, 552),
                ('equal', 310, 946, 552, 1188),
                ('replace', 946, 948, 1188, 1190),
                ('equal', 948, 953, 1190, 1195),
                ('replace', 953, 955, 1195, 1197),
                ('insert', 955, 955, 1197, 1198),
                ('equal', 955, 966, 1198, 1209),
                ('replace', 966, 967, 1209, 1210),
                ('insert', 967, 967, 1210, 1211),
                ('equal', 967, 1011, 1211, 1255),
                ('replace', 1011, 1012, 1255, 1256),
                ('insert', 1012, 1012, 1256, 1257),
                ('equal', 1012, 1020, 1257, 1265),
                ('insert', 1020, 1020, 1265, 2135),
            ],
            a_num_lines=1020,
            b_num_lines=2135,
            a_ranges=[
                (14, 15),
                (17, 38),
                (40, 56),
                (58, 74),
                (76, 92),
                (94, 110),
                (312, 313),
                (315, 320),
                (329, 330),
                (332, 337),
                (340, 345),
                (348, 353),
                (363, 364),
                (366, 371),
                (374, 379),
                (382, 387),
                (391, 396),
                (418, 419),
                (421, 426),
                (429, 434),
                (437, 442),
                (446, 451),
                (473, 474),
                (476, 481),
                (484, 489),
                (492, 497),
                (501, 506),
                (526, 527),
                (529, 534),
                (537, 542),
                (545, 550),
                (554, 559),
                (577, 578),
                (580, 585),
                (588, 593),
                (596, 601),
                (605, 610),
                (629, 630),
                (632, 637),
                (642, 647),
                (652, 657),
                (679, 680),
                (682, 687),
                (692, 697),
                (713, 714),
                (716, 721),
                (730, 731),
                (733, 742),
                (818, 819),
                (821, 826),
                (831, 836),
                (840, 847),
                (868, 869),
                (871, 876),
                (881, 886),
                (890, 901),
                (906, 911),
                (916, 921),
                (948, 949),
                (952, 969),
                (973, 978),
                (982, 987),
                (991, 996),
                (1000, 1005),
            ],
            b_ranges=[
                (14, 15),
                (17, 38),
                (40, 56),
                (58, 74),
                (76, 92),
                (94, 110),
                (554, 555),
                (557, 562),
                (571, 572),
                (574, 579),
                (582, 587),
                (590, 595),
                (605, 606),
                (608, 613),
                (616, 621),
                (624, 629),
                (633, 638),
                (660, 661),
                (663, 668),
                (671, 676),
                (679, 684),
                (688, 693),
                (715, 716),
                (718, 723),
                (726, 731),
                (734, 739),
                (743, 748),
                (768, 769),
                (771, 776),
                (779, 784),
                (787, 792),
                (796, 801),
                (819, 820),
                (822, 827),
                (830, 835),
                (838, 843),
                (847, 852),
                (871, 872),
                (874, 879),
                (884, 889),
                (894, 899),
                (921, 922),
                (924, 929),
                (934, 939),
                (955, 956),
                (958, 963),
                (972, 973),
                (975, 984),
                (1060, 1061),
                (1063, 1068),
                (1073, 1078),
                (1082, 1089),
                (1110, 1111),
                (1113, 1118),
                (1123, 1128),
                (1132, 1143),
                (1148, 1153),
                (1158, 1163),
                (1190, 1191),
                (1194, 1213),
                (1217, 1222),
                (1226, 1231),
                (1235, 1240),
                (1244, 1249),
                (1271, 1272),
                (1274, 1279),
                (1282, 1287),
                (1290, 1295),
                (1298, 1301),
                (1308, 1312),
                (1316, 1321),
                (1325, 1330),
                (1333, 1338),
                (1342, 1347),
                (1351, 1356),
                (1359, 1362),
                (1370, 1374),
                (1378, 1383),
                (1387, 1392),
                (1433, 1434),
                (1436, 1441),
                (1444, 1449),
                (1452, 1455),
                (1462, 1466),
                (1470, 1475),
                (1479, 1484),
                (1488, 1493),
                (1497, 1502),
                (1506, 1511),
                (1515, 1520),
                (1524, 1529),
                (1532, 1537),
                (1541, 1546),
                (1550, 1555),
                (1559, 1564),
                (1568, 1573),
                (1577, 1582),
                (1586, 1591),
                (1595, 1600),
                (1640, 1641),
                (1643, 1648),
                (1652, 1657),
                (1661, 1673),
                (1677, 1682),
                (1686, 1691),
                (1695, 1700),
                (1705, 1710),
                (1714, 1719),
                (1723, 1728),
                (1731, 1743),
                (1747, 1752),
                (1756, 1761),
                (1765, 1770),
                (1773, 1778),
                (1782, 1787),
                (1791, 1796),
                (1800, 1805),
                (1809, 1814),
                (1818, 1823),
                (1851, 1852),
                (1854, 1859),
                (1863, 1868),
                (1872, 1884),
                (1888, 1893),
                (1897, 1902),
                (1906, 1911),
                (1916, 1921),
                (1925, 1930),
                (1934, 1939),
                (1942, 1954),
                (1958, 1963),
                (1967, 1972),
                (1976, 1981),
                (1985, 1990),
                (1994, 1999),
                (2003, 2008),
                (2012, 2017),
                (2021, 2026),
                (2029, 2034),
                (2038, 2043),
                (2047, 2052),
                (2056, 2061),
                (2065, 2070),
                (2074, 2079),
                (2083, 2088),
                (2092, 2097),
                (2101, 2106),
                (2110, 2115),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 112, 0, 112),
                ('filtered-equal', 112, 112, 112, 353),
                ('filtered-equal', 112, 310, 353, 551),
                ('filtered-equal', 310, 310, 551, 552),
                ('filtered-equal', 310, 946, 552, 1188),
                ('filtered-equal', 946, 948, 1188, 1190),
                ('equal', 948, 949, 1190, 1191),
                ('filtered-equal', 949, 953, 1191, 1195),
                ('replace', 953, 955, 1195, 1197),
                ('insert', 955, 955, 1197, 1198),
                ('equal', 955, 966, 1198, 1209),
                ('replace', 966, 967, 1209, 1210),
                ('insert', 967, 967, 1210, 1211),
                ('equal', 967, 969, 1211, 1213),
                ('filtered-equal', 969, 1011, 1213, 1255),
                ('filtered-equal', 1011, 1012, 1255, 1256),
                ('filtered-equal', 1012, 1012, 1256, 1257),
                ('filtered-equal', 1012, 1020, 1257, 1265),
                ('filtered-equal', 1020, 1020, 1265, 1271),
                ('insert', 1020, 1020, 1271, 1272),
                ('filtered-equal', 1020, 1020, 1272, 1274),
                ('insert', 1020, 1020, 1274, 1279),
                ('filtered-equal', 1020, 1020, 1279, 1282),
                ('insert', 1020, 1020, 1282, 1287),
                ('filtered-equal', 1020, 1020, 1287, 1290),
                ('insert', 1020, 1020, 1290, 1295),
                ('filtered-equal', 1020, 1020, 1295, 1298),
                ('insert', 1020, 1020, 1298, 1301),
                ('filtered-equal', 1020, 1020, 1301, 1308),
                ('insert', 1020, 1020, 1308, 1312),
                ('filtered-equal', 1020, 1020, 1312, 1316),
                ('insert', 1020, 1020, 1316, 1321),
                ('filtered-equal', 1020, 1020, 1321, 1325),
                ('insert', 1020, 1020, 1325, 1330),
                ('filtered-equal', 1020, 1020, 1330, 1333),
                ('insert', 1020, 1020, 1333, 1338),
                ('filtered-equal', 1020, 1020, 1338, 1342),
                ('insert', 1020, 1020, 1342, 1347),
                ('filtered-equal', 1020, 1020, 1347, 1351),
                ('insert', 1020, 1020, 1351, 1356),
                ('filtered-equal', 1020, 1020, 1356, 1359),
                ('insert', 1020, 1020, 1359, 1362),
                ('filtered-equal', 1020, 1020, 1362, 1370),
                ('insert', 1020, 1020, 1370, 1374),
                ('filtered-equal', 1020, 1020, 1374, 1378),
                ('insert', 1020, 1020, 1378, 1383),
                ('filtered-equal', 1020, 1020, 1383, 1387),
                ('insert', 1020, 1020, 1387, 1392),
                ('filtered-equal', 1020, 1020, 1392, 1433),
                ('insert', 1020, 1020, 1433, 1434),
                ('filtered-equal', 1020, 1020, 1434, 1436),
                ('insert', 1020, 1020, 1436, 1441),
                ('filtered-equal', 1020, 1020, 1441, 1444),
                ('insert', 1020, 1020, 1444, 1449),
                ('filtered-equal', 1020, 1020, 1449, 1452),
                ('insert', 1020, 1020, 1452, 1455),
                ('filtered-equal', 1020, 1020, 1455, 1462),
                ('insert', 1020, 1020, 1462, 1466),
                ('filtered-equal', 1020, 1020, 1466, 1470),
                ('insert', 1020, 1020, 1470, 1475),
                ('filtered-equal', 1020, 1020, 1475, 1479),
                ('insert', 1020, 1020, 1479, 1484),
                ('filtered-equal', 1020, 1020, 1484, 1488),
                ('insert', 1020, 1020, 1488, 1493),
                ('filtered-equal', 1020, 1020, 1493, 1497),
                ('insert', 1020, 1020, 1497, 1502),
                ('filtered-equal', 1020, 1020, 1502, 1506),
                ('insert', 1020, 1020, 1506, 1511),
                ('filtered-equal', 1020, 1020, 1511, 1515),
                ('insert', 1020, 1020, 1515, 1520),
                ('filtered-equal', 1020, 1020, 1520, 1524),
                ('insert', 1020, 1020, 1524, 1529),
                ('filtered-equal', 1020, 1020, 1529, 1532),
                ('insert', 1020, 1020, 1532, 1537),
                ('filtered-equal', 1020, 1020, 1537, 1541),
                ('insert', 1020, 1020, 1541, 1546),
                ('filtered-equal', 1020, 1020, 1546, 1550),
                ('insert', 1020, 1020, 1550, 1555),
                ('filtered-equal', 1020, 1020, 1555, 1559),
                ('insert', 1020, 1020, 1559, 1564),
                ('filtered-equal', 1020, 1020, 1564, 1568),
                ('insert', 1020, 1020, 1568, 1573),
                ('filtered-equal', 1020, 1020, 1573, 1577),
                ('insert', 1020, 1020, 1577, 1582),
                ('filtered-equal', 1020, 1020, 1582, 1586),
                ('insert', 1020, 1020, 1586, 1591),
                ('filtered-equal', 1020, 1020, 1591, 1595),
                ('insert', 1020, 1020, 1595, 1600),
                ('filtered-equal', 1020, 1020, 1600, 1640),
                ('insert', 1020, 1020, 1640, 1641),
                ('filtered-equal', 1020, 1020, 1641, 1643),
                ('insert', 1020, 1020, 1643, 1648),
                ('filtered-equal', 1020, 1020, 1648, 1652),
                ('insert', 1020, 1020, 1652, 1657),
                ('filtered-equal', 1020, 1020, 1657, 1661),
                ('insert', 1020, 1020, 1661, 1673),
                ('filtered-equal', 1020, 1020, 1673, 1677),
                ('insert', 1020, 1020, 1677, 1682),
                ('filtered-equal', 1020, 1020, 1682, 1686),
                ('insert', 1020, 1020, 1686, 1691),
                ('filtered-equal', 1020, 1020, 1691, 1695),
                ('insert', 1020, 1020, 1695, 1700),
                ('filtered-equal', 1020, 1020, 1700, 1705),
                ('insert', 1020, 1020, 1705, 1710),
                ('filtered-equal', 1020, 1020, 1710, 1714),
                ('insert', 1020, 1020, 1714, 1719),
                ('filtered-equal', 1020, 1020, 1719, 1723),
                ('insert', 1020, 1020, 1723, 1728),
                ('filtered-equal', 1020, 1020, 1728, 1731),
                ('insert', 1020, 1020, 1731, 1743),
                ('filtered-equal', 1020, 1020, 1743, 1747),
                ('insert', 1020, 1020, 1747, 1752),
                ('filtered-equal', 1020, 1020, 1752, 1756),
                ('insert', 1020, 1020, 1756, 1761),
                ('filtered-equal', 1020, 1020, 1761, 1765),
                ('insert', 1020, 1020, 1765, 1770),
                ('filtered-equal', 1020, 1020, 1770, 1773),
                ('insert', 1020, 1020, 1773, 1778),
                ('filtered-equal', 1020, 1020, 1778, 1782),
                ('insert', 1020, 1020, 1782, 1787),
                ('filtered-equal', 1020, 1020, 1787, 1791),
                ('insert', 1020, 1020, 1791, 1796),
                ('filtered-equal', 1020, 1020, 1796, 1800),
                ('insert', 1020, 1020, 1800, 1805),
                ('filtered-equal', 1020, 1020, 1805, 1809),
                ('insert', 1020, 1020, 1809, 1814),
                ('filtered-equal', 1020, 1020, 1814, 1818),
                ('insert', 1020, 1020, 1818, 1823),
                ('filtered-equal', 1020, 1020, 1823, 1851),
                ('insert', 1020, 1020, 1851, 1852),
                ('filtered-equal', 1020, 1020, 1852, 1854),
                ('insert', 1020, 1020, 1854, 1859),
                ('filtered-equal', 1020, 1020, 1859, 1863),
                ('insert', 1020, 1020, 1863, 1868),
                ('filtered-equal', 1020, 1020, 1868, 1872),
                ('insert', 1020, 1020, 1872, 1884),
                ('filtered-equal', 1020, 1020, 1884, 1888),
                ('insert', 1020, 1020, 1888, 1893),
                ('filtered-equal', 1020, 1020, 1893, 1897),
                ('insert', 1020, 1020, 1897, 1902),
                ('filtered-equal', 1020, 1020, 1902, 1906),
                ('insert', 1020, 1020, 1906, 1911),
                ('filtered-equal', 1020, 1020, 1911, 1916),
                ('insert', 1020, 1020, 1916, 1921),
                ('filtered-equal', 1020, 1020, 1921, 1925),
                ('insert', 1020, 1020, 1925, 1930),
                ('filtered-equal', 1020, 1020, 1930, 1934),
                ('insert', 1020, 1020, 1934, 1939),
                ('filtered-equal', 1020, 1020, 1939, 1942),
                ('insert', 1020, 1020, 1942, 1954),
                ('filtered-equal', 1020, 1020, 1954, 1958),
                ('insert', 1020, 1020, 1958, 1963),
                ('filtered-equal', 1020, 1020, 1963, 1967),
                ('insert', 1020, 1020, 1967, 1972),
                ('filtered-equal', 1020, 1020, 1972, 1976),
                ('insert', 1020, 1020, 1976, 1981),
                ('filtered-equal', 1020, 1020, 1981, 1985),
                ('insert', 1020, 1020, 1985, 1990),
                ('filtered-equal', 1020, 1020, 1990, 1994),
                ('insert', 1020, 1020, 1994, 1999),
                ('filtered-equal', 1020, 1020, 1999, 2003),
                ('insert', 1020, 1020, 2003, 2008),
                ('filtered-equal', 1020, 1020, 2008, 2012),
                ('insert', 1020, 1020, 2012, 2017),
                ('filtered-equal', 1020, 1020, 2017, 2021),
                ('insert', 1020, 1020, 2021, 2026),
                ('filtered-equal', 1020, 1020, 2026, 2029),
                ('insert', 1020, 1020, 2029, 2034),
                ('filtered-equal', 1020, 1020, 2034, 2038),
                ('insert', 1020, 1020, 2038, 2043),
                ('filtered-equal', 1020, 1020, 2043, 2047),
                ('insert', 1020, 1020, 2047, 2052),
                ('filtered-equal', 1020, 1020, 2052, 2056),
                ('insert', 1020, 1020, 2056, 2061),
                ('filtered-equal', 1020, 1020, 2061, 2065),
                ('insert', 1020, 1020, 2065, 2070),
                ('filtered-equal', 1020, 1020, 2070, 2074),
                ('insert', 1020, 1020, 2074, 2079),
                ('filtered-equal', 1020, 1020, 2079, 2083),
                ('insert', 1020, 1020, 2083, 2088),
                ('filtered-equal', 1020, 1020, 2088, 2092),
                ('insert', 1020, 1020, 2092, 2097),
                ('filtered-equal', 1020, 1020, 2097, 2101),
                ('insert', 1020, 1020, 2101, 2106),
                ('filtered-equal', 1020, 1020, 2106, 2110),
                ('insert', 1020, 1020, 2110, 2115),
                ('filtered-equal', 1020, 1020, 2115, 2135),
            ],
        )

    def test_filter_interdiff_opcodes_with_customer_dataset_6(self) -> None:
        """Testing filter_interdiff_opcodes with customer dataset 6"""
        self._run_test_filter_interdiff_opcodes(
            opcodes=[
                ('equal', 0, 9, 0, 9),
                ('replace', 9, 10, 9, 10),
                ('insert', 10, 10, 10, 13),
                ('equal', 10, 36, 13, 39),
                ('insert', 36, 36, 39, 40),
                ('equal', 36, 156, 40, 160),
            ],
            a_num_lines=156,
            b_num_lines=160,
            a_ranges=[
                (2, 5),
                (6, 7),
                (9, 10),
                (12, 17),
                (23, 24),
                (33, 36),
                (52, 57),
                (60, 78),
                (81, 86),
                (88, 90),
                (98, 100),
                (103, 156),
            ],
            b_ranges=[
                (2, 5),
                (6, 7),
                (9, 13),
                (15, 20),
                (26, 27),
                (36, 40),
                (56, 61),
                (64, 82),
                (85, 90),
                (92, 94),
                (102, 104),
                (107, 160),
            ],
            expected_opcodes=[
                ('filtered-equal', 0, 9, 0, 9),
                ('replace', 9, 10, 9, 10),
                ('insert', 10, 10, 10, 13),
                ('filtered-equal', 10, 36, 13, 39),
                ('insert', 36, 36, 39, 40),
                ('filtered-equal', 36, 156, 40, 160),
            ],
        )

    def _sanity_check_opcodes(self, opcodes):
        prev_i2 = None
        prev_j2 = None

        for index, opcode in enumerate(opcodes):
            tag, i1, i2, j1, j2 = opcode

            if tag in ('equal', 'replace'):
                i_range = i2 - i1
                j_range = j2 - j1

                self.assertEqual(
                    (i2 - i1), (j2 - j1),
                    'Ranges are not equal for opcode index %s: %r. Got '
                    'i_range=%s, j_range=%s'
                    % (index, opcode, i_range, j_range))
            elif tag == 'insert':
                self.assertEqual(
                    i1, i2,
                    'i range should not change for opcode index %s: %r. Got '
                    'i1=%s, i2=%s'
                    % (index, opcode, i1, i2))
            elif tag == 'delete':
                self.assertEqual(
                    j1, j2,
                    'j range should not change for opcode index %s: %r. Got '
                    'j1=%s, j2=%s'
                    % (index, opcode, j1, j2))

            if prev_i2 is not None and prev_j2 is not None:
                self.assertEqual(i1, prev_i2)
                self.assertEqual(j1, prev_j2)

            prev_i2 = i2
            prev_j2 = j2

    def _run_test_filter_interdiff_opcodes(
        self,
        *,
        opcodes: Iterable[tuple[str, int, int, int, int]],
        a_num_lines: int,
        b_num_lines: int,
        a_ranges: Iterable[tuple[int, int]],
        b_ranges: Iterable[tuple[int, int]],
        expected_opcodes: Sequence[tuple[str, int, int, int, int]],
    ) -> None:
        """Perform a filtered interdiff test with the provided arguments.

        This will take the provided interdiff opcodes and information on
        changes made to the original and patched files and run them through
        the interdiff filtering process, comparing the results against the
        expected opcodes.

        Version Added:
            8.0

        Args:
            opcodes (list of tuple):
                The opcodes from the interdiff.

            a_num_lines (int):
                Total number of lines in the patched file for the filediff.

            b_num_lines (int):
                Total number of lines in the patched file for the
                interfilediff.

            a_ranges (list of tuple):
                List of ``(start, end)`` ranges for changes in the filediff.

            b_ranges (list of tuple):
                List of ``(start, end)`` ranges for changes in the
                interfilediff.
        """
        self._sanity_check_opcodes(expected_opcodes)

        a = [
            f'equal line {i}'
            for i in range(a_num_lines)
        ]

        b = [
            f'equal line {i}'
            for i in range(b_num_lines)
        ]

        filediff_orig_lines = list(a)
        interfilediff_orig_lines = list(b)

        for start, end in a_ranges:
            for i in range(start, end):
                filediff_orig_lines[i] = f'rev1 orig line {i}'
                a[i] = f'rev1 changed line {i}'

        for start, end in b_ranges:
            for i in range(start, end):
                interfilediff_orig_lines[i] = f'rev2 orig line {i}'
                b[i] = f'rev2 changed line {i}'

        differ = get_differ(a, b)

        new_opcodes = list(filter_interdiff_opcodes(
            opcodes=opcodes,
            filediff_orig_lines=filediff_orig_lines,
            interfilediff_orig_lines=interfilediff_orig_lines,
            differ=differ,
        ))

        self._sanity_check_opcodes(new_opcodes)
        self.assertEqual(new_opcodes, expected_opcodes)


class PostProcessFilteredEqualsTests(TestCase):
    """Unit tests for post_process_filtered_equals."""

    def test_post_process_filtered_equals(self):
        """Testing post_process_filtered_equals"""
        opcodes = [
            ('equal', 0, 10, 0, 10, {}),
            ('insert', 10, 20, 0, 10, {}),
            ('equal', 20, 30, 10, 20, {}),
            ('equal', 30, 40, 20, 30, {}),
            ('filtered-equal', 40, 50, 30, 40, {}),
        ]

        new_opcodes = list(post_process_filtered_equals(opcodes))

        self.assertEqual(
            new_opcodes,
            [
                ('equal', 0, 10, 0, 10, {}),
                ('insert', 10, 20, 0, 10, {}),
                ('equal', 20, 50, 10, 40, {}),
            ])

    def test_post_process_filtered_equals_with_indentation(self):
        """Testing post_process_filtered_equals with indentation changes"""
        opcodes = [
            ('equal', 0, 10, 0, 10, {}),
            ('insert', 10, 20, 0, 10, {}),
            ('equal', 20, 30, 10, 20, {
                'indentation_changes': {
                    '21-11': (True, 4),
                }
            }),
            ('equal', 30, 40, 20, 30, {}),
            ('filtered-equal', 30, 50, 20, 40, {}),
        ]

        new_opcodes = list(post_process_filtered_equals(opcodes))

        self.assertEqual(
            new_opcodes,
            [
                ('equal', 0, 10, 0, 10, {}),
                ('insert', 10, 20, 0, 10, {}),
                ('equal', 20, 30, 10, 20, {
                    'indentation_changes': {
                        '21-11': (True, 4),
                    }
                }),
                ('equal', 30, 50, 20, 40, {}),
            ])

    def test_post_process_filtered_equals_with_adjacent_indentation(self):
        """Testing post_process_filtered_equals with
        adjacent indentation changes
        """
        opcodes = [
            ('equal', 0, 10, 0, 10, {}),
            ('insert', 10, 20, 0, 10, {}),
            ('equal', 20, 30, 10, 20, {
                'indentation_changes': {
                    '21-11': (True, 4),
                }
            }),
            ('equal', 30, 40, 20, 30, {
                'indentation_changes': {
                    '31-21': (False, 8),
                }
            }),
            ('filtered-equal', 40, 50, 30, 40, {}),
        ]

        new_opcodes = list(post_process_filtered_equals(opcodes))

        self.assertEqual(
            new_opcodes,
            [
                ('equal', 0, 10, 0, 10, {}),
                ('insert', 10, 20, 0, 10, {}),
                ('equal', 20, 30, 10, 20, {
                    'indentation_changes': {
                        '21-11': (True, 4),
                    }
                }),
                ('equal', 30, 40, 20, 30, {
                    'indentation_changes': {
                        '31-21': (False, 8),
                    }
                }),
                ('equal', 40, 50, 30, 40, {}),
            ])
