# Prompt for Creating an AI-Assisted Vim Editor

## Project Overview
Develop an AI-enhanced version of Vim ("AIVim") that enables:
1. In-line AI assistance for code editing and generation
2. Integration of AI responses directly into the codebase
3. Easy embedding into other applications as a default text editor
4. Implementation in Python for cross-platform compatibility

## Core Features

### AI Integration Capabilities
- Allow users to highlight code sections and request AI assistance through keyboard shortcuts
- Support natural language queries for code modifications ("refactor this to be more efficient", "add error handling", etc.)
- Enable in-line code generation based on comments or natural language descriptions
- Provide AI-powered explanations of selected code blocks
- Implement AI-assisted debugging for highlighted code segments

### User Interface and Interaction
- Maintain Vim's modal editing paradigm while adding AI-specific commands
- Show line numbers by default for easy reference in AI commands
- Create a dedicated AI interaction pane that doesn't disrupt the main editing experience
- Implement specific Vim-style commands for AI operations:
  - `ESC + :explain <initial_line_number> <final_line_number>` - Request explanation for selected lines
  - `ESC + :improve <initial_line_number> <final_line_number>` - Request improvements for selected lines
  - `ESC + :generate <initial_line_number> <final_line_number>` - Generate new code based on context
  - `ESC + :ai <user query text>` - Submit custom AI query
- Enable navigation between file versions using `Ctrl + Left/Right arrow keys` for reviewing AI modifications
- Implement syntax highlighting for AI-suggested code modifications
- Display differences between original and AI-suggested code

### Embedability Requirements
- Modular architecture allowing clean separation between UI and core functionality
- Well-defined API for host application integration
- Minimal dependencies to ensure compatibility across environments
- Configuration options for host applications to customize AI features
- Standard hooks for embedding applications to interact with the AI subsystem

## Technical Specifications

### Python Implementation
- Use Python 3.8+ for core implementation
- Leverage existing Python Vim interfaces (e.g., python-vim, neovim-python)
- Implement as both a standalone application and a library for embedding
- Apply clean architecture principles for separation of concerns
- Ensure proper thread management for AI operations to maintain editor responsiveness

### AI Interaction System
- Design a protocol for communication between editor and AI services
- Support multiple AI providers through adapter pattern
- Implement contextual awareness by providing AI with relevant code context
- Create file version history system for each AI modification
- Implement command handlers for the specific AI commands:
  - `:explain <initial_line> <final_line>` - Get detailed explanation of selected code
  - `:improve <initial_line> <final_line>` - Request optimization/refactoring of selected code
  - `:generate <initial_line> <final_line>` - Create new code based on comments or context
  - `:ai <query>` - Process custom AI queries and integrate results
- Create efficient caching mechanism for common AI requests
- Ensure secure handling of potentially sensitive code shared with AI

### Data Management
- Implement session history for AI interactions
- Provide options for anonymizing code before sending to AI services
- Create local storage for frequently used AI responses
- Allow export/import of AI interaction patterns for team sharing

## User Experience Flow

1. User invokes an AI command using the standard Vim command mode:
   - `ESC + :explain <initial_line_number> <final_line_number>` for explanations
   - `ESC + :improve <initial_line_number> <final_line_number>` for improvements
   - `ESC + :generate <initial_line_number> <final_line_number>` for code generation
   - `ESC + :ai <user query text>` for custom queries
2. Editor sends relevant code context and request to AI service
3. While waiting, editor shows non-intrusive progress indicator
4. AI creates a new file version with the modifications
5. User can navigate between original and AI-modified versions using `Ctrl + Left/Right arrow keys`
6. User can accept, reject, or request additional modifications
7. Final accepted changes are saved to the current file

## Implementation Roadmap

### Phase 1: Core Framework
- Basic Vim extension with AI command syntax (explain, improve, generate, ai)
- Display line numbers by default
- Version history navigation with Ctrl + Left/Right arrow keys
- Integration with at least one AI provider (e.g., OpenAI, Anthropic)
- Ability to process AI responses and create new file versions

### Phase 2: Enhanced Interaction
- Context-aware AI requests that include surrounding code
- Diff-style presentation of suggested changes
- Multiple suggestion options for a single request
- Keyboard navigation for AI suggestions

### Phase 3: Advanced Features
- Code analysis capabilities (complexity, potential bugs)
- AI-assisted refactoring tools
- Custom AI instruction templates for consistent results
- Team sharing of effective AI prompts

### Phase 4: Embedding API
- Clean API design for host application integration
- Documentation and examples for embedding
- Performance optimization for embedded scenarios
- Plugin system for extending AI capabilities

## Integration Guidelines

### Host Application Requirements
- Python runtime 3.8+ available
- Ability to spawn and manage child processes
- Text buffer access and manipulation capabilities
- User interface elements for AI interaction (can be minimal)

### API Structure
- Editor class for core editing capabilities
- AIService class for AI integration
- ConfigManager for customization
- EventSystem for interaction with host application

### Customization Options
- AI provider selection and configuration
- Custom keyboard shortcuts
- UI appearance and behavior
- Custom prompt templates for consistent AI interaction

## Security and Privacy Considerations

- Clear guidelines on what code is sent to external AI services
- Options for using local AI models when privacy is paramount
- Automatic detection and redaction of sensitive information
- Compliance features for organizations with strict data policies

## Documentation Requirements

- Detailed API documentation for developers
- User manual with keyboard shortcut reference
- Example configurations for common editing scenarios
- Best practices for effective AI-assisted editing
- Video tutorials demonstrating key workflows
