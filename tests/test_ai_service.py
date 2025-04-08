"""
Tests for the AI service component
"""
import os
import pytest
from unittest.mock import MagicMock, patch

from aivim.ai_service import AIService


@pytest.mark.skipif(not os.environ.get("OPENAI_API_KEY"), reason="No OpenAI API key available")
class TestAIService:
    """Tests for the AIService class"""
    
    def setup_method(self):
        """Set up test environment"""
        try:
            self.ai_service = AIService()
        except ValueError:
            pytest.skip("OpenAI API key not available")
    
    @patch('openai.OpenAI')
    def test_get_explanation(self, mock_openai):
        """Test get_explanation method"""
        # Setup mock
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "This code defines a function"
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        # Create service with mock
        with patch('aivim.ai_service.OpenAI', mock_openai):
            service = AIService()
            
            # Call the method
            result = service.get_explanation("def test():\n    return True", "")
            
            # Check result
            assert result == "This code defines a function"
            
            # Verify the OpenAI API was called correctly
            mock_openai.return_value.chat.completions.create.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_get_improvement(self, mock_openai):
        """Test get_improvement method"""
        # Setup mock
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "```python\ndef test():\n    return True\n```"
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        # Create service with mock
        with patch('aivim.ai_service.OpenAI', mock_openai):
            service = AIService()
            
            # Call the method
            result = service.get_improvement("def test():\n    pass", "")
            
            # Check result - should extract just the code
            assert result == "def test():\n    return True"
            
            # Verify the OpenAI API was called correctly
            mock_openai.return_value.chat.completions.create.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_generate_code(self, mock_openai):
        """Test generate_code method"""
        # Setup mock
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "```python\ndef calculate_sum(a, b):\n    return a + b\n```"
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        # Create service with mock
        with patch('aivim.ai_service.OpenAI', mock_openai):
            service = AIService()
            
            # Call the method
            result = service.generate_code("# Function to calculate sum of two numbers", "")
            
            # Check result - should extract just the code
            assert result == "def calculate_sum(a, b):\n    return a + b"
            
            # Verify the OpenAI API was called correctly
            mock_openai.return_value.chat.completions.create.assert_called_once()
    
    @patch('openai.OpenAI')
    def test_custom_query(self, mock_openai):
        """Test custom_query method"""
        # Setup mock
        mock_completion = MagicMock()
        mock_completion.choices[0].message.content = "The complexity of this code is O(n)"
        mock_openai.return_value.chat.completions.create.return_value = mock_completion
        
        # Create service with mock
        with patch('aivim.ai_service.OpenAI', mock_openai):
            service = AIService()
            
            # Call the method
            result = service.custom_query("What is the time complexity?", "for i in range(n):\n    print(i)")
            
            # Check result
            assert result == "The complexity of this code is O(n)"
            
            # Verify the OpenAI API was called correctly
            mock_openai.return_value.chat.completions.create.assert_called_once()
