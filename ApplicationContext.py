# File: ApplicationContext.py

import signal
import sys
import asyncio
import logging
from typing import NoReturn, Optional


class ApplicationContext:
    """
    A class to hold the application's global context.

    This class is used to store references to objects that need to be
    cleaned up when the application is shutting down.

    Attributes:
        cleanup_task (Optional[asyncio.Task]): A task for performing cleanup operations.
        conversation_manager (Optional[ConversationManager]): The conversation manager instance.
        event_loop (Optional[asyncio.AbstractEventLoop]): The event loop running the application.
    """

    def __init__(self):
        self.cleanup_task: Optional[asyncio.Task] = None
        self.conversation_manager: Optional['ConversationManager'] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None


# Global application context
app_context = ApplicationContext()


async def async_cleanup() -> None:
    """
    Perform asynchronous cleanup operations.

    This function is responsible for cleaning up resources that require
    asynchronous operations, such as saving the conversation history.
    """
    logging.info("Starting asynchronous cleanup")
    if app_context.conversation_manager:
        try:
            await app_context.conversation_manager.save_conversation_history_async()
            logging.info("Conversation history saved successfully")
        except Exception as e:
            logging.error(f"Error saving conversation history: {e}", exc_info=True)
    logging.info("Asynchronous cleanup completed")


def signal_handler(sig: int, frame) -> NoReturn:
    """
    Handle interrupt signals (e.g., KeyboardInterrupt) gracefully.

    This function is designed to be used as a signal handler for SIGINT (Ctrl+C).
    It logs the interrupt event, initiates the cleanup process, and exits the program.

    Args:
        sig (int): The signal number.
        frame: The current stack frame.

    Returns:
        NoReturn: This function does not return as it exits the program.
    """
    logging.info(f"Received signal {sig}. Initiating graceful shutdown.")
    print("\nReceived interrupt signal. Shutting down gracefully...")

    if app_context.event_loop and app_context.event_loop.is_running():
        # Schedule the cleanup task in the event loop
        app_context.cleanup_task = app_context.event_loop.create_task(async_cleanup())

        # Run the event loop until the cleanup task is complete
        app_context.event_loop.run_until_complete(app_context.cleanup_task)
    else:
        logging.warning("Event loop not running. Skipping asynchronous cleanup.")

    # Perform any additional synchronous cleanup here
    # For example, closing file handles, releasing system resources, etc.

    logging.info("Shutdown complete. Exiting.")
    sys.exit(0)


def setup_signal_handling():
    """
    Set up signal handling for the application.

    This function should be called early in the application's startup process
    to ensure that interrupt signals are properly handled.
    """
    signal.signal(signal.SIGINT, signal_handler)
    logging.info("Signal handling set up")


# You might want to add a function to initialize the app context
def initialize_app_context(event_loop: asyncio.AbstractEventLoop, conversation_manager: 'ConversationManager'):
    """
    Initialize the application context with necessary objects.

    Args:
        event_loop (asyncio.AbstractEventLoop): The event loop running the application.
        conversation_manager (ConversationManager): The conversation manager instance.
    """
    app_context.event_loop = event_loop
    app_context.conversation_manager = conversation_manager
    logging.info("Application context initialized")
