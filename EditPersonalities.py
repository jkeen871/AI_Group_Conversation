import sys
import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit,
                             QTextEdit, QLabel, QPushButton, QColorDialog, QMessageBox,
                             QScrollArea, QWidget, QComboBox)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt
from ai_config import AI_CONFIG


class EditPersonalities(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit AI Personalities")
        self.setGeometry(100, 100, 1000, 700)
        self.personalities_file = 'personalities.py'  # Path to your personalities file
        self.initUI()
        self.loadPersonalities()

    def initUI(self):
        layout = QHBoxLayout()

        # Left side: List of personalities
        left_layout = QVBoxLayout()
        self.personality_list = QListWidget()
        self.personality_list.itemClicked.connect(self.loadPersonalityDetails)
        left_layout.addWidget(self.personality_list)

        # Add New Personality button
        new_personality_button = QPushButton("Add New Personality")
        new_personality_button.clicked.connect(self.addNewPersonality)
        left_layout.addWidget(new_personality_button)

        # Remove Personality button
        remove_personality_button = QPushButton("Remove Personality")
        remove_personality_button.clicked.connect(self.removePersonality)
        left_layout.addWidget(remove_personality_button)

        # Right side: Editable fields in a scroll area
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.name_edit = QLineEdit()
        right_layout.addWidget(QLabel("Name:"))
        right_layout.addWidget(self.name_edit)

        self.system_message_edit = QTextEdit()
        self.system_message_edit.setMinimumHeight(200)  # Set a minimum height
        right_layout.addWidget(QLabel("System Message:"))
        right_layout.addWidget(self.system_message_edit)

        self.ai_name_combo = QComboBox()
        self.ai_name_combo.addItems(AI_CONFIG.keys())
        right_layout.addWidget(QLabel("AI Name:"))
        right_layout.addWidget(self.ai_name_combo)

        color_layout = QHBoxLayout()
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.chooseColor)
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(20, 20)
        color_layout.addWidget(QLabel("Color:"))
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_preview)
        right_layout.addLayout(color_layout)

        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.saveChanges)
        right_layout.addWidget(save_button)

        # Create a scroll area and set the right widget as its content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(right_widget)

        layout.addLayout(left_layout, 1)
        layout.addWidget(scroll_area, 2)

        self.setLayout(layout)

    def removePersonality(self):
        current_item = self.personality_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a personality to remove.")
            return

        name = current_item.text()
        reply = QMessageBox.question(self, 'Remove Personality',
                                     f"Are you sure you want to remove '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            del AI_PERSONALITIES[name]
            self.saveToFile()
            self.loadPersonalities()
            self.clearPersonalityDetails()
            QMessageBox.information(self, "Removed", f"Personality '{name}' has been removed.")

    def clearPersonalityDetails(self):
        self.name_edit.clear()
        self.system_message_edit.clear()
        self.ai_name_combo.setCurrentIndex(0)
        self.current_color = QColor("#000000")
        self.updateColorButton()

    def loadPersonalities(self):
        self.personality_list.clear()
        # Read the personalities from the file
        with open(self.personalities_file, 'r') as f:
            content = f.read()
            exec(content, globals())
        for name in AI_PERSONALITIES.keys():
            self.personality_list.addItem(name)

    def loadPersonalityDetails(self, item):
        name = item.text()
        personality = AI_PERSONALITIES[name]
        self.name_edit.setText(personality['name'])
        self.system_message_edit.setText(personality['system_message'])
        self.ai_name_combo.setCurrentText(personality['ai_name'])
        self.current_color = QColor(personality['color'])
        self.updateColorButton()

    def chooseColor(self):
        color = QColorDialog.getColor(self.current_color, self)
        if color.isValid():
            self.current_color = color
            self.updateColorButton()

    def updateColorButton(self):
        self.color_preview.setStyleSheet(f"background-color: {self.current_color.name()};")

    def saveChanges(self):
        current_item = self.personality_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a personality to save changes.")
            return

        current_name = current_item.text()
        new_name = self.name_edit.text()

        # Check if the name has changed and if the new name already exists
        if current_name != new_name and new_name in AI_PERSONALITIES:
            QMessageBox.warning(self, "Name Exists", "A personality with this name already exists.")
            return

        AI_PERSONALITIES[new_name] = {
            'name': new_name,
            'system_message': self.system_message_edit.toPlainText(),
            'ai_name': self.ai_name_combo.currentText(),
            'color': self.current_color.name()
        }

        # If the name has changed, remove the old entry
        if current_name != new_name:
            del AI_PERSONALITIES[current_name]

        # Update the current item's text
        current_item.setText(new_name)

        # Save changes to file
        self.saveToFile()

        QMessageBox.information(self, "Saved", "Changes saved successfully.")

    def addNewPersonality(self):
        new_name = "New Personality"
        counter = 1
        while new_name in AI_PERSONALITIES:
            new_name = f"New Personality {counter}"
            counter += 1

        AI_PERSONALITIES[new_name] = {
            'name': new_name,
            'system_message': "",
            'ai_name': list(AI_CONFIG.keys())[0],  # Default to the first AI in the config
            'color': "#000000"  # Default to black
        }

        self.loadPersonalities()
        # Select the new personality
        items = self.personality_list.findItems(new_name, Qt.MatchExactly)
        if items:
            self.personality_list.setCurrentItem(items[0])
            self.loadPersonalityDetails(items[0])

    def saveToFile(self):
        with open(self.personalities_file, 'r') as f:
            lines = f.readlines()

        # Find the start and end of the AI_PERSONALITIES dictionary
        start_index = next(i for i, line in enumerate(lines) if line.strip().startswith("AI_PERSONALITIES = {"))
        end_index = next(i for i in range(start_index + 1, len(lines)) if lines[i].strip() == "}")

        # Convert the AI_PERSONALITIES dictionary to a formatted string
        personalities_str = "AI_PERSONALITIES = {\n"
        for name, personality in AI_PERSONALITIES.items():
            personalities_str += f'    "{name}": {{\n'
            personalities_str += f'        "name": "{personality["name"]}",\n'
            personalities_str += f'        "system_message": """{personality["system_message"]}""",\n'
            personalities_str += f'        "ai_name": "{personality["ai_name"]}",\n'
            personalities_str += f'        "color": "{personality["color"]}",\n'
            personalities_str += "    },\n"
        personalities_str += "}"

        # Replace the old AI_PERSONALITIES dictionary with the new one
        lines[start_index:end_index + 1] = [personalities_str]

        # Write the updated content back to the file
        with open(self.personalities_file, 'w') as f:
            f.writelines(lines)


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = EditPersonalities()
    dialog.show()
    sys.exit(app.exec_())
