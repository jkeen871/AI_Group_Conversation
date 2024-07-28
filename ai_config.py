import anthropic
import openai
import google.generativeai as genai
import json
import datetime
import logging
import os
import traceback
import asyncio
from typing import AsyncGenerator
from keys import anthropic_key, openai_key, gemini_key

# Get the logger
logger = logging.getLogger(__name__)

# Configure Google Generative AI
genai.configure(api_key=gemini_key)

# Configure OpenAI
openai.api_key = openai_key

# Configure Anthropic
anthropic_client = anthropic.AsyncAnthropic(api_key=anthropic_key)

def log_ai_error(ai_name: str, error_message: str):
    """
    Logs an AI-related error message and traceback.

    Args:
        ai_name (str): The name of the AI service (e.g., 'Anthropic', 'Google Generative AI', 'OpenAI').
        error_message (str): The error message to log.
    """
    log_entry = {
        'timestamp': datetime.datetime.now().isoformat(),
        'ai_name': ai_name,
        'error_message': error_message,
        'traceback': traceback.format_exc()
    }
    logger.error(f"AI Error - {ai_name}: {error_message}\n{log_entry['traceback']}")

async def anthropic_generate(model: str, prompt: str) -> AsyncGenerator[str, None]:
    try:
        async with anthropic_client.messages.stream(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            async for text in stream.text_stream:
                yield text
    except Exception as e:
        error_message = f"Error generating Anthropic response: {e}"
        log_ai_error('Anthropic', error_message)
        logger.error(error_message)
        yield "Anthropic is not available now."

async def openai_generate(model: str, prompt: str) -> AsyncGenerator[str, None]:
    try:
        async for chunk in await openai.ChatCompletion.acreate(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        ):
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content
    except Exception as e:
        error_message = f"Error generating OpenAI response: {e}"
        log_ai_error('OpenAI', error_message)
        logger.error(error_message)
        yield "OpenAI is not available now."

async def genai_generate(model: str, prompt: str) -> AsyncGenerator[str, None]:
    try:
        genai_model = genai.GenerativeModel(model)
        response = await genai_model.generate_content_async(prompt, stream=True)
        async for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        error_message = f"Error generating Google Generative AI response: {e}"
        log_ai_error('Google Generative AI', error_message)
        logger.error(error_message)
        yield "Google Generative AI is not available now."

AI_CONFIG = {
    "anthropic": {
        "model": "claude-3-opus-20240229",
        "generate_func": anthropic_generate,
    },
    "openai": {
        "model": "gpt-4o",
        "generate_func": openai_generate,
    },
    "genai": {
        "model": "gemini-pro",
        "generate_func": genai_generate,
    },
}