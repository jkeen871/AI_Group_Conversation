#!/usr/bin/env python3
"""
convo.py: Main script for the AI Conversation Application

This script serves as the entry point for the AI Conversation Application,
running the Graphical User Interface (GUI) mode.
It handles the initialization of the application, logging setup,
and the main execution flow.

Usage:
    python convo.py

Dependencies:
    - PyQt5 (for GUI mode)
    - Custom modules: AIConversationGUI

Author: Jerry Keen
Contact: jkeen871@gmail.com
Date: July 29, 2024
Version: 2.0
"""

import logging
import os
import sys
import argparse
from PyQt5.QtWidgets import QApplication
from convo_gui import AIConversationGUI

# Setup module-level logger
logger = logging.getLogger(__name__)

def setup_logging(log_level):
    """
    Set up logging configuration for the application.

    Configures logging to write to both the console and a file. The log includes
    timestamps, log levels, and function names for comprehensive debugging.
    Each run of the program overwrites the previous log file.
    """
    log_dir = 'log'
    log_file = os.path.join(log_dir, 'app.log')

    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Console handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s')
    console_handler.setFormatter(console_format)

    # File handler for logging to a file, set mode to 'w' to overwrite each run
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)  # File logging level is always DEBUG for full details
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s')
    file_handler.setFormatter(file_format)

    # Adding handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.info("Logging setup completed")

    # Silence matplotlib.font_manager debug logs
    logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)

def run_gui_application():
    """
    Run the Graphical User Interface (GUI) version of the application.
    """
    logger.info("Starting AI Conversation GUI application")
    try:
        app = QApplication(sys.argv)
        main_window = AIConversationGUI()
        main_window.show()
        sys.exit(app.exec_())
    except Exception as e:
        logger.critical(f"Unhandled exception in GUI application: {str(e)}", exc_info=True)
        print(f"A critical error occurred. Please check the log file for details.")

def main():
    """
    Main function to run the AI Conversation Application.
    """
    parser = argparse.ArgumentParser(description="AI Conversation Application")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO

    setup_logging(log_level)

    logger.info("Starting GUI version")
    run_gui_application()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception in script: {str(e)}", exc_info=True)
        print(f"A critical error occurred. Please check the log file for details.")