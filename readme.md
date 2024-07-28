# AI Conversation GUI Application Technical Documentation

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Screenshots](#2-screenshots)
3. [Interacting with the GUI](#3-interacting-with-the-gui)
4. [Sample Conversation](#4-sample-conversation)
5. [Project Structure](#5-project-structure)
6. [File Dependencies](#6-file-dependencies)
7. [Module Dependencies](#7-module-dependencies)
8. [Configuration and Security Files](#8-configuration-and-security-files)
9. [Detailed File Descriptions](#9-detailed-file-descriptions)
10. [Creating and Configuring Dependent Files](#10-creating-and-configuring-dependent-files)
11. [Setup and Running the Application](#11-setup-and-running-the-application)
12. [Error Handling and Logging](#12-error-handling-and-logging)
13. [Extending the Application](#13-extending-the-application)
14. [Testing](#14-testing)
15. [Performance Considerations](#15-performance-considerations)
16. [Security Considerations](#16-security-considerations)
17. [Additional Notes](#17-additional-notes)

## 1. Project Overview

The AI Conversation GUI Application is an interactive graphical user interface that facilitates conversations with multiple AI personalities using advanced language models. It manages complex conversation flows and provides a rich visual interface for interacting with AI agents.

## 2. Screenshots

![AI Conversation Interface](https://github.com/jkeen871/AI_Group_Conversation/blob/master/screenshots/Screenshot from 2024-07-28 15-58-16)
![AI Conversation Interface](https://github.com/jkeen871/AI_Group_Conversation/blob/master/screenshots/Screenshot from 2024-07-28 15-59-26)
![AI Conversation Interface](https://github.com/jkeen871/AI_Group_Conversation/blob/master/screenshots/Screenshot from 2024-07-28 15-59-48)
![AI Conversation Interface](https://github.com/jkeen871/AI_Group_Conversation/blob/master/screenshots/Screenshot from 2024-07-28 16-02-04)

## 3. Interacting with the GUI

To interact with the AI personalities using the GUI:

1. Launch the application.
2. Select the desired AI participants from the list on the right side of the interface.
3. Enter your message in the input area at the bottom of the screen.
4. Click the "Send" button or press Enter to submit your message.
5. The AI responses will appear in the main conversation display.

You can also use the following features:
- Click "New Topic" to start a fresh conversation.
- Use "Get Moderator Summary" to generate an overview of the current conversation.
- Adjust the font, colors, and other display settings using the buttons on the right panel.
- View conversation history by clicking "View Conversation History".

## 4. Sample Conversation

[Include a sample conversation demonstrating the GUI interaction, possibly with screenshots or a step-by-step walkthrough of a conversation flow.]

## 5. Project Structure

The project consists of the following Python files:

1. `convo.py`: Main entry point of the application
2. `convo_gui.py`: Contains the AIConversationGUI class for the graphical interface
3. `conversation_manager.py`: Manages conversation history and AI interactions
4. `personalities.py`: Defines AI personalities and their characteristics
5. `ai_config.py`: Configuration for AI models and related settings
6. `ConversationHistoryWindow.py`: Manages the conversation history display
7. `EditPersonalities.py`: GUI for editing AI personalities
8. `EditAIConfigs.py`: GUI for editing AI configurations
9. `EditHelperPersonalities.py`: GUI for editing helper personalities
10. `Visualizer.py`: Handles visualization of conversation data
11. `ConversationRAG.py`: Implements the Retrieval-Augmented Generation system
12. `schema.py`: Defines data structures for conversation history

## 6. File Dependencies

### convo.py
- Imports:
  - `logging`: For application-wide logging
  - `os`: For system operations
  - `sys`: For system-specific parameters and functions
  - `argparse`: For parsing command-line arguments
  - `asyncio`: For asynchronous programming
  - `QApplication` from `PyQt5.QtWidgets`: For creating the GUI application
  - `AIConversationGUI` from `convo_gui`: The main GUI class

### convo_gui.py
- Imports:
  - Various PyQt5 modules for GUI components
  - `logging`: For logging operations
  - `json`: For handling configuration files
  - `ConversationManager` from `conversation_manager`: For managing conversations
  - `AI_PERSONALITIES`, `USER_IDENTITY` from `personalities`: For AI and user data
  - `VectorGraphVisualizer` from `Visualizer`: For graph visualization
  - `ConversationHistoryWindow` from `ConversationHistoryWindow`: For displaying conversation history
  - `EditPersonalities`, `EditAIConfigs`, `EditHelperPersonalities`: For editing various configurations

### conversation_manager.py
- Imports:
  - `logging`, `json`, `random`, `asyncio`, `datetime`: For various utilities
  - `AI_PERSONALITIES`, `HELPER_PERSONALITIES`, `MASTER_SYSTEM_MESSAGE`, `USER_IDENTITY` from `personalities`
  - `AI_CONFIG`, `log_ai_error` from `ai_config`
  - `ConversationRAG` from `ConversationRAG`: For the Retrieval-Augmented Generation system
  - `VectorGraphVisualizer` from `Visualizer`: For graph visualization

## 7. Module Dependencies

- Python Standard Library:
  - `logging`
  - `json`
  - `os`
  - `sys`
  - `asyncio`
  - `datetime`
  - `re`
  - `random`

- Third-party Libraries:
  - `PyQt5`: For creating the graphical user interface
  - `aiohttp`: For asynchronous HTTP requests
  - `tiktoken`: For token counting
  - `numpy`: For numerical operations
  - `sklearn`: For machine learning utilities (used in ConversationRAG)
  - `matplotlib`: For plotting in the Visualizer

- AI model specific libraries:
  - `openai`: For OpenAI GPT models
  - `anthropic`: For Anthropic's Claude model
  - `google.generativeai`: For Google's generative AI models

## 8. Configuration and Security Files

The project uses several configuration files to manage API keys, user preferences, and application settings.

### keys.py

This file stores API keys for various AI services.

#### Structure:
```python
openai_key = "your_openai_api_key_here"
gemini_key = "your_gemini_api_key_here"
anthropic_key = "your_anthropic_api_key_here"
```

### gui_config.json

This file stores user preferences for the GUI.

#### Structure:
```json
{
  "font_family": "Arial",
  "font_size": 12,
  "user_color": "#58a6ff",
  "ai_color": "#58a6ff",
  "system_color": "#7ee787",
  "conversation_font_color": "#c9d1d9",
  "conversation_background_color": "#0d1117"
}
```

### conversation_history.json

This file stores the conversation history.

#### Structure:
```json
{
  "thread_id": {
    "date": "YYYY-MM-DD HH:MM:SS",
    "topic": "Conversation Topic",
    "messages": [
      {
        "sender": "Participant Name",
        "message": "Message content",
        "ai_name": "AI Model Name",
        "model": "Model Identifier",
        "is_partial": false,
        "is_divider": false,
        "timestamp": "YYYY-MM-DDTHH:MM:SS.mmmmmm"
      }
    ]
  }
}
```

## 9. Detailed File Descriptions

### convo.py

Main script that initializes and runs the GUI application.

#### Key Functions:
- `setup_logging()`: Configures logging for the entire application
- `run_gui_application()`: Initializes and runs the GUI application
- `main()`: Entry point of the application, handles command-line arguments

### convo_gui.py

Contains the AIConversationGUI class, which manages the main application window and user interactions.

#### Key Methods:
- `__init__()`: Initializes the GUI components and loads configurations
- `init_ui()`: Sets up the main user interface
- `setup_right_panel_controls()`: Creates control buttons and displays
- `setup_multiline_input()`: Sets up the user input area
- `on_send_button_clicked()`: Handles sending user messages
- `append_message()`: Adds messages to the conversation display
- `update_conversation_window()`: Updates the conversation display with new messages
- `generate_moderator_summary()`: Generates and displays a summary of the conversation
- `new_topic()`: Starts a new conversation topic
- `open_history_window()`: Opens the conversation history window
- Various methods for handling UI events and updating the display

### conversation_manager.py

Contains the ConversationManager class, which handles conversation logic and AI interactions.

#### Key Methods:
- `generate_ai_conversation()`: Orchestrates a full AI conversation based on a prompt
- `generate_single_response()`: Generates and processes a single AI response
- `continue_conversation()`: Continues an existing conversation with new input
- `generate_moderator_summary()`: Generates a summary of the conversation
- `new_topic()`: Initializes a new conversation topic
- `update_conversation()`: Adds a new message to the conversation history
- `get_conversation_context()`: Retrieves the current conversation context
- Various helper methods for managing conversation flow and AI interactions

## 10. Creating and Configuring Dependent Files

### personalities.py

Create this file in the project root directory with the following structure:

```python
AI_PERSONALITIES = {
    "PersonalityName": {
        "name": "PersonalityName",
        "system_message": "Personality description and instructions",
        "ai_name": "ModelName",
        "color": "ColorHexCode",
        "character": "EmojiOrSymbol"
    },
    # Add more personalities as needed
}

HELPER_PERSONALITIES = {
    "HelperName": {
        "name": "HelperName",
        "system_message": "Helper instructions",
        "ai_name": "ModelName",
        "color": "ColorHexCode"
    },
    # Add more helper personalities as needed
}

MASTER_SYSTEM_MESSAGE = {
    "system_message": "Master instructions for all AI interactions"
}

USER_IDENTITY = {
    'UserName': {'greeting': 'Welcome message'}
}
```

### ai_config.py

Create this file in the project root directory with the following structure:

```python
import anthropic
import openai
import google.generativeai as genai
from keys import anthropic_key, openai_key, gemini_key

# Configure AI services
genai.configure(api_key=gemini_key)
openai.api_key = openai_key
anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_key)

# Define async generation functions for each AI model
async def anthropic_generate(model: str, prompt: str):
    # Implementation for Anthropic model generation
    pass

async def openai_generate(model: str, prompt: str):
    # Implementation for OpenAI model generation
    pass

async def genai_generate(model: str, prompt: str):
    # Implementation for Google's generative AI model generation
    pass

AI_CONFIG = {
    "anthropic": {
        "model": "claude-3-opus-20240229",
        "generate_func": anthropic_generate,
    },
    "openai": {
        "model": "gpt-4",
        "generate_func": openai_generate,
    },
    "genai": {
        "model": "gemini-pro",
        "generate_func": genai_generate,
    },
}

def log_ai_error(ai_name: str, error_message: str):
    # Implementation for logging AI-specific errors
    pass
```

## 11. Setup and Running the Application

1. Ensure all required Python libraries are installed:
   ```
   pip install PyQt5 aiohttp tiktoken numpy scikit-learn matplotlib openai anthropic google-generativeai
   ```

2. Create and configure `personalities.py`, `ai_config.py`, and `keys.py` as described in the "Creating and Configuring Dependent Files" section.

3. Run the application using:
   ```
   python convo.py -g
   ```

## 12. Error Handling and Logging

- Comprehensive error handling is implemented throughout the application.
- Detailed logging is set up in `convo.py` and used across all files.
- Logs are written to 'log/app.log' for debugging and troubleshooting.
- The GUI displays error messages to the user when appropriate.

## 13. Extending the Application

To add new features or AI personalities:

1. Update the `AI_PERSONALITIES` or `HELPER_PERSONALITIES` dictionary in `personalities.py`.
2. Add new AI model configurations in `ai_config.py` if necessary.
3. Implement new UI components or functionality in the AIConversationGUI class in `convo_gui.py`.
4. Extend the ConversationManager class in `conversation_manager.py` for new conversation management features.
5. Update the EditPersonalities, EditAIConfigs, or EditHelperPersonalities classes to allow editing of new configurations through the GUI.

## 14. Testing

- Implement unit tests for individual components (e.g., ConversationManager methods, AIConversationGUI methods).
- Create integration tests to ensure proper interaction between different modules.
- Perform end-to-end testing of the entire conversation flow through the GUI.
- Use PyQt's testing utilities for GUI-specific tests.

## 15. Performance Considerations

- The application uses asynchronous programming to handle concurrent operations efficiently.
- Consider implementing caching mechanisms for frequently accessed data or AI responses.
- Monitor and optimize AI model API usage to manage costs and improve response times.
- Use PyQt's built-in optimization techniques, such as lazy loading for UI components.

## 16. Security Considerations

- Ensure proper handling and storage of API keys and sensitive configuration data.
- Implement input validation and sanitization to prevent potential security vulnerabilities.
- Consider implementing user authentication if extending the application for multi-user scenarios.
- Use secure methods for storing and retrieving user preferences and conversation history.

## 17. Additional Notes

- The application uses PyQt5 for creating a cross-platform graphical user interface.
- A vector graph visualization is implemented to represent the conversation flow and relationships between messages.
- The Retrieval-Augmented Generation (RAG) system is used to enhance AI responses with relevant context from the conversation history.
- The application supports multiple conversation threads and allows switching between them.
- Users can customize the appearance of the application, including fonts, colors, and themes.
- The conversation history can be viewed, summarized, and exported.
- AI personalities, configurations, and helper functions can be edited through dedicated GUI interfaces.
