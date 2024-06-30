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

from itertools import cycle
import asyncio
from asyncio import Queue
import os
import random
import json
import re
import logging
from typing import Dict, Any, List, AsyncGenerator
from personalities import AI_PERSONALITIES, HELPER_PERSONALITIES, MASTER_SYSTEM_MESSAGE
from ai_config import AI_CONFIG, log_ai_error

# Import ainput or define a fallback
try:
    from aioconsole import ainput
except ImportError:
    import asyncio
    ainput = asyncio.run(input)  # Fallback to synchronous input if aioconsole is not available

class ConversationManager:
    """
    Manages the conversation history, AI interactions, and related operations.

    This class is responsible for maintaining the conversation history, generating AI responses,
    and handling the core logic of the conversation flow. It interacts with various AI models
    and personalities to create a dynamic conversational experience.

    Attributes:
        conversation_history (Dict[str, List[Dict]]): A dictionary storing conversation threads.
        current_thread_id (str): The ID of the current active conversation thread.
        user_name (str): The name of the human user participating in the conversation.
        CONVERSATION_HISTORY_FILE (str): The file path for storing conversation history.
        thinking_participant (str): The name of the AI participant currently "thinking".
        participants (List[str]): A list of AI participants in the conversation.
        last_addressed (str): The last participant addressed in the conversation.
        console (Console): A Rich console object for formatted output.
        logging (logging.Logger): A logger for debug and error messages.

    Methods:
        load_conversation_history(): Loads the conversation history from a file.
        save_conversation_history(): Saves the current conversation history to a file.
        update_conversation(message: str, sender: str): Adds a new message to the conversation history.
        format_and_print_message(message: str, sender: str): Formats and prints a message.
        get_conversation_context(): Retrieves the current conversation context.
        generate_ai_response(prompt: str, participant: str): Generates an AI response.
        extract_ai_response(full_response: str, participant: str): Extracts AI response from full text.
        generate_single_response(participant: str, prompt: str, responding_to: str): Generates a single AI response.
        detect_addressed_participant(message: str): Detects which participant a message is addressed to.
        randomize_participants(): Randomizes the order of AI participants.
        generate_ai_conversation(prompt: str): Generates a full AI conversation based on a prompt.
        generate_moderator_summary(): Generates a summary of the conversation by a moderator AI.
    """

    def __init__(self, user_name: str):
        """
        Initializes the ConversationManager with necessary attributes and loads conversation history.

        Args:
            user_name (str): The name of the human user participating in the conversation.
        """
        self.conversation_history = {}
        self.current_thread_id = ""
        self.user_name = user_name
        self.CONVERSATION_HISTORY_FILE = "conversation_history.json"
        self.thinking_participant = None
        self.participants = list(AI_PERSONALITIES.keys())
        self.last_addressed = None
        self.console = Console()
        self.logging = logging.getLogger(self.__class__.__name__)

        self.load_conversation_history()
        self.logging.debug("ConversationManager initialized")

    def load_conversation_history(self):
        """
        Loads the conversation history from a JSON file.

        If the file doesn't exist or is invalid, initializes an empty history.
        The conversation history is stored in self.conversation_history.
        """
        try:
            with open(self.CONVERSATION_HISTORY_FILE, "r") as file:
                self.conversation_history = json.load(file)
            self.logging.debug(f"Loaded conversation history from {self.CONVERSATION_HISTORY_FILE}")
        except (FileNotFoundError, json.JSONDecodeError):
            self.conversation_history = {}
            self.logging.debug(f"Conversation history file not found or invalid. Starting with an empty history.")

    def save_conversation_history(self):
        """
        Saves the current conversation history to a JSON file.

        The conversation history is saved to the file specified by CONVERSATION_HISTORY_FILE.
        This method should be called after any updates to the conversation history.
        """
        try:
            with open(self.CONVERSATION_HISTORY_FILE, 'w') as file:
                json.dump(self.conversation_history, file, indent=2)
            self.logging.debug(f"Saved conversation history to {self.CONVERSATION_HISTORY_FILE}")
        except Exception as e:
            self.logging.error(f"Error occurred while saving conversation history: {str(e)}")

    def update_conversation(self, message: str, sender: str = "User"):
        """
        Updates the conversation history with a new message and displays it.

        This method adds a new message to the current conversation thread and saves the updated history.
        It also formats and prints the message to the console.

        Args:
            message (str): The content of the message to be added.
            sender (str): The name of the message sender. Defaults to "User".
        """
        self.logging.debug(f"Updating conversation with message from {sender}")
        if self.current_thread_id not in self.conversation_history:
            self.conversation_history[self.current_thread_id] = []

        self.conversation_history[self.current_thread_id].append({
            "sender": sender,
            "message": message,
            "is_partial": False,
            "is_divider": False
        })
        self.save_conversation_history()

        self.format_and_print_message(message, sender)

    def format_and_print_message(self, message: str, sender: str):
        """
        Formats and prints a message with the sender's color as background and black text.

        This method applies specific formatting to the message based on the sender:
        - Participant names mentioned in the message are highlighted.
        - The AI model used is displayed in the title after the sender's name.
        - Messages are displayed in colored panels aligned to the left or right.

        Args:
            message (str): The message content to format and print.
            sender (str): The name of the message sender.
        """
        self.logging.debug(f"Formatting message from {sender}")

        if sender == "Moderator":
            sender_color = "yellow"
            model = AI_CONFIG.get("anthropic", {}).get("model", "")  # Assuming Moderator uses Anthropic
        elif sender == self.user_name:
            sender_color = "red"
            model = ""  # No model for human user
        else:
            ai_personality = AI_PERSONALITIES.get(sender, {})
            sender_color = ai_personality.get('color', 'white')
            ai_name = ai_personality.get('ai_name', '')
            model = AI_CONFIG.get(ai_name, {}).get("model", "")

        console = Console()

        lines = message.split('\n')
        current_panel_content = Text()
        in_code_block = False
        code_block = []
        code_lang = ""

        def print_current_panel():
            if current_panel_content:
                if sender != self.user_name:
                    panel_style = Style(color="black", bgcolor=sender_color)
                    title = f"{sender} [{model}]" if model else sender
                    message_panel = Panel(
                        current_panel_content,
                        title=Text(title, style=panel_style),
                        border_style=panel_style,
                        expand=False,
                        style=panel_style,
                        width=console.width - 5  # Limit the width of the participant's comment windows
                    )
                    # Align the whole box to the right, but keep text left-aligned
                    console.print(Align.right(message_panel))
                else:
                    panel = Panel(
                        current_panel_content,
                        title=Text(sender, style=Style(color="black", bold=True)),
                        border_style=Style(color="black"),
                        expand=False,
                        style=Style(color="black", bgcolor=sender_color)
                    )
                    # Align the user's box to the left
                    console.print(panel)

        # Print any remaining content
        print_current_panel()
        console.print("")  # single line between responses

        self.logging.debug("Message formatted and printed successfully")

        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # End of code block
                    print_current_panel()
                    current_panel_content = Text()

                    console.print("\n")  # Extra line before code block
                    syntax = Syntax('\n'.join(code_block), code_lang or "python", theme="monokai", line_numbers=False)
                    if sender != self.user_name:
                        console.print(Align.right(syntax))
                    else:
                        console.print(syntax)
                    console.print("\n")  # Extra line after code block

                    in_code_block = False
                    code_block = []
                else:
                    # Start of code block
                    print_current_panel()
                    current_panel_content = Text()
                    in_code_block = True
                    code_lang = line[3:].strip()
            elif in_code_block:
                code_block.append(line)
            else:
                # Format regular text, highlighting participant names
                formatted_line = Text()
                words = line.split()
                for word in words:
                    participant_match = False
                    for participant, details in AI_PERSONALITIES.items():
                        if participant.lower() in word.lower():
                            color = details.get('color', 'white')
                            # Use inverse colors for participant names
                            formatted_line.append(word, style=Style(color="black", bgcolor=color, bold=True))
                            participant_match = True
                            break
                    if not participant_match:
                        formatted_line.append(word)
                    formatted_line.append(" ")
                current_panel_content.append(formatted_line)
                current_panel_content.append('\n')

        # Print any remaining content
        print_current_panel()
        console.print("")  # single line between responses

        self.logging.debug("Message formatted and printed successfully")

    def get_conversation_context(self) -> str:
        """
        Retrieves the current conversation context as a formatted string.

        This method compiles the conversation history for the current thread into a single string,
        which can be used as context for generating AI responses.

        Returns:
            str: A string representation of the current conversation context.
        """
        self.logging.debug("Getting conversation context")
        if self.current_thread_id not in self.conversation_history:
            return ""

        context = []
        for entry in self.conversation_history[self.current_thread_id]:
            sender = entry.get('sender', 'Unknown')
            content = entry.get('message', '')
            if entry.get('is_divider'):
                context.append('-' * 40)
            else:
                context.append(f"{sender}: {content}")
        return "\n".join(context)

    async def generate_ai_response(self, prompt: str, participant: str) -> AsyncGenerator[str, None]:
        """
        Generates an AI response for a given participant.

        This method creates a full prompt by combining the system message, participant's personality,
        conversation context, and user prompt. It then uses the appropriate AI model to generate
        a response.

        Args:
            prompt (str): The user's input prompt.
            participant (str): The name of the AI participant generating the response.

        Yields:
            str: Partial responses as they are generated.

        Raises:
            Exception: If there's an error during the response generation process.
        """
        self.logging.debug(f"Generating AI response for {participant}")
        ai_personality = AI_PERSONALITIES.get(participant) or HELPER_PERSONALITIES.get(participant)
        ai_config = AI_CONFIG[ai_personality['ai_name']]

        system_message = MASTER_SYSTEM_MESSAGE['system_message'].format(
            user_name=self.user_name,
            participants=", ".join([p for p in AI_PERSONALITIES if p != participant])
        )

        conversation_context = self.get_conversation_context()
        full_prompt = f"{system_message}\n{ai_personality['system_message']}\n\nConversation history:\n{conversation_context}\n\nUser: {prompt}\n{participant}:"

        try:
            self.logging.debug(f"Sending full prompt to AI model for {participant}")
            async for partial_response in ai_config['generate_func'](ai_config['model'], full_prompt):
                yield partial_response
        except Exception as e:
            error_message = f"Error generating AI response for {participant}: {str(e)}"
            self.logging.error(error_message)
            log_ai_error(ai_personality['ai_name'], error_message)
            yield f"{participant} is not available at the moment."

    def extract_ai_response(self, full_response: str, participant: str) -> str:
        """
        Extracts the AI's response from the full response string.

        This method isolates the AI's actual response from the full text returned by the AI model,
        which may include repetitions of the prompt or other extraneous information.

        Args:
            full_response (str): The full response including system message and context.
            participant (str): The name of the AI participant.

        Returns:
            str: The extracted AI response.
        """
        self.logging.debug(f"Extracting AI response for {participant}")
        pattern = f"{re.escape(participant)}:(?!.*{re.escape(participant)}:)"
        match = re.search(pattern, full_response, re.DOTALL)

        if match:
            return full_response[match.end():].strip()
        else:
            parts = full_response.split(f"{participant}:", 1)
            if len(parts) > 1:
                return parts[1].strip()
            else:
                return full_response.strip()

    async def generate_single_response(self, participant: str, prompt: str, responding_to: str = None):
        """
        Generates and processes a single AI response.

        This method handles the process of generating a response from a single AI participant,
        including displaying a "thinking" message, extracting the response, and updating the
        conversation history.

        Args:
            participant (str): The name of the AI participant generating the response.
            prompt (str): The input prompt or context for the response.
            responding_to (str, optional): The name of the participant being responded to, if any.
        """
        self.thinking_participant = participant
        self.logging.debug(f"Generating single response for {participant}")
        thinking_task = asyncio.create_task(self.display_thinking_message(participant))

        try:
            full_response = ""
            async for partial_response in self.generate_ai_response(prompt, participant):
                full_response += partial_response

            ai_response = self.extract_ai_response(full_response, participant)
            self.logging.debug(f"Extracted response for {participant}: {ai_response[:100]}...")
        except Exception as e:
            self.logging.error(f"Error generating response for {participant}: {str(e)}")
            ai_response = f"Error generating response for {participant}: {str(e)}"
        finally:
            self.thinking_participant = None
            thinking_task.cancel()  # Cancel the thinking task
            await asyncio.sleep(0.1)  # Give a moment for the thinking message to clear

            # Clear the entire line where the spinner was
            print("\033[K", end="", flush=True)
            # Move the cursor to the beginning of the line
            print("\r", end="", flush=True)

            self.update_conversation(ai_response, participant)
            self.logging.debug(f"Added response from {participant} to conversation history")

    async def display_thinking_message(self, participant: str):
        """
        Displays a "thinking" message for the AI participant.

        This method shows a spinner with a message indicating that the AI is thinking or responding.
        It continues until the thinking_participant attribute is changed.

        Args:
            participant (str): The name of the AI participant who is "thinking".
        """
        message = f"{participant} is thinking..."
        if hasattr(self, 'responding_to') and self.responding_to:
            message = f"{participant} is responding to {self.responding_to}..."
        spinner = Spinner('dots', text=message)
        with Live(spinner, refresh_per_second=10, transient=True) as live:
            while self.thinking_participant == participant:
                await asyncio.sleep(0.1)

    async def detect_addressed_participant(self, message: str) -> str:
        """
        Detects which participant a message is addressed to.

        This method uses a helper AI to determine if the message is directed at a specific participant.

        Args:
            message (str): The message to analyze.

        Returns:
            str: The name of the addressed participant, or None if not detected.
        """
        self.logging.debug("Detecting addressed participant")
        response_detector = HELPER_PERSONALITIES['ResponseDetector']
        ai_config = AI_CONFIG[response_detector['ai_name']]

        prompt = f"{response_detector['system_message']}\n\nMessage: {message}\n\nDetermine which participant, if any, this message is directed at. If the message is soliciting a response from the human user ({self.user_name}), respond with '{self.user_name}'."

        try:
            detector_response = ""
            async for chunk in ai_config['generate_func'](ai_config['model'], prompt):
                detector_response += chunk

            addressed_participant = detector_response.strip()
            self.logging.debug(f"Detected addressed participant: {addressed_participant}")
            return addressed_participant if addressed_participant not in ['None', 'null', ''] else None
        except Exception as e:
            self.logging.error(f"Error in participant detection: {str(e)}")
            return None

    def randomize_participants(self):
        """
        Randomizes the order of AI participants.

        This method shuffles the list of participants to ensure a random order of responses
        in the conversation.
        """
        self.participants = random.sample(self.participants, len(self.participants))
        self.logging.debug(f"Randomized participant order: {', '.join(self.participants)}")

    async def generate_ai_conversation(self, prompt: str):
        """
        Generates a full AI conversation based on a given prompt.

        This method orchestrates the conversation flow by:
        1. Randomizing the order of AI participants.
        2. Generating responses from each participant.
        3. Detecting if a response is directed at a specific participant.
        4. Handling additional responses for directed messages.
        5. Checking if the conversation requires user input.

        Args:
            prompt (str): The initial prompt or user input to start the conversation.
        """
        self.logging.debug(f"Generating AI conversation for prompt: {prompt}")

        # Randomize the order of participants
        randomized_participants = random.sample(self.participants, len(self.participants))
        participant_cycle = cycle(randomized_participants)
        current_participant = next(participant_cycle)
        self.logging.debug(f"Randomized participant order: {', '.join(randomized_participants)}")

        try:
            for _ in range(len(self.participants)):  # Ensure each participant gets a turn
                self.logging.debug(f"Current participant: {current_participant}")
                await self.generate_single_response(current_participant, prompt)

                last_message = self.conversation_history[self.current_thread_id][-1]['message']
                addressed_participant = await self.detect_addressed_participant(last_message)
                self.logging.debug(f"Detected addressed participant: {addressed_participant}")

                if addressed_participant and addressed_participant in self.participants and addressed_participant != current_participant:
                    self.logging.info(f"Message from {current_participant} was directed at {addressed_participant}")
                    # Generate a single response from the addressed participant
                    await self.generate_single_response(addressed_participant, prompt,
                                                        responding_to=current_participant)

                # Move to the next participant in the cycle
                current_participant = next(participant_cycle)

            # After all participants have spoken, check if the user needs to respond
            last_message = self.conversation_history[self.current_thread_id][-1]['message']
            final_addressed_participant = await self.detect_addressed_participant(last_message)
            if final_addressed_participant == self.user_name:
                self.logging.info(f"Conversation is soliciting a response from the user")
                return  # Exit the method to allow user input in the main loop

        except Exception as e:
            self.logging.error(f"Error in generate_ai_conversation: {str(e)}")
            return  # Return to main loop to get user input

        self.logging.debug("Finished generating AI conversation")

    async def generate_moderator_summary(self):
        """
        Generates a summary of the conversation by the moderator.

        This method uses a moderator AI to create a summary of the current conversation thread.
        The summary is then added to the conversation history.
        """
        self.logging.debug("Generating moderator summary")
        self.thinking_participant = "Moderator"
        moderator = HELPER_PERSONALITIES['Moderator']
        self.console.print(
            f"[italic {moderator['color']}]Moderator is summarizing the conversation...[/italic {moderator['color']}]")

        try:
            ai_config = AI_CONFIG[moderator['ai_name']]

            conversation_text = self.get_conversation_context()
            prompt = f"{moderator['system_message']}\n\nConversation:\n{conversation_text}\n\nProvide a summary of this conversation."

            summary = ""
            async for partial_summary in ai_config['generate_func'](ai_config['model'], prompt):
                summary += partial_summary

            self.logging.debug("Moderator summary generated successfully")
            self.update_conversation(summary, "Moderator")

        except Exception as e:
            self.logging.error(f"Error generating moderator summary: {str(e)}")
            self.update_conversation("Unable to generate summary at this time.", "System")
        finally:
            self.thinking_participant = None

