# AI Conversation GUI Application

## Table of Contents
1. [Project Overview](#1-project-overview)
2. [Screenshots](#2-screenshots)
3. [Features](#3-features)
4. [Project Structure](#4-project-structure)
5. [Configuration Files](#5-configuration-files)
6. [GUI Features](#6-gui-features)
7. [Setup and Installation](#7-setup-and-installation)
8. [Running the Application](#8-running-the-application)
9. [Adding and Editing Personalities](#9-adding-and-editing-personalities)
   - [Using the GUI](#using-the-gui)
   - [Editing Files Manually](#editing-files-manually)
   - [Personality Setup Examples](#personality-setup-examples)
10. [Extending the Application](#10-extending-the-application)
11. [Error Handling and Logging](#11-error-handling-and-logging)
12. [Testing](#12-testing)
13. [Performance Considerations](#13-performance-considerations)
14. [Security Considerations](#14-security-considerations)
15. [Developer Information](#15-developer-information)

## 1. Project Overview
The AI Conversation GUI Application is an advanced, interactive graphical user interface that facilitates conversations with multiple AI personalities using state-of-the-art language models. It manages complex conversation flows, provides a rich visual interface for user interactions, and offers various features for customization and analysis of AI-driven conversations.

## 2. Screenshots
![AI Conversation Interface](https://github.com/jkeen871/AI_Group_Conversation/blob/master/screenshots/Screenshot%20from%202024-07-29%2012-22-22.png)
![AI Conversation Interface](https://github.com/jkeen871/AI_Group_Conversation/blob/master/screenshots/Screenshot%20from%202024-07-28%2015-59-26.png)
![AI Conversation Interface](https://github.com/jkeen871/AI_Group_Conversation/blob/master/screenshots/Screenshot%20from%202024-07-28%2015-59-48.png)

## 3. Features
- Multi-AI personality conversations
- Real-time conversation visualization
- Customizable user interface
- Conversation history management
- Topic generation and tracking
- Moderator summaries
- Email integration for sharing conversations
- Extensible AI configurations
- Advanced error handling and logging
- GUI for editing AI personalities and configurations

## 4. Project Structure
The project consists of the following key Python files:

- `convo.py`: Main entry point of the application
- `convo_gui.py`: Contains the AIConversationGUI class for the graphical interface
- `conversation_manager.py`: Manages conversation history and AI interactions
- `personalities.py`: Defines AI personalities and their characteristics
- `ai_config.py`: Configuration for AI models and related settings
- `ConversationHistoryWindow.py`: Manages the conversation history display
- `EditPersonalities.py`: GUI for editing AI personalities
- `EditAIConfigs.py`: GUI for editing AI configurations
- `EditHelperPersonalities.py`: GUI for editing helper personalities
- `Visualizer.py`: Handles visualization of conversation data
- `ConversationRAG.py`: Implements the Retrieval-Augmented Generation system
- `schema.py`: Defines data structures for conversation history
- `google_api.py`: Handles Google API integration for email functionality
- `ApplicationContext.py`: Manages global application context and cleanup
- `ai_conversation_cli.py`: Command-line interface for the application
- `requirements.txt`: Lists all required Python packages

## 5. Configuration Files
The application uses several configuration files to manage settings and data:

### keys.py
Stores API keys for various AI services:
```python
openai_key = "your_openai_api_key_here"
gemini_key = "your_gemini_api_key_here"
anthropic_key = "your_anthropic_api_key_here"
```

### gui_config.json
Stores user preferences for the GUI:
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
Stores the conversation history:
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

### credentials.json and token.json
These files are used for Google API authentication for email functionality.

## 6. GUI Features
The application offers a rich set of GUI features:

- **Multi-pane Interface**: Main conversation display, participant selection, and control panel
- **Conversation Display**: Shows messages from all participants with color-coding
- **Participant Selection**: Allows users to choose which AI personalities to include in the conversation
- **Control Panel**: Provides buttons for various functions like changing fonts, colors, and accessing different features
- **New Topic Generation**: Allows starting a new conversation topic
- **Moderator Summaries**: Generates summaries of the current conversation
- **Conversation History**: Displays past conversations with search and filter capabilities
- **Email Integration**: Allows sending conversation summaries via email
- **Personality Editing**: GUI for customizing AI personalities and their characteristics
- **AI Configuration Editing**: Interface for modifying AI model configurations
- **Helper Personality Editing**: Customization of special helper AIs like the topic generator and moderator
- **Real-time Visualization**: Dynamic graph showing the relationships between conversation topics and participants
- **Token Usage Display**: Shows the current token usage for API calls
- **Theme Customization**: Allows changing fonts, colors, and overall theme of the application

## 7. Setup and Installation
1. Clone the repository:
   ```
   git clone https://github.com/jkeen871/ai-conversation-gui.git
   cd ai-conversation-gui
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up API keys in `keys.py`.

4. Configure Google API credentials for email functionality.

## 8. Running the Application
Run the application using:
```
python convo.py
```

## 9. Adding and Editing Personalities

### Using the GUI
1. **For AI Personalities:**
   - Click on the "Edit AI Personalities" button in the control panel.
   - In the new window, click "Add New Personality" to create a new AI personality.
   - Fill in the details: Name, System Message, AI Name (model), and Color.
   - Click "Save Changes" to add the new personality.

2. **For Helper Personalities:**
   - Click on the "Edit Helper Personalities" button in the control panel.
   - Follow a similar process as AI personalities to add or edit helper personalities.

3. **For AI Configurations:**
   - Click on the "Edit AI Configs" button to modify AI model settings.

### Editing Files Manually
You can also add or edit personalities by directly modifying the `personalities.py` file:

1. Open `personalities.py` in a text editor.
2. Locate the `AI_PERSONALITIES` or `HELPER_PERSONALITIES` dictionary.
3. Add a new entry or modify an existing one.

### Personality Setup Examples

1. **AI Personality Example:**
```python
"Dyann": {
    "name": "Dyann",
    "system_message": "You are Dyann, a conservative-leaning AI with expertise in interior design and ancient history...",
    "ai_name": "anthropic",
    "color": "blue",
    "character": "𝍄"
},
```

2. **Helper Personality Example:**
```python
"TopicGenerator": {
    "name": "TopicGenerator",
    "system_message": "You are the TopicGenerator. Your task is to generate a short, concise topic based on the conversation context provided...",
    "ai_name": "anthropic",
    "color": "cyan",
},
```

3. **AI Configuration Example:**
```python
"anthropic": {
    "model": "claude-3-opus-20240229",
    "generate_func": anthropic_generate,
},
```

When adding personalities manually, ensure that you follow the existing structure and include all necessary fields. After making changes, restart the application for them to take effect.

## 10. Extending the Application
To add new features or AI personalities:

1. Update `AI_PERSONALITIES` or `HELPER_PERSONALITIES` in `personalities.py`.
2. Add new AI model configurations in `ai_config.py` if necessary.
3. Implement new UI components in `convo_gui.py`.
4. Extend the `ConversationManager` class in `conversation_manager.py` for new conversation management features.
5. Update the various editing classes (`EditPersonalities`, `EditAIConfigs`, `EditHelperPersonalities`) to allow editing of new configurations through the GUI.

## 11. Error Handling and Logging
- Comprehensive error handling is implemented throughout the application.
- Detailed logging is set up in `convo.py` and used across all files.
- Logs are written to 'log/app.log' for debugging and troubleshooting.
- The GUI displays error messages to the user when appropriate.

## 12. Testing
- Implement unit tests for individual components (e.g., ConversationManager methods, AIConversationGUI methods).
- Create integration tests to ensure proper interaction between different modules.
- Perform end-to-end testing of the entire conversation flow through the GUI.
- Use PyQt's testing utilities for GUI-specific tests.

## 13. Performance Considerations
- The application uses asynchronous programming to handle concurrent operations efficiently.
- Consider implementing caching mechanisms for frequently accessed data or AI responses.
- Monitor and optimize AI model API usage to manage costs and improve response times.
- Use PyQt's built-in optimization techniques, such as lazy loading for UI components.

## 14. Security Considerations
- Ensure proper handling and storage of API keys and sensitive configuration data.
- Implement input validation and sanitization to prevent potential security vulnerabilities.
- Consider implementing user authentication if extending the application for multi-user scenarios.
- Use secure methods for storing and retrieving user preferences and conversation history.

## 15. Developer Information
- **Name**: Jerry Keen
- **Contact Email**: jkeen871@gmail.com

For any questions, suggestions, or contributions, please feel free to contact the developer.
