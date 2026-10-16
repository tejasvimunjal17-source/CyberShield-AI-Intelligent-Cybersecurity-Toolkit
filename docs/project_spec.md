# CyberShield AI — Intelligent Cybersecurity Toolkit

## 1. Project Overview

Project Name: CyberShield AI
Project Type: AI-powered cybersecurity web application
Tagline: Intelligent Security. Clear Insights. Safer Digital Experiences.
Primary Language: Python
Web Framework: Streamlit
AI Provider: OpenRouter
Threat Intelligence Provider: VirusTotal
Version: Initial Development
Deployment Target: GitHub and Streamlit Community Cloud

CyberShield AI is a modular cybersecurity platform designed to bring
practical security tools, threat intelligence, AI-assisted analysis,
security awareness, and educational resources together in one
professional web application.

The project is intended to demonstrate practical cybersecurity
knowledge, AI integration, API integration, secure software
development, and professional application architecture.

The application must be useful, understandable, maintainable, and
suitable for demonstration in a student cybersecurity portfolio.

CyberShield AI is the complete application. Individual security
utilities are modules within the application, not separate products.

## 2. Core Vision

The goal is to develop an integrated cybersecurity platform rather
than a simple QR generator, a standalone threat scanner, or a generic
AI chatbot.

The application should help users:

- Understand cybersecurity risks.
- Inspect suspicious URLs.
- Interpret available threat intelligence.
- Analyze file hashes.
- Generate and inspect QR codes.
- Understand potential phishing indicators.
- Learn cybersecurity fundamentals.
- Interpret security reports.
- Navigate the platform with AI assistance.
- Learn how to use security tools responsibly.

Every feature must have a clear purpose and integrate naturally
into the overall application.

Prioritize a smaller number of reliable, functional tools over a
large collection of superficial features.

## 3. Target Users

Primary users:

- Cybersecurity students.
- Cybersecurity beginners.
- IT students.
- Developers interested in secure software.
- Users learning about online threats.
- Users who need basic security-analysis utilities.

The interface should be accessible to beginners while maintaining
technical accuracy.

Explain technical terms clearly without hiding important limitations.

## 4. Main Application Structure

The application should have a professional dashboard and a consistent
navigation system.

Suggested modules:

1. Overview Dashboard
2. AI Security Assistant
3. URL Security Scanner
4. Threat Intelligence Analyzer
5. File Hash Analyzer
6. QR Code Generator
7. QR Code Security Analyzer
8. Phishing Awareness Lab
9. Security Learning Center
10. Security Reports
11. Settings and API Configuration
12. About CyberShield AI

These are proposed modules, not a requirement to implement every
feature immediately.

Claude must evaluate feasibility, prioritize core functionality,
and avoid implementing unnecessary modules simply to make the
application appear larger.

The QR Code Generator and Threat Analyzer are supporting features
inside CyberShield AI.

They do not define the entire application.

## 5. Platform Architecture

CyberShield AI should have three conceptual layers.

### Layer A: Main Platform

Responsible for:

- Application startup.
- Navigation.
- Dashboard.
- Shared layout.
- Theme.
- Configuration.
- Session management.
- Shared UI components.
- Reports and settings.

### Layer B: Security Tools

Responsible for performing actual operations.

Examples:

- URL parsing and inspection.
- File hashing.
- VirusTotal lookups.
- QR code generation.
- QR code decoding.
- Suspicious URL inspection.
- Phishing-indicator analysis.

Each tool should be implemented in a maintainable module.

### Layer C: CyberGuide AI

CyberGuide AI is the application's persistent floating chatbot.

It helps users understand and navigate the entire CyberShield AI
platform.

It is not a replacement for the platform or its security tools.

It acts as an intelligent guide integrated into the application.

## 6. CyberGuide AI — Floating Application Chatbot

Name: CyberGuide AI

Role: Intelligent platform guide and cybersecurity assistant.

Provider: OpenRouter

Interface: Persistent floating chat button that opens a compact
conversation panel.

### Primary Responsibilities

CyberGuide AI should understand:

- The application's overall purpose.
- Available modules.
- Navigation and page locations.
- Feature descriptions.
- Tool input requirements.
- Supported file types.
- Supported download formats.
- Configuration requirements.
- API dependencies.
- Tool workflows.
- Error messages.
- Known limitations.
- Security and privacy considerations.
- Setup and deployment procedures.

### Example Interaction: QR Code Generation

User:
"How do I generate a QR code?"

CyberGuide AI should explain:

1. Open the QR Code Generator.
2. Select the content type.
3. Enter a URL or text.
4. Configure colors and other available options.
5. Upload a logo if supported.
6. Generate the QR code.
7. Review the preview.
8. Validate the decoded content where supported.
9. Download the desired output format.
10. Test-scan the downloaded image.

It should mention any limitations that apply to the implemented
version of the application.

### Example Interaction: Suspicious URL

User:
"How do I analyze a suspicious website?"

CyberGuide AI should explain:

1. Open the appropriate URL or Threat Analyzer module.
2. Enter the URL.
3. Review the parsing and heuristic findings.
4. Request a VirusTotal lookup if configured and supported.
5. Interpret the returned results.
6. Follow the safety recommendations.

The chatbot must not automatically visit the suspicious website.

### Example Interaction: API Configuration

User:
"Why is VirusTotal not working?"

CyberGuide AI should explain the actual configuration requirements,
including the expected secret name, missing credentials, applicable
API limitations, and troubleshooting steps.

It must not claim to have inspected environment variables or tested
an API connection unless it actually has access to the corresponding
application functionality.

### Chatbot Knowledge Architecture

Maintain an authoritative knowledge source containing:

- Application overview.
- Feature registry.
- Navigation map.
- Tool documentation.
- Workflow instructions.
- Configuration documentation.
- Troubleshooting guidance.
- Security limitations.
- Frequently asked questions.

Keep this documentation synchronized with implemented features.

Prefer retrieving relevant documentation for a user's question
rather than placing the entire project source code into every prompt.

Use a lightweight retrieval approach appropriate for the project's
size. Do not add a vector database unless there is a demonstrated
need.

### Chatbot Accuracy Rules

CyberGuide AI must:

- Explain only implemented features as available capabilities.
- Clearly label planned features as planned.
- Distinguish AI explanations from actual scan results.
- Avoid fabricating tool outputs.
- Avoid claiming that an operation succeeded without confirmation.
- Explain errors and missing configuration.
- Use concise, structured answers.
- Provide step-by-step guidance when requested.
- Protect secrets and private user data.
- Avoid sending sensitive uploaded files to the AI provider.

Where practical, provide links to relevant application pages or
navigation actions.

If a requested feature does not exist, say so and explain whether
it is planned or unsupported.

## 7. OpenRouter Integration

OpenRouter powers CyberGuide AI and optional AI-assisted explanations.

The API key must be configured through Streamlit secrets or an
environment variable.

Expected configuration:

OPENROUTER_API_KEY

The model should be configurable rather than permanently tied to
an unverified model identifier.

The integration should implement:

- Request timeouts.
- Error handling.
- Sensible input limits.
- Clear loading indicators.
- Safe error messages.
- Appropriate conversation-context management.
- Missing-key handling.
- Rate-limit handling where applicable.

Do not expose the API key in frontend code, page content, logs,
GitHub, or exception messages.

The application must remain useful if OpenRouter is unavailable.

QR generation and file hashing must not require AI requests.

## 8. VirusTotal Integration

VirusTotal provides external reputation and analysis information
for supported URLs, file hashes, and explicitly submitted files.

Expected configuration:

VIRUSTOTAL_API_KEY

The implementation must follow the current official API documentation.

Capabilities may include:

- URL reputation lookups.
- File hash lookups.
- Supported analysis retrieval.
- Optional file submission with explicit consent.

Display only information returned by the API.

Handle:

- Missing API credentials.
- Invalid credentials.
- Rate limits.
- Network failures.
- Pending analyses.
- Unsupported inputs.
- Missing results.

Explain the difference between malicious detections, suspicious
detections, undetected results, and unavailable analysis.

Zero detections do not prove that a file or website is safe.

Never fabricate VirusTotal results.

Before submitting a file to an external service, explain that the
file will be shared with that service and require an explicit user
action.

Do not upload private files automatically.

## 9. QR Code Generator

The QR Code Generator is a supporting module.

It should provide actual QR generation functionality.

Potential capabilities:

- URL QR codes.
- Plain-text QR codes.
- Google Drive links.
- Document URLs.
- Email and contact information.
- Wi-Fi configuration.
- Supported messaging links.
- Custom foreground and background colors.
- Preset themes.
- Logo upload.
- Frames and captions.
- Output-size selection.
- Error-correction selection.
- Live preview.
- PNG export.
- SVG export where implemented.
- JPG export where implemented.
- PDF export where implemented.
- QR decoding verification where practical.

The preview and downloaded output must use the same settings.

Unsupported options must be disabled or clearly identified.

A QR code does not contain an entire arbitrary PDF or DOCX file.
It generally contains a URL pointing to an accessible resource.

Do not pretend a local temporary file path is a public file URL.

If file hosting is not configured, support existing URLs without
requiring a cloud-storage integration.

Do not execute uploaded scripts or files.

## 10. Threat Analyzer and URL Security

The Threat Analyzer should help users inspect suspicious inputs
and understand potential security risks.

Potential capabilities:

- URL syntax validation.
- Domain extraction.
- HTTP and HTTPS identification.
- Suspicious URL pattern detection.
- Punycode identification.
- Suspicious hostname indicators.
- URL shortener identification.
- Basic phishing-indicator analysis.
- Optional VirusTotal reputation checks.
- Structured findings.
- Recommended defensive actions.

Use appropriate language for findings.

For example:

"Potentially suspicious URL structure detected"

is preferable to:

"This website is definitely malicious"

unless an authoritative result actually supports the stronger claim.

The application must not automatically navigate to submitted URLs.

Avoid unrestricted server-side URL fetching.

If remote fetching is introduced, enforce appropriate SSRF protections.

## 11. File Hash Analyzer

The File Hash Analyzer should calculate hashes locally.

Supported algorithms may include:

- SHA-256.
- SHA-1.
- MD5.

Use SHA-256 as the primary identifier.

Explain that hashing identifies content but does not establish
whether a file is malicious.

Optional VirusTotal lookups should use actual calculated hashes.

Do not execute uploaded files.

Apply reasonable upload limits and safe temporary-file handling.

## 12. Security and Privacy

The application must follow secure development practices.

Requirements:

- Never hardcode API keys.
- Validate inputs.
- Restrict upload sizes.
- Validate file types where appropriate.
- Do not execute uploaded files.
- Do not automatically visit suspicious URLs.
- Do not log sensitive content unnecessarily.
- Do not render untrusted HTML.
- Use network timeouts.
- Handle external API failures.
- Explain external data sharing.
- Do not expose private files publicly without explicit consent.
- Do not claim a scan succeeded unless it actually did.
- Avoid cross-user leakage of session data.
- Keep optional external services separate from local tools.

The application is an educational cybersecurity toolkit.
It must not claim to provide complete protection or guarantee safety.

## 13. Reference Project: Sahay AI

An existing Sahay AI ZIP is available as an architectural reference.

Claude must inspect the actual archive before making architectural
assumptions.

Useful areas to examine include:

- Main Streamlit entry point.
- Navigation system.
- Reusable components.
- OpenRouter client.
- Configuration.
- CSS and themes.
- Dependency management.
- README.
- Deployment instructions.

Use relevant architectural patterns without blindly copying code.

Create CyberShield AI as a separate project.

Do not retain unrelated wellness features.

Do not copy credentials, private information, or unnecessary
infrastructure.

## 14. Technical Stack

Primary:

- Python.
- Streamlit.
- OpenRouter API.
- VirusTotal API.
- Appropriate QR-generation libraries.
- Appropriate QR-decoding libraries.
- Pillow or an equivalent supported image-processing library.
- Requests or an appropriate HTTP client.
- Pytest for automated testing.

Additional dependencies should be introduced only when justified.

Use versions compatible with the deployment environment.

Keep requirements.txt accurate and minimal.

## 15. Proposed Project Structure

CyberShield-AI/
    streamlit_app.py
    config.py
    requirements.txt
    README.md
    knowledge.md
    .gitignore
    .env.example

    .streamlit/
        config.toml
        secrets.toml.example

    components/
        sidebar.py
        header.py
        cards.py
        cyberguide_chat.py
        theme.py

    pages/
        dashboard.py
        ai_assistant.py
        url_scanner.py
        threat_analyzer.py
        file_analyzer.py
        virustotal_scanner.py
        qr_generator.py
        qr_analyzer.py
        phishing_lab.py
        learning_center.py
        settings.py
        about.py

    backend/
        openrouter_client.py
        virustotal_client.py
        url_analyzer.py
        file_hashing.py
        security_utils.py

    qr_tools/
        generator.py
        decoder.py
        styling.py
        exporters.py

    docs/
        architecture.md
        setup.md
        deployment.md
        security.md

    tests/
        test_url_analyzer.py
        test_file_hashing.py
        test_qr_generator.py
        test_qr_decoder.py
        test_api_clients.py

This is a suggested structure. Adapt it to the actual requirements.

Do not create empty modules simply to match the tree.

## 16. User Interface

Use a professional cybersecurity theme.

Preferred direction:

- Deep navy backgrounds.
- Cyan or teal accents.
- Readable typography.
- Consistent spacing.
- Clear status indicators.
- Accessible contrast.
- Responsive layouts.
- Functional buttons.
- Useful empty states.
- Consistent navigation.

Avoid fake statistics, decorative nonfunctional controls, and
fabricated threat intelligence.

The floating CyberGuide AI button should be accessible throughout
the application wherever the chosen Streamlit architecture supports it.

## 17. Testing

Create tests for actual functionality.

Important tests include:

- URL parsing.
- Invalid URLs.
- File hash correctness.
- QR generation.
- QR decoding.
- Unicode text.
- Color customization.
- Logo handling.
- Supported export formats.
- Missing API keys.
- Mocked API responses.
- Network timeouts.
- Rate-limit handling.
- Error handling.
- Chatbot documentation retrieval.
- Chatbot behavior when a feature is unavailable.

Do not use real API keys in automated tests.

Do not claim tests passed unless they were executed.

Do not claim deployment was verified unless the application was
actually deployed and tested.

## 18. Deployment

Prepare the project for GitHub and Streamlit Community Cloud.

Include:

- requirements.txt.
- README.md.
- .gitignore.
- .env.example.
- Streamlit configuration where necessary.
- Secret configuration examples.
- Installation instructions.
- Local execution instructions.
- Deployment instructions.
- Troubleshooting documentation.

Never include actual credentials in the repository.

## 19. Development Priorities

Recommended implementation order:

Phase 1:
- Project foundation.
- Navigation.
- Dashboard.
- Configuration.
- Theme.

Phase 2:
- URL analyzer.
- File hashing.
- QR generator.
- QR analyzer.

Phase 3:
- VirusTotal integration.
- AI assistant.
- Threat-analysis reporting.

Phase 4:
- Floating CyberGuide AI chatbot.
- Application knowledge source.
- Workflow guidance.
- Troubleshooting support.

Phase 5:
- Security learning modules.
- Reporting improvements.
- Automated tests.
- Documentation.

Phase 6:
- Deployment preparation.
- Final verification.
- Project packaging.

Adjust this order if implementation dependencies require it.

## 20. Definition of Done

The project is ready for its first release when:

- The application starts successfully.
- Navigation works.
- Implemented tools perform real operations.
- API keys are handled securely.
- Missing credentials do not crash the application.
- QR downloads contain valid QR output.
- File hashes are calculated correctly.
- VirusTotal results are based on real or explicitly mocked responses.
- CyberGuide AI explains actual implemented features.
- The chatbot does not fabricate tool execution.
- Tests have been run and their results documented.
- README instructions are accurate.
- Deployment configuration is prepared.
- No actual secrets are included.
- Known limitations are documented.

The goal is a credible, maintainable cybersecurity platform rather
than a collection of superficial demonstrations.