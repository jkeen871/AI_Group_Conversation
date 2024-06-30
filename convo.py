import asyncio
import logging
import os
from typing import NoReturn


from conversation_manager import ConversationManager
from ai_conversation_cli import AIConversationCLI

def setup_logging() -> None:
    """
    Set up logging configuration for the application.

    This function configures the root logger to write logs to a file,
    overwriting it each time the application starts. The log includes
    timestamps, log levels, and function names for comprehensive debugging.
    """
    os.makedirs('log', exist_ok=True)  # Create log directory if it doesn't exist
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
        filename='log/convo.log',
        filemode='w'
    )
    logging.debug("Logging initialized in convo.py")

async def run_application() -> NoReturn:
    app = AIConversationCLI()
    logging.info("Starting AI Conversation CLI application")

    try:
        # Clear the screen for a clean start
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Initialize ConversationManager with user input
        logging.debug(f"AIConversationCLI methods: {dir(app)}")
        logging.debug(f"get_user_input in AIConversationCLI: {'get_user_input' in dir(app)}")
        user_name = await app.get_user_input("Please enter your name: ")
        
        # Initialize ConversationManager here
        app.conversation_manager = ConversationManager(user_name)
        app.conversation_manager.current_thread_id = f"thread_{len(app.conversation_manager.conversation_history) + 1}"

        # Set the user's prompt
        app.set_user_prompt(user_name)
        
        print(f"Welcome, {user_name}! Type '_help' for a list of commands.")

        # Run the application
        logging.debug("Creating ai_conversation_task")
        app.ai_conversation_task = asyncio.create_task(app.run())
        logging.debug("ai_conversation_task created")
        await app.ai_conversation_task
    except Exception as e:
        logging.critical(f"Unhandled exception in main application: {str(e)}", exc_info=True)
    finally:
        logging.debug("Entering finally block")
        if app.ai_conversation_task and not app.ai_conversation_task.done():
            logging.debug("Cancelling ai_conversation_task")
            app.ai_conversation_task.cancel()
            try:
                await app.ai_conversation_task
            except asyncio.CancelledError:
                logging.debug("ai_conversation_task cancelled")
        logging.info("AI Conversation CLI application terminated")

def main() -> None:
    """
    Entry point of the application.

    This function sets up logging and runs the asynchronous application
    using asyncio.run(). It serves as the starting point for the entire
    AI Conversation CLI application.
    """
    setup_logging()
    asyncio.run(run_application())

if __name__ == "__main__":
    main()

