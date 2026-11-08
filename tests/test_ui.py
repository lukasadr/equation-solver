"""End-to-end tests for the PySide6 window, run headless (offscreen platform)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import theme  # noqa: E402
from main import MainWindow  # noqa: E402


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(theme.STYLESHEET)

    def setUp(self) -> None:
        self.window = MainWindow()
        self.window.show()
        QApplication.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.window.deleteLater()
        QApplication.processEvents()

    # -- helpers -----------------------------------------------------------

    def enter(self, a: str = "", b: str = "", c: str = "") -> None:
        for name, value in (("a", a), ("b", b), ("c", c)):
            self.window.fields[name].setText(value)

    def solve(self) -> None:
        QTest.mouseClick(self.window.solve_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()

    def details(self) -> str:
        return self.window.details_label.text()

    # -- tests -------------------------------------------------------------

    def test_solves_two_real_roots(self):
        self.enter("1", "-3", "2")
        self.solve()
        self.assertEqual(self.window.headline_label.text(), "Two distinct real roots")
        self.assertIn("x\u2081 = 1", self.details())
        self.assertIn("x\u2082 = 2", self.details())
        self.assertIn("\u0394 = b\u00b2 - 4ac = 1", self.details())
        self.assertTrue(self.window.copy_button.isEnabled())

    def test_solves_complex_roots(self):
        self.enter("1", "2", "5")
        self.solve()
        self.assertEqual(self.window.headline_label.text(), "Two complex conjugate roots")
        self.assertIn("x\u2081 = -1 + 2i", self.details())
        self.assertIn("x\u2082 = -1 - 2i", self.details())

    def test_solves_linear_and_degenerate_cases(self):
        self.enter("0", "2", "-4")
        self.solve()
        self.assertEqual(self.window.headline_label.text(), "Linear equation, one real root")
        self.assertIn("x = 2", self.details())

        self.enter("", "", "")
        self.solve()
        self.assertEqual(self.window.headline_label.text(), "Infinitely many solutions")

        self.enter("0", "0", "3")
        self.solve()
        self.assertEqual(self.window.headline_label.text(), "No solution")

    def test_accepts_decimals_and_fractions(self):
        self.enter("1,5", "-1/2", "0")
        self.solve()
        self.assertEqual(self.window.headline_label.text(), "Two distinct real roots")
        self.assertEqual(
            self.window.preview.text(), "(3/2)x\u00b2 - (1/2)x = 0"
        )
        self.assertIn("x\u2082 = 1/3", self.details())

    def test_invalid_input_is_reported_and_field_marked(self):
        self.enter("one", "2", "3")
        self.solve()
        self.assertTrue(self.window.error_label.isVisible())
        self.assertIn("Coefficient a", self.window.error_label.text())
        self.assertTrue(self.window.fields["a"].property("invalid"))
        self.assertEqual(self.window.headline_label.text(), "\u2014")

    def test_enter_key_solves(self):
        self.enter("1", "0", "-4")
        QTest.keyClick(self.window.fields["c"], Qt.Key.Key_Return)
        QApplication.processEvents()
        self.assertEqual(self.window.headline_label.text(), "Two distinct real roots")
        self.assertIn("x\u2081 = -2", self.details())

    def test_clear_resets_everything(self):
        self.enter("1", "-3", "2")
        self.solve()
        QTest.mouseClick(self.window.clear_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        self.assertEqual(self.window.fields["a"].text(), "")
        self.assertEqual(self.window.headline_label.text(), "\u2014")
        self.assertFalse(self.window.copy_button.isEnabled())
        self.assertFalse(self.window.plot.has_curve)

    def test_history_records_and_restores(self):
        self.enter("1", "-3", "2")
        self.solve()
        self.enter("1", "2", "5")
        self.solve()
        self.assertEqual(self.window.history_list.count(), 2)

        item = self.window.history_list.item(1)
        QTest.mouseClick(
            self.window.history_list.viewport(),
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
            self.window.history_list.visualItemRect(item).center(),
        )
        QApplication.processEvents()

        self.assertEqual(self.window.fields["a"].text(), "1")
        self.assertEqual(self.window.fields["b"].text(), "-3")
        self.assertEqual(self.window.fields["c"].text(), "2")
        self.assertIn("x\u2081 = 1", self.details())

    def test_duplicate_calculation_is_not_added_twice(self):
        self.enter("1", "-3", "2")
        self.solve()
        self.solve()
        self.assertEqual(self.window.history_list.count(), 1)

    def test_copy_puts_result_on_clipboard(self):
        self.enter("1", "0", "-4")
        self.solve()
        QTest.mouseClick(self.window.copy_button, Qt.MouseButton.LeftButton)
        QApplication.processEvents()
        clipboard = QApplication.clipboard().text()
        self.assertIn("x\u00b2 - 4 = 0", clipboard)
        self.assertIn("Two distinct real roots", clipboard)
        self.assertIn("x\u2081 = -2", clipboard)

    def test_plot_renders_pixels(self):
        self.enter("1", "-3", "2")
        self.solve()
        QApplication.processEvents()
        pixmap = self.window.plot.grab()
        self.assertFalse(pixmap.isNull())
        image = pixmap.toImage()
        colours = {
            image.pixel(x, y)
            for x in range(0, image.width(), max(image.width() // 12, 1))
            for y in range(0, image.height(), max(image.height() // 12, 1))
        }
        self.assertGreater(len(colours), 1, "graph appears blank")

    def test_grid_lines_are_not_hidden_by_the_curve(self):
        # Regression: the curve path inherited the panel brush and was filled,
        # which erased the grid inside the parabola.
        self.enter("1", "-3", "2")
        self.solve()
        QApplication.processEvents()

        image = self.window.plot.grab().toImage()
        grid = QColor(theme.GRID).rgb()
        columns = [0] * image.width()
        rows = [0] * image.height()
        for y in range(image.height()):
            for x in range(image.width()):
                if image.pixel(x, y) == grid:
                    columns[x] += 1
                    rows[y] += 1

        self.assertGreater(max(columns), 0.75 * image.height(), "vertical grid is broken")
        self.assertGreater(max(rows), 0.75 * image.width(), "horizontal grid is broken")


if __name__ == "__main__":
    unittest.main()
