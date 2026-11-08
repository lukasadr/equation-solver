"""Equation Solver - a PySide6 rewrite of the Tkinter "Polynome" app.

Run with ``python main.py`` from this folder.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import theme
from plot_widget import PlotWidget
from solver import (
    CoefficientError,
    Solution,
    detail_lines,
    format_equation,
    format_fraction,
    headline,
    parse_coefficient,
    solve,
)

ASSETS = Path(__file__).resolve().parent / "assets"
PLACEHOLDER_EQUATION = "ax\u00b2 + bx + c = 0"
MAX_HISTORY = 40
COEFFICIENT_HINT = "Integers, decimals (1.5 or 1,5) or fractions (1/2). Leave empty for 0."


def _section_label(text: str) -> QLabel:
    return QLabel(text.upper(), objectName="sectionLabel")


class MainWindow(QMainWindow):
    """Main window: coefficient inputs, result panel, graph and history."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Equation Solver")
        icon_path = ASSETS / "calculator.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1000, 660)
        self.setMinimumSize(780, 580)

        self._solution: Solution | None = None
        self._history: list[tuple[tuple[Fraction, Fraction, Fraction], Solution]] = []

        self._build_ui()
        self._install_shortcuts()
        self._preview_equation()
        self._center_on_screen()

    # -- construction ------------------------------------------------------

    def _build_ui(self) -> None:
        root = QWidget(objectName="root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(26, 22, 26, 22)
        outer.setSpacing(16)

        header = QVBoxLayout()
        header.setSpacing(2)
        header.addWidget(QLabel("Equation Solver", objectName="title"))
        header.addWidget(
            QLabel(
                "Quadratic equations with exact roots, complex solutions and a live graph.",
                objectName="subtitle",
            )
        )
        outer.addLayout(header)

        body = QHBoxLayout()
        body.setSpacing(16)
        body.addWidget(self._build_input_card(), 5)
        body.addWidget(self._build_right_column(), 6)
        outer.addLayout(body, 1)

    def _build_input_card(self) -> QFrame:
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        layout.addWidget(_section_label("Coefficients"))

        self.preview = QLabel("", objectName="preview")
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.preview)

        self.fields: dict[str, QLineEdit] = {}
        for name in ("a", "b", "c"):
            row = QHBoxLayout()
            row.setSpacing(10)

            label = QLabel(f"{name} =", objectName="coefficientLabel")
            label.setFixedWidth(30)

            edit = QLineEdit()
            edit.setPlaceholderText("0")
            edit.setToolTip(COEFFICIENT_HINT)
            edit.setMaxLength(32)
            edit.setClearButtonEnabled(True)
            edit.textChanged.connect(self._preview_equation)
            self.fields[name] = edit

            row.addWidget(label)
            row.addWidget(edit, 1)
            layout.addLayout(row)

        self.error_label = QLabel("", objectName="error")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        self.solve_button = QPushButton("Solve", objectName="primaryButton")
        self.solve_button.setAutoDefault(False)  # Enter is handled by a shortcut
        self.solve_button.clicked.connect(self._solve)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self._clear)
        buttons.addWidget(self.solve_button, 2)
        buttons.addWidget(self.clear_button, 1)
        layout.addLayout(buttons)

        layout.addSpacing(8)
        layout.addWidget(_section_label("Result"))

        self.headline_label = QLabel("\u2014", objectName="headline")
        self.headline_label.setWordWrap(True)
        layout.addWidget(self.headline_label)

        self.details_label = QLabel(
            "Enter coefficients and press Solve.", objectName="resultDetails"
        )
        self.details_label.setWordWrap(True)
        self.details_label.setMinimumHeight(112)
        self.details_label.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.details_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.details_label)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.copy_button = QPushButton("Copy result")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self._copy_result)
        footer.addWidget(self.copy_button)
        footer.addStretch(1)
        footer.addWidget(QLabel("Enter \u21b5 to solve", objectName="muted"))
        layout.addLayout(footer)

        layout.addStretch(1)
        return card

    def _build_right_column(self) -> QWidget:
        column = QWidget()
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self._build_plot_card(), 3)
        layout.addWidget(self._build_history_card(), 2)
        return column

    def _build_plot_card(self) -> QFrame:
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)
        layout.addWidget(_section_label("Graph"))
        self.plot = PlotWidget()
        layout.addWidget(self.plot, 1)
        return card

    def _build_history_card(self) -> QFrame:
        card = QFrame(objectName="card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.addWidget(_section_label("History"))
        header.addStretch(1)
        self.clear_history_button = QPushButton("Clear", objectName="linkButton")
        self.clear_history_button.clicked.connect(self._clear_history)
        header.addWidget(self.clear_history_button)
        layout.addLayout(header)

        self.history_list = QListWidget(objectName="historyList")
        self.history_list.setMinimumHeight(118)
        self.history_list.itemClicked.connect(self._restore_from_history)
        layout.addWidget(self.history_list, 1)

        self._refresh_history()
        return card

    def _install_shortcuts(self) -> None:
        self._add_shortcut(QKeySequence(Qt.Key.Key_Return), self._solve)
        self._add_shortcut(QKeySequence(Qt.Key.Key_Enter), self._solve)
        self._add_shortcut(QKeySequence("Ctrl+L"), self._clear)
        self._add_shortcut(QKeySequence("Ctrl+Shift+C"), self._copy_result)

    def _add_shortcut(self, sequence: QKeySequence, slot) -> None:
        shortcut = QShortcut(sequence, self)
        shortcut.activated.connect(slot)

    # -- behaviour ---------------------------------------------------------

    def _read_coefficients(self) -> tuple[Fraction, Fraction, Fraction] | None:
        values: list[Fraction] = []
        for name, edit in self.fields.items():
            try:
                values.append(parse_coefficient(edit.text()))
            except CoefficientError as error:
                self._show_error(f"Coefficient {name}: {error}.", edit)
                return None
        return values[0], values[1], values[2]

    def _solve(self) -> None:
        self._clear_error()
        coefficients = self._read_coefficients()
        if coefficients is None:
            return

        solution = solve(*coefficients)
        self._present(solution)
        self._push_history(coefficients, solution)

    def _present(self, solution: Solution) -> None:
        self._solution = solution
        self.headline_label.setText(headline(solution))
        self.details_label.setText("\n".join(detail_lines(solution)))
        self.copy_button.setEnabled(True)
        self.copy_button.setText("Copy result")
        self.plot.set_solution(solution)

    def _clear(self) -> None:
        for edit in self.fields.values():
            edit.blockSignals(True)
            edit.clear()
            edit.blockSignals(False)

        self._clear_error()
        self._solution = None
        self.headline_label.setText("\u2014")
        self.details_label.setText("Enter coefficients and press Solve.")
        self.copy_button.setEnabled(False)
        self.plot.clear()
        self._preview_equation()
        self.fields["a"].setFocus()

    def _copy_result(self) -> None:
        if self._solution is None:
            return
        solution = self._solution
        text = "\n".join(
            [format_equation(solution.a, solution.b, solution.c), headline(solution)]
            + detail_lines(solution)
        )
        QApplication.clipboard().setText(text)
        self.copy_button.setText("Copied")
        QTimer.singleShot(1400, self._reset_copy_button)

    def _reset_copy_button(self) -> None:
        self.copy_button.setText("Copy result")

    def _preview_equation(self) -> None:
        if all(not edit.text().strip() for edit in self.fields.values()):
            self.preview.setText(PLACEHOLDER_EQUATION)
            return

        values: list[Fraction] = []
        for edit in self.fields.values():
            try:
                values.append(parse_coefficient(edit.text()))
            except CoefficientError:
                self.preview.setText(PLACEHOLDER_EQUATION)
                return
        self.preview.setText(format_equation(values[0], values[1], values[2]))

    # -- history -----------------------------------------------------------

    def _push_history(
        self,
        coefficients: tuple[Fraction, Fraction, Fraction],
        solution: Solution,
    ) -> None:
        if self._history and self._history[0][0] == coefficients:
            return
        self._history.insert(0, (coefficients, solution))
        del self._history[MAX_HISTORY:]
        self._refresh_history()

    def _refresh_history(self) -> None:
        self.history_list.clear()
        if not self._history:
            placeholder = QListWidgetItem("No calculations yet")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            self.history_list.addItem(placeholder)
            return

        for index, (coefficients, solution) in enumerate(self._history):
            item = QListWidgetItem(
                f"{format_equation(*coefficients)}   \u00b7   {headline(solution)}"
            )
            item.setToolTip("\n".join(detail_lines(solution)))
            item.setData(Qt.ItemDataRole.UserRole, index)
            self.history_list.addItem(item)

    def _restore_from_history(self, item: QListWidgetItem) -> None:
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is None or not 0 <= int(index) < len(self._history):
            return

        coefficients, solution = self._history[int(index)]
        for name, value in zip(("a", "b", "c"), coefficients):
            self.fields[name].setText(format_fraction(value))
        self._clear_error()
        self._present(solution)

    def _clear_history(self) -> None:
        self._history.clear()
        self._refresh_history()

    # -- errors ------------------------------------------------------------

    def _show_error(self, message: str, edit: QLineEdit) -> None:
        edit.setProperty("invalid", True)
        edit.style().unpolish(edit)
        edit.style().polish(edit)
        self.error_label.setText(message)
        self.error_label.show()
        edit.setFocus()
        edit.selectAll()

    def _clear_error(self) -> None:
        self.error_label.hide()
        for edit in self.fields.values():
            if edit.property("invalid"):
                edit.setProperty("invalid", False)
                edit.style().unpolish(edit)
                edit.style().polish(edit)

    # -- window ------------------------------------------------------------

    def _center_on_screen(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen.availableGeometry().center())
        self.move(frame.topLeft())


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Equation Solver")
    app.setApplicationDisplayName("Equation Solver")
    app.setOrganizationName("Equation Solver")
    app.setStyle("Fusion")
    app.setStyleSheet(theme.STYLESHEET)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
