"""Colours and stylesheet for the Equation Solver window.

Keeping the palette in one place means the painter used by the graph and the
Qt stylesheet never drift apart.
"""

BG = "#0f111a"
SURFACE = "#171a26"
SURFACE_ALT = "#1e2231"
BORDER = "#272c3f"
TEXT = "#e9ebf5"
MUTED = "#8f95ad"
ACCENT = "#6c8cff"
ACCENT_HOVER = "#829fff"
ACCENT_PRESSED = "#5874e6"
ERROR = "#ff7389"
GRID = "#2c3349"
AXIS = "#4d5675"
ROOT_POINT = "#4ec9a8"

STYLESHEET = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: "Segoe UI", "Inter", "DejaVu Sans", sans-serif;
    font-size: 13px;
}}

QLabel#title {{
    font-size: 26px;
    font-weight: 600;
    color: {TEXT};
}}

QLabel#subtitle {{
    font-size: 13px;
    color: {MUTED};
}}

QLabel#sectionLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {MUTED};
}}

QLabel#preview {{
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 15px;
    color: {TEXT};
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 12px;
}}

QLabel#coefficientLabel {{
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 15px;
    color: {MUTED};
}}

QLabel#headline {{
    font-size: 16px;
    font-weight: 600;
    color: {TEXT};
}}

QLabel#resultDetails {{
    font-size: 13px;
    color: {TEXT};
}}

QLabel#error {{
    color: {ERROR};
    font-size: 12px;
}}

QLabel#muted {{
    color: {MUTED};
    font-size: 12px;
}}

QFrame#card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}

QLineEdit {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 10px;
    font-family: "JetBrains Mono", "Consolas", "DejaVu Sans Mono", monospace;
    font-size: 15px;
    color: {TEXT};
    selection-background-color: {ACCENT};
    selection-color: #0b0d14;
}}

QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}

QLineEdit[invalid="true"] {{
    border: 1px solid {ERROR};
}}

QPushButton {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 9px 16px;
    font-size: 13px;
    color: {TEXT};
}}

QPushButton:hover {{
    border: 1px solid {AXIS};
    background: #232838;
}}

QPushButton:pressed {{
    background: #1a1f2c;
}}

QPushButton:disabled {{
    color: #5d637a;
    border: 1px solid {BORDER};
}}

QPushButton#primaryButton {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
    color: #0b0d14;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background: {ACCENT_HOVER};
    border: 1px solid {ACCENT_HOVER};
}}

QPushButton#primaryButton:pressed {{
    background: {ACCENT_PRESSED};
    border: 1px solid {ACCENT_PRESSED};
}}

QPushButton#linkButton {{
    background: transparent;
    border: none;
    padding: 2px 4px;
    color: {MUTED};
    font-size: 12px;
}}

QPushButton#linkButton:hover {{
    color: {TEXT};
}}

QListWidget#historyList {{
    background: transparent;
    border: none;
    outline: none;
    font-size: 12px;
}}

QListWidget#historyList::item {{
    padding: 7px 8px;
    border-radius: 7px;
    color: {TEXT};
}}

QListWidget#historyList::item:hover {{
    background: {SURFACE_ALT};
}}

QListWidget#historyList::item:selected {{
    background: {SURFACE_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
}}

QListWidget#historyList::item:disabled {{
    color: {MUTED};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 2px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {AXIS};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QToolTip {{
    background: {SURFACE_ALT};
    color: {TEXT};
    border: 1px solid {BORDER};
    padding: 5px 7px;
}}
"""
