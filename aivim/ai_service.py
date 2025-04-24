"""
AI services for AIVim using multiple AI providers including OpenAI, Anthropic, and local LLMs
"""
import logging
import os
import time
import datetime
import json
import configparser
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

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
        # Config info
        self.config_status = {"loaded": False, "path": None, "message": "No config loaded"}
        
        # OpenAI setup
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.openai_client = None
        self.openai_models = [
            {"id": "gpt-4o", "name": "GPT-4o", "description": "Latest multimodal OpenAI model (May 2024)"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "description": "Powerful model with good balance of quality and speed"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "description": "Fast and efficient language model"}
        ]
        self.current_openai_model = "gpt-4o"  # Default OpenAI model
        
        # Anthropic setup
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.anthropic_client = None
        self.anthropic_models = [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "description": "Latest Claude model (Oct 2024)"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "description": "Anthropic's most powerful model"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "description": "Good balance of intelligence and speed"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "description": "Fast, efficient model for simpler tasks"}
        ]
        self.current_anthropic_model = "claude-3-5-sonnet-20241022"  # Default Anthropic model
        
        # Local LLM setup
        self.llama_model_path = os.environ.get("LLAMA_MODEL_PATH")
        self.local_llm = None
        self.local_models = []  # Will be populated during initialization
        self.current_local_model = ""  # Will be set during initialization
        
        # Default model provider
        self.current_model = "openai"  # Options: "openai", "claude", "local"
        
        # Load config if available
        self.load_config()
        
        # Initialize available clients
        self._initialize_clients()
        
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from config file
        
        Returns:
            Dict with config status information
        """
        config = configparser.ConfigParser()
        
        # Check for config files in common locations
        config_paths = [
            os.path.expanduser("~/.aivim/config"),
            os.path.expanduser("~/.config/aivim/config"),
            os.path.expanduser("~/.aivimrc"),
            "./aivim.config"
        ]
        
        config_found = False
        for path in config_paths:
            if os.path.exists(path):
                try:
                    config.read(path)
                    config_found = True
                    self.config_status = {
                        "loaded": True, 
                        "path": path,
                        "message": f"Config loaded from {path}"
                    }
                    logging.info(f"Loaded config from {path}")
                    
                    # Extract API keys if present
                    if 'OpenAI' in config and 'api_key' in config['OpenAI']:
                        self.openai_api_key = config['OpenAI']['api_key']
                        logging.info("Loaded OpenAI API key from config")
                        
                    if 'Anthropic' in config and 'api_key' in config['Anthropic']:
                        self.anthropic_api_key = config['Anthropic']['api_key']
                        logging.info("Loaded Anthropic API key from config")
                        
                    if 'LocalLLM' in config and 'model_path' in config['LocalLLM']:
                        self.llama_model_path = config['LocalLLM']['model_path']
                        logging.info(f"Loaded local model path from config: {self.llama_model_path}")
                        
                    # Set default model if specified
                    if 'General' in config and 'default_model' in config['General']:
                        self.current_model = config['General']['default_model'].lower()
                        logging.info(f"Set default model to {self.current_model} from config")
                    
                    break
                except Exception as e:
                    logging.error(f"Error loading config from {path}: {str(e)}")
                    self.config_status = {
                        "loaded": False, 
                        "path": path,
                        "message": f"Error loading config: {str(e)}"
                    }
        
        if not config_found:
            logging.warning("No config file found. Using environment variables.")
            self.config_status = {
                "loaded": False,
                "path": None,
                "message": "No config file found. Using environment variables."
            }
            
        return self.config_status
        
    def get_config_status(self) -> Dict[str, Any]:
        """
        Get the status of config loading
        
        Returns:
            Dict with config status information
        """
        return self.config_status
        
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
        
    def get_current_model_info(self) -> str:
        """
        Get information about the currently selected model
        
        Returns:
            String describing the current model in use
        """
        if self.current_model == "openai":
            if self.openai_client:
                for model in self.openai_models:
                    if model["id"] == self.current_openai_model:
                        return model["name"]
                return self.current_openai_model
            else:
                return "OpenAI (not configured)"
        elif self.current_model == "claude":
            if self.anthropic_client:
                for model in self.anthropic_models:
                    if model["id"] == self.current_anthropic_model:
                        return model["name"]
                return self.current_anthropic_model
            else:
                return "Claude (not configured)"
        elif self.current_model == "local":
            if self.local_llm:
                model_path = getattr(self.local_llm, 'model_path', 'unknown')
                # Extract just the filename from the path
                model_name = os.path.basename(model_path) if model_path != 'unknown' else 'Local LLM'
                return f"Local: {model_name}"
            else:
                return "Local LLM (not configured)"
        else:
            return f"Unknown model: {self.current_model}"
            
    def get_available_submodels(self, provider: str) -> List[Dict[str, Any]]:
        """
        Get a list of available submodels for a specific provider
        
        Args:
            provider: Name of the provider ("openai", "claude", "local")
            
        Returns:
            List of submodel dictionaries with id, name, description
        """
        provider = provider.lower()
        
        if provider == "openai":
            return self.openai_models
        elif provider == "claude":
            return self.anthropic_models
        elif provider == "local":
            # For local models, check if any are available
            if self.local_llm:
                # If we have a loaded model, return its info
                model_path = getattr(self.local_llm, 'model_path', 'unknown')
                model_name = os.path.basename(model_path) if model_path != 'unknown' else 'Local LLM'
                return [{"id": model_path, "name": model_name, "description": "Locally loaded LLM"}]
            
            # Otherwise, scan for available models
            available_models = []
            
            # Common locations to check for GGUF/GGML models
            model_dirs = [
                os.path.expanduser("~/.local/share/llama.cpp/models"),
                os.path.expanduser("~/models"),
                "./models"
            ]
            
            for model_dir in model_dirs:
                if os.path.exists(model_dir):
                    for file in os.listdir(model_dir):
                        if file.endswith((".gguf", ".bin")):
                            model_path = os.path.join(model_dir, file)
                            available_models.append({
                                "id": model_path,
                                "name": file,
                                "description": f"Found in {model_dir}"
                            })
            
            return available_models
        else:
            logging.warning(f"Unknown provider: {provider}")
            return []
    
    def set_submodel(self, provider: str, submodel_id: str) -> bool:
        """
        Set a specific submodel for the provider
        
        Args:
            provider: Name of the provider ("openai", "claude", "local")
            submodel_id: ID of the submodel to set
            
        Returns:
            True if successful, False otherwise
        """
        provider = provider.lower()
        
        if provider == "openai":
            # Verify this is a valid OpenAI model
            valid_model = False
            for model in self.openai_models:
                if model["id"] == submodel_id:
                    valid_model = True
                    break
                    
            if valid_model:
                self.current_openai_model = submodel_id
                logging.info(f"Set OpenAI model to: {submodel_id}")
                return True
            else:
                logging.error(f"Invalid OpenAI model: {submodel_id}")
                return False
                
        elif provider == "claude":
            # Verify this is a valid Claude model
            valid_model = False
            for model in self.anthropic_models:
                if model["id"] == submodel_id:
                    valid_model = True
                    break
                    
            if valid_model:
                self.current_anthropic_model = submodel_id
                logging.info(f"Set Claude model to: {submodel_id}")
                return True
            else:
                logging.error(f"Invalid Claude model: {submodel_id}")
                return False
                
        elif provider == "local":
            # For local models, we need to load the model if it's different
            # from the currently loaded one
            if self.local_llm and hasattr(self.local_llm, 'model_path'):
                current_path = self.local_llm.model_path
                if current_path == submodel_id:
                    logging.info(f"Local model already set to: {submodel_id}")
                    return True
            
            # Check if the model file exists
            if not os.path.exists(submodel_id):
                logging.error(f"Local model file not found: {submodel_id}")
                return False
                
            # Try to load the new model
            try:
                if LLAMA_AVAILABLE:
                    # Initialize with minimal settings
                    self.local_llm = Llama(
                        model_path=submodel_id,
                        n_ctx=2048,  # Context window size
                        n_threads=4   # Number of CPU threads to use
                    )
                    logging.info(f"Local LLM initialized with model: {submodel_id}")
                    return True
                else:
                    logging.error("llama-cpp-python package not installed")
                    return False
            except Exception as e:
                logging.error(f"Error loading local model: {str(e)}")
                return False
        else:
            logging.error(f"Unknown provider: {provider}")
            return False
            
    def is_model_configured(self) -> bool:
        """
        Check if the current model is properly configured
        
        Returns:
            True if the current model is configured, False otherwise
        """
        if self.current_model == "openai":
            return self.openai_client is not None
        elif self.current_model == "claude":
            return self.anthropic_client is not None
        elif self.current_model == "local":
            return self.local_llm is not None
        return False
    
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
            # Use the currently selected OpenAI model
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            model_to_use = self.current_openai_model
            
            # Log which model we're using
            logging.info(f"Using OpenAI model: {model_to_use}")
            
            # Set timeout for the API call to prevent UI freezing in restricted network environments
            import threading
            from concurrent.futures import ThreadPoolExecutor, TimeoutError
            
            def api_call():
                return self.openai_client.chat.completions.create(
                    model=model_to_use,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.2,
                    max_tokens=1000
                )
            
            # Execute the API call with a timeout
            with ThreadPoolExecutor() as executor:
                future = executor.submit(api_call)
                try:
                    # 10 second timeout to prevent UI freezing
                    response = future.result(timeout=10)
                    return response.choices[0].message.content
                except TimeoutError:
                    # Cancel the future if possible
                    future.cancel()
                    logging.error("OpenAI API request timed out after 10 seconds")
                    return "Error: Network request timed out. Please check your internet connection or try again later."
                
        except Exception as e:
            logging.error(f"OpenAI API error: {str(e)}")
            return f"Error: {str(e)}"
            
    def _anthropic_completion(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Create a completion using Anthropic Claude"""
        if not self.anthropic_client:
            return "Anthropic Claude API unavailable. Please set ANTHROPIC_API_KEY environment variable."
        
        try:
            # Use the currently selected Claude model
            model_to_use = self.current_anthropic_model
            
            # Log which model we're using
            logging.info(f"Using Anthropic model: {model_to_use}")
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            
            response = self.anthropic_client.messages.create(
                model=model_to_use,
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
            # Log the model we're using
            model_path = "unknown"
            if hasattr(self.local_llm, 'model_path'):
                model_path = self.local_llm.model_path
            model_name = os.path.basename(model_path)
            logging.info(f"Using local model: {model_name} ({model_path})")
            
            # Format the prompt in a chat-like format that local models can understand
            formatted_prompt = f"""
<|system|>
{system_prompt}
<|user|>
{user_prompt}
<|assistant|>
"""
            # Redirect stdout temporarily to capture perf context output
            import io
            import sys
            original_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            # Generate completion with the local model
            start_time = time.time()
            logging.info("Starting local LLM inference...")
            
            try:
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
                
                # Capture the performance output
                perf_output = sys.stdout.getvalue()
                
                # Log the performance output instead of printing to console
                for line in perf_output.split('\n'):
                    if line.strip():
                        logging.info(f"Local LLM perf: {line.strip()}")
            finally:
                # Restore stdout
                sys.stdout = original_stdout
            
            # Extract the generated text from the model output
            response = output["choices"][0]["text"].strip()
            
            elapsed_time = time.time() - start_time
            logging.info(f"Local LLM inference completed in {elapsed_time:.2f} seconds.")
            
            # Save the response to a file 
            self._save_local_model_response(system_prompt, user_prompt, response, elapsed_time)
            
            return response
        except Exception as e:
            return self._local_llm_error(e)
            
    def _save_local_model_response(self, system_prompt: str, user_prompt: str, 
                                 response: str, elapsed_time: float) -> None:
        """
        Save the local model response to a file for reference
        
        Args:
            system_prompt: The system prompt that was used
            user_prompt: The user prompt that was sent
            response: The model's response
            elapsed_time: Time taken to generate the response
        """
        try:
            # Create responses directory if it doesn't exist
            responses_dir = os.path.join(os.path.expanduser("~"), ".aivim", "responses")
            os.makedirs(responses_dir, exist_ok=True)
            
            # Generate timestamp for the filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            model_name = "local"
            if self.local_llm:
                model_path = getattr(self.local_llm, 'model_path', 'unknown')
                model_name = os.path.basename(model_path).replace('.', '_')
                
            # Create a descriptive filename
            filename = f"{timestamp}_{model_name}_response.json"
            filepath = os.path.join(responses_dir, filename)
            
            # Create the response data
            response_data = {
                "timestamp": timestamp,
                "model": model_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response": response,
                "elapsed_time_seconds": elapsed_time
            }
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(response_data, f, indent=2)
                
            logging.info(f"Saved local model response to {filepath}")
        except Exception as e:
            logging.error(f"Error saving local model response: {str(e)}")
        
    def _local_llm_error(self, error) -> str:
        """Handle local LLM errors and return appropriate message"""
        logging.error(f"Local LLM error: {str(error)}")
        return f"Error using local LLM: {str(error)}"
    
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