
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
    Enhanced with live detection and real-time processing capabilities
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
        
        # Enhanced live mode features
        self.live_mode_enabled = True  # Enable live NLP detection by default
        self.live_detection_thread = None
        self.last_content_hash = None
        self.nlp_context_cache = {}  # Cache for tab contexts
        self.live_nlp_regions = []  # Detected NLP regions in live mode
        self.processing_queue = []  # Queue of regions to process
        self.visual_indicators = {}  # Visual feedback for live processing
        self.smart_detection_enabled = True  # Enable intelligent NLP detection
        self.last_processed_content = {}  # Track what's been processed to avoid duplicates
        self.live_update_interval = 500  # Check for changes every 500ms in live mode
        
    def enter_nlp_mode(self) -> None:
        """Enter NLP mode and set up the environment"""
        self.editor.set_status_message("-- NLP LIVE MODE -- (Natural Language Programming)")
        self.scan_buffer_for_nlp_sections()
        
        # Start live detection if enabled
        if self.live_mode_enabled:
            self._start_live_detection()
        
    def exit_nlp_mode(self) -> None:
        """Exit NLP mode and clean up"""
        self.cancel_pending_updates()
        self._stop_live_detection()
        
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
                
                # Show a popup dialog with detailed error information
                with self.editor.thread_lock:
                    if not self.editor.display.is_dialog_open():
                        # Determine error type and provide useful information
                        error_message = str(e)
                        error_title = "NLP Error: Network Issue"
                        error_details = []
                        
                        if "timeout" in error_message.lower() or "timed out" in error_message.lower():
                            error_title = "NLP Error: Network Timeout"
                            error_details = [
                                "The request to the AI service timed out.",
                                "",
                                f"Error details: {error_message}",
                                "",
                                "Possible solutions:",
                                "- Check your internet connection",
                                "- Try again when the AI service is less busy",
                                "- Consider using a different AI model",
                                "",
                                "Your script has not been modified.",
                                "Press 'd' to dismiss this message."
                            ]
                        elif "api key" in error_message.lower() or "apikey" in error_message.lower() or "authentication" in error_message.lower():
                            error_title = "NLP Error: API Key Issue"
                            error_details = [
                                "There was a problem with your AI service API key.",
                                "",
                                f"Error details: {error_message}",
                                "",
                                "Please check your API key configuration:",
                                "- Ensure your API key is valid and not expired",
                                "- Verify you have sufficient credits/quota",
                                "- Check that the key has the necessary permissions",
                                "",
                                "Your script has not been modified.",
                                "Press 'd' to dismiss this message."
                            ]
                        else:
                            error_title = "NLP Error: AI Service Issue"
                            error_details = [
                                "An error occurred while communicating with the AI service.",
                                "",
                                f"Error details: {error_message}",
                                "",
                                "Possible solutions:",
                                "- Check your internet connection",
                                "- Verify the AI service is operational",
                                "- Try using a different AI model",
                                "",
                                "Your script has not been modified.",
                                "Press 'd' to dismiss this message."
                            ]
                        
                        self.editor.show_dialog(error_title, error_details)
                
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
                # Set error status message
                self.editor.set_status_message("Error processing script - See popup for details")
                
                # Show a popup dialog with detailed error information
                if not self.editor.display.is_dialog_open():
                    error_details = [
                        "An unexpected error occurred while processing the script.",
                        "",
                        f"Error details: {str(e)}",
                        "",
                        "This may be due to:",
                        "- Syntax errors in the script",
                        "- Unexpected input format",
                        "- Internal processing error",
                        "",
                        "Your script has not been modified.",
                        "Press 'd' to dismiss this message."
                    ]
                    self.editor.show_dialog("NLP Error: Processing Failed", error_details)
                
                # Stop loading animation
                self.editor.display.stop_loading_animation()
                
                # Play a sound to alert the user of the error (if supported)
                try:
                    curses.beep()  # Makes a beep sound if terminal supports it
                except:
                    pass  # Ignore if beep is not supported
                
                # Flash the screen briefly to get user's attention for the error
                try:
                    curses.flash()  # Flash the screen once
                except:
                    pass  # Ignore if flash is not supported
                
        finally:
            self.processing = False
        
    def schedule_update(self) -> None:
        """Schedule an asynchronous update after typing stops"""
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Set a minimum delay between scheduling attempts to prevent excessive refresh
        last_schedule_time = getattr(self, '_last_schedule_time', 0)
        if (current_time - last_schedule_time) < 50:  # Skip if less than 50ms since last schedule
            return
            
        self._last_schedule_time = current_time
        self.last_update_time = current_time
        
        # Cancel any pending timer
        if self.update_timer:
            self.update_timer.cancel()
            
        # Set a new timer with a longer delay to reduce processing frequency
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
            # Typing has stopped for the debounce period
            if self.processing_queue:
                # Process queued regions from live mode
                self._process_queued_regions()
            else:
                # Fall back to standard NLP section processing
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
                    
                    # Play a sound to alert the user that processing is complete (if supported)
                    try:
                        curses.beep()  # Makes a beep sound if terminal supports it
                    except:
                        pass  # Ignore if beep is not supported
                    
                    # Provide very clear notification that processing is done
                    self.editor.set_status_message("✓ NLP TRANSLATION COMPLETE - Press any key to continue editing")
                    
                    # Flash the screen briefly to get user's attention
                    try:
                        curses.flash()  # Flash the screen once
                    except:
                        pass  # Ignore if flash is not supported
                    
                    # Also show a dialog to indicate completion if no dialog is already open
                    if not self.editor.display.is_dialog_open():
                        completion_message = [
                            "Your natural language has been converted to code.",
                            "",
                            "✓ Processing complete",
                            "",
                            "Press 'd' to close this dialog and continue editing.",
                        ]
                        self.editor.show_dialog("NLP Translation Complete", completion_message)
                
        except Exception as e:
            logging.error(f"Error processing NLP sections: {str(e)}")
            with self.editor.thread_lock:
                # Stop loading animation on error
                self.editor.display.stop_loading_animation()
                
                # Play a sound to alert the user of the error (if supported)
                try:
                    curses.beep()  # Makes a beep sound if terminal supports it
                except:
                    pass  # Ignore if beep is not supported
                
                error_msg = f"ERROR PROCESSING NLP: {str(e)}"
                self.editor.set_status_message(error_msg)
                
                # Flash the screen briefly to get user's attention for the error
                try:
                    curses.flash()  # Flash the screen once
                except:
                    pass  # Ignore if flash is not supported
                
                # Show a dialog with more detailed error info if no dialog is already open
                if not self.editor.display.is_dialog_open():
                    error_details = [
                        "An error occurred during NLP processing:",
                        "",
                        f"{str(e)}",
                        "",
                        "This may be due to network issues, API limits, or syntax problems.",
                        "You can still continue editing normally.",
                        "Press 'd' to dismiss this message."
                    ]
                    self.editor.show_dialog("NLP Processing Error", error_details)
                
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
            
            # Show a popup dialog with detailed error information
            with self.editor.thread_lock:
                if not self.editor.display.is_dialog_open():
                    # Determine error type and provide useful information
                    error_message = str(e)
                    error_title = "NLP Error: Network Issue"
                    error_details = []
                    
                    if "timeout" in error_message.lower() or "timed out" in error_message.lower():
                        error_title = "NLP Error: Network Timeout"
                        error_details = [
                            "The request to the AI service timed out.",
                            "",
                            f"Error details: {error_message}",
                            "",
                            "Possible solutions:",
                            "- Check your internet connection",
                            "- Try again when the AI service is less busy",
                            "- Consider using a different AI model",
                            "",
                            "The original text has been preserved.",
                            "Press 'd' to dismiss this message."
                        ]
                    elif "api key" in error_message.lower() or "apikey" in error_message.lower() or "authentication" in error_message.lower():
                        error_title = "NLP Error: API Key Issue"
                        error_details = [
                            "There was a problem with your AI service API key.",
                            "",
                            f"Error details: {error_message}",
                            "",
                            "Please check your API key configuration:",
                            "- Ensure your API key is valid and not expired",
                            "- Verify you have sufficient credits/quota",
                            "- Check that the key has the necessary permissions",
                            "",
                            "The original text has been preserved.",
                            "Press 'd' to dismiss this message."
                        ]
                    else:
                        error_title = "NLP Error: AI Service Issue"
                        error_details = [
                            "An error occurred while communicating with the AI service.",
                            "",
                            f"Error details: {error_message}",
                            "",
                            "Possible solutions:",
                            "- Check your internet connection",
                            "- Verify the AI service is operational",
                            "- Try using a different AI model",
                            "",
                            "The original text has been preserved.",
                            "Press 'd' to dismiss this message."
                        ]
                    
                    self.editor.show_dialog(error_title, error_details)
            
            # Return the original text, so we don't modify the user's content
            return nlp_text
    
    def _start_live_detection(self) -> None:
        """Start the live NLP detection thread"""
        if self.live_detection_thread and self.live_detection_thread.is_alive():
            return  # Already running
            
        self.live_detection_thread = threading.Thread(
            target=self._live_detection_loop,
            daemon=True
        )
        self.live_detection_thread.start()
        
    def _stop_live_detection(self) -> None:
        """Stop the live NLP detection thread"""
        self.live_mode_enabled = False
        if self.live_detection_thread:
            self.live_detection_thread.join(timeout=1.0)
            
    def _live_detection_loop(self) -> None:
        """Background thread for live NLP detection"""
        while self.live_mode_enabled and self.editor.mode == "NLP":
            try:
                # Get current buffer content
                current_lines = self.editor.buffer.get_lines()
                current_content = "\n".join(current_lines)
                
                # Calculate content hash to detect changes
                import hashlib
                content_hash = hashlib.md5(current_content.encode()).hexdigest()
                
                # Only process if content has changed
                if content_hash != self.last_content_hash:
                    self.last_content_hash = content_hash
                    
                    # Detect NLP regions intelligently
                    self._detect_nlp_regions_smart(current_lines)
                    
                    # Process detected regions
                    self._process_live_nlp_regions()
                    
                # Sleep before next check
                time.sleep(self.live_update_interval / 1000.0)
                
            except Exception as e:
                logging.error(f"Error in live detection loop: {str(e)}")
                time.sleep(1.0)  # Sleep longer on error
                
    def _detect_nlp_regions_smart(self, lines: List[str]) -> None:
        """
        Intelligently detect NLP regions in the buffer
        This method differentiates between natural language and code
        """
        self.live_nlp_regions = []
        
        # First, check for explicit NLP markers (backward compatibility)
        self.scan_buffer_for_nlp_sections()
        for section in self.nlp_sections:
            if len(section) >= 2:
                self.live_nlp_regions.append({
                    'start': section[0],
                    'end': section[1],
                    'type': 'explicit',
                    'query': section[2] if len(section) > 2 else None,
                    'confidence': 1.0
                })
        
        if not self.smart_detection_enabled:
            return
            
        # Smart detection: Look for patterns that indicate natural language
        in_potential_nlp = False
        potential_start = 0
        nlp_indicators = 0
        
        for i, line in enumerate(lines):
            # Skip empty lines
            if not line.strip():
                continue
                
            # Check if line looks like natural language
            is_nlp_line, confidence = self._is_natural_language_line(line)
            
            if is_nlp_line and not in_potential_nlp:
                # Start of potential NLP region
                in_potential_nlp = True
                potential_start = i
                nlp_indicators = 1
            elif is_nlp_line and in_potential_nlp:
                # Continue NLP region
                nlp_indicators += 1
            elif not is_nlp_line and in_potential_nlp:
                # End of NLP region
                if nlp_indicators >= 2:  # At least 2 lines of NLP
                    # Check if this region overlaps with existing explicit regions
                    overlaps = False
                    for region in self.live_nlp_regions:
                        if (potential_start <= region['end'] and i - 1 >= region['start']):
                            overlaps = True
                            break
                            
                    if not overlaps:
                        self.live_nlp_regions.append({
                            'start': potential_start,
                            'end': i - 1,
                            'type': 'smart',
                            'query': None,
                            'confidence': min(nlp_indicators * 0.2, 0.9)  # Max 90% confidence
                        })
                        
                in_potential_nlp = False
                nlp_indicators = 0
                
        # Handle case where NLP region extends to end of file
        if in_potential_nlp and nlp_indicators >= 2:
            overlaps = False
            for region in self.live_nlp_regions:
                if potential_start <= region['end']:
                    overlaps = True
                    break
                    
            if not overlaps:
                self.live_nlp_regions.append({
                    'start': potential_start,
                    'end': len(lines) - 1,
                    'type': 'smart',
                    'query': None,
                    'confidence': min(nlp_indicators * 0.2, 0.9)
                })
                
    def _is_natural_language_line(self, line: str) -> Tuple[bool, float]:
        """
        Determine if a line is natural language rather than code
        Returns (is_nlp, confidence)
        """
        stripped = line.strip()
        
        # Empty lines are not NLP
        if not stripped:
            return False, 0.0
            
        # Check for explicit code patterns (definitely not NLP)
        code_patterns = [
            r'^\s*import\s+',  # Import statements
            r'^\s*from\s+\w+\s+import',  # From imports
            r'^\s*def\s+\w+\s*\(',  # Function definitions
            r'^\s*class\s+\w+',  # Class definitions
            r'^\s*(if|elif|else|for|while|try|except|finally|with)\s*[:\(]',  # Control structures
            r'^\s*return\s+',  # Return statements
            r'^\s*\w+\s*=\s*',  # Variable assignments
            r'^\s*\w+\.\w+\(',  # Method calls
            r'^\s*[\{\}\[\]\(\)]',  # Brackets
            r'^\s*[+-/*%=<>!&|~^]+$',  # Operators only
        ]
        
        for pattern in code_patterns:
            if re.match(pattern, line):
                return False, 0.0
                
        # Check if it's a comment that looks like natural language
        if self._is_comment_line(line):
            # Remove comment markers
            comment_text = stripped
            for marker in ['#', '//', '/*', '*/', '<!--', '-->', '"""', "'''"]:
                comment_text = comment_text.replace(marker, '').strip()
                
            # Check for natural language indicators in comments
            nlp_comment_indicators = [
                r'^(create|make|add|implement|build|design|write)',  # Action verbs
                r'^(todo|fixme|note|hack|bug|issue)',  # Development markers
                r'(should|must|need|want|require)',  # Modal verbs
                r'(please|ensure|make sure|be sure)',  # Polite requests
                r'\?$',  # Questions
                r'^(this|these|that|those)\s+(is|are|should|must)',  # Demonstratives
                r'(function|method|class|module|variable)\s+(that|which)',  # Technical descriptions
            ]
            
            confidence = 0.3  # Base confidence for comments
            for pattern in nlp_comment_indicators:
                if re.search(pattern, comment_text, re.IGNORECASE):
                    confidence += 0.2
                    
            return True, min(confidence, 0.9)
            
        # Check for prose-like patterns (not in comments)
        prose_indicators = [
            r'^[A-Z][a-z]+\s+',  # Starts with capitalized word
            r'\.$',  # Ends with period
            r'[,;]\s+\w+',  # Contains commas or semicolons with words after
            r'\s+(and|or|but|with|for|to|from|by|in|on|at)\s+',  # Common English connectives
            r'^(The|This|That|These|Those|It|We|You|They)\s+',  # Common pronouns
        ]
        
        confidence = 0.0
        matches = 0
        for pattern in prose_indicators:
            if re.search(pattern, stripped):
                matches += 1
                
        if matches >= 2:  # At least 2 prose indicators
            confidence = min(matches * 0.3, 0.8)
            return True, confidence
            
        return False, 0.0
        
    def _process_live_nlp_regions(self) -> None:
        """Process detected NLP regions in live mode"""
        import hashlib
        
        # Filter regions that haven't been processed yet
        regions_to_process = []
        
        for region in self.live_nlp_regions:
            # Create a unique key for this region
            region_key = f"{region['start']}-{region['end']}-{region['type']}"
            
            # Get content of the region
            lines = self.editor.buffer.get_lines()
            region_content = "\n".join(lines[region['start']:region['end']+1])
            content_hash = hashlib.md5(region_content.encode()).hexdigest()
            
            # Check if this region has been processed with the same content
            if region_key not in self.last_processed_content or self.last_processed_content[region_key] != content_hash:
                regions_to_process.append(region)
                self.last_processed_content[region_key] = content_hash
                
        # Process regions with high confidence first
        regions_to_process.sort(key=lambda r: r['confidence'], reverse=True)
        
        for region in regions_to_process:
            if region['confidence'] >= 0.6:  # Only process high-confidence regions automatically
                self._queue_region_for_processing(region)
                
    def _queue_region_for_processing(self, region: Dict[str, Any]) -> None:
        """Queue a region for asynchronous processing"""
        # Add visual indicator
        self._add_visual_indicator(region)
        
        # Add to processing queue
        self.processing_queue.append(region)
        
        # Schedule processing if not already processing
        if not self.processing:
            self.schedule_update()
            
    def _add_visual_indicator(self, region: Dict[str, Any]) -> None:
        """Add visual feedback for regions being processed"""
        # Store visual indicator info
        self.visual_indicators[f"{region['start']}-{region['end']}"] = {
            'type': 'processing',
            'start_time': time.time()
        }
        
        # Update status message
        with self.editor.thread_lock:
            if region['type'] == 'smart':
                self.editor.set_status_message(f"Detected NLP region (lines {region['start']+1}-{region['end']+1})")
            else:
                self.editor.set_status_message(f"Processing NLP section (lines {region['start']+1}-{region['end']+1})")
                
    def toggle_live_mode(self) -> None:
        """Toggle live NLP detection on/off"""
        self.live_mode_enabled = not self.live_mode_enabled
        
        if self.live_mode_enabled:
            self._start_live_detection()
            self.editor.set_status_message("NLP Live Mode: ON - Auto-detecting natural language")
        else:
            self._stop_live_detection()
            self.editor.set_status_message("NLP Live Mode: OFF - Manual processing only")
            
    def toggle_smart_detection(self) -> None:
        """Toggle smart NLP detection on/off"""
        self.smart_detection_enabled = not self.smart_detection_enabled
        
        if self.smart_detection_enabled:
            self.editor.set_status_message("Smart NLP Detection: ON - Intelligent language detection")
        else:
            self.editor.set_status_message("Smart NLP Detection: OFF - Explicit markers only")
            self.live_nlp_regions = [r for r in self.live_nlp_regions if r['type'] == 'explicit']
            
    def _process_queued_regions(self) -> None:
        """Process regions queued from live detection"""
        if not self.processing_queue or self.processing:
            return
            
        self.processing = True
        
        # Process the first region in the queue
        region = self.processing_queue.pop(0)
        
        # Set status message and start loading animation
        self.editor.set_status_message(f"Processing NLP region (lines {region['start']+1}-{region['end']+1})...")
        self.editor.display.start_loading_animation("Processing natural language...")
        
        # Start processing in a separate thread
        self.processing_thread = threading.Thread(
            target=self._process_single_region_thread,
            args=(region,)
        )
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
    def _process_single_region_thread(self, region: Dict[str, Any]) -> None:
        """Thread function to process a single NLP region"""
        try:
            # Get all open tabs for context
            file_contexts = self._get_tab_contexts()
            
            # Get the text of this region
            lines = self.editor.buffer.get_lines()
            start_line = region['start']
            end_line = region['end']
            section_lines = lines[start_line:end_line+1]
            section_text = "\n".join(section_lines)
            
            # Check if this is a comment section
            is_comment_section = all(self._is_comment_line(line) for line in section_lines if line.strip())
            
            # Generate appropriate context
            context_before = "\n".join(lines[max(0, start_line-10):start_line])
            context_after = "\n".join(lines[end_line+1:min(len(lines), end_line+11)])
            
            # Translate the NLP section to code
            translated_code = self._translate_nlp_to_code(
                section_text, 
                context_before, 
                context_after,
                file_contexts,
                is_comment_section,
                region.get('query')
            )
            
            if translated_code and self.processing:
                # Update the buffer with the translated code
                with self.editor.thread_lock:
                    # Store the current version in history
                    self.editor.history.add_version(self.editor.buffer.get_lines())
                    
                    # Process the translation result (same as existing code)
                    import json
                    import re
                    
                    try:
                        # Try to parse as JSON (new format)
                        try:
                            response_data = json.loads(translated_code)
                        except json.JSONDecodeError:
                            # Extract JSON from markdown
                            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', translated_code)
                            if json_match:
                                response_data = json.loads(json_match.group(1))
                            else:
                                raise ValueError("No valid JSON found")
                        
                        # Handle structured response
                        if "code_blocks" in response_data:
                            self._apply_code_blocks(response_data, start_line, region.get('query'))
                        else:
                            raise ValueError("Invalid JSON structure")
                            
                    except (json.JSONDecodeError, ValueError):
                        # Fallback to legacy processing
                        self._apply_legacy_translation(translated_code, start_line, end_line, region.get('query'))
                        
                    # Remove visual indicator
                    region_key = f"{region['start']}-{region['end']}"
                    if region_key in self.visual_indicators:
                        del self.visual_indicators[region_key]
                        
                    # Set completion message
                    self.editor.set_status_message(f"Processed NLP region (lines {region['start']+1}-{region['end']+1})")
                    
        except Exception as e:
            logging.error(f"Error processing NLP region: {str(e)}")
            with self.editor.thread_lock:
                self.editor.display.stop_loading_animation()
                self.editor.set_status_message(f"Error processing NLP region: {str(e)}")
                
        finally:
            self.processing = False
            self.editor.display.stop_loading_animation()
            
            # Process next region if any
            if self.processing_queue:
                self.schedule_update()
                
    def _apply_code_blocks(self, response_data: Dict, base_line: int, user_query: Optional[str]) -> None:
        """Apply code blocks from structured JSON response"""
        code_blocks = sorted(
            response_data["code_blocks"], 
            key=lambda block: block.get("target_line", 0),
            reverse=True
        )
        
        for block in code_blocks:
            target_line = block.get("target_line", base_line)
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
            if user_query and len(code_blocks) == 1:
                comment_line = f"# AI Done: {user_query}"
                code_lines.insert(0, comment_line)
            
            # Insert the new code lines
            for i, line in enumerate(code_lines):
                self.editor.buffer.insert_line(target_line + i, line)
        
        # Store in history
        self.editor.history.add_version(
            self.editor.buffer.get_lines(),
            {"action": "nlp_live_translation", "query": user_query}
        )
        
    def _apply_legacy_translation(self, translated_code: str, start_line: int, end_line: int, user_query: Optional[str]) -> None:
        """Apply translation using legacy format"""
        new_lines = translated_code.strip().split("\n")
        
        # Add user query comment if applicable
        if user_query:
            comment_line = f"# AI Done: {user_query}"
            new_lines.insert(0, comment_line)
            
        # Replace the section
        for _ in range(end_line - start_line + 1):
            self.editor.buffer.delete_line(start_line)
            
        for i, line in enumerate(new_lines):
            self.editor.buffer.insert_line(start_line + i, line)
            
        # Store in history
        self.editor.history.add_version(
            self.editor.buffer.get_lines(),
            {"action": "nlp_live_translation_legacy", "start_line": start_line, "end_line": start_line + len(new_lines) - 1}
        )
