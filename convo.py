#!/usr/bin/env python3
"""
convo.py: Main script for the AI Conversation Application

This script serves as the entry point for the AI Conversation Application,
supporting both Text User Interface (TUI) and Graphical User Interface (GUI) modes.
It includes the implementation for both interfaces, handling the initialization
of the application, logging setup, and the main execution flow.

Usage:
    python convo.py -t  # For TUI mode
    python convo.py -g  # For GUI mode

Dependencies:
    - PyQt5 (for GUI mode)
    - asyncio (for asynchronous operations)
    - Custom modules: ConversationManager, ConversationRAG

Author: Your Name
Date: Current Date
Version: 1.1
"""

import logging
import os
import sys
import asyncio
import argparse
from PyQt5.QtWidgets import (QApplication)

import cmd2
from rich.console import Console
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
    logger.setLevel(log_level)  # Use the passed log level

    # Console handler for logging to the console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)  # Use the same log level for the console handler
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


# TUI Implementation
class AIConversationCLI(cmd2.Cmd):
    """
    Command-line interface for the AI Conversation application.
    """

    def __init__(self):
        super().__init__(allow_cli_args=False)
        self.prompt = "User> "
        self.conversation_manager = None
        self.console = Console()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("AIConversationCLI initialized")

    async def get_user_input(self, prompt: str) -> str:
        """
        Gets user input asynchronously.
        """
        return await asyncio.get_event_loop().run_in_executor(None, input, prompt)

    async def run(self):
        """
        Run the main application loop for the AI Conversation CLI.
        """
        self.logger.debug("Entering run method")
        try:
            if not self.conversation_manager:
                user_name = await self.get_user_input("Please enter your name: ")
                self.conversation_manager = ConversationManager(user_name)
                self.prompt = f"{user_name}> "
                self.logger.info(f"ConversationManager initialized for user: {user_name}")

            while True:
                user_input = await self.get_user_input(self.prompt)
                if user_input.lower() in ['exit', 'quit']:
                    break
                response = await self.conversation_manager.generate_ai_conversation(user_input)
                self.console.print(f"AI: {response}")
        except asyncio.CancelledError:
            self.logger.info("Main task cancelled")
        except Exception as e:
            self.logger.error(f"Error in run method: {str(e)}", exc_info=True)
        finally:
            self.logger.debug("Exiting run method")


async def run_tui_application():
    """
    Run the Text User Interface (TUI) version of the application.
    """
    logger.info("Starting AI Conversation CLI application")
    try:
        app = AIConversationCLI()
        await app.run()
    except Exception as e:
        logger.critical(f"Unhandled exception in TUI application: {str(e)}", exc_info=True)
        print(f"A critical error occurred. Please check the log file for details.")


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
    parser.add_argument("-t", "--tui", action="store_true", help="Run the Text User Interface version")
    parser.add_argument("-g", "--gui", action="store_true", help="Run the Graphical User Interface version")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    setup_logging(log_level)

    if args.tui:
        logger.info("Starting TUI version")
        asyncio.run(run_tui_application())
    elif args.gui:
        logger.info("Starting GUI version")
        run_gui_application()
    else:
        logger.error("No interface specified. Please use -t for TUI or -g for GUI.")
        print("Please specify an interface: use -t for TUI or -g for GUI.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unhandled exception in script: {str(e)}", exc_info=True)
        print(f"A critical error occurred. Please check the log file for details.")
