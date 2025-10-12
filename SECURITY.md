# Security Policy

## Supported Versions

We release patches for security vulnerabilities. Which versions are eligible for receiving such patches depends on the CVSS v3.0 Rating:

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | :white_check_mark: |
| < 0.5   | :x:                |

## Reporting a Vulnerability

The AIVim team and community take security bugs in AIVim seriously. We appreciate your efforts to responsibly disclose your findings, and will make every effort to acknowledge your contributions.

To report a security issue, please use the GitHub Security Advisory ["Report a Vulnerability"](https://github.com/danimoya/AIVim-Editor/security/advisories/new) tab.

The AIVim team will send a response indicating the next steps in handling your report. After the initial reply to your report, the security team will keep you informed of the progress towards a fix and full announcement, and may ask for additional information or guidance.

### What to Include in Your Report

- Type of issue (e.g. buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

## Security Best Practices

### API Keys

**Never commit API keys or secrets to the repository.** AIVim supports multiple methods for providing API keys:

1. **Environment Variables** (Recommended):
   ```bash
   export OPENAI_API_KEY="your-key-here"
   export ANTHROPIC_API_KEY="your-key-here"
   ```

2. **Configuration File** (with proper permissions):
   ```bash
   # Store in ~/.aivim/config or ~/.config/aivim/config
   # Ensure file has restrictive permissions:
   chmod 600 ~/.aivim/config
   ```

3. **`.env` File** (for local development):
   - The `.env` file is automatically included in `.gitignore`
   - Never share or commit this file
   - Use `.env.example` for documentation purposes

### Running AIVim Securely

#### Flask Web Interface

When running the Flask web interface:

1. **Set a Strong Session Secret**:
   ```bash
   export SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```

2. **Never Run in Debug Mode in Production**:
   ```bash
   export FLASK_DEBUG=False
   export FLASK_ENV=production
   ```

3. **Bind to Localhost Only** (unless you need external access):
   ```bash
   export FLASK_HOST=127.0.0.1
   ```

4. **Configure Logging Appropriately**:
   ```bash
   export LOG_LEVEL=INFO  # Not DEBUG in production
   ```

#### Terminal Interface

The terminal interface is generally safe but:

- Be cautious when using AI-generated code
- Review generated code before executing
- Don't provide sensitive data in prompts
- Be aware that AI services may log your requests

### Dependency Security

We use multiple tools to ensure dependency security:

- **Bandit**: Python security linter (runs on every PR)
- **Safety**: Dependency vulnerability checker (runs on every PR)
- **Dependabot**: Automated dependency updates (configured)
- **CodeQL**: Security scanning (runs on security workflow)

### Rate Limiting

The Flask web interface includes built-in rate limiting (20 requests per minute per IP). This helps prevent:

- API quota exhaustion
- Denial of service attacks
- Abuse of AI services

### Input Validation

All API endpoints validate:

- Content-Type headers
- Request payload size (max 50KB per field)
- Required fields presence
- Input data types

### Secrets in Logs

The logging system automatically redacts:

- API keys
- Tokens
- Secrets

However, you should still:

- Use `LOG_LEVEL=INFO` or higher in production
- Regularly rotate log files
- Restrict log file permissions: `chmod 600 aivim.log`

## Known Security Considerations

### AI Service Providers

When using AIVim with external AI services:

1. **Data Privacy**: Your code and prompts are sent to third-party AI services (OpenAI, Anthropic, etc.)
2. **API Quotas**: Rate limiting helps prevent accidental quota exhaustion
3. **Cost Management**: AI API calls incur costs; monitor usage regularly

### Local LLM Models

When using local LLM models:

1. **Model Source**: Only download models from trusted sources
2. **Resource Usage**: Local models consume significant CPU/RAM
3. **Model Security**: Verify model integrity (checksums)

### Terminal UI

The terminal interface uses Python's `curses` library:

1. **Input Handling**: All keyboard input is properly sanitized
2. **File Operations**: File paths are validated before use
3. **Command Injection**: No shell commands are executed with user input

## Security Updates

Security updates will be released as soon as possible after a vulnerability is confirmed. Critical security updates may be released outside the normal release cycle.

To stay informed about security updates:

- Watch this repository for security advisories
- Subscribe to GitHub security alerts
- Check the [Releases](https://github.com/danimoya/AIVim-Editor/releases) page

## Acknowledgments

We thank the security researchers and contributors who have helped identify and resolve security issues in AIVim.

## Contact

For security concerns, please use the GitHub Security Advisory system rather than public issues.

For general questions, please use:
- GitHub Issues: https://github.com/danimoya/AIVim-Editor/issues
- Email: daniel.moya@dimensigon.com
