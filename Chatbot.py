# chatbot.py

from langchain_chroma import Chroma
from langchain.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM
from get_embedding_function import get_embedding_function
from transformers import GPT2TokenizerFast  # Tokenizer for token counting

CHROMA_PATH = "chroma"
MAX_CONTEXT_TOKENS = 2048  # Set the max token length for context (adjust as needed)

PROMPT_TEMPLATE = """
Answer the question based only on the following context:

{context}

---

Answer the question based on the above context: {question}
"""

class Chatbot:
    def __init__(self):
        """
        Initialize the Chatbot with necessary components: 
        embedding function, vector database, language model, and cache.
        """
        self.embedding_function = get_embedding_function()
        self.db = Chroma(persist_directory=CHROMA_PATH, embedding_function=self.embedding_function)
        self.model = OllamaLLM(model="llama3.2")  # Specify model name
        self.prompt_template = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        
        # Initialize a cache to store previous responses
        self.cache = {}
        
        # Tokenizer for counting tokens
        self.tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")  # Adapt to model tokenizer

    def truncate_context(self, context: str) -> str:
        """
        Truncate context to fit within the max token limit.
        
        Args:
            context (str): The initial full context string.

        Returns:
            str: A truncated version of the context fitting within token limit.
        """
        tokens = self.tokenizer.encode(context)
        if len(tokens) <= MAX_CONTEXT_TOKENS:
            return context  # No need to cut if within limit
        
        # Truncate to fit within token limit
        truncated_tokens = tokens[:MAX_CONTEXT_TOKENS]
        truncated_context = self.tokenizer.decode(truncated_tokens)
        return truncated_context

    def query(self, query_text: str) -> dict:
        """
        Retrieves context from the vector store and generates an answer.
        
        Args:
            query_text (str): The query to retrieve context and generate an answer.

        Returns:
            dict: Contains the response text and list of sources as HTML links.
        """
        try:
            # Check if the response is already cached
            if query_text in self.cache:
                return self.cache[query_text]

            # Search the database for relevant documents
            results = self.db.similarity_search_with_score(query_text, k=5)
            
            if not results:
                return {"response": "No relevant documents found.", "sources": []}

            # Create context from the search results
            context_text = "\n\n---\n\n".join([doc.page_content for doc, _ in results])
            truncated_context = self.truncate_context(context_text)
            
            # Prepare the prompt with truncated context if necessary
            prompt = self.prompt_template.format(context=truncated_context, question=query_text)

            # Invoke the language model with the formatted prompt
            response_text = self.model.invoke(prompt)

            # Format sources as clickable links
            sources = [
                f'<a href="file://{doc.metadata.get("source")}" target="_blank">{doc.metadata.get("id")}</a>'
                for doc, _ in results if doc.metadata.get("id")
            ]

            response = {"response": response_text, "sources": sources}
            
            # Cache the response for future requests
            self.cache[query_text] = response
            
            return response
        
        except Exception as e:
            # Log the error message for troubleshooting
            print(f"Error in query: {e}")
            return {"response": "An error occurred while processing your request.", "sources": []}
