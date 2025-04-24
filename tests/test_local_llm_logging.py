"""
Test the local LLM logging functionality
"""
import unittest
import logging
import io
import sys
from unittest.mock import MagicMock, patch

from aivim.ai_service import AIService


class TestLocalLLMLogging(unittest.TestCase):
    """Test the logging of local LLM output"""
    
    @patch('aivim.ai_service.LLAMA_AVAILABLE', True)
    def setUp(self):
        """Set up the test environment"""
        # Create a fake local LLM
        self.mock_llm = MagicMock()
        self.mock_llm.return_value = {
            "choices": [{"text": "This is the model's response"}]
        }
        
        # Create an AIService with the mock local LLM
        self.ai_service = AIService()
        self.ai_service.local_llm = self.mock_llm
        
        # Set up a logger to capture log output
        self.log_capture = io.StringIO()
        self.log_handler = logging.StreamHandler(self.log_capture)
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger().setLevel(logging.INFO)
        
    def tearDown(self):
        """Clean up after the test"""
        logging.getLogger().removeHandler(self.log_handler)
    
    @patch('aivim.ai_service.LLAMA_AVAILABLE', True)
    @patch('time.time')
    def test_local_llm_stdout_capture(self, mock_time):
        """Test that local LLM stdout output is captured and logged"""
        # Set up time.time() to return predictable values
        mock_time.side_effect = [100, 105]  # Start time and end time
        
        # Set up a test string that the LLM will print to stdout
        test_perf_output = "llama_print_timings: load time = 1234.56 ms\nllama_model_context: estimated tokens: 42\n"
        
        # Create a patched version of sys.stdout that will be temporarily replaced
        mock_stdout = io.StringIO()
        mock_stdout.write(test_perf_output)
        mock_stdout.seek(0)  # Reset to beginning so it can be read
        
        # Execute local completion with the mocked stdout
        with patch('sys.stdout', mock_stdout):
            self.ai_service._local_completion(
                system_prompt="Test system prompt",
                user_prompt="Test user prompt"
            )
        
        # Get and check the captured log
        log_content = self.log_capture.getvalue()
        
        # Verify that the performance output was logged correctly
        self.assertIn("Local LLM perf: llama_print_timings: load time = 1234.56 ms", log_content)
        self.assertIn("Local LLM perf: llama_model_context: estimated tokens: 42", log_content)
        self.assertIn("Local LLM inference completed in 5.00 seconds", log_content)
    
    @patch('aivim.ai_service.LLAMA_AVAILABLE', True)
    def test_local_llm_error_handling(self):
        """Test error handling in local LLM logging"""
        # Make the model raise an exception when called
        self.mock_llm.side_effect = Exception("Test model error")
        
        # Capture the logger output
        with self.assertLogs(level='ERROR') as log_context:
            result = self.ai_service._local_completion(
                system_prompt="Test system prompt",
                user_prompt="Test user prompt"
            )
        
        # Verify that the error was logged correctly
        self.assertIn("ERROR:root:Local LLM error: Test model error", 
                     "\n".join(log_context.output))
        
        # Verify the result is an error message
        self.assertIn("Error using local LLM: Test model error", result)


if __name__ == '__main__':
    unittest.main()