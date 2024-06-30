# AI Conversation CLI Detailed Technical Documentation

## Project Overview

The AI Conversation CLI is an interactive command-line application that facilitates conversations with multiple AI personalities using advanced language models. It manages complex conversation flows and provides a rich user interface for interacting with AI agents.

## Project Structure

The project consists of the following Python files:

1. `convo.py`: Main entry point of the application
2. `conversation_manager.py`: Manages conversation history and AI interactions
3. `ai_conversation_cli.py`: Handles the command-line interface and user interactions
4. `personalities.py`: Defines AI personalities and their characteristics
5. `ai_config.py`: Configuration for AI models and related settings

## File Dependencies

### convo.py
- Imports:
  - `asyncio`: For asynchronous programming
  - `logging`: For application-wide logging
  - `os`: For system operations (clearing screen)
  - `typing`: For type hinting
  - `ConversationManager` from `conversation_manager.py`
  - `AIConversationCLI` from `ai_conversation_cli.py`

### conversation_manager.py
- Imports:
  - `asyncio`: For asynchronous programming
  - `json`: For reading/writing conversation history
  - `logging`: For logging operations
  - `random`: For randomizing participant order
  - `re`: For regular expressions in response extraction
  - `typing`: For type hinting
  - `AI_PERSONALITIES`, `HELPER_PERSONALITIES`, `MASTER_SYSTEM_MESSAGE` from `personalities.py`
  - `AI_CONFIG`, `log_ai_error` from `ai_config.py`
  - Various classes from `rich` for formatted console output

### ai_conversation_cli.py
- Imports:
  - `cmd2`: For building the interactive CLI
  - `asyncio`: For asynchronous programming
  - `logging`: For logging operations
  - `tracemalloc`: For memory debugging
  - `ConversationManager` from `conversation_manager.py`
  - Various classes from `rich` for formatted console output
  - `AI_PERSONALITIES` from `personalities.py`
  - `ainput` from `aioconsole` (with fallback to asyncio.run(input))

## Module Dependencies

- Python Standard Library:
  - `asyncio`
  - `json`
  - `logging`
  - `os`
  - `random`
  - `re`
  - `typing`
  - `tracemalloc`

- Third-party Libraries:
  - `cmd2`: For creating interactive command-line applications
  - `rich`: For rich text and beautiful formatting in the terminal
  - `aioconsole`: For asynchronous console input (optional)
  - AI model specific libraries:
    - `openai`: For OpenAI GPT models
    - `anthropic`: For Anthropic's Claude model

## Configuration and Security Files

The project uses several configuration files to manage API keys, tokens, and credentials. These files are crucial for securely connecting to various AI services and should be handled with care.

### keys.py

This file is used to store API keys and other sensitive configuration data.

#### Purpose:
- Store API keys for various AI services (e.g., OpenAI, Anthropic)
- Keep sensitive configuration data separate from the main code

#### Structure:
Create this file in the project root directory with the following structure:

```python
# keys.py

OPENAI_API_KEY = "your_openai_api_key_here"
ANTHROPIC_API_KEY = "your_anthropic_api_key_here"

# Add any other API keys or sensitive configuration data here
```

#### Usage:
In your main code (e.g., ai_config.py), import and use these keys:

```python
from keys import OPENAI_API_KEY, ANTHROPIC_API_KEY

# Use the keys when initializing AI clients
openai.api_key = OPENAI_API_KEY
anthropic.api_key = ANTHROPIC_API_KEY
```

### token.json

This file is typically used for storing authentication tokens, often for OAuth 2.0 flows or similar authentication mechanisms.

#### Purpose:
- Store refresh tokens or access tokens for APIs that use token-based authentication
- Allow the application to maintain authentication between sessions

#### Structure:
Create this file in the project root directory with the following structure (example for OAuth 2.0):

```json
{
  "access_token": "your_access_token_here",
  "refresh_token": "your_refresh_token_here",
  "token_type": "Bearer",
  "expires_at": 1234567890
}
```

#### Usage:
In your code, you would typically read this file, check if the token is still valid, and refresh it if necessary:

```python
import json
from datetime import datetime, timedelta

def get_valid_token():
    with open('token.json', 'r') as token_file:
        token_data = json.load(token_file)
    
    if datetime.fromtimestamp(token_data['expires_at']) < datetime.now():
        # Implement token refresh logic here
        pass
    
    return token_data['access_token']
```

### credentials.json

This file is often used to store client credentials for OAuth 2.0 or similar authentication flows.

#### Purpose:
- Store client ID, client secret, and other credentials required for authenticating with certain APIs
- Keep these credentials separate from the main code for security reasons

#### Structure:
Create this file in the project root directory with the following structure:

```json
{
  "client_id": "your_client_id_here",
  "client_secret": "your_client_secret_here",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
}
```

#### Usage:
In your code, you would typically read this file when setting up OAuth flows:

```python
import json

def get_credentials():
    with open('credentials.json', 'r') as cred_file:
        return json.load(cred_file)

# Use these credentials when setting up OAuth client
credentials = get_credentials()
oauth_client = SomeOAuthClient(
    client_id=credentials['client_id'],
    client_secret=credentials['client_secret']
)
```

## Security Considerations for Configuration Files

1. **Never commit these files to version control:** Add them to your .gitignore file to prevent accidental commits.
2. **Use environment variables:** For production or shared environments, consider using environment variables instead of files to store sensitive data.
3. **Implement proper file permissions:** Ensure these files have restricted read/write permissions on the server.
4. **Encryption:** Consider encrypting the contents of these files for an added layer of security.
5. **Regular rotation:** Implement a policy to regularly rotate API keys and update these files.
6. **Separate configurations:** Use different keys/credentials for development, staging, and production environments.

## Detailed File Descriptions

### convo.py

Main script that initializes and runs the application.

#### Key Functions:
- `setup_logging()`: Configures logging for the entire application
- `run_application()`: Initializes AIConversationCLI and ConversationManager, runs the main application loop
- `main()`: Entry point of the application

### conversation_manager.py

Contains the ConversationManager class, which handles conversation logic and history.

#### Key Methods:
- `load_conversation_history()`: Loads conversation history from a JSON file
- `save_conversation_history()`: Saves conversation history to a JSON file
- `update_conversation()`: Adds a new message to the conversation history
- `format_and_print_message()`: Formats and displays messages in the console
- `get_conversation_context()`: Retrieves the current conversation context
- `generate_ai_response()`: Generates an AI response for a given prompt
- `extract_ai_response()`: Extracts the AI's response from the full response string
- `generate_single_response()`: Generates and processes a single AI response
- `display_thinking_message()`: Shows a "thinking" message while generating a response
- `detect_addressed_participant()`: Detects which participant a message is addressed to
- `randomize_participants()`: Randomizes the order of AI participants
- `generate_ai_conversation()`: Orchestrates a full AI conversation based on a prompt
- `generate_moderator_summary()`: Generates a summary of the conversation by a moderator AI

### ai_conversation_cli.py

Contains the AIConversationCLI class, which manages the command-line interface and user interactions.

#### Key Methods:
- `run()`: Main method to run the application
- `cleanup()`: Performs cleanup operations before exiting
- `get_user_input()`: Gets user input asynchronously
- `cmdloop_async()`: Asynchronous version of cmd2's command loop
- `onecmd_async()`: Processes a single command asynchronously
- `ai_conversation_loop()`: Main loop for processing user input and generating AI responses
- `process_input()`: Handles user input and generates AI responses
- `handle_command()`: Processes system commands (starting with '!')
- `show_conversation_history()`: Displays the conversation history
- Various `do_*` methods: Handle specific CLI commands (e.g., `do__quit`, `do__help`, `do__switch_thread`, `do__list_threads`, `do__clear`)

### personalities.py

Defines AI personalities and their characteristics.

#### Key Components:
- `AI_PERSONALITIES`: Dictionary defining main AI personalities
- `HELPER_PERSONALITIES`: Dictionary defining helper AI personalities (e.g., moderator, response detector)
- `MASTER_SYSTEM_MESSAGE`: Dictionary containing the master system message for AI interactions

### ai_config.py

Configuration for AI models and related settings.

#### Key Components:
- `AI_CONFIG`: Dictionary containing configurations for different AI models
- `log_ai_error()`: Function to log AI-specific errors
- AI model-specific configuration and functions

## Creating and Configuring Dependent Files

### personalities.py

Create this file in the project root directory with the following structure:

```python
AI_PERSONALITIES = {
    "PersonalityName": {
        "ai_name": "ModelName",
        "color": "ColorName",
        "system_message": "Personality description and instructions"
    },
    # Add more personalities as needed
}

HELPER_PERSONALITIES = {
    "Moderator": {
        "ai_name": "ModelName",
        "color": "yellow",
        "system_message": "Moderator instructions"
    },
    "ResponseDetector": {
        "ai_name": "ModelName",
        "system_message": "Instructions for detecting addressed participants"
    }
}

MASTER_SYSTEM_MESSAGE = {
    "system_message": "Master instructions for all AI interactions"
}
```

### ai_config.py

Create this file in the project root directory with the following structure:

```python
import logging
# Import necessary AI model libraries (e.g., openai, anthropic)

AI_CONFIG = {
    "ModelName": {
        "model": "model_identifier",
        "generate_func": async_generation_function
    },
    # Add configurations for other models
}

def log_ai_error(ai_name: str, error_message: str):
    logging.error(f"AI Error ({ai_name}): {error_message}")

# Define async generation functions for each AI model
async def openai_generate(model: str, prompt: str):
    # Implementation for OpenAI model generation
    pass

async def anthropic_generate(model: str, prompt: str):
    # Implementation for Anthropic model generation
    pass

# Add the generation functions to the AI_CONFIG
AI_CONFIG["gpt4"]["generate_func"] = openai_generate
AI_CONFIG["claude"]["generate_func"] = anthropic_generate
```

## Setup and Running the Application

1. Ensure all required Python libraries are installed:
   ```
   pip install cmd2 rich openai anthropic aioconsole
   ```

2. Create and configure `personalities.py` and `ai_config.py` as described in the "Creating and Configuring Dependent Files" section.

3. Set up any necessary environment variables or API keys for the AI models.

4. Run the application using:
   ```
   python convo.py
   ```

## Error Handling and Logging

- Comprehensive error handling is implemented throughout the application.
- Detailed logging is set up in `convo.py` and used across all files.
- Logs are written to 'log/convo.log' for debugging and troubleshooting.

## Extending the Application

To add new features or AI personalities:

1. Update the `AI_PERSONALITIES` dictionary in `personalities.py`.
2. Add new AI model configurations in `ai_config.py` if necessary.
3. Implement new command handlers in the AIConversationCLI class in `ai_conversation_cli.py`.
4. Extend the ConversationManager class in `conversation_manager.py` for new conversation management features.

## Testing

- Implement unit tests for individual components (e.g., ConversationManager methods, AIConversationCLI commands).
- Create integration tests to ensure proper interaction between different modules.
- Perform end-to-end testing of the entire conversation flow.

## Performance Considerations

- The application uses asynchronous programming to handle concurrent operations efficiently.
- Consider implementing caching mechanisms for frequently accessed data or AI responses.
- Monitor and optimize AI model API usage to manage costs and improve response times.

## Security Considerations

- Ensure proper handling and storage of API keys and sensitive configuration data.
- Implement input validation and sanitization to prevent potential security vulnerabilities.
- Consider implementing user authentication if extending the application for multi-user scenarios.

## Additional Notes

- The application uses the `rich` library for enhanced console output, including colored text, panels, and progress spinners.
- The `aioconsole` library is used for asynchronous console input, with a fallback to synchronous input if not available.
- Memory tracking is implemented using `tracemalloc` for debugging purposes.
- The application supports multiple conversation threads and allows switching between them.
- A moderator AI can generate summaries of the conversation.