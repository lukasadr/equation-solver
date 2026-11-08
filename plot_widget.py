"""A small QPainter based graph for y = ax² + bx + c.

No extra Qt module (QtCharts) is required: the curve is sampled and drawn by
hand, together with axes, grid, tick labels, the vertex and the real roots.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

import theme
from solver import Solution, SolutionKind, format_float, to_float

EMPTY_MESSAGE = "Solve an equation to plot the curve"


class PlotWidget(QWidget):
    """Draws the parabola (or line) matching the last solved equation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._a = 0.0
        self._b = 0.0
        self._c = 0.0
        self._kind: SolutionKind | None = None
        self._roots: list[complex] = []
        self._message = EMPTY_MESSAGE

    # -- public API --------------------------------------------------------

    def set_solution(self, solution: Solution) -> None:
        self._kind = solution.kind
        self._a = to_float(solution.a)
        self._b = to_float(solution.b)
        self._c = to_float(solution.c)
        self._roots = [root.value for root in solution.roots]
        self._message = ""

        if not all(math.isfinite(value) for value in (self._a, self._b, self._c)):
            self._kind = None
            self._message = "These coefficients are too large to plot"
        elif solution.kind is SolutionKind.INFINITE:
            self._message = "Nothing to plot: every x is a solution"
        elif solution.kind is SolutionKind.NONE:
            self._message = "Nothing to plot: the equation has no solution"

        self.update()

    @property
    def has_curve(self) -> bool:
        """True when a parabola or line is currently drawn."""

        return self._kind not in (None, SolutionKind.INFINITE, SolutionKind.NONE)

    def clear(self) -> None:
        self._a = self._b = self._c = 0.0
        self._kind = None
        self._roots = []
        self._message = EMPTY_MESSAGE
        self.update()

    # -- painting ----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(theme.BORDER), 1))
        painter.setBrush(QColor(theme.SURFACE_ALT).darker(103))
        painter.drawRoundedRect(frame, 10, 10)
        # The panel brush must not leak into the curve path, otherwise the path
        # would be filled (and hide the grid inside the parabola).
        painter.setBrush(Qt.BrushStyle.NoBrush)

        plot = frame.adjusted(18, 18, -18, -18)
        if plot.width() < 40 or plot.height() < 40:
            return

        if self._kind is None or self._kind in (SolutionKind.INFINITE, SolutionKind.NONE):
            self._draw_message(painter, frame, self._message)
            return

        x_min, x_max = self._x_limits()
        y_min, y_max = self._y_limits(x_min, x_max)
        if not all(math.isfinite(v) for v in (x_min, x_max, y_min, y_max)):
            self._draw_message(painter, frame, "These coefficients are too large to plot")
            return
        if x_max - x_min <= 0 or y_max - y_min <= 0:
            self._draw_message(painter, frame, EMPTY_MESSAGE)
            return

        def map_x(value: float) -> float:
            return plot.left() + (value - x_min) / (x_max - x_min) * plot.width()

        def map_y(value: float) -> float:
            return plot.bottom() - (value - y_min) / (y_max - y_min) * plot.height()

        self._draw_grid(painter, plot, x_min, x_max, y_min, y_max, map_x, map_y)
        self._draw_curve(painter, plot, x_min, x_max, y_min, y_max, map_x, map_y)
        self._draw_roots(painter, plot, map_x, map_y)

    def _draw_message(self, painter: QPainter, frame: QRectF, text: str) -> None:
        painter.setPen(QColor(theme.MUTED))
        font = painter.font()
        font.setPointSizeF(10.0)
        painter.setFont(font)
        painter.drawText(frame.adjusted(24, 24, -24, -24), Qt.AlignmentFlag.AlignCenter, text)

    def _draw_grid(self, painter, plot, x_min, x_max, y_min, y_max, map_x, map_y) -> None:
        step_x = _nice_step(x_max - x_min)
        step_y = _nice_step(y_max - y_min)

        grid_pen = QPen(QColor(theme.GRID), 1)
        painter.setPen(grid_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        tick = math.ceil(x_min / step_x) * step_x
        while tick <= x_max:
            x = _snap(map_x(tick))
            painter.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            tick += step_x

        tick = math.ceil(y_min / step_y) * step_y
        while tick <= y_max:
            y = _snap(map_y(tick))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            tick += step_y

        axis_pen = QPen(QColor(theme.AXIS), 1.2)
        painter.setPen(axis_pen)
        origin_y = _snap(map_y(0.0) if y_min <= 0 <= y_max else plot.bottom())
        origin_x = _snap(map_x(0.0) if x_min <= 0 <= x_max else plot.left())
        painter.drawLine(QPointF(plot.left(), origin_y), QPointF(plot.right(), origin_y))
        painter.drawLine(QPointF(origin_x, plot.top()), QPointF(origin_x, plot.bottom()))

        font = painter.font()
        font.setPointSizeF(8.0)
        painter.setFont(font)
        painter.setPen(QColor(theme.MUTED))

        label_y = min(origin_y + 13, plot.bottom() - 2)
        tick = math.ceil(x_min / step_x) * step_x
        while tick <= x_max:
            text = format_float(tick)
            if text != "0":
                x = map_x(tick)
                painter.drawText(
                    QRectF(x - 34, label_y, 68, 14),
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                    text,
                )
            tick += step_x

        label_x = min(origin_x + 5, plot.right() - 40)
        tick = math.ceil(y_min / step_y) * step_y
        while tick <= y_max:
            text = format_float(tick)
            if text != "0":
                y = map_y(tick)
                painter.drawText(
                    QRectF(label_x, y - 14, 42, 14),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    text,
                )
            tick += step_y

    def _draw_curve(self, painter, plot, x_min, x_max, y_min, y_max, map_x, map_y) -> None:
        path = QPainterPath()
        started = False
        span = y_max - y_min
        lower, upper = y_min - 10 * span, y_max + 10 * span

        samples = 361
        for index in range(samples):
            x = x_min + (x_max - x_min) * index / (samples - 1)
            y = self._evaluate(x)
            if not math.isfinite(y):
                started = False
                continue
            point = QPointF(map_x(x), map_y(min(max(y, lower), upper)))
            if started:
                path.lineTo(point)
            else:
                path.moveTo(point)
                started = True

        painter.save()
        painter.setClipRect(plot)
        painter.setBrush(Qt.BrushStyle.NoBrush)  # stroke only, never fill
        painter.setPen(QPen(QColor(theme.ACCENT), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPath(path)
        painter.restore()

        if self._kind is SolutionKind.DOUBLE_REAL and self._roots:
            vertex_x = self._roots[0].real
            if math.isfinite(vertex_x):
                painter.setPen(QPen(QColor(theme.ROOT_POINT), 1))
                painter.setBrush(QColor(theme.SURFACE_ALT))
                painter.drawEllipse(QPointF(map_x(vertex_x), map_y(0.0)), 4.0, 4.0)

    def _draw_roots(self, painter, plot, map_x, map_y) -> None:
        font = painter.font()
        font.setPointSizeF(9.0)
        painter.setFont(font)

        for index, root in enumerate(self._roots):
            if not math.isfinite(root.real) or abs(root.imag) > 1e-9:
                continue
            point = QPointF(map_x(root.real), map_y(0.0))
            if not plot.adjusted(-6, -6, 6, 6).contains(point):
                continue
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(theme.ROOT_POINT))
            painter.drawEllipse(point, 4.5, 4.5)

            label = "x" if len(self._roots) == 1 else ("x\u2081" if index == 0 else "x\u2082")
            painter.setPen(QColor(theme.ROOT_POINT))
            offset = 8 if index == 0 else -8
            painter.drawText(
                QRectF(point.x() - 18 + offset, point.y() - 20, 36, 14),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

    # -- geometry ----------------------------------------------------------

    def _evaluate(self, x: float) -> float:
        return self._a * x * x + self._b * x + self._c

    def _x_limits(self) -> tuple[float, float]:
        points: list[float] = []
        if self._kind is not SolutionKind.COMPLEX:
            points.extend(root.real for root in self._roots if math.isfinite(root.real))

        if self._kind is not SolutionKind.LINEAR and self._a:
            vertex = -self._b / (2 * self._a)
            if math.isfinite(vertex):
                points.append(vertex)

        if not points:
            points = [-2.0, 2.0]

        low, high = min(points), max(points)
        minimum_span = 4.0 if self._kind is SolutionKind.LINEAR else 2.0
        span = max(high - low, minimum_span)
        low, high = low - span * 0.3, high + span * 0.3
        return low, high

    def _y_limits(self, x_min: float, x_max: float) -> tuple[float, float]:
        samples = 241
        values = [
            self._evaluate(x_min + (x_max - x_min) * index / (samples - 1))
            for index in range(samples)
        ]
        finite = sorted(value for value in values if math.isfinite(value))
        if not finite:
            return 0.0, 1.0

        # Trim the extreme ends so a steep parabola still shows its shape.
        low = finite[min(int(0.02 * len(finite)), len(finite) - 1)]
        high = finite[min(int(0.98 * len(finite)), len(finite) - 1)]
        low = min(low, 0.0, high)
        high = max(high, 0.0)
        if high - low < 1e-9:
            high = low + 1.0

        padding = (high - low) * 0.15
        return low - padding, high + padding


def _snap(value: float) -> float:
    """Align a 1px line on a pixel centre so it renders crisp, not smeared."""

    return math.floor(value) + 0.5


def _nice_step(span: float, target_ticks: int = 6) -> float:
    """A round grid step (1, 2 or 5 times a power of ten) for the given span."""

    if not math.isfinite(span) or span <= 0:
        return 1.0
    raw = span / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 5, 10):
        if raw <= factor * magnitude:
            return factor * magnitude
    return 10 * magnitude
