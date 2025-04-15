#!/usr/bin/env python3
"""
Test script for AIService module
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aivim.ai_service import AIService


class TestAIService(unittest.TestCase):
    """Test cases for AIService"""
    
    def setUp(self):
        """Set up test environment"""
        # Use patch.dict to mock modules that may be imported
        self.modules_patcher = patch.dict('sys.modules', {
            'openai': MagicMock(),
            'anthropic': MagicMock(),
            'llama_cpp': MagicMock()
        })
        self.modules_patcher.start()
        
        # Create patch for OpenAI import inside AI service
        self.openai_class_patcher = patch('aivim.ai_service.OpenAI')
        self.mock_openai_class = self.openai_class_patcher.start()
        
        # Create patch for Llama class
        self.llama_class_patcher = patch('aivim.ai_service.Llama')
        self.mock_llama_class = self.llama_class_patcher.start()
        
        # Create patch for Anthropic import
        # Since it's imported conditionally, we need to make sure it's set up
        self.anthropic_patcher = patch('anthropic.Anthropic')
        self.mock_anthropic = self.anthropic_patcher.start()
        
        # Create AIService instance with mocked dependencies
        self.ai_service = AIService()
        
        # Initialize some standard values
        self.ai_service.current_model = "openai"  # Default model
        self.ai_service.openai_api_key = None
        self.ai_service.anthropic_api_key = None
        self.ai_service.llama_model_path = None
    
    def tearDown(self):
        """Tear down the test environment"""
        # Stop all patchers
        self.openai_class_patcher.stop()
        self.llama_class_patcher.stop()
        self.anthropic_patcher.stop()
        self.modules_patcher.stop()
    
    @patch('builtins.open', new_callable=mock_open, read_data='{"openai_api_key": "test_key"}')
    @patch('os.path.exists', return_value=True)
    def test_load_config_with_existing_file(self, mock_exists, mock_file):
        """Test loading configuration from an existing file"""
        result = self.ai_service.load_config()
        
        # Check that the method returned success status
        self.assertTrue(result.get('success'))
        
        # Check that file was opened with correct path
        mock_file.assert_called_once()
        
        # Check that the API key was loaded
        self.assertEqual(self.ai_service.openai_api_key, "test_key")
    
    @patch('os.path.exists', return_value=False)
    def test_load_config_with_nonexistent_file(self, mock_exists):
        """Test loading configuration from a nonexistent file"""
        result = self.ai_service.load_config()
        
        # Should fail but not crash
        self.assertFalse(result.get('success'))
        self.assertIn('error', result)
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    @patch('os.path.exists', return_value=True)
    def test_load_config_with_io_error(self, mock_exists, mock_file):
        """Test loading configuration with an IO error"""
        result = self.ai_service.load_config()
        
        # Should fail but not crash
        self.assertFalse(result.get('success'))
        self.assertIn('error', result)
        self.assertIn('Permission denied', result.get('error'))
    
    @patch.object(AIService, '_initialize_clients')
    def test_set_model_openai(self, mock_init_clients):
        """Test setting the model to OpenAI"""
        # Setup
        self.ai_service.openai_api_key = "test_key"
        
        # Test
        result = self.ai_service.set_model("openai")
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.ai_service.current_model, "openai")
    
    @patch.object(AIService, '_initialize_clients')
    def test_set_model_anthropic(self, mock_init_clients):
        """Test setting the model to Anthropic Claude"""
        # Setup
        self.ai_service.anthropic_api_key = "test_key"
        
        # Test
        result = self.ai_service.set_model("claude")
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.ai_service.current_model, "claude")
    
    @patch.object(AIService, '_initialize_clients')
    @patch('os.path.exists', return_value=True)
    def test_set_model_local(self, mock_exists, mock_init_clients):
        """Test setting the model to local LLM"""
        # Setup
        self.ai_service.llama_model_path = "/path/to/model.gguf"
        
        # Test
        result = self.ai_service.set_model("local")
        
        # Verify
        self.assertTrue(result)
        self.assertEqual(self.ai_service.current_model, "local")
    
    def test_set_model_invalid(self):
        """Test setting an invalid model"""
        result = self.ai_service.set_model("invalid_model")
        self.assertFalse(result)
    
    def test_get_current_model_info_openai(self):
        """Test getting current model info for OpenAI"""
        # Setup
        self.ai_service.current_model = "openai"
        
        # Create a mock OpenAI client
        self.ai_service.openai_client = MagicMock()
        
        # Test
        info = self.ai_service.get_current_model_info()
        
        # Verify
        self.assertEqual("GPT-4o", info)
    
    def test_get_current_model_info_anthropic(self):
        """Test getting current model info for Anthropic"""
        # Setup
        self.ai_service.current_model = "claude"
        
        # Mock the Anthropic client
        self.ai_service.anthropic_client = MagicMock()
        
        # Test
        info = self.ai_service.get_current_model_info()
        
        # Verify
        self.assertEqual("Claude 3.5 Sonnet", info)
    
    def test_get_current_model_info_local(self):
        """Test getting current model info for local LLM"""
        # Setup
        self.ai_service.current_model = "local"
        self.ai_service.llama_model_path = "/path/to/model.gguf"
        
        # Mock local_llm with a fake model_path
        mock_llama = MagicMock()
        mock_llama.model_path = "/path/to/model.gguf"
        self.ai_service.local_llm = mock_llama
        
        # Test
        info = self.ai_service.get_current_model_info()
        
        # Verify
        self.assertIn("Local", info)
        self.assertIn("model.gguf", info)
    
    def test_is_model_configured_openai_with_key(self):
        """Test checking if OpenAI model is configured with API key"""
        # Setup
        self.ai_service.current_model = "openai"
        # The actual implementation checks if the client is initialized, not just the key
        self.ai_service.openai_client = MagicMock()
        
        # Test and verify
        self.assertTrue(self.ai_service.is_model_configured())
    
    def test_is_model_configured_openai_without_key(self):
        """Test checking if OpenAI model is configured without API key"""
        # Setup
        self.ai_service.current_model = "openai"
        # The actual implementation checks if the client is None
        self.ai_service.openai_client = None
        
        # Test and verify
        self.assertFalse(self.ai_service.is_model_configured())
    
    def test_is_model_configured_anthropic_with_key(self):
        """Test checking if Anthropic model is configured with API key"""
        # Setup
        self.ai_service.current_model = "claude"
        # The actual implementation checks if the client is initialized, not just the key
        self.ai_service.anthropic_client = MagicMock()
        
        # Test and verify
        self.assertTrue(self.ai_service.is_model_configured())
    
    def test_is_model_configured_anthropic_without_key(self):
        """Test checking if Anthropic model is configured without API key"""
        # Setup
        self.ai_service.current_model = "claude"
        # The actual implementation checks if the client is None
        self.ai_service.anthropic_client = None
        
        # Test and verify
        self.assertFalse(self.ai_service.is_model_configured())
    
    def test_is_model_configured_local_with_model(self):
        """Test checking if local LLM is configured with model file"""
        # Setup
        self.ai_service.current_model = "local"
        # The actual implementation checks if local_llm is None
        self.ai_service.local_llm = MagicMock()
        
        # Test and verify
        self.assertTrue(self.ai_service.is_model_configured())
    
    def test_is_model_configured_local_without_model(self):
        """Test checking if local LLM is configured without model file"""
        # Setup
        self.ai_service.current_model = "local"
        # The actual implementation checks if local_llm is None
        self.ai_service.local_llm = None
        
        # Test and verify
        self.assertFalse(self.ai_service.is_model_configured())
    
    @patch.object(AIService, '_openai_completion', return_value="OpenAI response")
    def test_create_completion_openai(self, mock_openai_completion):
        """Test creating a completion with OpenAI"""
        # Setup
        self.ai_service.current_model = "openai"
        
        # Test
        response = self.ai_service._create_completion("system prompt", "user prompt")
        
        # Verify
        self.assertEqual(response, "OpenAI response")
        mock_openai_completion.assert_called_once_with("system prompt", "user prompt")
    
    @patch.object(AIService, '_anthropic_completion', return_value="Anthropic response")
    def test_create_completion_anthropic(self, mock_anthropic_completion):
        """Test creating a completion with Anthropic"""
        # Setup
        self.ai_service.current_model = "claude"
        
        # Test
        response = self.ai_service._create_completion("system prompt", "user prompt")
        
        # Verify
        self.assertEqual(response, "Anthropic response")
        mock_anthropic_completion.assert_called_once_with("system prompt", "user prompt")
    
    @patch.object(AIService, '_local_completion', return_value="Local LLM response")
    def test_create_completion_local(self, mock_local_completion):
        """Test creating a completion with local LLM"""
        # Setup
        self.ai_service.current_model = "local"
        
        # Test
        response = self.ai_service._create_completion("system prompt", "user prompt")
        
        # Verify
        self.assertEqual(response, "Local LLM response")
        mock_local_completion.assert_called_once_with("system prompt", "user prompt")
    
    def test_create_completion_unconfigured_model(self):
        """Test creating a completion with unconfigured model"""
        # Setup
        self.ai_service.current_model = "openai"
        # Make sure the OpenAI client is None to simulate an unconfigured model
        self.ai_service.openai_client = None
        
        # Test
        response = self.ai_service._create_completion("system prompt", "user prompt")
        
        # Verify
        self.assertIsNone(response)
    
    def test_get_explanation(self):
        """Test getting an explanation of code"""
        # Setup
        self.ai_service._create_completion = MagicMock(return_value="Explanation of code")
        
        # Test
        explanation = self.ai_service.get_explanation("def add(a, b): return a + b", "Context")
        
        # Verify
        self.assertEqual(explanation, "Explanation of code")
        self.ai_service._create_completion.assert_called_once()
        system_prompt = self.ai_service._create_completion.call_args[0][0]
        # Check for part of the actual prompt that is used
        self.assertIn("code explainer", system_prompt.lower())
    
    def test_get_improvement(self):
        """Test getting an improvement for code"""
        # Setup
        # The actual format returned by the service includes section headers and the original code
        mock_response = """# EXPLANATION
EXPLANATION: This is better
IMPROVED_CODE: def improved(): pass
# IMPROVED_CODE
def improved(): pass"""
        self.ai_service._create_completion = MagicMock(return_value=mock_response)
        
        # Test
        improvement = self.ai_service.get_improvement("def old(): pass", "Context")
        
        # Verify
        self.assertEqual(improvement, mock_response)
        self.ai_service._create_completion.assert_called_once()
        system_prompt = self.ai_service._create_completion.call_args[0][0]
        # Check for part of the actual prompt that is used
        self.assertIn("expert code improver", system_prompt.lower())
    
    def test_generate_code(self):
        """Test generating code based on a specification"""
        # Setup
        self.ai_service._create_completion = MagicMock(return_value="def generated(): pass")
        
        # Test
        generated = self.ai_service.generate_code("Create a function", "Context")
        
        # Verify
        self.assertEqual(generated, "def generated(): pass")
        self.ai_service._create_completion.assert_called_once()
        system_prompt = self.ai_service._create_completion.call_args[0][0]
        # Check for part of the actual prompt that is used
        self.assertIn("expert code generator", system_prompt.lower())
    
    def test_analyze_code(self):
        """Test analyzing code complexity and bugs"""
        # Setup
        self.ai_service._create_completion = MagicMock(return_value="Analysis results")
        
        # Test
        analysis = self.ai_service.analyze_code("def complex(): pass", "Context")
        
        # Verify
        self.assertEqual(analysis, "Analysis results")
        self.ai_service._create_completion.assert_called_once()
        system_prompt = self.ai_service._create_completion.call_args[0][0]
        # Check for part of the actual prompt that is used
        self.assertIn("expert code analyzer", system_prompt.lower())
    
    def test_custom_query(self):
        """Test custom query about code"""
        # Setup
        self.ai_service._create_completion = MagicMock(return_value="Query response")
        
        # Test
        response = self.ai_service.custom_query("How does this work?", "Code context")
        
        # Verify
        self.assertEqual(response, "Query response")
        self.ai_service._create_completion.assert_called_once()


if __name__ == "__main__":
    unittest.main()