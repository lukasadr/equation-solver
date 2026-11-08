"""Equation solving logic for the Equation Solver app.

This module is deliberately free of Qt imports so the maths can be tested and
reused on its own. Coefficients are handled as exact rational numbers
(``fractions.Fraction``) which lets the app show exact roots whenever they
exist, and fall back to 6-decimal approximations only when the roots are
irrational.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

SUPERSCRIPT_TWO = "\u00b2"
PLUS_MINUS = "\u00b1"
SQUARE_ROOT = "\u221a"
DELTA = "\u0394"


class CoefficientError(ValueError):
    """Raised when a coefficient cannot be parsed as a number."""


class SolutionKind(str, Enum):
    """How the equation behaves, independent of the UI."""

    TWO_REAL = "two_real"
    DOUBLE_REAL = "double_real"
    COMPLEX = "complex"
    LINEAR = "linear"
    INFINITE = "infinite"
    NONE = "none"


@dataclass(frozen=True)
class Root:
    """A single root, formatted for display and usable for plotting."""

    text: str
    value: complex


@dataclass(frozen=True)
class Solution:
    """The result of solving ``a*x**2 + b*x + c = 0``."""

    a: Fraction
    b: Fraction
    c: Fraction
    kind: SolutionKind
    delta: Fraction | None = None
    roots: tuple[Root, ...] = ()
    detail: str | None = None
    message: str = ""
    approximate: bool = False


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def parse_coefficient(text: str) -> Fraction:
    """Parse a user typed coefficient.

    Accepts integers (``2``), decimals with a dot or a comma (``1.5``, ``1,5``),
    fractions (``1/2``), scientific notation (``1e-3``), a leading ``+`` and
    surrounding spaces. An empty field means ``0``.
    """

    raw = text.strip().replace("\u2212", "-").replace("\u00a0", "")
    raw = "".join(raw.split())
    if raw == "":
        return Fraction(0)
    raw = raw.replace(",", ".")

    if raw.count("/") > 1:
        raise CoefficientError("use a single '/', like 1/2")

    try:
        if "/" in raw:
            numerator, denominator = raw.split("/")
            if not numerator or not denominator:
                raise CoefficientError("a fraction needs a numerator and a denominator")
            value = Fraction(numerator) / Fraction(denominator)
        else:
            value = Fraction(raw)
    except CoefficientError:
        raise
    except ZeroDivisionError:
        raise CoefficientError("cannot divide by zero") from None
    except (ValueError, ArithmeticError):
        raise CoefficientError("not a number") from None

    return value


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def to_float(value: Fraction) -> float:
    """Convert to float, returning ``nan`` when the value is out of range."""

    try:
        return float(value)
    except (OverflowError, ValueError):
        return math.nan


def format_fraction(value: Fraction) -> str:
    """Format a rational number as ``3`` or ``3/4``."""

    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def format_float(value: float) -> str:
    """Format a float with up to 6 significant decimals, without trailing zeros."""

    if not math.isfinite(value):
        return "undefined"
    if value == 0:
        return "0"
    if abs(value) >= 1e9 or abs(value) < 1e-6:
        return f"{value:.6g}"
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def format_equation(a: Fraction, b: Fraction, c: Fraction) -> str:
    """Format ``ax² + bx + c = 0`` with only the non-zero terms."""

    def term(magnitude: Fraction, variable: str) -> str:
        if not variable:
            return format_fraction(magnitude)
        if magnitude == 1:
            return variable
        if magnitude.denominator == 1:
            return f"{magnitude.numerator}{variable}"
        return f"({format_fraction(magnitude)}){variable}"

    parts: list[tuple[bool, str]] = []
    if a:
        parts.append((a < 0, term(abs(a), f"x{SUPERSCRIPT_TWO}")))
    if b:
        parts.append((b < 0, term(abs(b), "x")))
    if c:
        parts.append((c < 0, term(abs(c), "")))

    if not parts:
        return "0 = 0"

    negative, body = parts[0]
    left = f"-{body}" if negative else body
    for negative, body in parts[1:]:
        left += f" - {body}" if negative else f" + {body}"
    return f"{left} = 0"


def headline(solution: Solution) -> str:
    """A short human readable summary of the solution."""

    return {
        SolutionKind.TWO_REAL: "Two distinct real roots",
        SolutionKind.DOUBLE_REAL: "One double real root",
        SolutionKind.COMPLEX: "Two complex conjugate roots",
        SolutionKind.LINEAR: "Linear equation, one real root",
        SolutionKind.INFINITE: "Infinitely many solutions",
        SolutionKind.NONE: "No solution",
    }[solution.kind]


def detail_lines(solution: Solution) -> list[str]:
    """The lines shown in the result panel."""

    lines: list[str] = []
    if solution.delta is not None:
        delta = solution.delta
        digits = len(str(abs(delta.numerator))) + len(str(delta.denominator))
        if digits <= 2 * DISPLAY_DIGITS:
            text = f"{DELTA} = b{SUPERSCRIPT_TWO} - 4ac = {format_fraction(delta)}"
            if delta.denominator != 1:
                text += f" \u2248 {format_float(to_float(delta))}"
        else:
            text = f"{DELTA} = b{SUPERSCRIPT_TWO} - 4ac \u2248 {format_float(to_float(delta))}"
        lines.append(text)

    if solution.kind is SolutionKind.TWO_REAL:
        lines.append(f"x\u2081 = {solution.roots[0].text}")
        lines.append(f"x\u2082 = {solution.roots[1].text}")
    elif solution.kind is SolutionKind.DOUBLE_REAL:
        lines.append(f"x = {solution.roots[0].text}")
    elif solution.kind is SolutionKind.COMPLEX:
        lines.append(f"x\u2081 = {solution.roots[0].text}")
        lines.append(f"x\u2082 = {solution.roots[1].text}")
        lines.append(f"{DELTA} < 0, so the parabola never crosses the x-axis.")
    elif solution.kind is SolutionKind.LINEAR:
        lines.append(f"x = {solution.roots[0].text}")
        lines.append(solution.message)
    elif solution.message:
        lines.append(solution.message)

    if solution.detail:
        lines.append(solution.detail)
    if solution.approximate:
        lines.append("Values rounded to 6 decimals.")
    return lines


# ---------------------------------------------------------------------------
# Maths helpers
# ---------------------------------------------------------------------------


def _perfect_sqrt(value: Fraction) -> Fraction | None:
    """Return the exact square root of a rational, or ``None`` if irrational."""

    if value < 0:
        return None
    numerator_root = math.isqrt(value.numerator)
    denominator_root = math.isqrt(value.denominator)
    if (
        numerator_root * numerator_root == value.numerator
        and denominator_root * denominator_root == value.denominator
    ):
        return Fraction(numerator_root, denominator_root)
    return None


def _is_integer(value: Fraction) -> bool:
    return value.denominator == 1


def _simplify_sqrt(value: int) -> tuple[int, int]:
    """Split ``sqrt(value)`` into ``(k, m)`` with ``sqrt(value) == k*sqrt(m)``."""

    multiplier, radicand = 1, value
    divisor = 2
    while divisor * divisor <= radicand:
        while radicand % (divisor * divisor) == 0:
            radicand //= divisor * divisor
            multiplier *= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    return multiplier, radicand


def _radical_pair(a: int, b: int, delta: int, imaginary: bool) -> str | None:
    """Exact ``x = (...)`` form for irrational real or complex roots.

    Only used when the coefficients and the discriminant are integers, so the
    result is guaranteed to be a clean radical expression.
    """

    radicand = -delta if imaginary else delta
    if radicand <= 0 or radicand > 10**10:
        return None

    multiplier, square_free = _simplify_sqrt(radicand)
    if square_free == 1:
        return None  # sqrt is rational, an exact fraction is already shown

    constant, radical, denominator = -b, multiplier, 2 * a
    if denominator < 0:
        denominator = -denominator
        constant = -constant

    divisor = math.gcd(math.gcd(abs(constant), radical), denominator) or 1
    constant //= divisor
    radical //= divisor
    denominator //= divisor

    radical_text = f"i{SQUARE_ROOT}{square_free}" if imaginary else f"{SQUARE_ROOT}{square_free}"
    if radical != 1:
        radical_text = f"{radical}{radical_text}"

    if denominator == 1:
        if constant:
            return f"{constant} {PLUS_MINUS} {radical_text}"
        return f"{PLUS_MINUS} {radical_text}"
    if constant:
        return f"({constant} {PLUS_MINUS} {radical_text}) / {denominator}"
    return f"{PLUS_MINUS} {radical_text} / {denominator}"


DISPLAY_DIGITS = 12


def _is_compact(value: Fraction) -> bool:
    """Whether an exact fraction is short enough to print in full."""

    return (
        len(str(abs(value.numerator))) <= DISPLAY_DIGITS
        and len(str(value.denominator)) <= DISPLAY_DIGITS
    )


def _real_root_text(value: Fraction) -> str:
    if not _is_compact(value):
        return format_float(to_float(value))
    exact = format_fraction(value)
    if value.denominator == 1:
        return exact
    return f"{exact} \u2248 {format_float(to_float(value))}"


def _imaginary_text(magnitude: Fraction | float) -> str:
    if isinstance(magnitude, Fraction):
        magnitude = to_float(magnitude)
    if magnitude == 0:
        return "0"
    text = format_float(abs(magnitude))
    return "i" if text == "1" else f"{text}i"


def _complex_root_text(real: Fraction, imaginary_text: str, positive: bool) -> str:
    if _is_compact(real):
        real_text = format_fraction(real)
    else:
        real_text = format_float(to_float(real))

    if real == 0:
        return imaginary_text if positive else f"-{imaginary_text}"

    sign = "+" if positive else "-"
    return f"{real_text} {sign} {imaginary_text}"


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------


def solve(a: Fraction, b: Fraction, c: Fraction) -> Solution:
    """Solve ``a*x**2 + b*x + c = 0`` exactly whenever possible."""

    if a == 0:
        if b == 0:
            if c == 0:
                return Solution(
                    a, b, c, SolutionKind.INFINITE,
                    message="Every value of x satisfies the equation.",
                )
            return Solution(
                a, b, c, SolutionKind.NONE,
                message="No value of x satisfies the equation.",
            )

        root = -c / b
        return Solution(
            a, b, c, SolutionKind.LINEAR,
            roots=(Root(_real_root_text(root), complex(to_float(root), 0.0)),),
            message="The x\u00b2 term is zero, so this is a linear equation.",
            approximate=not _is_compact(root),
        )

    delta = b * b - 4 * a * c

    if delta > 0:
        exact_sqrt = _perfect_sqrt(delta)
        if exact_sqrt is not None:
            first = (-b - exact_sqrt) / (2 * a)
            second = (-b + exact_sqrt) / (2 * a)
            low, high = sorted((first, second))
            roots = tuple(
                Root(_real_root_text(value), complex(to_float(value), 0.0))
                for value in (low, high)
            )
            return Solution(
                a, b, c, SolutionKind.TWO_REAL, delta, roots,
                approximate=not (_is_compact(low) and _is_compact(high)),
            )

        square_root = math.sqrt(to_float(delta))
        a_float, b_float, c_float = to_float(a), to_float(b), to_float(c)
        # q avoids the cancellation that (-b ± sqrt(delta)) suffers from when
        # |b| is large compared to the discriminant.
        q = -0.5 * (b_float + math.copysign(square_root, b_float))
        first = q / a_float
        second = c_float / q if q else -b_float / (2 * a_float)
        low, high = sorted((first, second))
        roots = (
            Root(format_float(low), complex(low, 0.0)),
            Root(format_float(high), complex(high, 0.0)),
        )
        detail = None
        if _is_integer(a) and _is_integer(b) and _is_integer(delta):
            expression = _radical_pair(int(a), int(b), int(delta), imaginary=False)
            if expression:
                detail = f"Exact form: x = {expression}"
        return Solution(
            a, b, c, SolutionKind.TWO_REAL, delta, roots,
            detail=detail, approximate=True,
        )

    if delta == 0:
        root = -b / (2 * a)
        return Solution(
            a, b, c, SolutionKind.DOUBLE_REAL, delta,
            roots=(Root(_real_root_text(root), complex(to_float(root), 0.0)),),
            message="The parabola touches the x-axis at its vertex.",
            approximate=not _is_compact(root),
        )

    real = -b / (2 * a)
    magnitude_squared = -delta / (4 * a * a)
    exact_imaginary = _perfect_sqrt(magnitude_squared)
    if exact_imaginary is not None and _is_compact(exact_imaginary):
        imaginary_text = _imaginary_text(exact_imaginary)
        imaginary_float = to_float(exact_imaginary)
        approximate = not _is_compact(real)
    else:
        imaginary_float = math.sqrt(max(to_float(magnitude_squared), 0.0))
        imaginary_text = _imaginary_text(imaginary_float)
        approximate = True

    roots = (
        Root(
            _complex_root_text(real, imaginary_text, positive=True),
            complex(to_float(real), imaginary_float),
        ),
        Root(
            _complex_root_text(real, imaginary_text, positive=False),
            complex(to_float(real), -imaginary_float),
        ),
    )
    detail = None
    if _is_integer(a) and _is_integer(b) and _is_integer(delta):
        expression = _radical_pair(int(a), int(b), int(delta), imaginary=True)
        if expression:
            detail = f"Exact form: x = {expression}"
    return Solution(
        a, b, c, SolutionKind.COMPLEX, delta, roots,
        detail=detail, approximate=approximate,
    )
