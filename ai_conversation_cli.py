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
from rich.theme import Theme
from rich.table import Table
from rich.columns import Columns
import tracemalloc
import logging
import asyncio
from asyncio import Queue

try:
    from aioconsole import ainput
except ImportError:
    import asyncio
    ainput = asyncio.run(input)  # Fallback to synchronous input if aioconsole is not available



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
        logging (logging.Logger): Logger for this class.

    Methods:
        run(): Main method to run the application.
        cmdloop_async(): Asynchronous version of cmd2's command loop.
        onecmd_async(line: str): Asynchronously processes a single command.
        ai_conversation_loop(): Main loop for processing user input and generating AI responses.
        process_input(user_input: str): Processes user input and generates AI responses.
        handle_command(command: str): Handles system commands (starting with '!').
        show_conversation_history(): Displays the conversation history.
    """

    def __init__(self):
        """
        Initializes the AIConversationCLI instance.
        Sets up the command prompt, console, logging, and other necessary attributes.
        The ConversationManager is not initialized here but in the run method.
        """
        super().__init__(allow_cli_args=False)
        self.setup_logging()
        self.prompt = "User>"
        self.console = Console()
        self.conversation_manager = None  # Will be initialized in run()
        self.ai_conversation_task = None  # Ensure it is initialized as None
        self.async_alert = cmd2.ansi.style("(async) ", fg=cmd2.ansi.Fg.CYAN)
        self.async_mode = False
        self.is_generating = asyncio.Event()
        self.is_generating.set()
        self.input_queue = Queue()
        self.logging.debug("AIConversationCLI initialized")

    def set_user_prompt(self, user_name: str):
        self.prompt = f"{user_name}> "

    def setup_logging(self):
        """
        Sets up logging configuration for the application.

        Configures logging to write to a file, overwriting it each time the application starts.
        The log includes timestamps, log levels, and function names for comprehensive debugging.
        """
        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(levelname)s - %(name)s - %(funcName)s - %(message)s',
                            filename='ai_conversation_app.log',
                            filemode='w')
        self.logging = logging.getLogger(self.__class__.__name__)
        self.logging.debug("Logging initialized")

    async def run(self):
        """
        Runs the main application loop.

        This method initializes the conversation manager, sets up the AI conversation task,
        and runs the command loop. It handles the main flow of the application, including
        user input and AI responses.
        """
        self.logging.debug("Entering run method")

#        # Clear the screen
#        os.system('cls' if os.name == 'nt' else 'clear')
#
#        user_name = await self.get_user_input("Please enter your name: ")
#        self.conversation_manager = ConversationManager(user_name)
#        self.conversation_manager.current_thread_id = f"thread_{len(self.conversation_manager.conversation_history) + 1}"
#        print(f"Welcome, {user_name}! Type 'help' for a list of commands.")

        try:
            self.ai_conversation_task = asyncio.create_task(self.ai_conversation_loop())
            await self.cmdloop_async()
        except asyncio.CancelledError:
            self.logging.info("Main task cancelled")
        except Exception as e:
            self.logging.error(f"Error in run method: {str(e)}", exc_info=True)
        finally:
            if self.ai_conversation_task and not self.ai_conversation_task.done():
                self.ai_conversation_task.cancel()
                try:
                    await self.ai_conversation_task
                except asyncio.CancelledError:
                    pass
            await self.cleanup()

    async def cleanup(self):
        """
        Performs cleanup operations before the application exits.

        This method ensures that any necessary cleanup tasks are performed,
        such as saving the conversation history.
        """
        self.logging.debug("Performing cleanup")
        if self.conversation_manager:
            self.conversation_manager.save_conversation_history()

    async def get_user_input(self, prompt: str) -> str:
        """
        Gets user input asynchronously if possible, otherwise falls back to synchronous input.

        Args:
            prompt (str): The prompt to display to the user.

        Returns:
            str: The user's input.
        """
        try:
            return await ainput(prompt)
        except Exception as e:
            self.logging.error(f"Error getting user input: {str(e)}")
            return input(prompt)  # Fallback to synchronous input

    async def cmdloop_async(self):
        """
        Asynchronous version of cmd2's cmdloop.

        This method runs the main command loop of the application, handling user input
        and processing commands asynchronously.
        """
        self.logging.debug("Starting cmdloop_async")
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
                    if stop:
                        break
                except Exception as e:
                    self.logging.error(f"Error in command loop: {str(e)}", exc_info=True)
        finally:
            self.postloop()
        self.logging.debug("Exiting cmdloop_async")

    async def onecmd_async(self, line):
        """
        Asynchronous version of cmd2's onecmd.

        This method processes a single command line asynchronously. It handles both
        system commands (starting with '!') and regular user input.

        Args:
            line (str): The command line to process.

        Returns:
            The result of processing the command.
        """
        self.logging.debug(f"Processing command: {line}")
        if line.startswith('!'):
            await self.handle_command(line[1:])
            return

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
                    return
                return func(arg)
            except AttributeError:
                return self.default(line)

    async def ai_conversation_loop(self):
        """
        Main loop for processing user input and generating AI responses.

        This method continuously monitors the input queue for user messages,
        processes them, and generates AI responses using the ConversationManager.
        """
        self.logging.debug("Starting AI conversation loop")
        while True:
            try:
                user_input = await self.input_queue.get()
                self.logging.debug(f"Processing user input: {user_input}")
                await self.process_input(user_input)
            except asyncio.CancelledError:
                self.logging.info("AI conversation loop cancelled")
                break
            except Exception as e:
                self.logging.error(f"Error in AI conversation loop: {str(e)}", exc_info=True)
        self.logging.debug("Exiting AI conversation loop")

    async def process_input(self, user_input: str):
        """
        Processes user input and generates AI responses.

        This method handles the core conversation flow, updating the conversation history
        with user input and generating AI responses until user input is required again.

        Args:
            user_input (str): The input provided by the user.
        """
        self.logging.debug(f"Processing input: {user_input}")

        self.conversation_manager.update_conversation(user_input, self.conversation_manager.user_name)
        while True:
            # Generate AI responses until the conversation requires user input
            await self.conversation_manager.generate_ai_conversation(user_input)

            try:
                # Use asyncio.wait_for to set a timeout for user input
                user_input = await asyncio.wait_for(
                    self.get_user_input(self.prompt),
                    timeout=60  # 60 seconds timeout, adjust as needed
                )
            except asyncio.TimeoutError:
                self.logging.warning("User input timed out. Continuing conversation.")
                user_input = "I'm still here, please continue."
            except Exception as e:
                self.logging.error(f"Error getting user input: {str(e)}")
                user_input = "Sorry, there was an issue. Please continue."

            # Check if the input is a command (starts with '!')
            if user_input.startswith('!'):
                await self.handle_command(user_input[1:])
                continue

            self.conversation_manager.update_conversation(user_input, self.conversation_manager.user_name)

            # If the user enters a command (starting with '_'), break the loop
            if user_input.startswith('_'):
                break

            # If the user wants to quit, break the loop
            if user_input.lower() in ['quit', 'exit', 'bye']:
                break

    async def handle_command(self, command: str):
        """
        Handles system commands that start with '!'.

        This method processes special commands that are not part of the regular conversation flow.

        Args:
            command (str): The command to process (without the leading '!').
        """
        self.logging.debug(f"Handling command: {command}")
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()

        if cmd == 'history':
            await self.show_conversation_history()
        else:
            self.console.print(f"[bold red]Unknown command: {cmd}[/bold red]")

    async def show_conversation_history(self):
        """
        Displays the conversation history in a copyable text format with participant-specific colors.

        This method loads the conversation history, allows the user to select a specific thread,
        and then displays the selected thread's messages with each participant's text in their
        designated color. It adds a separator line after each message header for better organization.

        The user's messages are always in red, the moderator's in yellow, and AI personalities
        in their colors as defined in the AI_PERSONALITIES dictionary.
        """
        self.logging.debug("Entering show_conversation_history method")

        # Reload the conversation history to ensure we have the latest data
        self.conversation_manager.load_conversation_history()

        if not self.conversation_manager.conversation_history:
            self.logging.warning("No conversation history found")
            self.console.print("[bold red]No conversation history found[/bold red]")
            return

        # Sort threads by date (assuming the first message in each thread has a timestamp)
        sorted_threads = sorted(
            self.conversation_manager.conversation_history.items(),
            key=lambda x: x[1][0].get('timestamp', '0') if x[1] else '0',
            reverse=True
        )
        self.logging.debug(f"Sorted {len(sorted_threads)} threads")

        # Create a list of thread options
        thread_options = [
            f"{thread_id}: {len(messages)} messages, Last update: {messages[-1].get('timestamp', 'Unknown') if messages else 'Unknown'}"
            for thread_id, messages in sorted_threads
        ]

        # Present the list to the user
        self.console.print("[bold]Available threads:[/bold]")
        for i, option in enumerate(thread_options, 1):
            self.console.print(f"{i}. {option}")

        # Get user selection
        while True:
            try:
                selection = await self.get_user_input(
                    "Enter the number of the thread you want to view (or 'q' to quit): ")
                if selection.lower() == 'q':
                    self.logging.debug("User chose to quit thread selection")
                    return
                selection = int(selection) - 1
                if 0 <= selection < len(thread_options):
                    break
                else:
                    self.logging.warning(f"Invalid thread selection: {selection + 1}")
                    self.console.print("[bold red]Invalid selection. Please try again.[/bold red]")
            except ValueError:
                self.logging.warning("Invalid input for thread selection")
                self.console.print("[bold red]Please enter a valid number.[/bold red]")

        selected_thread_id = sorted_threads[selection][0]
        history = self.conversation_manager.conversation_history[selected_thread_id]
        self.logging.info(f"Selected thread: {selected_thread_id} with {len(history)} messages")

        # Create a custom theme for the console
        theme = Theme({
            "user": "red",
            "moderator": "yellow",
            **{name: details['color'] for name, details in AI_PERSONALITIES.items()}
        })
        colored_console = Console(theme=theme)
        self.logging.debug("Created custom color theme for console output")

        output = Text()
        output.append(f"Conversation History (Thread: {selected_thread_id})\n\n")

        for entry in history:
            timestamp = entry.get('timestamp', 'Unknown')
            sender = entry['sender']
            message = entry['message']

            # Determine the color for the sender
            if sender == self.conversation_manager.user_name:
                color = "user"
            elif sender == "Moderator":
                color = "moderator"
            else:
                color = AI_PERSONALITIES.get(sender, {}).get('color', 'white')

            # Add the colored sender and message to the output
            output.append(f"[{timestamp}] ", style="bold")
            output.append(sender, style=color)
            output.append(":\n")
            output.append("─" * 40 + "\n")  # Add a separator line
            output.append(f"{message}\n\n")

            self.logging.debug(f"Added message from {sender} to output")

        # Display the output in a pager
        self.logging.debug("Displaying conversation history in pager")
        with colored_console.pager():
            colored_console.print(output)

        self.logging.debug("Exiting show_conversation_history method")

    def default(self, statement):
        """
        Handles default command input (user messages).

        This method is called when the input doesn't match any defined commands.
        It processes the input as part of the conversation or as a system command.

        Args:
            statement: The user's input statement.
        """
        self.logging.debug(f"Processing default input: {statement}")
        try:
            # Check if the input is a command (starts with '!')
            if statement.startswith('!'):
                asyncio.create_task(self.handle_command(statement[1:]))
            else:
                asyncio.create_task(self.process_input_wrapper(statement))
        except Exception as e:
            self.logging.error(f"Error processing input: {str(e)}", exc_info=True)

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
            self.logging.error(f"Error in process_input: {str(e)}", exc_info=True)

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
        self.logging.debug("Quit command received")
        if self.ai_conversation_task:
            self.ai_conversation_task.cancel()
        return True

    def do__help(self, arg):
        """
        Displays the help message with available commands.

        This method provides information about the available commands and their usage.

        Args:
            arg: Any arguments passed with the help command (unused).
        """
        self.logging.debug("Help command received")
        help_text = """
        Commands:
        help - Show this help message
        quit - Exit the application
        switch_thread [thread_id] - Switch to a different conversation thread
        list_threads - List all available conversation threads
        clear - Clear the current conversation thread

        To direct a comment at a specific participant, start your message with their name followed by a colon.
        Example: "Vanessa: What do you think about this?"
        """
        self.console.print(Markdown(help_text))

    def do__switch_thread(self, thread_id):
        """
        Switches to a different conversation thread.

        This method changes the current active thread to the specified thread ID.

        Args:
            thread_id (str): The ID of the thread to switch to.
        """
        self.logging.debug(f"Attempting to switch to thread: {thread_id}")
        if thread_id in self.conversation_manager.conversation_history:
            self.conversation_manager.current_thread_id = thread_id
            self.console.print(f"[bold]Switched to thread: {thread_id}[/bold]")
            # Replay the conversation history for the new thread
            for entry in self.conversation_manager.conversation_history[thread_id]:
                self.conversation_manager.update_conversation(entry['message'], entry['sender'])
            self.logging.debug(f"Successfully switched to thread: {thread_id}")
        else:
            self.console.print(f"[bold red]Thread {thread_id} not found[/bold red]")
            self.logging.warning(f"Attempted to switch to non-existent thread: {thread_id}")

    def do__list_threads(self, arg):
        """
        Lists all available conversation threads.

        This method displays a list of all conversation threads and their message counts.

        Args:
            arg: Any arguments passed with the list_threads command (unused).
        """
        self.logging.debug("Listing available threads")
        thread_list = "\n".join(
            [f"{thread_id}: {len(messages)} messages" for thread_id, messages in self.conversation_manager.conversation_history.items()])
        self.console.print(f"[bold]Available threads:[/bold]\n{thread_list}")
        self.logging.debug(f"Thread list displayed: {thread_list}")

    def do__clear(self, arg):
        """
        Clears the current conversation thread.

        This method removes all messages from the current conversation thread.

        Args:
            arg: Any arguments passed with the clear command (unused).
        """
        self.logging.debug(f"Attempting to clear current thread: {self.conversation_manager.current_thread_id}")
        if self.conversation_manager.current_thread_id in self.conversation_manager.conversation_history:
            self.conversation_manager.conversation_history[self.conversation_manager.current_thread_id] = []
            self.conversation_manager.save_conversation_history()
            self.console.print("[bold green]Conversation cleared[/bold green]")
            self.logging.info(f"Cleared conversation thread: {self.conversation_manager.current_thread_id}")
        else:
            self.console.print("[bold red]No active conversation thread to clear[/bold red]")
            self.logging.warning("Attempted to clear non-existent or inactive thread")

