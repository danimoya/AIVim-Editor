
"""
Natural Language Programming mode for AIVim
"""
import logging
import re
import threading
import time
from typing import List, Dict, Any, Optional, Tuple

class NLPHandler:
    """
    Handler for Natural Language Programming mode
    Translates natural language to code while preserving comments and structure
    """
    def __init__(self, editor):
        """
        Initialize the NLP handler
        
        Args:
            editor: Reference to the editor instance
        """
        self.editor = editor
        self.processing = False
        self.processing_thread = None
        self.pending_updates = []
        self.last_update_time = 0
        self.update_debounce_ms = 1000  # Wait 1 second after typing stops before processing
        self.update_timer = None
        self.nlp_sections = []  # List of (start_line, end_line) tuples for NLP sections
        
    def enter_nlp_mode(self) -> None:
        """Enter NLP mode and set up the environment"""
        self.editor.set_status_message("-- NLP MODE -- (Natural Language Programming)")
        self.scan_buffer_for_nlp_sections()
        
    def exit_nlp_mode(self) -> None:
        """Exit NLP mode and clean up"""
        self.cancel_pending_updates()
        
    def handle_key(self, key: int) -> bool:
        """
        Handle key press in NLP mode
        
        Args:
            key: The key code
            
        Returns:
            True if the key was handled, False otherwise
        """
        # Let the editor handle most keys normally (like in INSERT mode)
        # but schedule an update when content changes
        self.schedule_update()
        return False  # Let the editor's normal INSERT mode handle the key
        
    def schedule_update(self) -> None:
        """Schedule an asynchronous update after typing stops"""
        current_time = time.time() * 1000  # Convert to milliseconds
        self.last_update_time = current_time
        
        # Cancel any pending timer
        if self.update_timer:
            self.update_timer.cancel()
            
        # Set a new timer
        self.update_timer = threading.Timer(
            self.update_debounce_ms / 1000.0,  # Convert back to seconds
            self._check_and_process_update
        )
        self.update_timer.daemon = True
        self.update_timer.start()
        
    def _check_and_process_update(self) -> None:
        """Check if we should process an update based on typing activity"""
        current_time = time.time() * 1000  # Convert to milliseconds
        time_since_last_update = current_time - self.last_update_time
        
        if time_since_last_update >= self.update_debounce_ms:
            # Typing has stopped for the debounce period, process the update
            self.process_nlp_sections()
        else:
            # Still typing, reschedule
            self.schedule_update()
            
    def cancel_pending_updates(self) -> None:
        """Cancel any pending updates"""
        if self.update_timer:
            self.update_timer.cancel()
            self.update_timer = None
            
        if self.processing_thread and self.processing_thread.is_alive():
            # Can't really stop the thread, but we can set a flag
            self.processing = False
            
    def scan_buffer_for_nlp_sections(self) -> None:
        """Scan the buffer to identify NLP sections marked with special comments"""
        self.nlp_sections = []
        lines = self.editor.buffer.get_lines()
        
        in_nlp_section = False
        start_line = 0
        
        for i, line in enumerate(lines):
            # Check for NLP section markers
            if "# NLP-BEGIN" in line or "// NLP-BEGIN" in line or "<!-- NLP-BEGIN -->" in line:
                in_nlp_section = True
                start_line = i
            elif "# NLP-END" in line or "// NLP-END" in line or "<!-- NLP-END -->" in line:
                if in_nlp_section:
                    self.nlp_sections.append((start_line, i))
                    in_nlp_section = False
                    
        # Handle case where a section was started but not ended
        if in_nlp_section:
            self.nlp_sections.append((start_line, len(lines) - 1))
            
        # Also identify comment blocks that might be natural language
        self._identify_comment_blocks(lines)
        
    def _identify_comment_blocks(self, lines: List[str]) -> None:
        """
        Identify comment blocks that might contain natural language instructions
        
        Args:
            lines: List of lines in the buffer
        """
        comment_start = None
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check if line is a comment
            is_comment = (line.startswith('#') or 
                         line.startswith('//') or 
                         line.startswith('/*') or 
                         line.startswith('*') or 
                         line.startswith('"""') or 
                         line.startswith("'''"))
                
            if is_comment and comment_start is None:
                # Start of a comment block
                comment_start = i
            elif not is_comment and comment_start is not None:
                # End of a comment block
                if i - comment_start > 2:  # Longer comment blocks are likely natural language
                    # Only add if not already inside an NLP section
                    if not any(start <= comment_start <= end for start, end in self.nlp_sections):
                        self.nlp_sections.append((comment_start, i - 1))
                comment_start = None
                
        # Handle case where a comment block goes to the end of the file
        if comment_start is not None:
            if len(lines) - comment_start > 2:  # Longer comment blocks
                if not any(start <= comment_start <= end for start, end in self.nlp_sections):
                    self.nlp_sections.append((comment_start, len(lines) - 1))
    
    def process_nlp_sections(self) -> None:
        """Process NLP sections and translate to code asynchronously"""
        if self.processing:
            # Already processing, queue this update
            return
            
        # Scan buffer for NLP sections first
        self.scan_buffer_for_nlp_sections()
        
        if not self.nlp_sections:
            return
            
        self.processing = True
        
        # Set status message
        self.editor.set_status_message("Translating natural language to code...")
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(
            target=self._process_nlp_sections_thread
        )
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def _process_nlp_sections_thread(self) -> None:
        """Thread function to process NLP sections"""
        try:
            # Get all open tabs for context
            file_contexts = self._get_tab_contexts()
            
            # Process each NLP section
            for start_line, end_line in self.nlp_sections:
                if not self.processing:
                    # Processing was canceled
                    break
                    
                # Get the text of this section
                lines = self.editor.buffer.get_lines()
                section_lines = lines[start_line:end_line+1]
                section_text = "\n".join(section_lines)
                
                # Check if this is a comment section or a marked NLP section
                is_comment_section = all(self._is_comment_line(line) for line in section_lines)
                
                # Generate appropriate context text
                context_before = "\n".join(lines[max(0, start_line-10):start_line])
                context_after = "\n".join(lines[end_line+1:min(len(lines), end_line+11)])
                
                # Translate the NLP section to code
                translated_code = self._translate_nlp_to_code(
                    section_text, 
                    context_before, 
                    context_after,
                    file_contexts,
                    is_comment_section
                )
                
                if translated_code and self.processing:
                    # Update the buffer with the translated code
                    with self.editor.thread_lock:
                        # Store the current version in history
                        self.editor.history.add_version(self.editor.buffer.get_lines())
                        
                        # Split the translated code into lines
                        new_lines = translated_code.strip().split("\n")
                        
                        # Replace the section with the translated code
                        for _ in range(end_line - start_line + 1):
                            self.editor.buffer.delete_line(start_line)
                            
                        for i, line in enumerate(new_lines):
                            self.editor.buffer.insert_line(start_line + i, line)
                            
                        # Store the updated version in history
                        self.editor.history.add_version(
                            self.editor.buffer.get_lines(),
                            {"action": "nlp_translation", "start_line": start_line, "end_line": start_line + len(new_lines) - 1}
                        )
                        
                        # Update the list of NLP sections
                        # The current section is now updated, so we need to adjust the indices
                        old_length = end_line - start_line + 1
                        new_length = len(new_lines)
                        delta = new_length - old_length
                        
                        # Adjust the remaining sections
                        for i, (s, e) in enumerate(self.nlp_sections):
                            if s > end_line:
                                self.nlp_sections[i] = (s + delta, e + delta)
            
            # Processing complete
            with self.editor.thread_lock:
                if self.processing:
                    self.editor.set_status_message("Natural language translation complete")
                
        except Exception as e:
            logging.error(f"Error processing NLP sections: {str(e)}")
            with self.editor.thread_lock:
                self.editor.set_status_message(f"Error processing NLP: {str(e)}")
                
        finally:
            self.processing = False
    
    def _is_comment_line(self, line: str) -> bool:
        """
        Check if a line is a comment
        
        Args:
            line: The line to check
            
        Returns:
            True if the line is a comment, False otherwise
        """
        line = line.strip()
        return (line.startswith('#') or 
                line.startswith('//') or 
                line.startswith('/*') or 
                line.startswith('*') or 
                line.startswith('"""') or 
                line.startswith("'''") or
                line.startswith('<!--'))
    
    def _get_tab_contexts(self) -> Dict[str, str]:
        """
        Get the context from all open tabs
        
        Returns:
            Dictionary mapping filenames to their content
        """
        contexts = {}
        for tab in self.editor.tabs:
            if tab.filename and tab != self.editor.current_tab:
                contexts[tab.filename] = "\n".join(tab.buffer.get_lines())
        return contexts
    
    def _translate_nlp_to_code(self, 
                              nlp_text: str, 
                              context_before: str, 
                              context_after: str,
                              file_contexts: Dict[str, str],
                              is_comment_section: bool) -> str:
        """
        Translate natural language to code using the AI service
        
        Args:
            nlp_text: The natural language text to translate
            context_before: The code context before the NLP section
            context_after: The code context after the NLP section
            file_contexts: Dictionary mapping filenames to their content
            is_comment_section: Whether this is a comment section
            
        Returns:
            Translated code
        """
        if not self.editor.ai_service:
            return nlp_text  # No AI service available
            
        # Prepare context for the AI
        file_context_text = ""
        for filename, content in file_contexts.items():
            file_context_text += f"\n--- {filename} ---\n{content}\n"
            
        # Prepare the system prompt
        system_prompt = (
            "You are a Natural Language Programming assistant. "
            "Your task is to translate natural language instructions into code. "
            "Preserve any existing code and comments in the input. "
            "If the input is entirely comments, translate the comments into code that implements the described functionality. "
            "If the input is mixed with code and comments, update the code according to the natural language instructions. "
            "Maintain the style and structure of the surrounding code for consistency."
        )
        
        # Prepare the user prompt
        if is_comment_section:
            user_prompt = f"""
# Natural language comments to translate to code:
```
{nlp_text}
```

# Context code before this section:
```
{context_before}
```

# Context code after this section:
```
{context_after}
```

# Other files in the project for context:
{file_context_text}

Translate the natural language comments into working code that implements the described functionality.
If the comment refers to modifications of existing code, integrate those changes.
Preserve important comments in the output but implement the described functionality in code.
"""
        else:
            user_prompt = f"""
# Natural language and code section to process:
```
{nlp_text}
```

# Context code before this section:
```
{context_before}
```

# Context code after this section:
```
{context_after}
```

# Other files in the project for context:
{file_context_text}

Translate any natural language instructions in this section into working code.
Preserve existing code unless the natural language instructions specifically ask to modify it.
Preserve important comments but implement the described functionality in code.
"""
        
        # Use the AI service to translate
        try:
            translated_code = self.editor.ai_service._create_completion(system_prompt, user_prompt)
            return translated_code
        except Exception as e:
            logging.error(f"Error translating NLP to code: {str(e)}")
            return None
