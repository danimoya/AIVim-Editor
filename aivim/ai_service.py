"""
AI services for AIVim using OpenAI's API
"""
import logging
import os
from typing import Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


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
        
        # This is a placeholder for actual Claude implementation
        # The newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024.
        return "Claude API support coming soon. Please use OpenAI or local models for now."
        
    def _local_completion(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Create a completion using a local model"""
        # This is a simplified placeholder. In a real implementation, this would 
        # connect to a local model server or library like llama.cpp
        return f"Local AI response to: {user_prompt[:30]}... (Local AI not yet implemented)"
    
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
        Get an improved version of the provided code
        
        Args:
            code: The specific code to improve
            context: The surrounding code for context
            
        Returns:
            An improved version of the code
        """
        system_prompt = (
            "You are an expert code improver. "
            "Analyze the provided code and suggest improvements. "
            "Maintain the original functionality while making enhancements for: "
            "performance, readability, maintainability, or error handling. "
            "Provide both the improved code and explanation of changes."
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

Please provide an improved version of this code along with an explanation of the improvements.
"""
        
        improvement = self._create_completion(system_prompt, user_prompt)
        return improvement or "Failed to generate improvement."
    
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