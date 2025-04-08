#!/usr/bin/env python3
"""
Script to update the README.md file with new sections.
"""

def main():
    """Main function to update README.md"""
    
    # Read the current README file
    with open('README.md', 'r') as f:
        readme_lines = f.readlines()
    
    # Find the position to insert the system-wide installation section
    installation_end_index = None
    
    for i, line in enumerate(readme_lines):
        if line.strip() == '```' and ''.join(readme_lines[i-5:i]).find('python -m aivim.run_editor') != -1:
            installation_end_index = i
            break
    
    if installation_end_index is None:
        print("Could not find installation section end.")
        return
    
    # System-wide installation section content
    syswide_install = """
### System-wide Installation

To make AIVim available as a system-wide command (`aivim`), follow these steps:

```bash
# For temporary use in current session
alias aivim='python -m aivim.run_editor'

# For permanent installation, add to your shell configuration
echo 'alias aivim="python -m aivim.run_editor"' >> ~/.bashrc
# Or for Zsh
echo 'alias aivim="python -m aivim.run_editor"' >> ~/.zshrc

# Apply changes without restarting the terminal
source ~/.bashrc  # or source ~/.zshrc
```

For a more robust system-wide installation, create a symbolic link:

```bash
# Create a symbolic link in a directory that's in your PATH
sudo ln -s "$(which python) $(pwd)/run_editor.py" /usr/local/bin/aivim
sudo chmod +x /usr/local/bin/aivim

# Now you can run AIVim from anywhere
aivim myfile.py
```
"""
    
    # Config file section content
    config_file = """
### Configuration File

Instead of setting environment variables, you can create a configuration file for storing API keys:

```bash
# Create a config directory
mkdir -p ~/.config/aivim

# Create and edit the configuration file
cat > ~/.config/aivim/config.ini << EOF
[api_keys]
openai = your_openai_api_key_here
anthropic = your_anthropic_api_key_here
llama_model_path = /path/to/your/local/model.gguf

[settings]
default_model = openai
EOF

# Set proper permissions to protect your API keys
chmod 600 ~/.config/aivim/config.ini
```

AIVim will automatically check for this configuration file and use these settings in addition to any environment variables that are set.
"""
    
    # Find the line where the LLM section begins
    llm_section_index = None
    for i, line in enumerate(readme_lines):
        if line.strip() == '## Setting Up Local LLM Support':
            llm_section_index = i
            break
    
    if llm_section_index is None:
        print("Could not find LLM section.")
        return
    
    # Insert the sections
    updated_lines = (
        readme_lines[:installation_end_index+1] + 
        [syswide_install] + 
        [config_file] + 
        readme_lines[installation_end_index+1:]
    )
    
    # Write the updated file
    with open('README.md', 'w') as f:
        f.writelines(updated_lines)
    
    print("README.md updated successfully!")

if __name__ == "__main__":
    main()