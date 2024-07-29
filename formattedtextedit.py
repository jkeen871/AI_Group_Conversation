from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QAction,
                             QTextEdit, QComboBox)
from PyQt5.QtGui import QIcon, QTextListFormat, QTextCursor, QFont
from PyQt5.QtCore import Qt

class FormattedTextEdit(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Create toolbar
        self.toolbar = QToolBar()
        layout.addWidget(self.toolbar)

        # Create text edit
        self.text_edit = QTextEdit()
        layout.addWidget(self.text_edit)

        # Bold
        bold_action = QAction(QIcon('icons/bold.png'), 'Bold', self)
        bold_action.triggered.connect(self.toggle_bold)
        self.toolbar.addAction(bold_action)

        # Italic
        italic_action = QAction(QIcon('icons/italic.png'), 'Italic', self)
        italic_action.triggered.connect(self.toggle_italic)
        self.toolbar.addAction(italic_action)

        # Underline
        underline_action = QAction(QIcon('icons/underline.png'), 'Underline', self)
        underline_action.triggered.connect(self.toggle_underline)
        self.toolbar.addAction(underline_action)

        self.toolbar.addSeparator()

        # Bullet list
        bullet_action = QAction(QIcon('icons/bullet_list.png'), 'Bullet List', self)
        bullet_action.triggered.connect(self.toggle_bullet_list)
        self.toolbar.addAction(bullet_action)

        # Numbered list
        numbered_action = QAction(QIcon('icons/numbered_list.png'), 'Numbered List', self)
        numbered_action.triggered.connect(self.toggle_numbered_list)
        self.toolbar.addAction(numbered_action)

        self.toolbar.addSeparator()

        # Code block
        code_action = QAction(QIcon('icons/code.png'), 'Code Block', self)
        code_action.triggered.connect(self.insert_code_block)
        self.toolbar.addAction(code_action)

        # Heading levels
        self.heading_combo = QComboBox()
        self.heading_combo.addItems(['Normal', 'Heading 1', 'Heading 2', 'Heading 3'])
        self.heading_combo.currentIndexChanged.connect(self.set_heading)
        self.toolbar.addWidget(self.heading_combo)

    def toggle_bold(self):
        self.text_edit.setFontWeight(
            QFont.Bold if self.text_edit.fontWeight() != QFont.Bold else QFont.Normal
        )

    def toggle_italic(self):
        self.text_edit.setFontItalic(not self.text_edit.fontItalic())

    def toggle_underline(self):
        self.text_edit.setFontUnderline(not self.text_edit.fontUnderline())

    def toggle_bullet_list(self):
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()

        block_fmt = cursor.blockFormat()
        list_fmt = QTextListFormat()

        if cursor.currentList():
            block_fmt.setIndent(0)
            cursor.setBlockFormat(block_fmt)
            cursor.createList(list_fmt)
        else:
            list_fmt.setStyle(QTextListFormat.ListDisc)
            cursor.createList(list_fmt)

        cursor.endEditBlock()

    def toggle_numbered_list(self):
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()

        block_fmt = cursor.blockFormat()
        list_fmt = QTextListFormat()

        if cursor.currentList():
            block_fmt.setIndent(0)
            cursor.setBlockFormat(block_fmt)
            cursor.createList(list_fmt)
        else:
            list_fmt.setStyle(QTextListFormat.ListDecimal)
            cursor.createList(list_fmt)

        cursor.endEditBlock()

    def insert_code_block(self):
        cursor = self.text_edit.textCursor()
        cursor.insertText("=== code begin ===\n")
        cursor.insertText("\n")
        cursor.insertText("=== code end ===")
        cursor.movePosition(QTextCursor.Up)
        self.text_edit.setTextCursor(cursor)

    def set_heading(self, index):
        cursor = self.text_edit.textCursor()
        char_fmt = cursor.charFormat()
        block_fmt = cursor.blockFormat()

        if index == 0:  # Normal
            char_fmt.setFontWeight(QFont.Normal)
            block_fmt.setHeadingLevel(0)
        elif index == 1:  # Heading 1
            char_fmt.setFontWeight(QFont.Bold)
            block_fmt.setHeadingLevel(1)
        elif index == 2:  # Heading 2
            char_fmt.setFontWeight(QFont.Bold)
            block_fmt.setHeadingLevel(2)
        elif index == 3:  # Heading 3
            char_fmt.setFontWeight(QFont.Bold)
            block_fmt.setHeadingLevel(3)

        cursor.setCharFormat(char_fmt)
        cursor.setBlockFormat(block_fmt)
        self.text_edit.setTextCursor(cursor)

    def toPlainText(self):
        return self.text_edit.toPlainText()

    def clear(self):
        self.text_edit.clear()

    def setPlaceholderText(self, text):
        self.text_edit.setPlaceholderText(text)