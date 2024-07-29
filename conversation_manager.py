import logging
import json
import random
import asyncio
from datetime import datetime
from typing import Dict, List, AsyncGenerator, Optional, Union, Tuple
from PyQt5.QtCore import QObject, pyqtSignal
import aiohttp
import tiktoken
import re
from schema import ConversationHistory, ConversationThread, MessageEntry
from ai_config import AI_CONFIG, log_ai_error
from personalities import AI_PERSONALITIES, HELPER_PERSONALITIES, MASTER_SYSTEM_MESSAGE, USER_IDENTITY
from ConversationRAG import ConversationRAG
from Visualizer import VectorGraphVisualizer


class ConversationManager(QObject):
    ai_thinking_started = pyqtSignal(str)
    ai_thinking_finished = pyqtSignal(str)
    token_usage_updated = pyqtSignal(int)
    user_identity_loaded = pyqtSignal(str)
    ai_response_generated = pyqtSignal(str, str, str, str)

    def __init__(self, user_name: str, is_gui: bool = False):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.user_name: str = user_name
        self.is_gui: bool = is_gui
        self.conversation_history: ConversationHistory = {}
        self.current_thread_id: str = ""
        self.CONVERSATION_HISTORY_FILE: str = "conversation_history.json"
        self.thinking_participant: Optional[str] = None
        self.participants: List[str] = list(AI_PERSONALITIES.keys())
        self.last_addressed: Optional[str] = None
        self.rag = ConversationRAG()
        self.visualizer = None
        self.console = None
        self.used_rag: bool = False
        self.context_token_count: int = 0
        self.response_token_count: int = 0
        self.total_tokens: int = 0
        self.is_interrupted = False
        self.cl100k_tokenizer = tiktoken.get_encoding("cl100k_base")
        self.p50k_tokenizer = tiktoken.get_encoding("p50k_base")
        self.active_participants: List[str] = []
        self.responded_participants: Set[str] = set()
        self.is_first_prompt: bool = True
        self.load_conversation_history()
        self.session: Optional[aiohttp.ClientSession] = None
        self.current_round: int = 0


        self.logger.debug("ConversationManager initialization complete")

    def set_active_participants(self, participants: List[str]):
        self.active_participants = participants
        self.logger.info(f"Active participants set to: {self.active_participants}")

    def interrupt(self):
        self.is_interrupted = True
        self.logger.info("Conversation interrupted")

    def reset_interrupt(self):
        self.is_interrupted = False
        self.logger.info("Interrupt flag reset")

    async def create_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self.logger.debug("Created new aiohttp ClientSession")

    async def close_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("Closed aiohttp ClientSession")

    def load_user_identity(self):
        """
        Load or create user identity and emit greeting.
        """
        self.logger.debug(f"Loading user identity for {self.user_name}")
        if self.user_name in USER_IDENTITY:
            greeting = USER_IDENTITY[self.user_name]["greeting"]
            self.logger.info(f"User {self.user_name} found in USER_IDENTITY")
        else:
            greeting = f"Welcome, {self.user_name}!"
            USER_IDENTITY[self.user_name] = {'greeting': greeting}
            self.logger.info(f"Added {self.user_name} to USER_IDENTITY")

        self.user_identity_loaded.emit(greeting)

    def load_conversation_history(self) -> None:
        try:
            with open(self.CONVERSATION_HISTORY_FILE, "r") as file:
                loaded_history = json.load(file)

            self.conversation_history = {
                thread_id: ConversationThread.from_dict(thread_data)
                for thread_id, thread_data in loaded_history.items()
            }

            self.logger.debug(f"Loaded conversation history from {self.CONVERSATION_HISTORY_FILE}")
        except (FileNotFoundError, json.JSONDecodeError):
            self.conversation_history = {}
            self.logger.warning("Conversation history file not found or invalid. Starting with an empty history.")

    def save_conversation_history(self) -> None:
        try:
            history_dict = {
                thread_id: thread.to_dict()
                for thread_id, thread in self.conversation_history.items()
            }
            with open(self.CONVERSATION_HISTORY_FILE, 'w') as file:
                json.dump(history_dict, file, indent=2, default=str)
            self.logger.debug(f"Saved conversation history to {self.CONVERSATION_HISTORY_FILE}")
        except Exception as e:
            self.logger.error(f"Error occurred while saving conversation history: {str(e)}", exc_info=True)

    def update_conversation_topic(self, topic: str):
        if self.current_thread_id in self.conversation_history:
            self.conversation_history[self.current_thread_id].topic = topic
            self.save_conversation_history()
            self.logger.info(f"Updated conversation topic: {topic}")
            # Emit a signal or update the GUI to display the new topic
            # if self.is_gui:
            #    self.ai_response_generated.emit("System", f"The topic of this conversation has been set to: {topic}",
            #                                    "System", "System")
        else:
            self.logger.error("Cannot update topic: No active conversation thread")

    def update_conversation(self, message: str, sender: str = "User", ai_name: str = None, model: str = None) -> None:
        self.logger.debug(f"Updating conversation with message from {sender}")

        if self.current_thread_id not in self.conversation_history:
            self.new_topic()

        # Skip System messages
        if sender.lower() == "system":
            self.logger.debug("Skipping System message")
            return

        new_entry = MessageEntry(
            sender=sender,
            message=message,
            ai_name=ai_name,
            model=model,
            is_partial=False,
            is_divider=False,
            timestamp=datetime.now().isoformat()
        )

        # Check for duplicates
        messages = self.conversation_history[self.current_thread_id].messages
        if not messages or new_entry != messages[-1]:
            messages.append(new_entry)
            self.save_conversation_history()

            # Update the RAG database
            try:
                self.rag.add_message(f"{sender}: {message}")
                self.logger.debug("RAG system updated with new message")
                if self.visualizer:
                    self.visualizer.update_plot()
            except Exception as e:
                self.logger.error(f"Error updating RAG system: {str(e)}", exc_info=True)
        else:
            self.logger.debug("Skipping duplicate message")

    async def generate_moderator_summary_for_history(self, thread_id: str) -> str:
        self.logger.debug(f"Generating moderator summary for historical thread: {thread_id}")
        self.thinking_participant = "Moderator"

        try:
            await self.create_session()
            conversation_text = self.get_conversation_context_for_history(thread_id)
            if not conversation_text:
                return "Unable to generate summary: No conversation history found."

            context_detector = HELPER_PERSONALITIES['ContextDetector']
            context_ai_config = AI_CONFIG[context_detector['ai_name']]
            context_prompt = f"{context_detector['system_message']}\n\nConversation:\n{conversation_text}\n\nContext category:"

            context_category = await self.generate_context_category(context_ai_config, context_prompt)

            moderator = HELPER_PERSONALITIES['Moderator']
            moderator_ai_config = AI_CONFIG[moderator['ai_name']]
            moderator_prompt = f"{moderator['system_message']}\n\nConversation context: {context_category}\n\nConversation:\n{conversation_text}\n\nProvide a summary based on the conversation context:"

            summary = await self.generate_summary(moderator_ai_config, moderator_prompt)

            self.logger.debug("Moderator summary for historical thread generated successfully")
            return summary
        except Exception as e:
            self.logger.error(f"Error generating moderator summary for historical thread: {str(e)}", exc_info=True)
            return f"Unable to generate summary: {str(e)}"
        finally:
            self.thinking_participant = None
            await self.close_session()

    async def generate_context_category(self, ai_config, prompt):
        context_category = ""
        async for partial_context in ai_config['generate_func'](ai_config['model'], prompt):
            context_category += partial_context.strip()
        return context_category

    async def generate_summary(self, ai_config, prompt):
        summary = ""
        async for partial_summary in ai_config['generate_func'](ai_config['model'], prompt):
            summary += partial_summary
        return summary

    def get_conversation_context_for_history(self, thread_id: str) -> str:
        if thread_id in self.conversation_history:
            thread = self.conversation_history[thread_id]
            messages = thread.messages  # Access the messages attribute
            return "\n".join([f"{msg.sender}: {msg.message}" for msg in messages])
        else:
            return "No conversation history found for the given thread ID."

    def update_token_usage(self, tokens: int):
        """
        Update the token usage count and emit the updated total.

        Args:
            tokens (int): The number of tokens to add to the total.
        """
        self.total_tokens += tokens
        self.token_usage_updated.emit(self.total_tokens)
        self.logger.debug(f"Updated token usage. Total tokens: {self.total_tokens}")

    def get_current_context(self) -> str:
        """
        Get the current context of the conversation.

        Returns:
            str: The current context as a string.
        """
        try:
            recent_messages = self.conversation_history[self.current_thread_id][-5:]
            return "\n".join([f"{msg['sender']}: {msg['message']}" for msg in recent_messages])
        except Exception as e:
            self.logger.error(f"Error getting current context: {str(e)}", exc_info=True)
            return ""

    def get_conversation_context(self, thread_id: str) -> str:
        try:
            if self.current_round == 1:
                return f"This is the start of a new conversation topic (Thread ID: {thread_id})."

            recent_context = self.rag.get_recent_messages(5)
            if not recent_context:
                return f"No recent context available for this topic (Thread ID: {thread_id})."

            relevant_history = self.rag.get_relevant_history(recent_context)

            if relevant_history:
                full_context = f"Recent relevant conversation (Thread ID: {thread_id}):\n{relevant_history}\n\nCurrent context:\n{recent_context}"
            else:
                full_context = f"Current context (Thread ID: {thread_id}):\n{recent_context}"

            self.context_token_count = self.count_tokens(full_context)
            return full_context
        except Exception as e:
            self.logger.error(f"Error retrieving conversation context from RAG for thread {thread_id}: {str(e)}",
                              exc_info=True)
            return f"Error retrieving context for thread {thread_id}. Starting with a clean slate."

    def get_fallback_context(self) -> str:
        """
        Get a fallback context when RAG fails.

        Returns:
            str: The fallback context as a string.
        """
        self.logger.warning("Using fallback method for context retrieval")
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

    def get_tokenizer(self, model: str):
        """
        Get the appropriate tokenizer for a given model.

        Args:
            model (str): The model name.

        Returns:
            Tokenizer: The tokenizer for the specified model.
        """
        if model.startswith("gpt-3.5"):
            return self.p50k_tokenizer
        else:  # Claude models and GPT-4 use cl100k
            return self.cl100k_tokenizer

    def count_tokens(self, text: str, model: str = "claude-3-opus-20240229") -> int:
        """
        Count the number of tokens in a given text for a specific model.

        Args:
            text (str): The text to count tokens for.
            model (str): The model to use for token counting.

        Returns:
            int: The number of tokens in the text.
        """
        tokenizer = self.get_tokenizer(model)
        return len(tokenizer.encode(text))

    async def generate_ai_conversation(self, prompt: str, active_participants: List[str]) -> Dict[
        str, Tuple[str, str, str]]:
        self.logger.debug(f"Generating AI conversation for prompt: {prompt}")
        await self.create_session()

        if self.is_first_prompt:
            self.new_topic()
            self.is_first_prompt = False

        if not self.current_thread_id or self.current_thread_id not in self.conversation_history:
            self.new_topic()

        # Update conversation with user's prompt only once
        self.update_conversation(prompt, self.user_name, "Human", self.user_name)

        responses = {}
        self.responded_participants.clear()

        try:
            for participant in active_participants:
                self.logger.debug(f"Generating response for participant: {participant}")
                response, ai_name, model = await self.generate_single_response(participant, prompt)
                if response:  # Only add non-empty responses
                    responses[participant] = (response, ai_name, model)
                    # Update conversation here instead of in generate_single_response
                    self.update_conversation(response, participant, ai_name, model)
                    self.ai_response_generated.emit(participant, response, ai_name, model)
                    self.logger.debug(f"Response generated for {participant}: {response[:50]}...")

            self.logger.info(f"Round of responses completed. Total responses: {len(responses)}")

            if set(active_participants) == self.responded_participants:
                self.logger.info("All active participants have responded. Generating topic.")
                topic = await self.generate_topic(prompt, responses)
                self.update_conversation_topic(topic)
                self.logger.info(f"Topic generated: {topic}")
            else:
                self.logger.info("Not all active participants have responded. Skipping topic generation.")
                missing_participants = set(active_participants) - self.responded_participants
                self.logger.debug(f"Participants who didn't respond: {missing_participants}")

            return responses
        except Exception as e:
            self.logger.error(f"Error in generate_ai_conversation: {str(e)}", exc_info=True)
            return {"System": (f"An error occurred in the conversation: {str(e)}", "System", "System")}

    async def generate_topic(self, prompt: str, responses: Dict[str, Tuple[str, str, str]] = None) -> str:
        self.logger.debug("Generating topic for the conversation")
        topic_generator = HELPER_PERSONALITIES['TopicGenerator']
        ai_config = AI_CONFIG[topic_generator['ai_name']]

        # Create a context that includes the full conversation history
        context = self.get_conversation_context(self.current_thread_id)

        topic_prompt = f"{topic_generator['system_message']}\n\nConversation context:\n{context}\n\nGenerate a topic based on this conversation:"

        topic = ""
        async for partial_topic in ai_config['generate_func'](ai_config['model'], topic_prompt):
            topic += partial_topic.strip()

        self.logger.debug(f"Generated topic: {topic}")

        # Set the generated topic in the conversation history
        self.update_conversation_topic(topic)

        return topic

    def extract_ai_response(self, full_response: str, participant: str) -> str:
        self.logger.debug(f"Extracting AI response for {participant}")
        try:
            # If the response is already in the correct format, return it
            if isinstance(full_response, str) and not full_response.startswith(participant):
                return full_response.strip()

            # Try to extract the response using regex
            pattern = f"{re.escape(participant)}:(?!.*{re.escape(participant)}:)"
            match = re.search(pattern, full_response, re.DOTALL)

            if match:
                extracted_response = full_response[match.end():].strip()
                self.logger.debug("Successfully extracted AI response using regex")
                return extracted_response

            # If regex fails, try splitting the string
            parts = full_response.split(f"{participant}:", 1)
            if len(parts) > 1:
                extracted_response = parts[1].strip()
                self.logger.debug("Extracted AI response using string split")
                return extracted_response

            # If all extraction methods fail, return the full response
            self.logger.warning("Failed to extract AI response, returning full response")
            return full_response.strip()
        except Exception as e:
            self.logger.error(f"Error in extract_ai_response: {str(e)}", exc_info=True)
            return f"Error extracting response: {str(e)}"

    async def generate_single_response(self, participant: str, prompt: str) -> Tuple[str, str, str]:
        self.thinking_participant = participant
        self.logger.debug(f"Generating single response for {participant}")

        if self.is_interrupted:
            return "", "", ""

        if self.is_gui:
            self.ai_thinking_started.emit(participant)

        ai_response = ""
        ai_name = ""
        model = ""
        try:
            self.used_rag = False
            self.context_token_count = 0
            self.response_token_count = 0

            full_response = ""
            async for partial_response in self.generate_ai_response(prompt, participant):
                if self.is_interrupted:
                    break
                full_response += partial_response

            ai_response = self.extract_ai_response(full_response, participant)
            self.logger.debug(f"Extracted response for {participant}: %.100s...", ai_response)

            # Get AI name and model
            ai_personality = AI_PERSONALITIES.get(participant) or HELPER_PERSONALITIES.get(participant)
            ai_name = ai_personality['ai_name']
            ai_config = AI_CONFIG.get(ai_name)
            model = ai_config['model'] if ai_config else "Unknown"

            # Remove the update_conversation call from here

            # Update token usage
            self.update_token_usage(self.count_tokens(ai_response))

            # Add participant to the responded set
            self.responded_participants.add(participant)
            self.logger.debug(f"Added {participant} to responded participants")

        except Exception as e:
            self.logger.error(f"Error generating response for {participant}: {str(e)}", exc_info=True)
            ai_response = f"Error: {str(e)}"
            ai_name = "Error"
            model = "Error"

        finally:
            self.thinking_participant = None
            if self.is_gui:
                self.ai_thinking_finished.emit(participant)

        return ai_response, ai_name, model

    async def detect_addressed_participant(self, message: str) -> Optional[str]:
        """
        Detect which participant (if any) a message is addressed to.

        Args:
            message (str): The message to analyze.

        Returns:
            Optional[str]: The name of the addressed participant, or None if not detected.
        """
        self.logger.debug("Detecting addressed participant for message")

        participants = list(AI_PERSONALITIES.keys()) + [self.user_name]
        response_detector = HELPER_PERSONALITIES['ResponseDetector']
        ai_config = AI_CONFIG[response_detector['ai_name']]

        prompt = f"{response_detector['system_message']}\n\nMessage: {message}\n\nParticipants: {', '.join(participants)}\n\nAddressed participant:"

        try:
            async for partial_response in ai_config['generate_func'](ai_config['model'], prompt):
                if partial_response.strip():
                    detected_participant = partial_response.strip()
                    self.logger.debug(f"Detected addressed participant: {detected_participant}")
                    return detected_participant
        except Exception as e:
            self.logger.error(f"Error detecting addressed participant: {str(e)}", exc_info=True)

        self.logger.debug("No specific participant detected")
        return None

    async def generate_ai_response(self, prompt: str, participant: str) -> AsyncGenerator[str, None]:
        self.logger.debug(f"Generating AI response for {participant} in thread {self.current_thread_id}")
        await self.create_session()

        ai_personality = AI_PERSONALITIES.get(participant) or HELPER_PERSONALITIES.get(participant)

        if ai_personality is None:
            self.logger.error(f"No AI personality found for participant: {participant}")
            yield f"Error: No AI personality found for {participant}"
            return

        ai_config = AI_CONFIG.get(ai_personality['ai_name'])
        if ai_config is None:
            self.logger.error(f"No AI configuration found for AI name: {ai_personality['ai_name']}")
            yield f"Error: No AI configuration found for {participant}"
            return

        model = ai_config['model']

        system_message = MASTER_SYSTEM_MESSAGE['system_message'].format(
            user_name=self.user_name,
            participants=", ".join([p for p in AI_PERSONALITIES if p != participant])
        )

        conversation_context = self.get_conversation_context(self.current_thread_id)

        is_new_topic = self.current_round == 1
        new_topic_indicator = f"This is a new conversation topic (Thread ID: {self.current_thread_id}). Please do not reference any previous conversations. " if is_new_topic else ""

        full_prompt = f"{system_message}\n{ai_personality['system_message']}\n\n{new_topic_indicator}{conversation_context}\n\nUser: {prompt}\n{participant}:"

        self.context_token_count = self.count_tokens(full_prompt, model)
        self.response_token_count = 0

        try:
            self.logger.debug(f"Sending full prompt to AI model for {participant} in thread {self.current_thread_id}")
            async for partial_response in ai_config['generate_func'](model, full_prompt):
                if self.is_interrupted:
                    self.logger.info(f"AI response generation for {participant} interrupted")
                    return
                self.response_token_count += self.count_tokens(partial_response, model)
                self.total_tokens += self.count_tokens(partial_response, model)
                if self.is_gui:
                    self.token_usage_updated.emit(self.total_tokens)
                yield partial_response

        except Exception as e:
            error_message = f"Error generating AI response for {participant} in thread {self.current_thread_id}: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            log_ai_error(ai_personality['ai_name'], error_message)
            yield f"{participant} is not available at the moment. Error: {str(e)}"

        finally:
            if is_new_topic:
                self.current_round += 1

    async def evaluate_response(self, response: str, participant: str) -> Tuple[str, Optional[str]]:
        detector = HELPER_PERSONALITIES['ResponseDetector']
        ai_config = AI_CONFIG[detector['ai_name']]

        prompt = f"{detector['system_message']}\n\nResponse: {response}\n\nEvaluate if this response is directed at the user or another AI participant."

        evaluation = ""
        async for partial_eval in ai_config['generate_func'](ai_config['model'], prompt):
            evaluation += partial_eval

        if "user" in evaluation.lower():
            return "user", None
        elif any(participant in evaluation.lower() for participant in self.participants):
            for p in self.participants:
                if p.lower() in evaluation.lower():
                    return "ai", p
        return "general", None

    async def continue_conversation(self, user_input: str, active_participants: List[str]) -> Optional[str]:
        self.logger.debug(f"Continuing conversation with user input: {user_input}")
        self.is_interrupted = False  # Reset interrupt flag at the start of conversation continuation

        if not self.current_thread_id or self.current_thread_id not in self.conversation_history:
            self.logger.error("No valid conversation thread")
            return "An error occurred. Please start a new conversation."

        try:
            addressed_participant = await self.detect_addressed_participant(user_input)

            if addressed_participant:
                if addressed_participant == self.user_name:
                    return f"The question was directed at you. Please respond."
                elif addressed_participant in active_participants:
                    if self.is_interrupted:
                        self.logger.info("Conversation interrupted before generating response")
                        return "Conversation interrupted"
                    response, ai_name, model = await self.generate_single_response(addressed_participant, user_input)
                    return f"{addressed_participant}: {response}\n\nYour turn to respond"

            # If no specific participant is addressed, generate responses from all active participants
            responses = {}
            for participant in active_participants:
                if self.is_interrupted:
                    self.logger.info("Conversation continuation interrupted")
                    return "Conversation interrupted"
                response, ai_name, model = await self.generate_single_response(participant, user_input)
                if response:
                    responses[participant] = (response, ai_name, model)
                    # self.ai_response_generated.emit(participant, response, ai_name, model)

            # Generate topic after the first round if it hasn't been generated yet
            if self.current_round == 1:
                topic = await self.generate_topic(user_input)
                self.update_conversation_topic(topic)
                self.current_round += 1

            if responses:
                formatted_responses = "\n".join([f"{p}: {r[0]}" for p, r in responses.items()])
                return f"{formatted_responses}\n\nYour turn to respond"
            else:
                return "No responses were generated. Please try again."

        except Exception as e:
            self.logger.error(f"Error in continue_conversation: {str(e)}", exc_info=True)
            return "An error occurred in the conversation. Please try again."

    async def generate_moderator_summary(self) -> str:
        self.logger.debug("Generating moderator summary")
        self.thinking_participant = "Moderator"

        try:
            await self.create_session()

            conversation_text = self.get_conversation_context(self.current_thread_id)
            context_detector = HELPER_PERSONALITIES['ContextDetector']
            context_ai_config = AI_CONFIG[context_detector['ai_name']]
            context_prompt = f"{context_detector['system_message']}\n\nConversation:\n{conversation_text}\n\nContext category:"

            context_category = await self.generate_context_category(context_ai_config, context_prompt)

            moderator = HELPER_PERSONALITIES['Moderator']
            moderator_ai_config = AI_CONFIG[moderator['ai_name']]
            moderator_prompt = f"{moderator['system_message']}\n\nConversation context: {context_category}\n\nConversation:\n{conversation_text}\n\nProvide a summary based on the conversation context:"

            summary = await self.generate_summary(moderator_ai_config, moderator_prompt)

            self.logger.debug("Moderator summary generated successfully")
            return summary
        except Exception as e:
            self.logger.error(f"Error generating moderator summary: {str(e)}", exc_info=True)
            return f"Unable to generate summary: {str(e)}"
        finally:
            self.thinking_participant = None
            await self.close_session()

    def format_message(self, message: str) -> str:
        """
        Format a message, wrapping code blocks with the appropriate markers.
        """
        lines = message.split('\n')
        formatted_lines = []
        in_code_block = False
        for line in lines:
            if line.strip().startswith('```') or line.strip().startswith('==='):
                if in_code_block:
                    formatted_lines.append("=== code end ===")
                else:
                    formatted_lines.append("=== code begin ===")
                in_code_block = not in_code_block
            else:
                formatted_lines.append(line)

        if in_code_block:
            formatted_lines.append("=== code end ===")

        return '\n'.join(formatted_lines)

    def new_topic(self):
        if self.is_first_prompt:
            self.logger.info("Creating the first topic")
            self.current_thread_id = f"thread_{len(self.conversation_history) + 1}"
            self.conversation_history[self.current_thread_id] = ConversationThread(
                date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                topic="",
                messages=[]
            )
            self.responded_participants.clear()
            self.current_round = 0
            self.is_first_prompt = False
            self.logger.info(f"Created first conversation topic with thread ID: {self.current_thread_id}")

            # Create a new RAG instance
            try:
                self.rag = ConversationRAG()
                self.logger.info("Created new ConversationRAG instance for new topic")
                if self.visualizer:
                    self.visualizer.set_rag(self.rag)
                    self.logger.info("Updated visualizer with new RAG instance")
            except Exception as e:
                self.logger.error(f"Error creating new RAG instance: {str(e)}", exc_info=True)
                self.logger.warning("Continuing with existing RAG instance")

            # Reset token counts for the new topic
            self.context_token_count = 0
            self.response_token_count = 0
            self.total_tokens = 0

            # Emit signal to update token usage display in GUI
            if self.is_gui:
                self.token_usage_updated.emit(self.total_tokens)

            # Clear the topic
            self.update_conversation_topic("")
        else:
            self.logger.info("Starting a new topic")

    def start_conversation(self):
        self.logger.info("Initializing new conversation")
        initial_message = "A new conversation topic has been started. What would you like to discuss?"
        self.update_conversation(initial_message, "System")
        if self.is_gui:
            self.ai_response_generated.emit("System", initial_message)

    def trigger_graph_update(self):
        if self.visualizer:
            self.visualizer.update_plot()

    def format_and_print_message(self, message: str, sender: str) -> None:
        """
        Format and print a message to the console.

        Args:
            message (str): The message to print.
            sender (str): The sender of the message.
        """
        if sender in AI_PERSONALITIES:
            color = AI_PERSONALITIES[sender]['color']
        elif sender in HELPER_PERSONALITIES:
            color = HELPER_PERSONALITIES[sender]['color']
        else:
            color = 'white'

        formatted_message = f"[bold {color}]{sender}:[/bold {color}] {message}"
        self.console.print(formatted_message)

    def get_conversation_summary(self) -> str:
        """
        Get a summary of the current conversation.

        Returns:
            str: A summary of the conversation.
        """
        if not self.current_thread_id or self.current_thread_id not in self.conversation_history:
            return "No active conversation."

        messages = self.conversation_history[self.current_thread_id]
        summary = f"Conversation summary (Thread ID: {self.current_thread_id}):\n"
        for msg in messages:
            summary += f"{msg['sender']}: {msg['message'][:50]}...\n"
        return summary

    def get_token_usage(self) -> Dict[str, int]:
        """
        Get the current token usage statistics.

        Returns:
            Dict[str, int]: A dictionary containing token usage statistics.
        """
        return {
            "context_tokens": self.context_token_count,
            "response_tokens": self.response_token_count,
            "total_tokens": self.total_tokens
        }

    def set_visualizer(self, visualizer: VectorGraphVisualizer) -> None:
        """
        Set the visualizer for the conversation manager.

        Args:
            visualizer (VectorGraphVisualizer): The visualizer to use.
        """
        self.visualizer = visualizer
        self.logger.debug("Visualizer set for ConversationManager")

    def set_console(self, console) -> None:
        """
        Set the console for the conversation manager.

        Args:
            console: The console to use for output.
        """
        self.console = console
        self.logger.debug("Console set for ConversationManager")

    def __del__(self):
        """
        Clean up resources when the ConversationManager is destroyed.
        """
        try:
            self.save_conversation_history()
            self.logger.debug("ConversationManager destroyed, conversation history saved")
        except Exception as e:
            self.logger.error(f"Error in ConversationManager destructor: {str(e)}")

        # Use asyncio.run to close the session in the destructor
        if hasattr(self, 'session') and self.session and not self.session.closed:
            asyncio.run(self.close_session())
