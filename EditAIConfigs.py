import sys
import json
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit,
                             QTextEdit, QLabel, QPushButton, QMessageBox,
                             QScrollArea, QWidget, QSplitter)
from PyQt5.QtCore import Qt
import importlib
import inspect


class EditAIConfigs(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit AI Configs")
        self.setGeometry(100, 100, 1200, 800)
        self.config_file = 'ai_config.py'
        self.initUI()
        self.loadConfigs()

    def initUI(self):
        layout = QHBoxLayout()

        # Left side: List of AI configs
        left_layout = QVBoxLayout()
        self.config_list = QListWidget()
        self.config_list.itemClicked.connect(self.loadConfigDetails)
        left_layout.addWidget(self.config_list)

        # Add New Config button
        new_config_button = QPushButton("Add New Config")
        new_config_button.clicked.connect(self.addNewConfig)
        left_layout.addWidget(new_config_button)

        # Remove Config button
        remove_config_button = QPushButton("Remove Config")
        remove_config_button.clicked.connect(self.removeConfig)
        left_layout.addWidget(remove_config_button)

        # Right side: Editable fields in a scroll area
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.name_edit = QLineEdit()
        right_layout.addWidget(QLabel("Name:"))
        right_layout.addWidget(self.name_edit)

        self.model_edit = QLineEdit()
        right_layout.addWidget(QLabel("Model:"))
        right_layout.addWidget(self.model_edit)

        self.function_edit = QTextEdit()
        self.function_edit.setMinimumHeight(400)
        right_layout.addWidget(QLabel("Generate Function:"))
        right_layout.addWidget(self.function_edit)

        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.saveChanges)
        right_layout.addWidget(save_button)

        # Create a scroll area and set the right widget as its content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(right_widget)

        # Use QSplitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        left_container = QWidget()
        left_container.setLayout(left_layout)
        splitter.addWidget(left_container)
        splitter.addWidget(scroll_area)
        splitter.setSizes([300, 900])  # Set initial sizes

        layout.addWidget(splitter)
        self.setLayout(layout)

    def loadConfigs(self):
        self.config_list.clear()
        # Read the AI configs from the file
        self.ai_config_module = importlib.import_module('ai_config')
        importlib.reload(self.ai_config_module)
        self.AI_CONFIG = getattr(self.ai_config_module, 'AI_CONFIG')

        # Convert function objects to their source code
        for name, config in self.AI_CONFIG.items():
            if callable(config['generate_func']):
                config['generate_func'] = inspect.getsource(config['generate_func'])

        for name in self.AI_CONFIG.keys():
            self.config_list.addItem(name)

    def loadConfigDetails(self, item):
        name = item.text()
        config = self.AI_CONFIG[name]
        self.name_edit.setText(name)
        self.model_edit.setText(config['model'])
        self.function_edit.setText(config['generate_func'])

    def saveChanges(self):
        current_item = self.config_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a config to save changes.")
            return

        current_name = current_item.text()
        new_name = self.name_edit.text()

        if current_name != new_name and new_name in self.AI_CONFIG:
            QMessageBox.warning(self, "Name Exists", "A config with this name already exists.")
            return

        # Prepare the new config
        new_config = {
            'model': self.model_edit.text(),
            'generate_func': self.function_edit.toPlainText()  # This is already a string
        }

        # Update the AI_CONFIG
        self.AI_CONFIG[new_name] = new_config
        if current_name != new_name:
            del self.AI_CONFIG[current_name]

        current_item.setText(new_name)

        self.saveToFile()

        QMessageBox.information(self, "Saved", "Changes saved successfully.")

    def saveToFile(self):
        with open(self.config_file, 'r') as f:
            lines = f.readlines()

        start_index = next(i for i, line in enumerate(lines) if line.strip().startswith("AI_CONFIG = {"))
        end_index = next(i for i in range(start_index + 1, len(lines)) if lines[i].strip() == "}")

        config_str = "AI_CONFIG = {\n"
        for name, config in self.AI_CONFIG.items():
            config_str += f'    "{name}": {{\n'
            config_str += f'        "model": "{config["model"]}",\n'
            config_str += f'        "generate_func": {name}_generate,\n'
            config_str += "    },\n"
        config_str += "}\n\n"

        # Add the function definitions after the AI_CONFIG dictionary
        for name, config in self.AI_CONFIG.items():
            config_str += f"{config['generate_func']}\n\n"  # Write the function source directly

        lines[start_index:end_index + 1] = [config_str]

        with open(self.config_file, 'w') as f:
            f.writelines(lines)
    def addNewConfig(self):
        new_name = "New Config"
        counter = 1
        while new_name in self.AI_CONFIG:
            new_name = f"New Config {counter}"
            counter += 1

        self.AI_CONFIG[new_name] = {
            'model': "",
            'generate_func': lambda x, y: None  # Placeholder function
        }

        self.loadConfigs()
        items = self.config_list.findItems(new_name, Qt.MatchExactly)
        if items:
            self.config_list.setCurrentItem(items[0])
            self.loadConfigDetails(items[0])

    def removeConfig(self):
        current_item = self.config_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a config to remove.")
            return

        name = current_item.text()
        reply = QMessageBox.question(self, 'Remove Config',
                                     f"Are you sure you want to remove '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            del self.AI_CONFIG[name]
            self.saveToFile()
            self.loadConfigs()
            self.clearConfigDetails()
            QMessageBox.information(self, "Removed", f"Config '{name}' has been removed.")

    def clearConfigDetails(self):
        self.name_edit.clear()
        self.model_edit.clear()
        self.function_edit.clear()


if __name__ == '__main__':
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    dialog = EditAIConfigs()
    dialog.show()
    sys.exit(app.exec_())