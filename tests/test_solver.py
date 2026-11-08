"""Tests for the pure solving logic (no Qt required)."""

from __future__ import annotations

import sys
import unittest
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from solver import (  # noqa: E402
    CoefficientError,
    SolutionKind,
    detail_lines,
    format_equation,
    headline,
    parse_coefficient,
    solve,
)


def F(value: int | str, denominator: int = 1) -> Fraction:
    return Fraction(value, denominator)


class ParseCoefficientTests(unittest.TestCase):
    def test_integers_decimals_and_fractions(self):
        self.assertEqual(parse_coefficient("2"), F(2))
        self.assertEqual(parse_coefficient("-7"), F(-7))
        self.assertEqual(parse_coefficient("1.5"), F(3, 2))
        self.assertEqual(parse_coefficient("1,5"), F(3, 2))
        self.assertEqual(parse_coefficient("1/2"), F(1, 2))
        self.assertEqual(parse_coefficient("-3/4"), F(-3, 4))
        self.assertEqual(parse_coefficient(" 2e3 "), F(2000))
        self.assertEqual(parse_coefficient("+.5"), F(1, 2))

    def test_empty_means_zero(self):
        self.assertEqual(parse_coefficient(""), F(0))
        self.assertEqual(parse_coefficient("   "), F(0))

    def test_rejects_invalid_input(self):
        for text in ("abc", "1/0", "1/", "/2", "1/2/3", "1..2", "x"):
            with self.subTest(text=text), self.assertRaises(CoefficientError):
                parse_coefficient(text)


class SolveTests(unittest.TestCase):
    def test_two_real_roots(self):
        result = solve(F(1), F(-3), F(2))
        self.assertIs(result.kind, SolutionKind.TWO_REAL)
        self.assertEqual(result.delta, F(1))
        self.assertEqual([root.text for root in result.roots], ["1", "2"])
        self.assertEqual([root.value for root in result.roots], [1 + 0j, 2 + 0j])
        self.assertFalse(result.approximate)

    def test_fractional_roots_stay_exact(self):
        result = solve(F(2), F(-1), F(-1))
        self.assertEqual([root.text for root in result.roots], ["-1/2 \u2248 -0.5", "1"])

    def test_double_root(self):
        result = solve(F(1), F(2), F(1))
        self.assertIs(result.kind, SolutionKind.DOUBLE_REAL)
        self.assertEqual(result.delta, F(0))
        self.assertEqual(result.roots[0].text, "-1")
        self.assertEqual(result.roots[0].value, -1 + 0j)

    def test_complex_conjugate_roots(self):
        result = solve(F(1), F(2), F(5))
        self.assertIs(result.kind, SolutionKind.COMPLEX)
        self.assertEqual(result.delta, F(-16))
        self.assertEqual([root.text for root in result.roots], ["-1 + 2i", "-1 - 2i"])
        self.assertEqual(result.roots[0].value, -1 + 2j)
        self.assertEqual(result.roots[1].value, -1 - 2j)
        self.assertFalse(result.approximate)

    def test_purely_imaginary_roots(self):
        result = solve(F(1), F(0), F(1))
        self.assertEqual([root.text for root in result.roots], ["i", "-i"])

    def test_irrational_roots_show_exact_radical_form(self):
        result = solve(F(1), F(1), F(-1))
        self.assertIs(result.kind, SolutionKind.TWO_REAL)
        self.assertTrue(result.approximate)
        self.assertEqual([root.text for root in result.roots], ["-1.618034", "0.618034"])
        self.assertEqual(result.detail, "Exact form: x = (-1 \u00b1 \u221a5) / 2")

    def test_irrational_roots_without_integer_coefficients(self):
        result = solve(F(1, 2), F(0), F(-1))
        self.assertIs(result.kind, SolutionKind.TWO_REAL)
        self.assertIsNone(result.detail)
        self.assertTrue(result.approximate)

    def test_linear_equation(self):
        result = solve(F(0), F(2), F(-4))
        self.assertIs(result.kind, SolutionKind.LINEAR)
        self.assertEqual(result.roots[0].text, "2")
        self.assertIsNone(result.delta)

    def test_infinite_solutions(self):
        result = solve(F(0), F(0), F(0))
        self.assertIs(result.kind, SolutionKind.INFINITE)
        self.assertEqual(headline(result), "Infinitely many solutions")

    def test_no_solution(self):
        result = solve(F(0), F(0), F(3))
        self.assertIs(result.kind, SolutionKind.NONE)
        self.assertEqual(headline(result), "No solution")

    def test_negative_leading_coefficient(self):
        result = solve(F(-1), F(0), F(2))
        self.assertEqual([root.text for root in result.roots], ["-1.414214", "1.414214"])
        self.assertEqual(result.detail, "Exact form: x = \u00b1 \u221a2")

    def test_large_coefficients_keep_the_small_root(self):
        # The naive (-b ± sqrt(delta)) / 2a formula returns 0 here.
        result = solve(F(10**18), F(-(10**18)), F(1))
        self.assertEqual([root.text for root in result.roots], ["1e-18", "1"])

    def test_huge_discriminant_is_summarised(self):
        lines = detail_lines(solve(F(10**40), F(1), F(1)))
        self.assertTrue(any("\u0394 = b\u00b2 - 4ac \u2248" in line for line in lines), lines)
        self.assertLess(max(len(line) for line in lines), 200)

    def test_delta_is_reported_for_all_real_cases(self):
        lines = detail_lines(solve(F(1), F(2), F(5)))
        self.assertIn("\u0394 = b\u00b2 - 4ac = -16", lines)
        self.assertTrue(any("never crosses" in line for line in lines))


class FormatTests(unittest.TestCase):
    def test_format_equation(self):
        self.assertEqual(format_equation(F(1), F(-3), F(2)), "x\u00b2 - 3x + 2 = 0")
        self.assertEqual(format_equation(F(1), F(-1), F(0)), "x\u00b2 - x = 0")
        self.assertEqual(format_equation(F(0), F(2), F(3)), "2x + 3 = 0")
        self.assertEqual(format_equation(F(0), F(0), F(0)), "0 = 0")
        self.assertEqual(format_equation(F(-1), F(0), F(2)), "-x\u00b2 + 2 = 0")
        self.assertEqual(
            format_equation(F(1, 2), F(0), F(-1)), "(1/2)x\u00b2 - 1 = 0"
        )
        self.assertEqual(format_equation(F(0), F(-1), F(0)), "-x = 0")

    def test_long_exact_values_fall_back_to_decimals(self):
        result = solve(F(10**40), F(0), F(1))
        self.assertTrue(result.approximate)
        self.assertLess(len(result.roots[0].text), 70)

    def test_headlines(self):
        self.assertEqual(headline(solve(F(1), F(0), F(1))), "Two complex conjugate roots")
        self.assertEqual(headline(solve(F(1), F(0), F(0))), "One double real root")
        self.assertEqual(headline(solve(F(0), F(1), F(0))), "Linear equation, one real root")


if __name__ == "__main__":
    unittest.main()
