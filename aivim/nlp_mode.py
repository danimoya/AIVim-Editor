
"""
Natural Language Programming mode for AIVim
"""
import curses
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
        # Check for Ctrl+Enter - sends entire script with all tabs as context
        if key == 10 and curses.keyname(key).decode().lower() in ['^j', '^m']:  # Ctrl+Enter (^J or ^M depending on terminal)
            self.handle_ctrl_enter()
            return True
            
        # Check for Shift+Enter - process current section without other tabs as context
        if key == 10 and curses.keyname(key).decode().lower() == 'key_enter':  # This identifies Shift+Enter in many terminals
            self.handle_shift_enter()
            return True
        
        # Handle regular Enter key - just add a new line like in INSERT mode
        if key == 10:  # Regular Enter key
            # Let the editor handle it in INSERT mode (don't process the whole script)
            self.schedule_update()  # Still schedule an update for the changes
            return False  # Let normal INSERT mode handle the new line
            
        # Let the editor handle most keys normally (like in INSERT mode)
        # but schedule an update when content changes
        self.schedule_update()
        return False  # Let the editor's normal INSERT mode handle the key
        
    def handle_shift_enter(self) -> None:
        """
        Handle Shift+Enter in NLP mode - processes current section without other tabs as context
        This provides more focused processing of just the current content
        """
        if self.processing:
            self.editor.set_status_message("Already processing NLP request, please wait...")
            return
            
        # Scan for NLP sections before processing
        self.scan_buffer_for_nlp_sections()
        
        # If we found sections, process them
        if self.nlp_sections:
            self.processing = True
            self.editor.set_status_message("Processing NLP sections (current file only)...")
            
            # Start processing in a separate thread
            thread = threading.Thread(
                target=self._process_nlp_sections_thread
            )
            thread.daemon = True
            thread.start()
        else:
            self.editor.set_status_message("No NLP sections found to process")
            self.cancel_pending_updates()
        
    def handle_ctrl_enter(self) -> None:
        """
        Handle Ctrl+Enter in NLP mode - sends entire script with all tabs as context
        This is a special mode that provides maximum context to the AI
        """
        if self.processing:
            self.editor.set_status_message("Already processing NLP request, please wait...")
            return
            
        self.processing = True
        self.editor.set_status_message("Processing entire script with all tabs as context...")
        
        # Start processing in a separate thread
        thread = threading.Thread(
            target=self._process_entire_script_thread
        )
        thread.daemon = True
        thread.start()
        
    def _process_entire_script_thread(self) -> None:
        """Thread function to process the entire script with all tabs as context"""
        try:
            # Get all lines in the current buffer
            lines = self.editor.buffer.get_lines()
            script_text = "\n".join(lines)
            
            # Get all open tabs for context
            file_contexts = self._get_tab_contexts()
            
            # Prepare a context string with all other open files
            file_context_text = ""
            for filename, content in file_contexts.items():
                file_context_text += f"\n--- {filename} ---\n{content}\n"
                
            # Prepare the system prompt for full script processing
            system_prompt = (
                "You are a Natural Language Programming assistant with deep coding expertise. "
                "Your task is to analyze the entire script and its context, then implement any "
                "requested changes or additions as commented in the script. "
                "Format code clearly with appropriate comments explaining your implementation. "
                "Return the entire updated script with your changes integrated."
            )
            
            # Prepare the user prompt
            user_prompt = f"""
# Current script:
```
{script_text}
```

# Other files in the project for context:
{file_context_text}

Analyze this entire script and implement any natural language requests marked with #nlp comments.
Preserve the overall structure and functionality while making the requested changes.
Return the complete updated script with your implementations.
"""
            
            # Use the AI service to process
            translated_code = None
            try:
                if self.editor.ai_service:
                    translated_code = self.editor.ai_service._create_completion(system_prompt, user_prompt)
            except Exception as e:
                logging.error(f"Error processing entire script: {str(e)}")
                
            if translated_code and self.processing:
                # Update the buffer with the translated code
                with self.editor.thread_lock:
                    # Store the current version in history
                    self.editor.history.add_version(self.editor.buffer.get_lines())
                    
                    # Split the translated code into lines
                    new_lines = translated_code.strip().split("\n")
                    
                    # Replace the entire buffer
                    self.editor.buffer.clear()
                    for i, line in enumerate(new_lines):
                        self.editor.buffer.insert_line(i, line)
                        
                    # Store the updated version in history
                    self.editor.history.add_version(
                        self.editor.buffer.get_lines(),
                        {"action": "nlp_full_script", "start_line": 0, "end_line": len(new_lines) - 1}
                    )
                    
                    # Set status message
                    self.editor.set_status_message("Full script processed with all context")
                
        except Exception as e:
            logging.error(f"Error in _process_entire_script_thread: {str(e)}")
            with self.editor.thread_lock:
                self.editor.set_status_message(f"Error processing script: {str(e)}")
                
        finally:
            self.processing = False
        
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
        """
        Scan the buffer to identify NLP sections marked with inline #nlp format
        
        New format:
        - Single line: '#nlp <query>' processes just that single line
        - Multi-line: Multiple '#nlp' marks scattered in file define a section
        """
        self.nlp_sections = []
        lines = self.editor.buffer.get_lines()
        
        # Track single-line queries with specific instructions
        for i, line in enumerate(lines):
            # Check for #nlp with query on same line
            if "#nlp " in line:
                # This is a single-line query with instructions
                query = line.split("#nlp ", 1)[1]
                self.nlp_sections.append((i, i, query))
            elif "//nlp " in line:
                query = line.split("//nlp ", 1)[1]
                self.nlp_sections.append((i, i, query))
            elif "<!--nlp " in line:
                query = line.split("<!--nlp ", 1)[1].split("-->", 1)[0]
                self.nlp_sections.append((i, i, query))
            
        # Track multi-line sections marked with just #nlp
        in_nlp_section = False
        start_line = 0
        
        for i, line in enumerate(lines):
            # Check for lone #nlp markers (without trailing space and query)
            if line.strip() == "#nlp" or line.strip() == "//nlp" or line.strip() == "<!--nlp-->":
                if not in_nlp_section:
                    # Start of multi-line section
                    in_nlp_section = True
                    start_line = i
                else:
                    # End of multi-line section
                    self.nlp_sections.append((start_line, i))
                    in_nlp_section = False
                    
        # Handle case where a multi-line section was started but not ended
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
                    # We need to handle both 2-tuple and 3-tuple formats
                    inside_existing_section = False
                    for section in self.nlp_sections:
                        # Handle both 2-tuple and 3-tuple formats safely
                        if len(section) >= 2:  # Could be 2 or 3 elements
                            # Access by index rather than unpacking to avoid ValueError
                            section_start = section[0]
                            section_end = section[1]
                            if section_start <= comment_start <= section_end:
                                inside_existing_section = True
                                break
                    
                    if not inside_existing_section:
                        self.nlp_sections.append((comment_start, i - 1))
                comment_start = None
                
        # Handle case where a comment block goes to the end of the file
        if comment_start is not None:
            if len(lines) - comment_start > 2:  # Longer comment blocks
                # We need to handle both 2-tuple and 3-tuple formats
                inside_existing_section = False
                for section in self.nlp_sections:
                    # Handle both 2-tuple and 3-tuple formats safely
                    if len(section) >= 2:  # Could be 2 or 3 elements
                        # Access by index rather than unpacking to avoid ValueError
                        section_start = section[0]
                        section_end = section[1]
                        if section_start <= comment_start <= section_end:
                            inside_existing_section = True
                            break
                
                if not inside_existing_section:
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
        
        # Set status message and start loading animation
        self.editor.set_status_message("Translating natural language to code...")
        self.editor.display.start_loading_animation("Translating natural language to code")
        
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
            for section in self.nlp_sections:
                if not self.processing:
                    # Processing was canceled
                    break
                    
                # Check for tuple format: (start_line, end_line) or (start_line, end_line, query)
                if len(section) == 2:
                    start_line, end_line = section
                    user_query = None
                elif len(section) == 3:
                    start_line, end_line, user_query = section
                else:
                    continue  # Invalid format
                    
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
                    is_comment_section,
                    user_query
                )
                
                if translated_code and self.processing:
                    # Update the buffer with the translated code
                    with self.editor.thread_lock:
                        # Store the current version in history
                        self.editor.history.add_version(self.editor.buffer.get_lines())
                        
                        # Import necessary modules at the beginning to avoid unbound errors
                        import json
                        import re
                        
                        try:
                            # Try to parse the response as JSON
                            try:
                                # First, try parsing directly
                                response_data = json.loads(translated_code)
                            except json.JSONDecodeError:
                                # If direct parsing failed, try to extract JSON from markdown code blocks
                                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', translated_code)
                                if json_match:
                                    response_data = json.loads(json_match.group(1))
                                else:
                                    # Fallback: treat as regular text (backward compatibility)
                                    raise ValueError("No valid JSON found in response")
                            
                            # Handle the structured JSON response with line-specific insertions
                            if "code_blocks" in response_data and isinstance(response_data["code_blocks"], list):
                                # Sort code blocks by target line (highest first to avoid line number shifts)
                                code_blocks = sorted(
                                    response_data["code_blocks"], 
                                    key=lambda block: block.get("target_line", 0),
                                    reverse=True
                                )
                                
                                # Process each code block
                                for block in code_blocks:
                                    target_line = block.get("target_line", start_line)
                                    code = block.get("code", "")
                                    replace_lines = block.get("replace_lines", 0)
                                    
                                    # Ensure valid line numbers
                                    target_line = max(0, min(target_line, len(self.editor.buffer.get_lines())))
                                    
                                    # Delete lines to be replaced
                                    for _ in range(replace_lines):
                                        if target_line < len(self.editor.buffer.get_lines()):
                                            self.editor.buffer.delete_line(target_line)
                                    
                                    # Split code into lines and insert
                                    code_lines = code.strip().split("\n")
                                    
                                    # Add user query comment if applicable
                                    if user_query and len(code_blocks) == 1:  # Only for single blocks
                                        comment_line = f"# AI Done: {user_query}"
                                        code_lines.insert(0, comment_line)
                                    
                                    # Insert the new code lines
                                    for i, line in enumerate(code_lines):
                                        self.editor.buffer.insert_line(target_line + i, line)
                                
                                # Store explanation if provided
                                if "explanation" in response_data and isinstance(response_data["explanation"], str):
                                    explanation = response_data["explanation"]
                                    logging.info(f"NLP Translation Explanation: {explanation}")
                                    
                                # Store the updated version in history
                                self.editor.history.add_version(
                                    self.editor.buffer.get_lines(),
                                    {"action": "nlp_translation_json", "query": user_query}
                                )
                                
                            else:
                                raise ValueError("Invalid JSON structure: missing code_blocks array")
                                
                        except (json.JSONDecodeError, ValueError) as json_error:
                            # Fallback to the old method for backward compatibility
                            logging.warning(f"Failed to parse JSON response: {str(json_error)}. Using legacy mode.")
                            
                            # Split the translated code into lines
                            new_lines = translated_code.strip().split("\n")
                            
                            # For single-line queries with user query, append comment 
                            # "AI Done: <user_query>" before the code
                            if user_query:
                                comment_line = f"# AI Done: {user_query}"
                                new_lines.insert(0, comment_line)
                                
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
                        
                        # We need to adjust the line numbers for the remaining NLP sections
                        # Determine how many lines have been added/removed
                        # This code is designed to avoid referencing problematic variables
                        
                        # Original length of the section
                        original_section_length = end_line - start_line + 1
                        
                        # Current length (after modification) is the difference between
                        # the current buffer size and original size, plus the original section size
                        current_buffer_size = len(self.editor.buffer.get_lines())
                        line_delta = current_buffer_size - len(lines) - original_section_length
                        
                        # Skip adjustment if line_delta is extreme (safety check)
                        if abs(line_delta) < 100:  # Reasonable limit for code changes
                            # Adjust sections after this one
                            for i, section_to_adjust in enumerate(self.nlp_sections):
                                if isinstance(section_to_adjust, tuple):
                                    if len(section_to_adjust) == 2:
                                        s, e = section_to_adjust
                                        if s > end_line:
                                            self.nlp_sections[i] = (s + line_delta, e + line_delta)
                                    elif len(section_to_adjust) == 3:
                                        s, e, q = section_to_adjust
                                        if s > end_line:
                                            self.nlp_sections[i] = (s + line_delta, e + line_delta, q)
            
            # Processing complete
            with self.editor.thread_lock:
                if self.processing:
                    # Stop loading animation
                    self.editor.display.stop_loading_animation()
                    self.editor.set_status_message("Natural language translation complete")
                
        except Exception as e:
            logging.error(f"Error processing NLP sections: {str(e)}")
            with self.editor.thread_lock:
                # Stop loading animation on error
                self.editor.display.stop_loading_animation()
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
                              is_comment_section: bool,
                              user_query: Optional[str] = None) -> Optional[str]:
        """
        Translate natural language to code using the AI service
        
        Args:
            nlp_text: The natural language text to translate
            context_before: The code context before the NLP section
            context_after: The code context after the NLP section
            file_contexts: Dictionary mapping filenames to their content
            is_comment_section: Whether this is a comment section
            user_query: Optional explicit query from inline #nlp format
            
        Returns:
            Translated code or None if translation failed
        """
        if not self.editor.ai_service:
            return nlp_text  # No AI service available
            
        # Prepare context for the AI
        file_context_text = ""
        for filename, content in file_contexts.items():
            file_context_text += f"\n--- {filename} ---\n{content}\n"
            
        # Prepare the system prompt with JSON output format
        system_prompt = (
            "You are a Natural Language Programming assistant. "
            "Your task is to translate natural language instructions into code. "
            "Preserve any existing code and comments in the input. "
            "If the input is entirely comments, translate the comments into code that implements the described functionality. "
            "If the input is mixed with code and comments, update the code according to the natural language instructions. "
            "Maintain the style and structure of the surrounding code for consistency. "
            "Your response must be a valid JSON object with the following structure: "
            "{"
            "  \"explanation\": \"Brief explanation of the code generation or changes\", "
            "  \"code_blocks\": ["
            "    {"
            "      \"target_line\": 123, "  # Line number where this code should be inserted
            "      \"code\": \"def example():\\n    return True\", "  # The code to insert
            "      \"replace_lines\": 2 "  # Number of original lines to replace (0 for pure insertion)
            "    }, "
            "    {... more code blocks if needed ...}"
            "  ]"
            "}"
        )
        
        # Prepare the user prompt with line numbers
        # Get all lines from buffer for line numbering context
        all_lines = self.editor.buffer.get_lines()
        
        # Get line numbers for this section
        # We're in _translate_nlp_to_code so we need to extract start/end line from text itself
        # The caller will provide these as part of the context in the original section 
        # processing loop where start_line and end_line are defined
        section_line_count = len(nlp_text.split("\n"))
        estimated_start_line = 0
        
        # Try to estimate the start line from the context
        lines_before = len(context_before.split("\n")) if context_before else 0
        if lines_before > 0:
            estimated_start_line = max(0, lines_before)
            
        # Format section with line numbers
        numbered_nlp_text = "\n".join([f"{estimated_start_line + i}: {line}" for i, line in enumerate(nlp_text.split("\n"))])
        
        # Format context before with line numbers
        context_before_lines = context_before.split("\n")
        start_before = max(0, estimated_start_line - len(context_before_lines))
        numbered_context_before = "\n".join([f"{start_before + i}: {line}" for i, line in enumerate(context_before_lines)])
        
        # Format context after with line numbers
        context_after_lines = context_after.split("\n")
        estimated_end_line = estimated_start_line + section_line_count - 1
        start_after = estimated_end_line + 1
        numbered_context_after = "\n".join([f"{start_after + i}: {line}" for i, line in enumerate(context_after_lines)])
        
        if is_comment_section:
            user_prompt = f"""
# Natural language comments to translate to code (with line numbers):
```
{numbered_nlp_text}
```

# Context code before this section (with line numbers):
```
{numbered_context_before}
```

# Context code after this section (with line numbers):
```
{numbered_context_after}
```

# Other files in the project for context:
{file_context_text}

Translate the natural language comments into working code that implements the described functionality.
If the comment refers to modifications of existing code, integrate those changes.
Preserve important comments in the output but implement the described functionality in code.

In your JSON response, specify the exact target_line for each code block, considering the original line numbers.
For replacements, use 'replace_lines' to indicate how many original lines should be replaced.
For insertions, set 'replace_lines' to 0.
"""
        else:
            user_prompt = f"""
# Natural language and code section to process (with line numbers):
```
{numbered_nlp_text}
```

# Context code before this section (with line numbers):
```
{numbered_context_before}
```

# Context code after this section (with line numbers):
```
{numbered_context_after}
```

# Other files in the project for context:
{file_context_text}

Translate any natural language instructions in this section into working code.
Preserve existing code unless the natural language instructions specifically ask to modify it.
Preserve important comments but implement the described functionality in code.

In your JSON response, specify the exact target_line for each code block, considering the original line numbers.
For replacements, use 'replace_lines' to indicate how many original lines should be replaced.
For insertions, set 'replace_lines' to 0.
"""
        
        # Use the AI service to translate
        try:
            translated_code = self.editor.ai_service._create_completion(system_prompt, user_prompt)
            return translated_code
        except Exception as e:
            logging.error(f"Error translating NLP to code: {str(e)}")
            return None
