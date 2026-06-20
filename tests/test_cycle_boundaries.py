from datetime import date

import pytest

from app.services.cycle_service import CycleService


# _validate_cycle_boundaries is a staticmethod, so we can test it directly
validate = CycleService._validate_cycle_boundaries


class TestMonthly:
    def test_valid_january_2026(self):
        validate(1, date(2026, 1, 1), date(2026, 1, 31))

    def test_valid_february_2026(self):
        validate(1, date(2026, 2, 1), date(2026, 2, 28))

    def test_valid_february_leap_year(self):
        validate(1, date(2024, 2, 1), date(2024, 2, 29))

    def test_valid_december(self):
        validate(1, date(2026, 12, 1), date(2026, 12, 31))

    def test_invalid_start_not_first_day(self):
        with pytest.raises(ValueError, match="第一天"):
            validate(1, date(2026, 6, 15), date(2026, 6, 30))

    def test_invalid_end_wrong_day(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(1, date(2026, 6, 1), date(2026, 6, 15))

    def test_invalid_end_from_other_month(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(1, date(2026, 6, 1), date(2026, 7, 31))


class TestBimonthly:
    def test_valid_jan_feb(self):
        validate(2, date(2026, 1, 1), date(2026, 2, 28))

    def test_valid_feb_mar_leap_year(self):
        validate(2, date(2024, 2, 1), date(2024, 3, 31))

    def test_valid_dec_jan_year_rollover(self):
        validate(2, date(2026, 12, 1), date(2027, 1, 31))

    def test_valid_jul_aug(self):
        validate(2, date(2026, 7, 1), date(2026, 8, 31))

    def test_invalid_end_too_short(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(2, date(2026, 3, 1), date(2026, 3, 31))

    def test_invalid_end_three_months(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(2, date(2026, 3, 1), date(2026, 5, 31))


class TestQuarterly:
    def test_valid_q1(self):
        validate(3, date(2026, 1, 1), date(2026, 3, 31))

    def test_valid_q2(self):
        validate(3, date(2026, 4, 1), date(2026, 6, 30))

    def test_valid_q3(self):
        validate(3, date(2026, 7, 1), date(2026, 9, 30))

    def test_valid_q4(self):
        validate(3, date(2026, 10, 1), date(2026, 12, 31))

    def test_valid_q1_leap_year(self):
        validate(3, date(2024, 1, 1), date(2024, 3, 31))

    def test_invalid_start_month_feb(self):
        with pytest.raises(ValueError, match="1 月、4 月、7 月或 10 月"):
            validate(3, date(2026, 2, 1), date(2026, 3, 31))

    def test_invalid_start_month_may(self):
        with pytest.raises(ValueError, match="1 月、4 月、7 月或 10 月"):
            validate(3, date(2026, 5, 1), date(2026, 6, 30))

    def test_invalid_start_month_aug(self):
        with pytest.raises(ValueError, match="1 月、4 月、7 月或 10 月"):
            validate(3, date(2026, 8, 1), date(2026, 9, 30))

    def test_invalid_start_month_nov(self):
        with pytest.raises(ValueError, match="1 月、4 月、7 月或 10 月"):
            validate(3, date(2026, 11, 1), date(2026, 12, 31))

    def test_invalid_end_wrong_quarter(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(3, date(2026, 1, 1), date(2026, 6, 30))

    def test_invalid_start_not_first_day(self):
        with pytest.raises(ValueError, match="第一天"):
            validate(3, date(2026, 1, 15), date(2026, 3, 31))


class TestHalfYear:
    def test_valid_h1(self):
        validate(4, date(2026, 1, 1), date(2026, 6, 30))

    def test_valid_h2(self):
        validate(4, date(2026, 7, 1), date(2026, 12, 31))

    def test_invalid_start_month_feb(self):
        with pytest.raises(ValueError, match="1 月或 7 月"):
            validate(4, date(2026, 2, 1), date(2026, 6, 30))

    def test_invalid_start_month_aug(self):
        with pytest.raises(ValueError, match="1 月或 7 月"):
            validate(4, date(2026, 8, 1), date(2026, 12, 31))

    def test_invalid_end_wrong_half(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(4, date(2026, 1, 1), date(2026, 12, 31))


class TestYearly:
    def test_valid(self):
        validate(5, date(2026, 1, 1), date(2026, 12, 31))

    def test_invalid_start_not_jan(self):
        with pytest.raises(ValueError, match="1 月 1 日"):
            validate(5, date(2026, 3, 1), date(2026, 12, 31))

    def test_invalid_start_feb(self):
        with pytest.raises(ValueError, match="1 月 1 日"):
            validate(5, date(2026, 2, 1), date(2026, 12, 31))

    def test_invalid_end_not_dec_31(self):
        with pytest.raises(ValueError, match="12 月 31 日"):
            validate(5, date(2026, 1, 1), date(2026, 11, 30))


class TestCommon:
    """Common validation across all types."""

    def test_invalid_start_not_first_day_monthly(self):
        with pytest.raises(ValueError, match="第一天"):
            validate(1, date(2026, 5, 10), date(2026, 5, 31))

    def test_invalid_start_not_first_day_bimonthly(self):
        with pytest.raises(ValueError, match="第一天"):
            validate(2, date(2026, 5, 10), date(2026, 6, 30))

    def test_invalid_type_zero(self):
        with pytest.raises(ValueError, match="无效的周期类型"):
            validate(0, date(2026, 1, 1), date(2026, 12, 31))

    def test_invalid_type_six(self):
        with pytest.raises(ValueError, match="无效的周期类型"):
            validate(6, date(2026, 1, 1), date(2026, 12, 31))


class TestDateRangeMismatchCycle:
    """日期范围与周期类型不匹配 —— 虽然起止日都是某月1日/末日，但落在错误的区间。"""

    # ── 月度：日期跨到其他月份 ──

    def test_monthly_span_two_months(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(1, date(2026, 6, 1), date(2026, 7, 31))

    def test_monthly_start_jun_end_aug(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(1, date(2026, 6, 1), date(2026, 8, 31))

    # ── 双月度：日期跨到第三个月 ──

    def test_bimonthly_span_three_months(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(2, date(2026, 3, 1), date(2026, 5, 31))

    # ── 季度：日期横向偏移 ──

    def test_quarterly_start_q1_end_q2(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(3, date(2026, 1, 1), date(2026, 6, 30))

    def test_quarterly_start_q2_end_q3(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(3, date(2026, 4, 1), date(2026, 9, 30))

    def test_quarterly_start_jan_end_apr(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(3, date(2026, 1, 1), date(2026, 4, 30))

    def test_quarterly_start_oct_end_mar(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(3, date(2026, 10, 1), date(2027, 3, 31))

    def test_quarterly_start_jan31_end_apr30(self):
        with pytest.raises(ValueError, match="第一天"):
            validate(3, date(2026, 1, 31), date(2026, 4, 30))

    # ── 半年度：日期跨过半年分界线 ──

    def test_halfyear_h1_end_h2(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(4, date(2026, 1, 1), date(2026, 9, 30))

    def test_halfyear_h2_end_next_h1(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(4, date(2026, 7, 1), date(2027, 6, 30))

    def test_halfyear_h1_with_h2_range(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(4, date(2026, 1, 1), date(2026, 12, 31))

    # ── 年度：日期不是完整的一年 ──

    def test_yearly_only_h1(self):
        with pytest.raises(ValueError, match="12 月 31 日"):
            validate(5, date(2026, 1, 1), date(2026, 6, 30))

    def test_yearly_only_q1(self):
        with pytest.raises(ValueError, match="12 月 31 日"):
            validate(5, date(2026, 1, 1), date(2026, 3, 31))

    def test_yearly_only_eleven_months(self):
        with pytest.raises(ValueError, match="12 月 31 日"):
            validate(5, date(2026, 1, 1), date(2026, 11, 30))

    def test_yearly_start_not_jan_end_dec(self):
        with pytest.raises(ValueError, match="1 月 1 日"):
            validate(5, date(2026, 2, 1), date(2027, 1, 31))

    # ── 跨类型混淆：用月度日期冒充季度 ──

    def test_monthly_range_as_quarterly(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(3, date(2026, 1, 1), date(2026, 1, 31))

    def test_quarterly_range_as_monthly(self):
        with pytest.raises(ValueError, match="最后一天"):
            validate(1, date(2026, 1, 1), date(2026, 3, 31))
