import json
import asyncio
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QTextEdit, QPushButton,
    QHBoxLayout, QMainWindow, QMessageBox, QStatusBar, QDialog,
    QDialogButtonBox, QLineEdit, QLabel, QFormLayout
)
from PyQt5.QtGui import QTextCursor, QColor, QTextCharFormat
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv, set_key
from google_api import get_gmail_service
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from email.mime.text import MIMEText
import base64
import os
from google_api import get_gmail_service


class ModeratorReplyThread(QThread):
    reply_received = pyqtSignal(str)

    def __init__(self, conversation_manager, thread_id):
        super().__init__()
        self.conversation_manager = conversation_manager
        self.thread_id = thread_id

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            reply = loop.run_until_complete(
                self.conversation_manager.generate_moderator_summary_for_history(self.thread_id)
            )
            self.reply_received.emit(reply)
        finally:
            loop.close()


class ModeratorSummaryDialog(QDialog):
    def __init__(self, parent=None, summary=""):
        super().__init__(parent)
        self.summary = summary
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Moderator Summary")
        self.setModal(True)
        layout = QVBoxLayout(self)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setText(self.summary)
        layout.addWidget(self.summary_text)

        send_email_button = QPushButton("Send Email")
        send_email_button.clicked.connect(self.open_email_dialog)
        layout.addWidget(send_email_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def open_email_dialog(self):
        email_dialog = EmailDialog(self, self.summary)
        email_dialog.exec_()


class EmailDialog(QDialog):
    def __init__(self, parent=None, summary=""):
        super().__init__(parent)
        self.summary = summary
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Send Email")
        self.setModal(True)
        layout = QVBoxLayout(self)

        self.to_email = QLineEdit()
        layout.addWidget(QLabel("To:"))
        layout.addWidget(self.to_email)

        self.subject = QLineEdit()
        self.subject.setText("Conversation Summary")
        layout.addWidget(QLabel("Subject:"))
        layout.addWidget(self.subject)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.send_email)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Add Setup button
        self.setup_button = QPushButton("Setup")
        self.setup_button.clicked.connect(self.open_email_setup)
        layout.addWidget(self.setup_button)

    def send_email(self):
        to_email = self.to_email.text()
        subject = self.subject.text()
        body = self.summary

        try:
            service = get_gmail_service()
            message = MIMEText(body)
            message['to'] = to_email
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            send_message = {'raw': raw_message}

            message = service.users().messages().send(userId="me", body=send_message).execute()
            QMessageBox.information(self, "Email Sent", f"Email sent to {to_email} with subject: {subject}")
            self.accept()
        except HttpError as error:
            QMessageBox.critical(self, "Error", f"Failed to send email: {str(error)}")

    def open_email_setup(self):
        setup_window = EmailSetupWindow(self)
        setup_window.exec_()


class EmailSetupWindow(QDialog):
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Email Setup")
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        self.info_label = QLabel("Please authenticate with your Google account.")
        layout.addWidget(self.info_label)

        self.auth_button = QPushButton("Authenticate")
        self.auth_button.clicked.connect(self.authenticate_google)
        layout.addWidget(self.auth_button)

        button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def authenticate_google(self):
        creds = None
        try:
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    raise Exception("Credentials are invalid or expired")
        except Exception as e:
            print(f"Error during refresh: {e}")
            if os.path.exists('token.json'):
                os.remove('token.json')
            creds = None

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', self.SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        self.accept()


class ConversationHistoryWindow(QDialog):  # Changed from QMainWindow to QDialog
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setModal(True)  # Make the window modal
        self.init_ui()
        self.load_conversation_history()
        self.moderator_reply_thread = None

    def init_ui(self):
        self.setWindowTitle('Conversation History')
        self.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout(self)

        self.thread_combo = QComboBox()
        self.thread_combo.currentIndexChanged.connect(self.load_conversation)
        layout.addWidget(self.thread_combo)

        self.conversation_display = QTextEdit()
        self.conversation_display.setReadOnly(True)
        layout.addWidget(self.conversation_display)

        button_layout = QHBoxLayout()

        self.moderator_reply_button = QPushButton("Get Moderator Summary")
        self.moderator_reply_button.clicked.connect(self.get_moderator_summary)
        button_layout.addWidget(self.moderator_reply_button)

        self.email_conversation_button = QPushButton("Email Conversation")
        self.email_conversation_button.clicked.connect(self.email_conversation)
        button_layout.addWidget(self.email_conversation_button)

        exit_button = QPushButton("Close")
        exit_button.clicked.connect(self.close)
        button_layout.addWidget(exit_button)

        layout.addLayout(button_layout)

        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)

    def load_conversation_history(self):
        try:
            with open('conversation_history.json', 'r') as f:
                self.history = json.load(f)

            # Clear existing items
            self.thread_combo.clear()

            # Populate combo box with formatted strings
            for thread_id, thread_data in self.history.items():
                date_time = thread_data['date']
                topic = thread_data['topic']
                display_text = f"{date_time} - {topic}"
                self.thread_combo.addItem(display_text, thread_id)  # Store thread_id as item data
        except FileNotFoundError:
            print("Conversation history file not found.")
        except json.JSONDecodeError:
            print("Error decoding the conversation history file.")

    def load_conversation(self, index):
        thread_id = self.thread_combo.itemData(index)  # Get the stored thread_id
        if thread_id in self.history:
            self.display_conversation(self.history[thread_id])

    def display_conversation(self, conversation):
        self.conversation_display.clear()
        for message in conversation['messages']:  # Fixed: Access 'messages' key
            sender = message['sender']
            content = message['message']
            self.append_message_to_widget(sender, content)

    def append_message_to_widget(self, sender, content):
        cursor = self.conversation_display.textCursor()
        cursor.movePosition(QTextCursor.End)

        format_sender = QTextCharFormat()
        format_sender.setFontWeight(700)
        cursor.insertText(f"{sender}: ", format_sender)

        format_content = QTextCharFormat()
        cursor.insertText(f"{content}\n\n", format_content)

        self.conversation_display.setTextCursor(cursor)
        self.conversation_display.ensureCursorVisible()

    def get_moderator_summary(self):
        current_index = self.thread_combo.currentIndex()
        if current_index >= 0:
            thread_id = self.thread_combo.itemData(current_index)
            if hasattr(self.parent, 'conversation_manager'):
                self.moderator_reply_button.setEnabled(False)
                self.status_bar.showMessage("Generating Moderator Summary...")
                self.moderator_reply_thread = ModeratorReplyThread(self.parent.conversation_manager, thread_id)
                self.moderator_reply_thread.reply_received.connect(self.on_moderator_reply_received)
                self.moderator_reply_thread.finished.connect(self.on_moderator_reply_finished)
                self.moderator_reply_thread.start()
            else:
                QMessageBox.warning(self, "Error", "Conversation manager not available.")
        else:
            QMessageBox.warning(self, "No Thread Selected", "Please select a conversation thread first.")

    def on_moderator_reply_received(self, reply):
        self.status_bar.clearMessage()
        summary_dialog = ModeratorSummaryDialog(self, reply)
        summary_dialog.exec_()

    def on_moderator_reply_finished(self):
        self.moderator_reply_button.setEnabled(True)

    def email_conversation(self):
        current_index = self.thread_combo.currentIndex()
        if current_index >= 0:
            thread_id = self.thread_combo.itemData(current_index)
            if thread_id in self.history:
                conversation = self.history[thread_id]
                email_content = "\n\n".join([f"{msg['sender']}: {msg['message']}" for msg in conversation['messages']])
                email_dialog = EmailDialog(self, email_content)
                email_dialog.exec_()
            else:
                QMessageBox.warning(self, "Error", "Selected conversation thread not found in history.")
        else:
            QMessageBox.warning(self, "No Thread Selected", "Please select a conversation thread first.")

    def closeEvent(self, event):
        if self.moderator_reply_thread and self.moderator_reply_thread.isRunning():
            self.moderator_reply_thread.terminate()
            self.moderator_reply_thread.wait()
        self.parent.history_window = None
        event.accept()
