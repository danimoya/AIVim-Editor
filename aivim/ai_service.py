"""
AI services for AIVim using OpenAI's API
"""
import os
import json
from typing import Optional, Dict, Any, List

from openai import OpenAI

class AIService:
    """
    Service for interacting with AI models
    """
    def __init__(self):
        # Get API key from environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Initialize OpenAI client
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o"
    
    def get_explanation(self, code: str, context: str) -> str:
        """
        Get an explanation of the provided code
        
        Args:
            code: The specific code to explain
            context: The surrounding code for context
            
        Returns:
            A detailed explanation of the code
        """
        prompt = f"""
        Please explain the following code in detail. Focus on what the code does, 
        its purpose, and any interesting or complex aspects:

        ```
        {code}
        ```
        
        Here is the surrounding context for reference:
        
        ```
        {context}
        ```
        
        Provide a clear, concise explanation that would help someone understand this code.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful code assistant that explains code clearly and concisely."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error getting explanation: {str(e)}"
    
    def get_improvement(self, code: str, context: str) -> str:
        """
        Get an improved version of the provided code
        
        Args:
            code: The specific code to improve
            context: The surrounding code for context
            
        Returns:
            An improved version of the code
        """
        prompt = f"""
        Please improve the following code. Maintain the same functionality, but make it more:
        - Efficient
        - Readable
        - Maintainable
        - Robust (with proper error handling)

        Original code:
        ```
        {code}
        ```
        
        Here is the surrounding context for reference:
        
        ```
        {context}
        ```
        
        Return only the improved code without any explanations.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful code assistant that improves code quality."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content
            
            # Try to extract just the code part (remove any markdown code blocks if present)
            if "```" in content:
                # Find first and last code block indicators
                start = content.find("```") + 3
                # Skip language identifier line if present
                if "\n" in content[start:]:
                    start = content.find("\n", start) + 1
                end = content.rfind("```")
                
                # Extract only the code
                if start < end:
                    return content[start:end].strip()
            
            return content
            
        except Exception as e:
            return f"Error improving code: {str(e)}"
    
    def generate_code(self, specification: str, context: str) -> str:
        """
        Generate code based on a specification
        
        Args:
            specification: The code or comments describing what to generate
            context: The surrounding code for context
            
        Returns:
            Generated code based on the specification
        """
        prompt = f"""
        Please generate code based on the following specification or comments:
        
        ```
        {specification}
        ```
        
        Here is the surrounding context for reference:
        
        ```
        {context}
        ```
        
        Return only the generated code without any explanations.
        Use the appropriate programming language based on the context.
        Match the coding style of the surrounding code.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful code assistant that generates high-quality code."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            content = response.choices[0].message.content
            
            # Try to extract just the code part (remove any markdown code blocks if present)
            if "```" in content:
                # Find first and last code block indicators
                start = content.find("```") + 3
                # Skip language identifier line if present
                if "\n" in content[start:]:
                    start = content.find("\n", start) + 1
                end = content.rfind("```")
                
                # Extract only the code
                if start < end:
                    return content[start:end].strip()
            
            return content
            
        except Exception as e:
            return f"Error generating code: {str(e)}"
    
    def custom_query(self, query: str, context: str) -> str:
        """
        Process a custom query about the code
        
        Args:
            query: The user's query
            context: The code context for reference
            
        Returns:
            The AI's response to the query
        """
        prompt = f"""
        Here is some code for context:
        
        ```
        {context}
        ```
        
        Please answer the following question about the code:
        {query}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful code assistant that can answer questions about code."},
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error processing query: {str(e)}"
        