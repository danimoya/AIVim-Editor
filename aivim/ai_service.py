"""
AI services for AIVim using multiple AI providers including OpenAI, Anthropic, and local LLMs
"""
import logging
import os
import time
from typing import Optional, Dict, Any

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False


class AIService:
    """
    Service for interacting with AI models
    """
    def __init__(self):
        """Initialize AI service"""
        # OpenAI setup
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.openai_client = None
        
        # Anthropic setup
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.anthropic_client = None
        
        # Local LLM setup
        self.llama_model_path = os.environ.get("LLAMA_MODEL_PATH")
        self.local_llm = None
        
        # Default model provider
        self.current_model = "openai"  # Options: "openai", "claude", "local"
        
        # Initialize available clients
        self._initialize_clients()
        
    def _initialize_clients(self):
        """Initialize available AI clients based on API keys"""
        # Initialize OpenAI
        if OPENAI_AVAILABLE:
            if self.openai_api_key:
                try:
                    self.openai_client = OpenAI(api_key=self.openai_api_key)
                    logging.info("OpenAI client initialized successfully")
                except Exception as e:
                    logging.error(f"Error initializing OpenAI client: {str(e)}")
            else:
                logging.warning("OPENAI_API_KEY environment variable not set. OpenAI features will not work.")
        else:
            logging.warning("OpenAI package not installed. OpenAI features will not work.")
            
        # Initialize Anthropic
        try:
            import anthropic
            if self.anthropic_api_key:
                try:
                    self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                    logging.info("Anthropic client initialized successfully")
                except Exception as e:
                    logging.error(f"Error initializing Anthropic client: {str(e)}")
            else:
                logging.warning("ANTHROPIC_API_KEY environment variable not set. Claude features will not work.")
        except ImportError:
            logging.warning("Anthropic package not installed. Claude features will not work.")
            
        # Initialize Local LLM (llama.cpp)
        if LLAMA_AVAILABLE:
            # Try to load a default model if path is not provided
            model_path = self.llama_model_path
            if not model_path:
                # First check for models in common locations
                possible_paths = [
                    os.path.expanduser("~/.local/share/llama.cpp/models"),
                    os.path.expanduser("~/models"),
                    "./models"
                ]
                
                # Names of popular open models to check for
                model_names = [
                    "llama-2-7b-chat.gguf",
                    "ggml-model-q4_0.bin",
                    "mistral-7b-instruct-v0.1.Q4_0.gguf",
                    "llama-2-13b-chat.gguf"
                ]
                
                # Search for models
                for path in possible_paths:
                    if os.path.exists(path):
                        for model in model_names:
                            model_path = os.path.join(path, model)
                            if os.path.exists(model_path):
                                logging.info(f"Found local model: {model_path}")
                                break
                    if model_path:
                        break
            
            if model_path and os.path.exists(model_path):
                try:
                    # Initialize with minimal settings
                    self.local_llm = Llama(
                        model_path=model_path,
                        n_ctx=2048,      # Context window size
                        n_threads=4      # Number of CPU threads to use
                    )
                    logging.info(f"Local LLM initialized with model: {model_path}")
                except Exception as e:
                    logging.error(f"Error initializing local LLM: {str(e)}")
            else:
                logging.warning("No local model found. Set LLAMA_MODEL_PATH environment variable to use local LLM.")
        else:
            logging.warning("llama-cpp-python package not installed. Local LLM features will not work.")
            
    def set_model(self, model_name: str) -> bool:
        """
        Set the AI model provider to use
        
        Args:
            model_name: Model provider name ("openai", "claude", "local")
            
        Returns:
            True if successful, False otherwise
        """
        model_name = model_name.lower()
        
        if model_name == "openai" and not self.openai_client:
            logging.error("OpenAI client not available. Check API key and package installation.")
            return False
        elif model_name == "claude" and not self.anthropic_client:
            logging.error("Claude client not available. Check API key and package installation.")
            return False
        elif model_name == "local" and not self.local_llm:
            if not LLAMA_AVAILABLE:
                logging.error("Local LLM not available. Please install llama-cpp-python package.")
            else:
                logging.error("Local LLM not initialized. Set LLAMA_MODEL_PATH environment variable.")
            return False
        elif model_name not in ["openai", "claude", "local"]:
            logging.error(f"Unknown model: {model_name}")
            return False
            
        self.current_model = model_name
        logging.info(f"AI model set to: {model_name}")
        return True
    
    def _create_completion(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Create an AI completion using the selected model provider
        
        Args:
            system_prompt: System instructions
            user_prompt: User query
            
        Returns:
            Generated text or None if the request failed
        """
        # Check which model is currently selected
        if self.current_model == "openai":
            return self._openai_completion(system_prompt, user_prompt)
        elif self.current_model == "claude":
            return self._anthropic_completion(system_prompt, user_prompt)
        elif self.current_model == "local":
            return self._local_completion(system_prompt, user_prompt)
        else:
            return f"Unknown model type: {self.current_model}"
    
    def _openai_completion(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Create a completion using OpenAI"""
        if not OPENAI_AVAILABLE:
            return "OpenAI package not installed. Please install it with 'pip install openai'."
        
        if not self.openai_client:
            return "OpenAI API unavailable. Please set OPENAI_API_KEY environment variable."
        
        try:
            # Use the gpt-4o model released after the knowledge cutoff
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")
            return f"Error: {str(e)}"
            
    def _anthropic_completion(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Create a completion using Anthropic Claude"""
        if not self.anthropic_client:
            return "Anthropic Claude API unavailable. Please set ANTHROPIC_API_KEY environment variable."
        
        try:
            # Use the claude-3-5-sonnet-20241022 model, the latest available
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=1000
            )
            return response.content[0].text
        except Exception as e:
            logging.error(f"Anthropic API error: {str(e)}")
            return f"Error: {str(e)}"
        
    def _local_completion(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Create a completion using a local model with llama.cpp"""
        if not LLAMA_AVAILABLE:
            return "llama-cpp-python package not installed. Please install it with 'pip install llama-cpp-python'."
            
        if not self.local_llm:
            return ("Local LLM not initialized. Please set LLAMA_MODEL_PATH environment variable "
                   "or place a supported model in ./models directory.")
            
        try:
            # Format the prompt in a chat-like format that local models can understand
            formatted_prompt = f"""
<|system|>
{system_prompt}
<|user|>
{user_prompt}
<|assistant|>
"""
            # Generate completion with the local model
            start_time = time.time()
            logging.info("Starting local LLM inference...")
            
            # Use the llama.cpp API to generate text
            output = self.local_llm(
                formatted_prompt,
                max_tokens=1000,
                stop=["<|user|>", "<|system|>"],  # Stop tokens
                echo=False,            # Don't echo the prompt
                temperature=0.2,       # Lower temp for more deterministic outputs
                top_p=0.95,            # Nucleus sampling for more focused outputs
                repeat_penalty=1.1     # Slight penalty for repetition
            )
            
            # Extract the generated text from the model output
            response = output["choices"][0]["text"].strip()
            
            elapsed_time = time.time() - start_time
            logging.info(f"Local LLM inference completed in {elapsed_time:.2f} seconds.")
            
            return response
        except Exception as e:
            logging.error(f"Local LLM error: {str(e)}")
            return f"Error using local LLM: {str(e)}"
    
    def get_explanation(self, code: str, context: str) -> str:
        """
        Get an explanation of the provided code
        
        Args:
            code: The specific code to explain
            context: The surrounding code for context
            
        Returns:
            A detailed explanation of the code
        """
        system_prompt = (
            "You are an expert code analyst. "
            "Provide a detailed explanation of the provided code, "
            "including its purpose, how it works, and any potential issues. "
            "Focus on clarity and depth of explanation."
        )
        
        user_prompt = f"""
# Code to explain:
```
{code}
```

# Context (surrounding code):
```
{context}
```

Please explain this code in detail.
"""
        
        explanation = self._create_completion(system_prompt, user_prompt)
        return explanation or "Failed to generate explanation."
    
    def get_improvement(self, code: str, context: str) -> str:
        """
        Get an improved version of the provided code with structured output
        
        Args:
            code: The specific code to improve
            context: The surrounding code for context
            
        Returns:
            A structured string with EXPLANATION and IMPROVED_CODE sections
        """
        system_prompt = (
            "You are an expert code improver. "
            "Analyze the provided code and suggest improvements. "
            "Maintain the original functionality while making enhancements for: "
            "performance, readability, maintainability, or error handling. "
            "YOUR RESPONSE MUST USE THIS EXACT FORMAT with these section headers:\n\n"
            "# EXPLANATION\n<Your detailed explanation of all improvements>\n\n"
            "# IMPROVED_CODE\n<The complete improved code without any markdown formatting>\n\n"
        )
        
        user_prompt = f"""
# Code to improve:
```
{code}
```

# Context (surrounding code):
```
{context}
```

Please provide your response using the EXACT format with these section headers:
1. Start with "# EXPLANATION" followed by your detailed explanation
2. Then include "# IMPROVED_CODE" followed by just the improved code (no markdown code blocks)
"""
        
        improvement = self._create_completion(system_prompt, user_prompt)
        if not improvement:
            return "Failed to generate improvement."
            
        # Ensure we have the two required sections
        if "# EXPLANATION" not in improvement or "# IMPROVED_CODE" not in improvement:
            # Try to parse it anyway by adding the headers
            processed = "# EXPLANATION\n" + improvement + "\n\n# IMPROVED_CODE\n" + code
            return processed
            
        return improvement
    
    def generate_code(self, specification: str, context: str) -> str:
        """
        Generate code based on a specification
        
        Args:
            specification: The code or comments describing what to generate
            context: The surrounding code for context
            
        Returns:
            Generated code based on the specification
        """
        system_prompt = (
            "You are an expert code generator. "
            "Generate high-quality, efficient code based on the specification. "
            "Ensure the generated code fits well with the provided context. "
            "Focus on correctness, efficiency, and readability. "
            "Include helpful comments where appropriate."
        )
        
        user_prompt = f"""
# Specification:
{specification}

# Context (surrounding code):
```
{context}
```

Please generate code that meets this specification and fits well with the context.
"""
        
        generated_code = self._create_completion(system_prompt, user_prompt)
        return generated_code or "Failed to generate code."
    
    def custom_query(self, query: str, context: str) -> str:
        """
        Process a custom query about the code
        
        Args:
            query: The user's query
            context: The code context for reference
            
        Returns:
            The AI's response to the query
        """
        system_prompt = (
            "You are an expert programming assistant. "
            "Answer the user's query about their code accurately and helpfully. "
            "If the query is unclear, ask for clarification. "
            "Provide factual, specific information without making assumptions. "
            "When relevant, include code examples."
        )
        
        user_prompt = f"""
# Query:
{query}

# Code context:
```
{context}
```

Please respond to this query considering the code context.
"""
        
        response = self._create_completion(system_prompt, user_prompt)
        return response or "Failed to process query."
        
    def analyze_code(self, code: str, context: str) -> str:
        """
        Analyze code complexity and identify potential bugs
        
        Args:
            code: The specific code to analyze
            context: The surrounding code for context
            
        Returns:
            A detailed analysis of code complexity and potential bugs
        """
        system_prompt = (
            "You are an expert code analyzer specializing in identifying complexity issues and potential bugs. "
            "Analyze the provided code thoroughly and provide detailed feedback on: "
            "1. Cyclomatic complexity - identify complex functions or methods and suggest simplification "
            "2. Potential bugs - edge cases, error handling gaps, race conditions, etc. "
            "3. Code smells - duplicate code, long methods, long parameter lists "
            "4. Performance issues - inefficient algorithms, memory usage concerns "
            "5. Security vulnerabilities - if any are evident "
            "6. Maintainability concerns "
            "Format your response with clear sections for each category and provide line references. "
            "For each issue, explain why it's problematic and suggest a practical solution."
        )
        
        user_prompt = f"""
# Code to analyze:
```
{code}
```

# Context (surrounding code):
```
{context}
```

Please provide a comprehensive analysis of this code, focusing on complexity and potential bugs.
"""
        
        analysis = self._create_completion(system_prompt, user_prompt)
        return analysis or "Failed to analyze code."