import sys
import logging
import json
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTextEdit, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QGridLayout, QSplitter,
    QLabel, QFontComboBox, QSpinBox, QColorDialog, QDialog, QGroupBox, QScrollArea,
    QFontDialog, QListWidget, QAbstractItemView, QListWidgetItem, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QRegExp
from PyQt5.QtGui import (QTextCursor, QColor, QTextCharFormat, QFont, QIcon, QPalette,
                         QSyntaxHighlighter, QTextBlockFormat, QTextDocument, QTextOption,
                         )
from conversation_manager import ConversationManager
from personalities import AI_PERSONALITIES, USER_IDENTITY
from Visualizer import VectorGraphVisualizer
import re
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.styles import get_style_by_name
from pygments.style import Style
from pygments.token import Comment, Keyword, Name, String, Number, Operator, Punctuation
from ConversationHistoryWindow import ConversationHistoryWindow
from EditPersonalities import EditPersonalities
from EditAIConfigs import EditAIConfigs
from EditHelperPersonalties import EditHelperPersonalities
import asyncio
from typing import List
from formattedtextedit import FormattedTextEdit

# Set up logging
logger = logging.getLogger(__name__)


class CustomTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.NoModifier:
            self.parent.on_send_button_clicked()
        else:
            super().keyPressEvent(event)


class AIResponseThread(QThread):
    response_received = pyqtSignal(str, str, str, str)  # participant, response, ai_name, model
    topic_generated = pyqtSignal(str)  # topic
    conversation_completed = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(self, conversation_manager, prompt, is_initial_conversation=True,
                 is_moderator_summary=False, active_participants=None, historical_thread_id=None):
        super().__init__()
        self.conversation_manager = conversation_manager
        self.prompt = prompt
        self.is_initial_conversation = is_initial_conversation
        self.is_moderator_summary = is_moderator_summary
        self.active_participants = active_participants or []
        self.historical_thread_id = historical_thread_id
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("AIResponseThread initialized")

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if self.is_moderator_summary:
                self.logger.debug("Generating moderator summary")
                summary = loop.run_until_complete(
                    self.conversation_manager.generate_moderator_summary()
                )
                self.response_received.emit("Moderator", summary, "System", "Moderator")
            elif self.is_initial_conversation:
                self.logger.debug("Generating initial AI conversation")
                responses = loop.run_until_complete(
                    self.conversation_manager.generate_ai_conversation(self.prompt, self.active_participants)
                )
                if isinstance(responses, dict):
                    for participant, response_data in responses.items():
                        if self.conversation_manager.is_interrupted:
                            break
                        if response_data:
                            response, ai_name, model = response_data
                            self.logger.debug(f"Emitting response from {participant}")
                            self.response_received.emit(participant, response, ai_name, model)
                            loop.run_until_complete(asyncio.sleep(0.1))

                    # Check if a topic was generated
                    current_thread = self.conversation_manager.conversation_history[
                        self.conversation_manager.current_thread_id]
                    if current_thread.topic:
                        self.logger.debug(f"Topic generated: {current_thread.topic}")
                        self.topic_generated.emit(current_thread.topic)
                    else:
                        self.logger.debug("No topic was generated")
                elif isinstance(responses, str):
                    self.logger.debug("Emitting system response")
                    self.response_received.emit("System", responses, "System", "System")
            else:
                self.logger.debug("Continuing conversation")
                response = loop.run_until_complete(
                    self.conversation_manager.continue_conversation(self.prompt, self.active_participants)
                )
                if isinstance(response, dict):
                    for participant, response_data in response.items():
                        if self.conversation_manager.is_interrupted:
                            break
                        if response_data:
                            response, ai_name, model = response_data
                            self.logger.debug(f"Emitting response from {participant}")
                            self.response_received.emit(participant, response, ai_name, model)
                            loop.run_until_complete(asyncio.sleep(0.1))
                elif isinstance(response, str):
                    self.logger.debug("Emitting system response")
                    self.response_received.emit("System", response, "System", "System")
        except Exception as e:
            self.logger.error(f"Error in AIResponseThread: {str(e)}", exc_info=True)
            self.error_occurred.emit(f"Error: {str(e)}")
        finally:
            self.logger.debug("Closing conversation manager session")
            loop.run_until_complete(self.conversation_manager.close_session())
            loop.close()
            self.conversation_completed.emit()
            self.logger.debug("AIResponseThread completed")

    def stop(self):
        self.conversation_manager.interrupt()
        self.logger.debug("AIResponseThread interrupted")


class CustomPygmentsStyle(Style):
    background_color = "#E6F3FF"  # Light blue background
    default_style = ""
    styles = {
        Comment: "italic #008000",
        Keyword: "bold #0000FF",
        Name: "#000000",
        String: "#A31515",
        Number: "#098658",
        Operator: "#000000",
        Punctuation: "#000000",
    }


class CodeBlockHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []

        marker_format = QTextCharFormat()
        marker_format.setForeground(QColor("#808080"))
        self.highlighting_rules.append((re.compile(r""), marker_format))
        self.highlighting_rules.append((re.compile(r""), marker_format))

    def highlightBlock(self, text):
        logger.debug(f"Highlighting code block: {text}")
        for pattern, format in self.highlighting_rules:
            for match in pattern.finditer(text):
                start, end = match.span()
                self.setFormat(start, end - start, format)
        logger.debug(f"Completed highlighting code block: {text}")

class MarkdownFormatter:
    def __init__(self, conversation_display, code_wrap_mode=QTextOption.NoWrap,
                 text_wrap_mode=QTextOption.WrapAtWordBoundaryOrAnywhere):
        self.conversation_display = conversation_display
        self.code_block_highlighter = CodeBlockHighlighter(self.conversation_display.document())
        self.github_dark_style = get_style_by_name('github-dark')
        self.html_formatter = HtmlFormatter(style=self.github_dark_style, noclasses=True)
        self.code_wrap_mode = code_wrap_mode
        self.text_wrap_mode = text_wrap_mode
        self.original_text_color = self.conversation_display.textColor()
        logger.debug(f"Initialized MarkdownFormatter with conversation_display: {conversation_display}")


    def format_text(self, cursor, text):
        logger.debug(f"Formatting text: {text} with cursor: {cursor}")
        code_block_regex = re.compile(r'```(\w+)?\n([\s\S]+?)\n```')
        parts = code_block_regex.split(text)
        logger.debug(f"Split text into parts: {parts}")

        for i in range(0, len(parts), 3):
            regular_text = parts[i]
            logger.debug(f"Inserting regular text part: {regular_text}")
            self.insert_regular_text(cursor, regular_text)

            if i + 2 < len(parts):
                language = parts[i+1]
                code_block = parts[i+2]
                logger.debug(f"Inserting code block part: {code_block} with language: {language}")
                self.insert_code_block(cursor, code_block, language)

        self.reset_formatting(cursor)

    def insert_regular_text(self, cursor, text):
        logger.debug(f"Inserting regular text block: {text} with cursor: {cursor}")
        text_option = QTextOption()
        text_option.setWrapMode(self.text_wrap_mode)
        cursor.document().setDefaultTextOption(text_option)
        cursor.insertText(text)
        logger.debug("Inserted regular text block.")

    def insert_code_block(self, cursor, code, language):
        logger.debug(f"Inserting code block: {code} with cursor: {cursor} and language: {language}")
        try:
            lexer = get_lexer_by_name(language)
        except Exception as e:
            logger.error(f"Error in lexer for language {language}: {e}. Using 'text' lexer.")
            lexer = get_lexer_by_name('text')

        highlighted_code = highlight(code, lexer, self.html_formatter)
        logger.debug(f"Highlighted code: {highlighted_code}")

        original_wrap_mode = self.conversation_display.wordWrapMode()
        logger.debug(f"Original word wrap mode: {original_wrap_mode}")

        self.conversation_display.setWordWrapMode(self.code_wrap_mode)
        logger.debug("Set word wrap mode for code block.")

        cursor.insertHtml(highlighted_code)
        logger.debug("Inserted HTML code block.")

        self.conversation_display.setWordWrapMode(original_wrap_mode)
        logger.debug("Restored original word wrap mode.")

        cursor.movePosition(QTextCursor.End)
        logger.debug("Moved cursor to end after code block.")

        self.reset_formatting(cursor)

    def reset_formatting(self, cursor):
        char_format = QTextCharFormat()
        char_format.setFont(cursor.document().defaultFont())
        char_format.setForeground(QColor("#F5F5F5"))
        cursor.setCharFormat(char_format)

        block_format = QTextBlockFormat()
        cursor.setBlockFormat(block_format)

        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        cursor.document().setDefaultTextOption(text_option)


class AIConversationGUI(QMainWindow):
  #  ai_response_generated = pyqtSignal(str, str, str, str)
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("Initializing AIConversationGUI")
        self.conversation_manager = None
        self.user_name = None
        self.config_file = 'gui_config.json'
        self.history_window = None
        self.response_thread = None
        self.load_config()
        self.init_ui()
        self.markdown_formatter = MarkdownFormatter(self.conversation_display)
        self.apply_config()
        self.user_color = QColor(self.config['user_color'])
        self.ai_color = QColor(self.config['ai_color'])
        self.system_color = QColor(self.config['system_color'])
        self.check_existing_user_identity()
        self.vector_graph = None
        self.last_message_index = 0
        self.active_participants: List[str] = []
        self.topic_generated = False
        self.vector_graph = None

        # Initialize active participants
        self.update_participants()

        self.logger.info("AIConversationGUI initialization complete")

    def set_active_participants(self, participants: List[str]):
        self.active_participants = participants
        self.logger.info(f"Active participants set to: {self.active_participants}")

    def change_font(self):
        self.logger.debug("Opening font selection dialog")
        font, ok = QFontDialog.getFont(self.conversation_display.font(), self)
        if ok:
            self.conversation_display.setFont(font)
            self.config['font_family'] = font.family()
            self.config['font_size'] = font.pointSize()
            self.save_config()
            self.logger.info(f"Font updated to {font.family()} with size {font.pointSize()}")
        else:
            self.logger.debug("Font selection cancelled")

    def open_edit_personalities_dialog(self):
        """
        Open the dialog to edit AI personalities.
        """
        self.logger.debug("Opening Edit Personalities dialog")
        dialog = EditPersonalities(self)
        dialog.exec_()

    def open_edit_ai_configs_dialog(self):
        """
        Open the dialog to edit AI configurations.
        """
        self.logger.debug("Opening Edit AI Configs dialog")
        dialog = EditAIConfigs(self)
        dialog.exec_()

    def open_edit_helper_personalities_dialog(self):
        """
        Open the dialog to edit helper personalities.
        """
        self.logger.debug("Opening Edit Helper Personalities dialog")
        dialog = EditHelperPersonalities(self)
        dialog.exec_()

    def load_config(self):
        """
        Load configuration from gui_config.json file.
        If the file doesn't exist or is missing keys, use default values.
        """
        self.logger.debug("Loading GUI configuration")
        default_config = {
            'font_family': 'Arial',
            'font_size': 12,
            'user_color': '#58a6ff',
            'ai_color': '#58a6ff',
            'system_color': '#7ee787',
            'conversation_font_color': '#c9d1d9',
            'conversation_background_color': '#0d1117'
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)

                # Update default_config with loaded values, keeping defaults for any missing keys
                self.config = {**default_config, **loaded_config}

                self.logger.info("Configuration loaded and merged with defaults successfully")
            except json.JSONDecodeError:
                self.logger.error("Error decoding JSON from config file. Using default settings.")
                self.config = default_config
        else:
            self.logger.info("Config file not found. Using default configuration.")
            self.config = default_config

        self.save_config()  # Save the config to ensure all keys are present in the file

    def save_config(self):
        """
        Save current configuration to gui_config.json file.
        """
        self.logger.debug("Saving GUI configuration")
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info("Configuration saved successfully")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")

    def apply_config(self):
        """
        Apply loaded configuration to GUI elements.
        """
        self.logger.debug("Applying loaded configuration to GUI")

        # Set font
        font = QFont(self.config['font_family'], self.config['font_size'])
        self.conversation_display.setFont(font)

        # Set colors
        self.user_color = QColor(self.config['user_color'])
        self.conversation_font_color = QColor(self.config['conversation_font_color'])
        self.conversation_background_color = QColor(self.config['conversation_background_color'])

        # Apply colors to conversation display
        self.update_conversation_display_colors()

        self.logger.info("Configuration applied to GUI elements")


    def init_ui(self):
        """
          Initialize the user interface components.
          """
        self.logger.debug("Starting UI initialization")

        # Set window properties
        self.setWindowTitle('AI Conversation')
        self.setGeometry(100, 100, 1200, 800)
        self.logger.debug("Window properties set")

        # Create central widget and main layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        self.logger.debug("Central widget and main layout created")

        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        self.logger.debug("Main splitter created")

        # Left panel (conversation area)
        left_panel = QWidget()
        self.left_layout = QVBoxLayout(left_panel)
        splitter.addWidget(left_panel)
        self.logger.debug("Left panel created")

        # Create a vertical splitter for conversation display and input area
        conversation_splitter = QSplitter(Qt.Vertical)
        self.left_layout.addWidget(conversation_splitter)

        # Conversation display
        conversation_group = QGroupBox("Conversation")
        conversation_layout = QVBoxLayout(conversation_group)
        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        conversation_layout.addWidget(self.conversation_display)
        conversation_splitter.addWidget(conversation_group)
        self.logger.debug("Conversation display area set up")

        # Set up the multiline input area
        input_widget = self.setup_multiline_input()
        conversation_splitter.addWidget(input_widget)
        self.logger.debug("Multiline input area set up")

        # Set initial sizes for the conversation splitter (adjust as needed)
        conversation_splitter.setSizes([300, 100])

        # Right panel (controls and status)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        splitter.addWidget(right_panel)
        self.logger.debug("Right panel created")


        self.setup_right_panel_controls(right_layout)

        self.setup_participant_selection(right_layout)

        # Set initial sizes for the main splitter
        splitter.setSizes([2 * self.width() // 3, self.width() // 3])

        # Status bar
        self.statusBar().showMessage("Ready")
        self.logger.debug("Status bar initialized")

        # Disable the send button initially
        self.send_button.setEnabled(False)
        self.logger.debug("Send button initially disabled")

        self.logger.info("UI initialization completed")

    def setup_participant_selection(self, parent_layout):
        participant_group = QGroupBox("AI Participants")
        participant_layout = QVBoxLayout(participant_group)

        self.participant_list = QListWidget()
        self.participant_list.setSelectionMode(QAbstractItemView.MultiSelection)

        # Sort participants in alphabetical order
        sorted_participants = sorted(AI_PERSONALITIES.keys())

        for i, participant in enumerate(sorted_participants):
            item = QListWidgetItem(participant)
            self.participant_list.addItem(item)
            if i == 0:
                item.setSelected(True)  # Only select the first (top) participant by default

        participant_layout.addWidget(self.participant_list)

        update_button = QPushButton("Update Participants")
        update_button.clicked.connect(self.update_participants)
        participant_layout.addWidget(update_button)

        parent_layout.addWidget(participant_group)

        # Connect the itemSelectionChanged signal to update_participants
        self.participant_list.itemSelectionChanged.connect(self.update_participants)

    def update_participants(self):
        self.active_participants = [item.text() for item in self.participant_list.selectedItems()]
        self.logger.info(f"Active participants updated: {self.active_participants}")
        if self.conversation_manager:
            self.conversation_manager.set_active_participants(self.active_participants)

    def setup_right_panel_controls(self, right_layout):
        """
        Set up the controls for the right panel.
        """
        # Vector Graph
        vector_group = QGroupBox("Vector Graph")
        vector_group.setMinimumSize(200, 200)  # Set a minimum size
        self.vector_graph_layout = QVBoxLayout(vector_group)
        right_layout.addWidget(vector_group)

        # Grid layout for buttons
        button_grid = QGridLayout()
        right_layout.addLayout(button_grid)

        # Define buttons with their text, icon, tooltip, and their corresponding method
        buttons_info = [
            ("Change Font", 'icons/font.png', "Change Font", self.change_font),
            ("Edit AI Configs", 'icons/edit_ai_configs.png', "Edit AI Configs", self.open_edit_ai_configs_dialog),
            ("Edit AI Personalities", 'icons/edit_personalities.png', "Edit AI Personalities",
             self.open_edit_personalities_dialog),
            ("Edit Helper Personalities", 'icons/edit_helper_personalities.png', "Edit Helper Personalities",
             self.open_edit_helper_personalities_dialog),
            ("Moderator Response", 'icons/moderator_response.png', "Generate Moderator Response",
             self.generate_moderator_summary),
            ("New Topic", 'icons/new_topic.png', "Start New Topic", self.new_topic),
            ("User Color", 'icons/color.png', "Choose User Color", self.choose_color),
            ("Font Color", 'icons/font_color.png', "Choose Conversation Font Color",
             self.choose_conversation_font_color),
            ("Background Color", 'icons/background_color.png', "Choose Background Color",
             self.choose_conversation_background_color),
            ("View Conversation History", 'icons/history.png', "View Conversation History", self.open_history_window),
        ]

        # Sort buttons_info by button text
        buttons_info.sort(key=lambda x: x[0])

        # Add buttons to the grid in sorted order and set text alignment to left
        for row, (text, icon_path, tooltip, slot) in enumerate(buttons_info):
            button = QPushButton(text)
            button.setIcon(QIcon(icon_path))  # Replace with your icon path
            button.setToolTip(tooltip)
            button.clicked.connect(slot)
            button.setStyleSheet("text-align: left;")  # Left-justify the button text
            button_grid.addWidget(button, row // 2, row % 2)

        # Token usage
        token_group = QGroupBox("Token Usage")
        token_layout = QVBoxLayout(token_group)
        self.token_label = QLabel("Total Tokens: 0")
        token_layout.addWidget(self.token_label)
        right_layout.addWidget(token_group)
        self.logger.debug("Token usage display set up")

        # Interrupt button (unchanged)
        self.interrupt_button = QPushButton("Interrupt")
        self.interrupt_button.setIcon(QIcon('icons/interrupt.png'))  # Replace with your icon path
        self.interrupt_button.setToolTip("Interrupt")
        self.interrupt_button.clicked.connect(self.interrupt_conversation)
        button_grid.addWidget(self.interrupt_button, (len(buttons_info) + 1) // 2, 0, 1, 2)
        self.logger.debug("Interrupt button added")


    def open_history_window(self):
        """
          Open the conversation history window.
          """
        self.logger.debug("Opening conversation history window")
        if self.history_window is None:
            self.history_window = ConversationHistoryWindow(
                self,
                insert_header=self.insert_header,
                insert_divider=self.insert_divider,
                insert_message_content=self.insert_message_content,
                reset_formatting=self.reset_formatting,
                config=self.config
            )
        self.history_window.show()


    def setup_multiline_input(self):
        """
          Set up a multiline, scrollable input area for user messages with formatting controls.
          """
        self.logger.debug("Setting up multiline input area with formatting controls")

        input_container = QWidget()
        input_layout = QVBoxLayout(input_container)

        # Create formatted input box
        self.user_input = FormattedTextEdit(self)
        self.user_input.setPlaceholderText("Type your message here...")
        input_layout.addWidget(self.user_input)

        # Create send button
        button_layout = QHBoxLayout()
        self.send_button = QPushButton('Send')
        self.send_button.clicked.connect(self.on_send_button_clicked)
        button_layout.addStretch()
        button_layout.addWidget(self.send_button)

        input_layout.addLayout(button_layout)

        self.logger.debug("Multiline input area with formatting controls set up successfully")
        return input_container

    def setup_font_controls(self, parent_layout):
        """
        Set up controls for changing the font in the conversation display.
        """
        self.logger.debug("Setting up font controls")

        font_container = QWidget()
        font_layout = QHBoxLayout(font_container)

        # Font family selection
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self.update_font)
        font_layout.addWidget(QLabel("Font:"))
        font_layout.addWidget(self.font_combo)

        # Font size selection
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 24)
        self.font_size_spin.setValue(self.config['font_size'])
        self.font_size_spin.valueChanged.connect(self.update_font)
        font_layout.addWidget(QLabel("Size:"))
        font_layout.addWidget(self.font_size_spin)

        # Add font controls to the provided layout
        parent_layout.addWidget(font_container)

        self.logger.debug("Font controls set up successfully")

    def setup_color_controls(self, parent_layout):
        self.logger.debug("Setting up color controls")

        color_container = QWidget()
        color_layout = QHBoxLayout(color_container)

        # User color selection
        self.color_button = QPushButton("Choose User Color")
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)

        self.color_preview = QLabel()
        self.color_preview.setFixedSize(20, 20)
        self.color_preview.setStyleSheet(f"background-color: {self.config['user_color']};")
        color_layout.addWidget(self.color_preview)

        # Conversation font color selection
        self.conversation_font_color_button = QPushButton("Choose Conversation Font Color")
        self.conversation_font_color_button.clicked.connect(self.choose_conversation_font_color)
        color_layout.addWidget(self.conversation_font_color_button)

        self.conversation_font_color_preview = QLabel()
        self.conversation_font_color_preview.setFixedSize(20, 20)
        self.conversation_font_color_preview.setStyleSheet(
            f"background-color: {self.config['conversation_font_color']};")
        color_layout.addWidget(self.conversation_font_color_preview)

        # Add color controls to the provided layout
        parent_layout.addWidget(color_container)

        self.logger.debug("Color controls set up successfully")

    def setup_background_color_controls(self, parent_layout):
        """
        Set up controls for changing the background color of the conversation display.
        """
        self.logger.debug("Setting up background color controls")

        bg_color_container = QWidget()
        bg_color_layout = QHBoxLayout(bg_color_container)

        self.conversation_background_color_button = QPushButton("Choose Background Color")
        self.conversation_background_color_button.clicked.connect(self.choose_conversation_background_color)
        bg_color_layout.addWidget(self.conversation_background_color_button)

        self.conversation_background_color_preview = QLabel()
        self.conversation_background_color_preview.setFixedSize(20, 20)
        self.conversation_background_color_preview.setStyleSheet(
            f"background-color: {self.config['conversation_background_color']};")
        bg_color_layout.addWidget(self.conversation_background_color_preview)

        # Add background color controls to the provided layout
        parent_layout.addWidget(bg_color_container)

        self.logger.debug("Background color controls set up successfully")

    def update_font(self):
        """
        Update the font of the conversation display based on user selection and save the new configuration.
        """
        self.logger.debug("Updating conversation display font")
        font = self.font_combo.currentFont()
        font.setPointSize(self.font_size_spin.value())
        self.conversation_display.setFont(font)

        # Update config
        self.config['font_family'] = font.family()
        self.config['font_size'] = font.pointSize()
        self.save_config()

        self.logger.info(f"Font updated to {font.family()} with size {font.pointSize()}")

    def choose_conversation_font_color(self):
        """
        Open a color dialog, update the conversation font color, and save the new configuration.
        """
        self.logger.debug("Opening conversation font color selection dialog")
        color = QColorDialog.getColor()
        if color.isValid():
            self.conversation_font_color = color

            # Update config
            self.config['conversation_font_color'] = color.name()
            self.save_config()

            # Apply the new color
            self.update_conversation_display_colors()

            self.logger.info(f"Conversation font color updated to {color.name()}")
        else:
            self.logger.debug("Conversation font color selection cancelled")

    def choose_conversation_background_color(self):
        """
        Open a color dialog, update the conversation background color, and save the new configuration.
        """
        self.logger.debug("Opening conversation background color selection dialog")
        color = QColorDialog.getColor()
        if color.isValid():
            self.conversation_background_color = color

            # Update config
            self.config['conversation_background_color'] = color.name()
            self.save_config()

            # Apply the new color
            self.update_conversation_display_colors()

            self.logger.info(f"Conversation background color updated to {color.name()}")
        else:
            self.logger.debug("Conversation background color selection cancelled")

    def update_conversation_display_colors(self):
        """
        Update the conversation display with the current font and background colors.
        """
        self.logger.debug("Updating conversation display colors")
        palette = self.conversation_display.palette()
        palette.setColor(QPalette.Base, self.conversation_background_color)
        palette.setColor(QPalette.Text, self.conversation_font_color)
        self.conversation_display.setPalette(palette)
        self.logger.info("Conversation display colors updated")

    def choose_color(self):
        """
        Open a color dialog, update the user's font color, and save the new configuration.
        """
        self.logger.debug("Opening color selection dialog")
        color = QColorDialog.getColor()
        if color.isValid():
            self.user_color = color

            # Update config
            self.config['user_color'] = color.name()
            self.save_config()

            # Schedule the color update to run after the current event loop iteration
            QTimer.singleShot(0, self.update_user_message_colors)

            self.logger.info(f"User font color updated to {color.name()}")
        else:
            self.logger.debug("Color selection cancelled")

    def update_user_message_colors(self):
        """
        Update the color of existing user messages in the conversation display.
        """
        self.conversation_display.setUpdatesEnabled(False)
        cursor = self.conversation_display.textCursor()
        cursor.beginEditBlock()

        document = self.conversation_display.document()
        block = document.begin()

        while block.isValid():
            if block.text().startswith(f"{self.user_name}:"):
                cursor.setPosition(block.position())
                cursor.select(QTextCursor.BlockUnderCursor)
                format = cursor.charFormat()
                format.setForeground(self.user_color)
                cursor.mergeCharFormat(format)
            block = block.next()

        cursor.endEditBlock()
        self.conversation_display.setTextCursor(cursor)
        self.conversation_display.setUpdatesEnabled(True)
        self.conversation_display.update()

    def check_existing_user_identity(self):
        self.logger.debug("Checking for existing user identity")
        if USER_IDENTITY:
            self.user_name = next(iter(USER_IDENTITY))
            self.logger.info(f"Existing user identity found: {self.user_name}")
            self.initialize_conversation_manager(self.user_name)
        else:
            self.logger.info("No existing user identity found, prompting for name")
            self.prompt_for_name()

    def prompt_for_name(self):
        """
        Prompt the user to enter their name.
        """
        self.logger.debug("Prompting user for name")
        self.append_message("System", "Welcome to the AI Conversation! Please enter your name:")
        self.user_input.setPlaceholderText("Enter your name here")
        self.send_button.setText("Set Name")
        self.send_button.setEnabled(True)
        self.send_button.clicked.disconnect()
        self.send_button.clicked.connect(self.set_user_name)
        self.logger.info("Name prompt set up")

    def set_user_name(self):
        """
        Set the user's name based on their input.
        """
        name = self.user_input.toPlainText().strip()
        self.logger.info(f"Attempting to set user name: {name}")
        if name:
            self.user_name = name
            if self.user_name not in USER_IDENTITY:
                USER_IDENTITY[self.user_name] = {'greeting': f"Welcome, {self.user_name}!"}
                self.logger.info(f"Added new user to USER_IDENTITY: {self.user_name}")
            self.initialize_conversation_manager(self.user_name)
        else:
            self.logger.warning("Invalid name entered")
            self.append_message("System", "Please enter a valid name.")
            self.prompt_for_name()


    def initialize_conversation_manager(self, name):
        self.logger.info(f"Initializing conversation manager for user: {name}")
        self.conversation_manager = ConversationManager(name, is_gui=True)
        self.conversation_manager.load_user_identity()
        self.setup_connections()
        self.append_message("System",
                            f"Welcome, {name}! You can now start the conversation by entering your first message.")
        self.user_input.clear()

        self.user_input.setPlaceholderText("Type your message here to start the conversation...")
        self.send_button.setText("Start Conversation")
        self.send_button.clicked.disconnect()
        self.send_button.clicked.connect(self.on_send_button_clicked)

        # Initialize and set up the visualizer
        self.setup_visualizer()

        # Add a label to display the current topic
        self.topic_label = QLabel("Topic: Not set")
        self.left_layout.insertWidget(0, self.topic_label)

        # Enable the send button for future messages
        self.send_button.setEnabled(True)

        self.logger.info("Conversation manager initialized, waiting for first user input")


    def setup_connections(self):
        self.logger.debug("Setting up signal-slot connections")
        if self.conversation_manager is not None:
            # Connect signals from ConversationManager
            self.conversation_manager.ai_thinking_started.connect(self.on_ai_thinking_started)
            self.conversation_manager.ai_thinking_finished.connect(self.on_ai_thinking_finished)
            self.conversation_manager.token_usage_updated.connect(self.update_token_usage)
            self.conversation_manager.user_identity_loaded.connect(self.on_user_identity_loaded)
            self.conversation_manager.ai_response_generated.connect(self.update_conversation_window)
            self.conversation_manager.ai_thinking_started.connect(self.on_ai_thinking_started)
            self.conversation_manager.ai_thinking_finished.connect(self.on_ai_thinking_finished)
            self.logger.debug("Connected ConversationManager signals to appropriate slots")
        else:
            self.logger.warning("Cannot set up connections: conversation_manager is None")

        # Connect UI element signals
        self.send_button.clicked.connect(self.on_send_button_clicked)
        # Connect the new signal for topic updates
        self.conversation_manager.ai_response_generated.connect(self.handle_ai_response)

    def start_conversation(self):
        self.logger.info("Starting new conversation")
        self.append_message("System", "A new conversation topic has been started. What would you like to talk about?")
        self.update_status_bar("Ready for new topic")

    def setup_visualizer(self):
        try:
            # Create the VectorGraphVisualizer
            self.vector_graph = VectorGraphVisualizer(self.conversation_manager.rag)

            # Set size policy to allow the widget to expand
            self.vector_graph.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            # Set the visualizer for the conversation manager
            self.conversation_manager.set_visualizer(self.vector_graph)

            # Add the visualizer to the right panel
            self.vector_graph_layout.addWidget(self.vector_graph)

            # Make sure the visualizer is visible
            self.vector_graph.show()

            self.logger.info("Visualizer set up successfully")
        except Exception as e:
            self.logger.error(f"Error setting up visualizer: {str(e)}")

    def insert_empty_lines(self, cursor, count=1):
        for _ in range(count):
            cursor.insertBlock()

    def insert_header(self, cursor, sender):
        header_format = QTextCharFormat()
        header_format.setFontWeight(QFont.Bold)

        if sender in AI_PERSONALITIES:
            header_format.setForeground(QColor('yellow'))  # Set personality name color to yellow
            character = AI_PERSONALITIES[sender]['character']  # Get the character for the sender
            character_color = QColor(AI_PERSONALITIES[sender]['color'])  # Get the color for the character
        elif sender == self.user_name:
            header_format.setForeground(QColor('yellow'))  # Set user name color to yellow
            character = '😎'  # Use a default character for the user
            character_color = self.user_color
        else:  # System messages or unknown senders
            header_format.setForeground(QColor('black'))  # Set text color to black for system messages
            character = ''  # No character for system messages
            character_color = QColor('white')

        cursor.setCharFormat(header_format)
        cursor.insertText(f"{sender}: ")

        if character:
            char_format = QTextCharFormat()
            char_format.setForeground(character_color)
            cursor.setCharFormat(char_format)
            cursor.insertText(character)
            cursor.setCharFormat(header_format)  # Reset the format after inserting the character

    def insert_divider(self, cursor):
        cursor.insertBlock()
        divider_format = QTextCharFormat()
        divider_format.setForeground(QColor('lightgray'))
        cursor.setCharFormat(divider_format)
        cursor.insertText('-' * 50)  # 50 dashes for the divider line
        cursor.insertBlock()


    def reset_formatting(self, cursor):
        char_format = QTextCharFormat()
        char_format.setFont(cursor.document().defaultFont())
        char_format.setForeground(QColor(self.config['conversation_font_color']))
        cursor.setCharFormat(char_format)

        block_format = QTextBlockFormat()
        cursor.setBlockFormat(block_format)

        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        cursor.document().setDefaultTextOption(text_option)


    def insert_message_content(self, cursor, message):
        # Set up content format
        content_format = QTextCharFormat()
        content_format.setForeground(QColor(self.config['conversation_font_color']))
        content_format.setBackground(QColor(self.config['conversation_background_color']))
        cursor.setCharFormat(content_format)
        logger.debug("Set content format for message.")

        # Enable word wrap
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        cursor.block().document().setDefaultTextOption(text_option)
        logger.debug("Enabled word wrap for message content.")

        # Split the message into code and non-code parts
        parts = re.split(r'(=== code begin ===[\s\S]*?=== code end ===)', message)
        logger.debug(f"Split message into parts: {parts}")

        for part in parts:
            # Reset to default format before processing each part
            self.reset_formatting(cursor)

            if part.startswith('=== code begin ===') and part.endswith('=== code end ==='):
                # This is a code block
                code = part.replace('=== code begin ===', '').replace('=== code end ===', '').strip()
                logger.debug(f"Processing code block: {code}")

                try:
                    lexer = guess_lexer(code)
                except Exception as e:
                    logger.error(f"Error guessing lexer: {e}")
                    lexer = get_lexer_by_name('text')

                # Use github-dark style for Pygments
                style = get_style_by_name('github-dark')
                formatter = HtmlFormatter(style=style, noclasses=True)
                highlighted_code = highlight(code, lexer, formatter)

                # Insert the highlighted code
                cursor.insertHtml(highlighted_code)
                logger.debug("Inserted highlighted code block.")

                # Reset formatting after code block
                self.reset_formatting(cursor)
                logger.debug("Reset formatting after code block.")

                # Insert a new block after the code
                cursor.insertBlock()
                logger.debug("Inserted new block after code block.")

            else:
                # This is regular text, use markdown formatting
                logger.debug(f"Processing regular text part: {part}")
                self.markdown_formatter.format_text(cursor, part)
                logger.debug("Formatted regular text part.")

            # Reset to content format after processing each part
            cursor.setCharFormat(content_format)
            logger.debug("Reset content format after processing part.")

        # Ensure there's a new line after the message
        cursor.insertBlock()
        logger.debug("Inserted new block after message.")

        # Final reset of formatting
        self.reset_formatting(cursor)
        logger.debug("Final reset of formatting after message.")


    def append_message(self, sender, message, ai_name=None, model=None):
        self.logger.debug(f"Appending message from {sender}: {message}")

        cursor = self.conversation_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.logger.debug("Cursor moved to end of conversation display.")

        # Insert two empty lines before new messages (one extra for spacing)
        self.insert_empty_lines(cursor, 2)

        # Set up formats
        header_format = QTextCharFormat()
        header_format.setFontWeight(QFont.Bold)

        # Set header background color based on sender
        if sender in AI_PERSONALITIES:
            header_format.setBackground(QColor(AI_PERSONALITIES[sender]['color']))
        elif sender == self.user_name:
            header_format.setBackground(self.user_color)
        elif sender == "System":
            header_format.setBackground(self.system_color)
        else:
            header_format.setBackground(QColor(self.config['conversation_background_color']))

        # Set header text color
        header_format.setForeground(QColor(self.config['conversation_font_color']))

        # Insert header
        cursor.setCharFormat(header_format)
        cursor.insertText(f"{sender}: ")
        self.logger.debug(f"Inserted header for {sender}.")

        # Insert divider line
        self.insert_divider(cursor)
        self.logger.debug("Inserted divider line.")

        # Check if this is a topic message
        if sender == "System" and message.startswith("Conversation topic:"):
            self.insert_topic_message(cursor, message)
        else:
            # Insert regular message content
            self.insert_message_content(cursor, message)

        self.logger.debug("Inserted message content.")

        # Ensure the new message is visible
        self.conversation_display.setTextCursor(cursor)
        self.conversation_display.ensureCursorVisible()
        self.logger.debug("Set cursor to new message and ensured visibility.")

        # Update conversation history
        if self.conversation_manager and self.conversation_manager.current_thread_id:
            self.conversation_manager.update_conversation(message, sender, ai_name, model)
            self.logger.debug("Updated conversation history.")

    def setup_conversation_display(self):
        # Set default font for the conversation display
        font = QFont("Arial", 10)
        self.conversation_display.setFont(font)

        # Enable word wrapping
        self.conversation_display.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

        # Set line spacing
        text_option = self.conversation_display.document().defaultTextOption()
        text_option.setLineHeight(150, QTextOption.ProportionalHeight)
        self.conversation_display.document().setDefaultTextOption(text_option)

        # Set the text edit to read-only mode
        self.conversation_display.setReadOnly(True)

        # Enable text interaction
        self.conversation_display.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )


    @pyqtSlot(str)
    def on_ai_thinking_started(self, participant: str):
        """
          Handle the start of AI thinking process.

          Args:
              participant (str): The name of the AI participant that started thinking
          """
        self.logger.debug(f"AI thinking started: {participant}")
        self.update_status_bar(f"{participant} is thinking...")


    @pyqtSlot(str)
    def on_ai_thinking_finished(self, participant: str):
        """
          Handle the end of AI thinking process.

          Args:
              participant (str): The name of the AI participant that finished thinking
          """
        self.logger.debug(f"AI thinking finished: {participant}")
        self.update_status_bar("Ready")

    @pyqtSlot(int)
    def start_conversation(self):
        self.logger.info("Starting new conversation")
        self.append_message("System", "A new conversation topic has been started. What would you like to talk about?")
        self.update_status_bar("Ready for new topic")

    @pyqtSlot(str)
    def on_user_identity_loaded(self, greeting):
        self.logger.debug(f"User identity loaded: {greeting}")
        self.append_message("System", greeting)


    @pyqtSlot(str, str, str, str)
    def update_conversation_window(self, participant: str, response: str, ai_name: str, model: str):
        """
          Update the conversation window with a new message.

          This method is called when a new AI response is generated, including the moderator summary.

          Args:
              participant (str): The name of the participant who generated the response
              response (str): The content of the response
              ai_name (str): The name of the AI model used
              model (str): The specific model version used
          """
        self.logger.debug(f"Updating conversation window: {participant}")
        if response:  # Only append non-empty responses
            self.append_message(participant, response, ai_name, model)
            self.update_token_usage(self.conversation_manager.get_token_usage()['total_tokens'])
            self.logger.debug(f"Appended message from {participant} to conversation window")
        else:
            self.logger.warning(f"Received empty response from {participant}")

    @pyqtSlot(str)
    def on_topic_generated(self, topic):
        self.logger.info(f"Topic generated: {topic}")
        self.topic_generated = True
        self.append_message("System", f"Conversation topic: {topic}")
        self.update_topic_display(topic)

    @pyqtSlot(str)
    def check_and_generate_topic(self):
        if self.conversation_manager and set(
                self.active_participants) == self.conversation_manager.responded_participants:
            self.logger.info("All active participants have responded. Requesting topic generation.")
            self.generate_topic()
        else:
            self.logger.info("Not all active participants have responded. Skipping topic generation.")

    def generate_topic(self):
        self.logger.info("Generating topic for the conversation")
        self.update_status_bar("Generating topic...")

        # Create and start the AIResponseThread for topic generation
        self.response_thread = AIResponseThread(
            self.conversation_manager,
            "",
            is_initial_conversation=False,
            is_topic_generation=True
        )
        self.response_thread.response_received.connect(self.on_topic_generated)
        self.response_thread.error_occurred.connect(self.on_error_occurred)
        self.response_thread.start()

    @pyqtSlot(int)
    def update_token_usage(self, total_tokens):
        # self.logger.debug(f"Updating token usage: {total_tokens}")
        self.token_label.setText(f"Total Tokens: {total_tokens}")

    @pyqtSlot(str)
    def on_error_occurred(self, error_message: str):
        """
        Handle errors that occur during conversation or moderator summary generation.

        Args:
            error_message (str): The error message to display
        """
        self.logger.error(f"Error in conversation: {error_message}")
        self.update_status_bar("Error occurred")
        self.append_message("System", f"An error occurred: {error_message}")
        self.send_button.setEnabled(True)
        self.logger.info("GUI updated after error occurrence")


    @pyqtSlot(str, str, str, str)
    def handle_ai_response(self, participant, response, ai_name, model):
        if participant == "System" and response.startswith("The topic of this conversation has been set to:"):
            self.update_topic_display(response.split(": ", 1)[1])

    # else:
    #    self.update_conversation_window(participant, response, ai_name, model)


    def on_send_button_clicked(self):
        self.logger.debug("Send button clicked")
        user_input = self.user_input.toPlainText().strip()
        if user_input:
            if self.conversation_manager is None:
                self.set_user_name()
            elif user_input.startswith("!"):
                self.handle_command(user_input)
            else:
                if not self.active_participants:
                    QMessageBox.warning(self, "Warning",
                                        "Please select at least one AI participant before starting the conversation.")
                    return
                if self.conversation_manager:
                    self.conversation_manager.reset_interrupt()  # Reset interrupt flag
                self.send_message(user_input)
                if self.conversation_manager.is_first_prompt:
                    self.send_button.setText("Send")  # Change button text after first message
            self.user_input.clear()


    def continue_conversation(self, user_input):
        """
        Continue the conversation with the given user input.
        """
        self.logger.info(f"Continuing conversation with user input: {user_input[:50]}...")  # Log first 50 chars
        self.append_message(self.user_name, user_input)
        self.update_status_bar("Processing message...")
        self.send_button.setEnabled(False)

        self.response_thread = AIResponseThread(
            self.conversation_manager,
            user_input,
            is_initial_conversation=False,
            active_participants=self.active_participants
        )
        self.response_thread.response_received.connect(self.on_response_received)
        self.response_thread.conversation_completed.connect(self.on_conversation_completed)
        self.response_thread.error_occurred.connect(self.on_error_occurred)
        self.response_thread.start()
        self.logger.debug("AI response thread started")

    def send_message(self, user_message):
        self.logger.info(f"Sending initial message: {user_message[:50]}...")
        if self.conversation_manager:
            # Only display the message, don't add it to conversation history here
            self.append_message(self.user_name, user_message, "Human", self.user_name)
            self.update_status_bar("Processing message...")
            self.send_button.setEnabled(False)

            self.response_thread = AIResponseThread(
                self.conversation_manager,
                user_message,
                is_initial_conversation=True,
                active_participants=self.active_participants
            )
            self.response_thread.response_received.connect(self.on_response_received)
            self.response_thread.topic_generated.connect(self.on_topic_generated)
            self.response_thread.conversation_completed.connect(self.on_conversation_completed)
            self.response_thread.error_occurred.connect(self.on_error_occurred)
            self.response_thread.start()
            self.logger.debug("AI response thread started")
        else:
            self.logger.warning("Cannot send message: conversation_manager is None")
            self.append_message("System", "The conversation has not been initialized. Please enter your name first.",
                                "System", "System")
            self.prompt_for_name()

    @pyqtSlot(str, str, str, str)
    def on_response_received(self, participant, response, ai_name, model):
        self.logger.debug(f"Response received from {participant}")
        # self.update_conversation_window(participant, response, ai_name, model)
        self.update_vector_graph()  # Update the vector graph after each response

        # Check if this is the last response in the round
        if self.response_thread and self.response_thread.isFinished():
            self.on_conversation_completed()


    def on_conversation_completed(self):
        """
          Handle the completion of a conversation round or moderator summary generation.
          """
        self.logger.debug("Conversation or moderator summary generation completed")
        self.update_status_bar("Ready")
        self.send_button.setEnabled(True)
        self.logger.info("GUI updated after conversation completion")

    def update_vector_graph(self):
        if self.vector_graph:
            try:
                self.vector_graph.update_plot()
                self.logger.debug("Vector graph updated")
            except Exception as e:
                self.logger.error(f"Error updating vector graph: {e}")
        else:
            self.logger.warning("Vector graph not initialized")

    def handle_command(self, command):
        self.logger.info(f"Handling command: {command}")
        if command == "!Moderator":
            self.generate_moderator_summary()
        elif command == "!Goodbye":
            self.close()
        elif command == "!NewTopic":
            self.new_topic()
        elif command == "!ChangeUserName":
            self.prompt_for_name()
        elif command == "!Help":
            self.display_help()
        else:
            self.append_message("System", "Unknown command. Type !Help for available commands.")


    def generate_moderator_summary(self):
        """
          Initiate the generation of a moderator summary for the current conversation.

          This method creates and starts an AIResponseThread to generate the summary asynchronously.
          """
        self.logger.info("Initiating moderator summary generation")
        self.update_status_bar("Generating moderator summary...")

        self.response_thread = AIResponseThread(
            self.conversation_manager,
            "",
            is_initial_conversation=False,
            is_moderator_summary=True
        )
        self.response_thread.response_received.connect(self.on_moderator_summary_received)
        self.response_thread.conversation_completed.connect(self.on_conversation_completed)
        self.response_thread.error_occurred.connect(self.on_error_occurred)
        self.response_thread.start()

        self.logger.debug("AIResponseThread for moderator summary started")


    @pyqtSlot(str, str, str, str)
    def on_moderator_summary_received(self, participant: str, response: str, ai_name: str, model: str):
        """
          Handle the reception of the moderator summary.

          This method is called when the moderator summary is generated.

          Args:
              participant (str): Should be "Moderator"
              response (str): The generated summary
              ai_name (str): The name of the AI model used
              model (str): The specific model version used
          """
        self.logger.info("Received moderator summary")
        self.update_status_bar("Moderator summary received")

        # Use the existing method to update the conversation window
        self.update_conversation_window(participant, response, ai_name, model)


    def new_topic(self):
        self.logger.info("Starting a new topic")
        if self.conversation_manager:
            self.conversation_manager.new_topic()
            self.logger.info("New topic started in ConversationManager")

            # Reset the visualizer
            if self.vector_graph:
                self.vector_graph.reset()
                self.vector_graph.set_rag(self.conversation_manager.rag)
                self.logger.info("Reset and updated visualizer with new RAG instance")

            # Update token usage display
            self.update_token_usage(0)

            # Clear the conversation display
            self.conversation_display.clear()

            # Clear the topic display
            self.update_topic_display("Not set")

            # Start the new conversation
            self.start_conversation()

            # Enable the send button and clear the input field
            self.send_button.setEnabled(True)
            self.user_input.clear()

        else:
            self.logger.error("Cannot start new topic: conversation_manager is None")
            self.append_message("System", "Error: Cannot start a new topic. Please initialize the conversation first.")


    def update_topic_display(self, topic):
        # Remove any potential formatting characters and extra spaces
        plain_topic = self.clean_topic_string(topic)
        self.topic_label.setText(f"Topic: {plain_topic}")
        self.topic_label.setStyleSheet("font-weight: bold; color: #58a6ff;")
        self.logger.debug(f"Updated topic display: {plain_topic}")


    def clean_topic_string(self, topic):
        # Remove any extra spaces and potential formatting characters
        import re
        cleaned_topic = re.sub(r'\s+', ' ', topic).strip()
        # Remove any potential markdown or other formatting characters
        cleaned_topic = re.sub(r'[*_`#]+', '', cleaned_topic)
        return cleaned_topic


    def insert_topic_message(self, cursor, message):
        # Extract and clean the topic
        _, topic = message.split(":", 1)
        cleaned_topic = self.clean_topic_string(topic)

        # Use the default text format for the topic
        cursor.setCharFormat(QTextCharFormat())
        cursor.insertText(f"New Conversation Topic: {cleaned_topic}\n")
        self.logger.debug(f"Inserted cleaned topic: {cleaned_topic}")

        # Update the topic display
        self.update_topic_display(cleaned_topic)

    def display_help(self):
        self.logger.debug("Displaying help information")
        help_text = """
        Available commands:
        !Moderator - Get an overview of the conversation
        !Goodbye - End the conversation and close the program
        !NewTopic - Start a new conversation topic
        !ChangeUserName - Change your user name
        !Help - Display this help message
        """
        self.append_message("System", help_text)


    def update_status_bar(self, message: str):
        """
          Update the status bar with a new message.

          Args:
              message (str): The message to display in the status bar
          """
        self.logger.debug(f"Updating status bar: {message}")
        self.statusBar().showMessage(message)

    def interrupt_conversation(self):
        self.logger.info("Interrupting conversation")
        if self.conversation_manager:
            self.conversation_manager.interrupt()
        if self.response_thread and self.response_thread.isRunning():
            self.response_thread.terminate()
            self.response_thread.wait()
        self.update_status_bar("Conversation interrupted")
        self.append_message("System", "Conversation interrupted. You can continue with a new message.")
        self.send_button.setEnabled(True)

    def closeEvent(self, event):
        self.logger.info("Closing application")
        self.save_config()
        if self.conversation_manager:
            self.conversation_manager.save_conversation_history()

        # Close the vector graph
        if self.vector_graph:
            self.vector_graph.close()

        event.accept()


def run_gui():
    app = QApplication(sys.argv)
    main_window = AIConversationGUI()
    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    # Set up logging configuration
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        filename='ai_conversation.log',
                        filemode='w')

    # Add console handler to display logs in console as well
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.debug)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logging.getLogger('').addHandler(console_handler)

    # Run the GUI
    run_gui()
