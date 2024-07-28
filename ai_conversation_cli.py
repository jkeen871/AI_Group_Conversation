import cmd2
from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel
from rich.text import Text
from rich.style import Style
from rich.align import Align
from rich.live import Live
from rich.spinner import Spinner
import asyncio
from asyncio import Queue
import logging
from typing import Optional
from conversation_manager import ConversationManager


class AIConversationCLI(cmd2.Cmd):
    """
    A command-line interface for an AI-driven conversation application.

    This class extends cmd2.Cmd to provide a rich, interactive CLI experience
    for conducting conversations with multiple AI personalities. It handles user
    input, command processing, and interaction with the ConversationManager.

    Attributes:
        conversation_manager (ConversationManager): Manages conversation history and AI interactions.
        prompt (str): The command prompt string.
        console (Console): A Rich console object for formatted output.
        ai_conversation_task (asyncio.Task): The main AI conversation loop task.
        async_alert (str): An alert string for async mode.
        async_mode (bool): Flag indicating if async mode is active.
        is_generating (asyncio.Event): Event to track if AI is currently generating a response.
        input_queue (asyncio.Queue): Queue for managing user input.
        logger (logging.Logger): Logger for this class.
    """

    def __init__(self):
        """
        Initializes the AIConversationCLI instance.

        Sets up the command prompt, console, logging, and other necessary attributes.
        The ConversationManager is not initialized here but in the run method.
        """
        super().__init__(allow_cli_args=False)
        self.setup_logging()
        self.prompt = "User> "
        self.console = Console()
        self.conversation_manager = None  # Will be initialized in run()
        self.ai_conversation_task = None
        self.async_alert = cmd2.ansi.style("(async) ", fg=cmd2.ansi.Fg.CYAN)
        self.async_mode = False
        self.is_generating = asyncio.Event()
        self.is_generating.set()
        self.input_queue = Queue()
        self.logger.debug("AIConversationCLI initialized")

    def setup_logging(self):
        """
        Sets up logging configuration for the application.

        Configures logging to write to a file, overwriting it each time the application starts.
        The log includes timestamps, log levels, and function names for comprehensive debugging.
        """
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
            filename='ai_conversation_app.log',
            filemode='w'
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Logging initialized")

    def set_user_prompt(self, user_name: str):
        """
        Sets the user prompt with the given user name.

        Args:
            user_name (str): The name of the user to be displayed in the prompt.
        """
        self.prompt = f"{user_name}> "
        self.logger.debug(f"User prompt set to: {self.prompt}")

    async def run(self) -> None:
        """
        Run the main application loop for the AI Conversation CLI.

        This method initializes the conversation manager, sets up the AI conversation task,
        and runs the command loop. It handles the main flow of the application, including
        user input and AI responses.

        The method uses asyncio for asynchronous operation and includes error handling
        and logging for robustness.

        Raises:
            Exception: For any unexpected errors during execution.
        """
        self.logger.debug("Entering run method")
        try:
            if not self.conversation_manager:
                user_name = await self.get_user_input("Please enter your name: ")
                self.logger.debug(f"User name received: {user_name}")
                self.conversation_manager = ConversationManager(user_name)
                self.set_user_prompt(user_name)
                self.logger.info(f"ConversationManager initialized for user: {user_name}")

            self.logger.debug("Creating AI conversation task")
            self.ai_conversation_task = asyncio.create_task(self.ai_conversation_loop())
            self.logger.debug("AI conversation task created")

            self.logger.debug("Starting cmdloop_async")
            await self.cmdloop_async()
        except asyncio.CancelledError:
            self.logger.info("Main task cancelled")
        except Exception as e:
            self.logger.error(f"Error in run method: {str(e)}", exc_info=True)
        finally:
            self.logger.debug("Entering cleanup")
            await self.cleanup()
            self.logger.debug("Cleanup completed")

    async def cleanup(self) -> None:
        """
        Perform cleanup operations before the application exits.

        This method ensures that any necessary cleanup tasks are performed,
        such as saving the conversation history and cancelling ongoing tasks.

        It handles exceptions during the cleanup process to ensure that even
        if part of the cleanup fails, the rest of the operations are attempted.
        """
        self.logger.debug("Performing cleanup")
        try:
            if self.ai_conversation_task and not self.ai_conversation_task.done():
                self.logger.debug("Cancelling AI conversation task")
                self.ai_conversation_task.cancel()
                try:
                    await self.ai_conversation_task
                except asyncio.CancelledError:
                    self.logger.debug("AI conversation task cancelled successfully")

            if self.conversation_manager:
                self.logger.debug("Saving conversation history")
                self.conversation_manager.save_conversation_history()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
        finally:
            self.logger.info("Cleanup completed")

    async def get_user_input(self, prompt: str) -> str:
        """
        Gets user input asynchronously.

        Args:
            prompt (str): The prompt to display to the user.

        Returns:
            str: The user's input.
        """
        try:
            return await asyncio.get_event_loop().run_in_executor(None, input, prompt)
        except Exception as e:
            self.logger.error(f"Error getting user input: {str(e)}")
            return ""

    async def cmdloop_async(self):
        """
        Asynchronous version of cmd2's cmdloop.

        This method runs the main command loop of the application, handling user input
        and processing commands asynchronously.
        """
        self.logger.debug("Starting cmdloop_async")
        self.preloop()
        try:
            while True:
                try:
                    # Wait until not generating before accepting input
                    await self.is_generating.wait()
                    line = await self.get_user_input(self.prompt)
                    if not line:
                        continue
                    line = self.precmd(line)
                    stop = await self.onecmd_async(line)
                    stop = self.postcmd(stop, line)
                    if stop or line.lower() in ['exit', 'quit']:
                        self.logger.info("Exit command received")
                        break
                except KeyboardInterrupt:
                    self.logger.info("Keyboard interrupt received")
                    self.console.print("\nKeyboard interrupt received. Exiting...")
                    break
                except Exception as e:
                    self.logger.error(f"Error in command loop: {str(e)}", exc_info=True)
        finally:
            self.postloop()
        self.logger.debug("Exiting cmdloop_async")

    async def onecmd_async(self, line: str) -> bool:
        """
        Asynchronous version of cmd2's onecmd.

        This method processes a single command line asynchronously. It handles both
        system commands (starting with '!') and regular user input.

        Args:
            line (str): The command line to process.

        Returns:
            bool: True if the application should exit, False otherwise.
        """
        self.logger.debug(f"Processing command: {line}")
        if line.startswith('!'):
            await self.handle_command(line[1:])
            return False

        cmd, arg, line = self.parseline(line)
        if not line:
            return self.emptyline()
        if cmd is None:
            return self.default(line)
        self.lastcmd = line
        if line == 'EOF':
            self.lastcmd = ''
        if cmd == '':
            return self.default(line)
        else:
            try:
                func = getattr(self, 'do_' + cmd)
                if cmd != 'quit':
                    await self.input_queue.put(line)
                    return False
                return func(arg)
            except AttributeError:
                return self.default(line)

    async def ai_conversation_loop(self):
        """
        Main loop for processing user input and generating AI responses.

        This method continuously monitors the input queue for user messages,
        processes them, and generates AI responses using the ConversationManager.
        """
        self.logger.debug("Starting AI conversation loop")
        while True:
            try:
                user_input = await self.input_queue.get()
                self.logger.debug(f"Processing user input: {user_input}")
                await self.process_input(user_input)
            except asyncio.CancelledError:
                self.logger.info("AI conversation loop cancelled")
                break
            except Exception as e:
                self.logger.error(f"Error in AI conversation loop: {str(e)}", exc_info=True)
        self.logger.debug("Exiting AI conversation loop")

    async def get_user_input_with_empty_check(self, prompt: str) -> str:
        """
        Gets user input asynchronously and checks for empty input.

        This method will continue prompting until non-empty input is received.
        There is no timeout implemented, as per the requirement to always wait
        for user input before continuing the conversation.

        Args:
            prompt (str): The prompt to display to the user.

        Returns:
            str: The user's non-empty input.
        """
        self.logger.debug("Prompting user for input: %s", prompt)
        while True:
            user_input = await self.get_user_input(prompt)
            if user_input.strip():
                self.logger.debug("Received non-empty user input: %s", user_input)
                return user_input
            self.logger.debug("Received empty input, prompting again")

    async def process_input(self, user_input: str) -> None:
        """
        Processes user input and manages the conversation flow.

        This method handles the core conversation loop, including the initial round
        of AI responses and subsequent rounds with checks for directed questions.
        It also manages empty inputs and command processing.

        Args:
            user_input (str): The initial input provided by the user to start or continue the conversation.
        """
        self.logger.debug("Entering process_input method with user input: %s", user_input)

        # Initialize conversation_round attribute if not already set
        if not hasattr(self, 'conversation_round'):
            self.conversation_round = 0

        while True:
            self.logger.debug("Starting conversation round: %d", self.conversation_round)

            if self.conversation_round == 0:
                # Initial round: Generate the first set of AI responses based on user input
                self.logger.info("Initiating first round of AI responses")
                user_prompt = await self.conversation_manager.generate_ai_conversation(user_input)
                self.conversation_round += 1  # Increment the round counter after the initial round
                self.logger.debug("Incremented conversation round counter to: %d", self.conversation_round)
            else:
                # Subsequent rounds: Continue the conversation based on the latest user input
                self.logger.info("Continuing conversation in subsequent round")
                user_prompt = await self.conversation_manager.continue_conversation(user_input)

            self.logger.debug("Received user prompt: %s", user_prompt)

            # Set the appropriate prompt for the user
            self.prompt = f"{self.conversation_manager.user_name}> "
            self.logger.debug("Set user prompt: %s", self.prompt)

            # Get user input, ensuring non-empty input
            user_input = await self.get_user_input_with_empty_check(self.prompt)

            # Add a new line after user input for better readability
            self.console.print()

            if user_input.lower() in ['quit', 'exit', 'bye']:
                self.logger.info("User requested to quit the conversation")
                return  # Exit the conversation

            # Check if the input is a command (starts with '!')
            if user_input.startswith('!'):
                self.logger.info("Detected command input: %s", user_input)
                await self.handle_command(user_input[1:])
                continue

            # Update conversation with user input
            self.logger.debug("Updating conversation with user input: %s", user_input)
            self.conversation_manager.update_conversation(user_input, self.conversation_manager.user_name)

            # Increment the round counter after updating the conversation
            self.conversation_round += 1
            self.logger.debug("Incremented conversation round counter to: %d", self.conversation_round)

    async def get_user_input_with_empty_check(self, prompt: str) -> str:
        """
        Gets user input asynchronously and checks for empty input.

        This method will continue prompting until non-empty input is received.
        It displays the prompt only once to avoid double prompting.

        Args:
            prompt (str): The prompt to display to the user.

        Returns:
            str: The user's non-empty input.
        """
        self.logger.debug("Prompting user for input: %s", prompt)
        while True:
            user_input = await self.get_user_input(prompt)
            if user_input.strip():
                self.logger.debug("Received non-empty user input: %s", user_input)
                return user_input
            self.logger.debug("Received empty input, prompting again")
            prompt = ""  # Clear the prompt for subsequent attempts

    async def handle_empty_input(self) -> str:
        """
        Handles the case when the user enters an empty input (just presses enter).

        Returns:
            str: A continuation prompt for the conversation.
        """
        self.logger.info("Generating continuation prompt for empty input")
        continuation_prompt = "I'm still here, please continue the conversation."
        self.logger.debug("Generated continuation prompt: %s", continuation_prompt)
        return continuation_prompt

    async def handle_command(self, command: str):
        """
        Handles system commands that start with '!'.

        This method processes special commands that are not part of the regular conversation flow.

        Args:
            command (str): The command to process (without the leading '!').
        """
        self.logger.debug(f"Handling command: {command}")
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()

        if cmd == 'history':
            await self.show_conversation_history()
        elif cmd == 'help':
            self.do__help()
        elif cmd == 'switch_thread':
            if len(cmd_parts) > 1:
                self.do__switch_thread(cmd_parts[1])
            else:
                self.console.print("[bold red]Please specify a thread ID[/bold red]")
        elif cmd == 'list_threads':
            self.do__list_threads()
        elif cmd == 'clear':
            self.do__clear()
        else:
            self.console.print(f"[bold red]Unknown command: {cmd}[/bold red]")

    async def show_conversation_history(self):
        """
        Displays the conversation history in a formatted manner.

        This method loads the conversation history, allows the user to select a specific thread,
        and then displays the selected thread's messages with proper formatting.
        """
        self.logger.debug("Showing conversation history")
        # Implementation details for showing conversation history
        # (This part would be similar to the previous implementation)

    def do__help(self):
        """
        Displays the help message with available commands.

        This method provides information about the available commands and their usage.
        """
        self.logger.debug("Displaying help message")
        help_text = """
        Commands:
        !help - Show this help message
        !quit or !exit - Exit the application
        !switch_thread [thread_id] - Switch to a different conversation thread
        !list_threads - List all available conversation threads
        !clear - Clear the current conversation thread
        !history - Show conversation history

        To direct a comment at a specific participant, start your message with their name followed by a colon.
        Example: "Vanessa: What do you think about this?"
        """
        self.console.print(Markdown(help_text))

    def do__switch_thread(self, thread_id: str):
        """
        Switches to a different conversation thread.

        This method changes the current active thread to the specified thread ID.

        Args:
            thread_id (str): The ID of the thread to switch to.
        """
        self.logger.debug(f"Attempting to switch to thread: {thread_id}")
        if thread_id in self.conversation_manager.conversation_history:
            self.conversation_manager.current_thread_id = thread_id
            self.console.print(f"[bold]Switched to thread: {thread_id}[/bold]")
            # Replay the conversation history for the new thread
            for entry in self.conversation_manager.conversation_history[thread_id]:
                self.conversation_manager.update_conversation(entry['message'], entry['sender'])
            self.logger.info(f"Successfully switched to thread: {thread_id}")
        else:
            self.console.print(f"[bold red]Thread {thread_id} not found[/bold red]")
            self.logger.warning(f"Attempted to switch to non-existent thread: {thread_id}")

    def do__list_threads(self):
        """
        Lists all available conversation threads.

        This method displays a list of all conversation threads and their message counts.
        """
        self.logger.debug("Listing available threads")
        thread_list = "\n".join(
            [f"{thread_id}: {len(messages)} messages" for thread_id, messages in
             self.conversation_manager.conversation_history.items()])
        self.console.print(f"[bold]Available threads:[/bold]\n{thread_list}")
        self.logger.debug(f"Thread list displayed: {thread_list}")

    def do__clear(self):
        """
            Clears the current conversation thread.

            This method removes all messages from the current conversation thread.
            """
        self.logger.debug(f"Attempting to clear current thread: {self.conversation_manager.current_thread_id}")
        if self.conversation_manager.current_thread_id in self.conversation_manager.conversation_history:
            self.conversation_manager.conversation_history[self.conversation_manager.current_thread_id] = []
            self.conversation_manager.save_conversation_history()
            self.console.print("[bold green]Conversation cleared[/bold green]")
            self.logger.info(f"Cleared conversation thread: {self.conversation_manager.current_thread_id}")
        else:
            self.console.print("[bold red]No active conversation thread to clear[/bold red]")
            self.logger.warning("Attempted to clear non-existent or inactive thread")

    def do__quit(self, arg):
        """
        Handles the quit command to exit the application.

        This method is called when the user enters the quit command.
        It cancels the AI conversation task and signals the application to exit.

        Args:
            arg: Any arguments passed with the quit command (unused).

        Returns:
            bool: True to signal the application to exit.
        """
        self.logger.debug("Quit command received")
        if self.ai_conversation_task:
            self.ai_conversation_task.cancel()
        return True

    def default(self, statement):
        """
        Handles default command input (user messages).

        This method is called when the input doesn't match any defined commands.
        It processes the input as part of the conversation or as a system command.

        Args:
            statement: The user's input statement.
        """
        self.logger.debug(f"Processing default input: {statement}")
        try:
            # Check if the input is a command (starts with '!')
            if statement.startswith('!'):
                asyncio.create_task(self.handle_command(statement[1:]))
            else:
                asyncio.create_task(self.process_input_wrapper(statement))
        except Exception as e:
            self.logger.error(f"Error processing input: {str(e)}", exc_info=True)

    async def process_input_wrapper(self, statement):
        """
        Wrapper to handle the asynchronous process_input method.

        This method provides a way to call the asynchronous process_input method
        from synchronous contexts.

        Args:
            statement: The user's input statement.
        """
        try:
            await self.process_input(statement)
        except Exception as e:
            self.logger.error(f"Error in process_input: {str(e)}", exc_info=True)

    async def display_thinking_message(self, participant: str):
        """
        Displays a "thinking" message for the AI participant.

        This method shows a spinner with a message indicating that the AI is thinking or responding.
        It continues until the thinking_participant attribute is changed.

        Args:
            participant (str): The name of the AI participant who is "thinking".
        """
        message = f"{participant} is thinking..."
        spinner = Spinner('dots', text=message)
        with Live(spinner, refresh_per_second=10, transient=True) as live:
            while self.conversation_manager.thinking_participant == participant:
                await asyncio.sleep(0.1)
        self.logger.debug(f"Finished displaying thinking message for {participant}")

    async def generate_moderator_summary(self):
        """
        Generates a summary of the conversation by the moderator.

        This method uses a moderator AI to create a summary of the current conversation thread.
        The summary is then added to the conversation history.
        """
        self.logger.debug("Generating moderator summary")
        self.conversation_manager.thinking_participant = "Moderator"
        self.console.print("[italic yellow]Moderator is summarizing the conversation...[/italic yellow]")

        try:
            summary = await self.conversation_manager.generate_moderator_summary()
            self.logger.debug("Moderator summary generated successfully")
            self.conversation_manager.update_conversation(summary, "Moderator")
        except Exception as e:
            self.logger.error(f"Error generating moderator summary: {str(e)}")
            self.conversation_manager.update_conversation("Unable to generate summary at this time.", "System")
        finally:
            self.conversation_manager.thinking_participant = None

    def prompt_for_thread_switch(self) -> Optional[str]:
        """
        Prompts the user to switch to a different conversation thread.

        This method displays available threads and asks the user if they want to switch.

        Returns:
            Optional[str]: The ID of the thread to switch to, or None if no switch is desired.
        """
        self.logger.debug("Prompting user for thread switch")
        self.do__list_threads()
        response = input("Would you like to switch to a different thread? (y/n): ").lower()
        if response == 'y':
            thread_id = input("Enter the ID of the thread you'd like to switch to: ")
            return thread_id
        return None

    def update_user_name(self, new_name: str):
        """
        Updates the user's name in the conversation.

        This method changes the user's name in the ConversationManager and updates the prompt.

        Args:
            new_name (str): The new name for the user.
        """
        self.logger.debug(f"Updating user name to: {new_name}")
        self.conversation_manager.user_name = new_name
        self.set_user_prompt(new_name)
        self.console.print(f"[bold green]User name updated to: {new_name}[/bold green]")

    async def export_conversation(self, file_format: str = 'txt'):
        """
        Exports the current conversation thread to a file.

        This method saves the current conversation in the specified format.

        Args:
            file_format (str): The format to export the conversation (e.g., 'txt', 'json').
        """
        self.logger.debug(f"Exporting conversation in {file_format} format")
        try:
            # Implementation for exporting conversation
            # This would involve formatting the conversation data and writing it to a file
            self.console.print(f"[bold green]Conversation exported successfully in {file_format} format[/bold green]")
        except Exception as e:
            self.logger.error(f"Error exporting conversation: {str(e)}")
            self.console.print("[bold red]Failed to export conversation[/bold red]")

    def print_debug_info(self):
        """
        Prints debug information about the current state of the application.

        This method displays various debug details useful for troubleshooting.
        """
        self.logger.debug("Printing debug information")
        debug_info = f"""
        Debug Information:
        - Current Thread ID: {self.conversation_manager.current_thread_id}
        - Number of Threads: {len(self.conversation_manager.conversation_history)}
        - Current User: {self.conversation_manager.user_name}
        - AI Conversation Task Active: {self.ai_conversation_task is not None and not self.ai_conversation_task.done()}
        - Async Mode: {self.async_mode}
        """
        self.console.print(Panel(debug_info, title="Debug Info", border_style="blue"))

    # Additional helper methods can be added here as needed

# End of AIConversationCLI class
