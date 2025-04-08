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
        self.api_key = os.environ.get("OPENAI_API_KEY")
        
        if not OPENAI_AVAILABLE:
            logging.warning("OpenAI package not installed. AI features will not work.")
            self.client = None
        elif not self.api_key:
            logging.warning("OPENAI_API_KEY environment variable not set. AI features will not work.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                logging.info("OpenAI client initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize OpenAI client: {str(e)}")
                self.client = None
    
    def _create_completion(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Create an AI completion using OpenAI
        
        Args:
            system_prompt: System instructions
            user_prompt: User query
            
        Returns:
            Generated text or None if the request failed
        """
        if not OPENAI_AVAILABLE:
            return "OpenAI package not installed. Please install it with 'pip install openai'."
        
        if not self.client:
            return "AI services unavailable. Please set OPENAI_API_KEY environment variable."
        
        try:
            # Use the gpt-4o model released after the knowledge cutoff
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
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