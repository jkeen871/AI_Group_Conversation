import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import re


class ConversationRAG:
    def __init__(self, max_history=1000):
        self.vectorizer = TfidfVectorizer(token_pattern=r'\b\w+\b')
        self.conversation_history = []
        self.word_history = []
        self.vector_history = None
        self.max_history = max_history
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("ConversationRAG initialized with max_history=%d", max_history)

    def _update_vectors(self):
        try:
            if self.word_history:
                self.vector_history = self.vectorizer.fit_transform(self.word_history)
                self.logger.debug("Vector history updated successfully")
            else:
                self.vector_history = None
                self.logger.debug("Vector history set to None (empty conversation)")
        except Exception as e:
            self.logger.error("Error updating vectors: %s", str(e), exc_info=True)
            self.vector_history = None

    def add_message(self, message: str):
        self.conversation_history.append(message)
        words = re.findall(r'\b\w+\b', message.lower())
        self.word_history.extend(words)
        if len(self.word_history) > self.max_history:
            excess = len(self.word_history) - self.max_history
            self.word_history = self.word_history[excess:]
            while len(' '.join(self.conversation_history)) > len(' '.join(self.word_history)):
                self.conversation_history.pop(0)
        self._update_vectors()
        self.logger.debug(f"Added message to RAG. Current word history size: {len(self.word_history)}")

    def get_recent_messages(self, n: int) -> str:
        return "\n".join(self.conversation_history[-n:])

    def get_relevant_history(self, query: str, top_k: int = 5) -> str:
        self.logger.debug(f"Getting relevant history for query: {query[:50]}...")
        if not self.word_history:
            self.logger.info("Word history in RAG is empty")
            return ""

        if self.vector_history is None:
            self.logger.warning("Vector history is None, returning recent conversation history")
            return self.get_recent_messages(top_k)

        try:
            query_words = re.findall(r'\b\w+\b', query.lower())
            query_vector = self.vectorizer.transform(query_words)
            similarities = cosine_similarity(query_vector, self.vector_history).flatten()

            # Get top_k unique indices, sorted by similarity
            unique_indices = sorted(set(range(len(similarities))), key=lambda i: similarities[i], reverse=True)[:top_k]

            # Map word indices to full messages
            relevant_messages = set()
            word_count = 0
            for idx in unique_indices:
                for i, msg in enumerate(self.conversation_history):
                    msg_words = re.findall(r'\b\w+\b', msg.lower())
                    if word_count + len(msg_words) > idx:
                        relevant_messages.add(msg)
                        break
                    word_count += len(msg_words)

            self.logger.debug(f"Retrieved {len(relevant_messages)} relevant historical messages from RAG")
            return "\n".join(relevant_messages)
        except Exception as e:
            self.logger.error(f"Error retrieving relevant history from RAG: {str(e)}", exc_info=True)
            return self.get_recent_messages(top_k)

    def clear(self):
        self.logger.debug("Clearing RAG database")
        try:
            self.conversation_history.clear()
            self.word_history.clear()
            self.vector_history = None
            self.vectorizer = TfidfVectorizer(token_pattern=r'\b\w+\b')
            self.logger.info("RAG database cleared successfully")
        except Exception as e:
            self.logger.error(f"Error clearing RAG database: {str(e)}", exc_info=True)
            raise
