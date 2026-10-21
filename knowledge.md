# CyberShield AI: CyberGuide AI knowledge base

This file is the documentation CyberGuide AI retrieves from. It describes only what is implemented. Planned items are labeled "planned". Each "##" section is one retrievable topic. A "Page:" line names the page key CyberGuide can offer a button for.

## Application overview
CyberShield AI is an educational cybersecurity toolkit built with Python and Streamlit. It combines local security tools (URL heuristics, file hashing, QR generation and decoding) with two optional external services: VirusTotal for reputation lookups and OpenRouter for AI explanations and CyberGuide AI. The local tools work without any API key. A new visitor first sees a landing page and enters the app with the Get Started button. The app does not guarantee safety and is not a replacement for professional security software.
Page: dashboard

## Feature registry
Implemented modules: Overview Dashboard, URL Security Scanner, File Hash Analyzer, QR Code Generator, QR Code Security Analyzer, Security Learning Center, Settings & API Configuration, About CyberShield AI.
Threat intelligence lookups (VirusTotal) are built into the URL Security Scanner, File Hash Analyzer and QR Code Security Analyzer. There is no separate Threat Intelligence page.
Planned, not available yet: AI Security Assistant (full page), Phishing Awareness Lab, Security Reports. CyberGuide AI, the floating chat, is available today.

## Navigation map
When you open the app you first see the landing page. Press Get Started to enter the application, which opens on the Overview Dashboard. Inside the application, use the 🛡️ shield button in the top-left corner of every page to open the navigation sidebar, and press it again to close it (the Overview Dashboard also has Open buttons for each tool). The sidebar groups pages as Platform (Overview Dashboard), Analysis (URL Security Scanner, File Hash Analyzer), QR Tools (QR Code Generator, QR Code Security Analyzer), Learn (Security Learning Center) and System (Settings & API Configuration, About CyberShield AI). See the topic "Navigation sidebar and shield button" for details. CyberGuide AI is the chat button in the bottom-right corner of every page.
Page: dashboard

## Navigation sidebar and shield button
Inside the application, a 🛡️ shield button sits fixed in the top-left corner of every page. Press it to open the navigation sidebar. Press the shield again to close it. The tooltip reads "Open navigation" or "Close navigation". A subtle ripple animation plays around the shield; it is switched off if your device is set to reduce motion, and it never changes how the button works.
The sidebar lists all eight pages with icons: Overview Dashboard, URL Security Scanner, File Hash Analyzer, QR Code Generator, QR Code Security Analyzer, Security Learning Center, Settings & API Configuration, and About CyberShield AI. The page you are on is highlighted and its tooltip says "Current page".
To go to a page, open the sidebar and press its name. The sidebar then closes by itself. Opening or closing the sidebar never changes the page you are on, and your chat history and tool results are kept. Choosing the page you are already on is harmless.
The sidebar is a panel that overlays the left side of the page rather than pushing the content aside, and it starts closed. On narrow phone screens it covers most of the width, so close it with the shield button or by choosing a page. The sidebar and shield are not shown on the landing page. CyberGuide AI, the chat button in the bottom-right corner, is separate from the sidebar. Planned features such as the Phishing Awareness Lab are not listed because they are not available yet.
Page: dashboard

## Landing page and entering the app
The landing page is the first screen for every new visit. It has a brand bar, a hero section, six feature cards (URL Security Scanner, File Hash Analyzer, QR Code Generator, QR Code Security Analyzer, CyberGuide AI and Security Learning Center), a How It Works section, an About section with limitations, and a footer. Features and About in the top bar scroll to those sections.
Get Started (in the hero section, or in the final section at the bottom) opens the application on the Overview Dashboard. A feature card's button opens that tool directly; the CyberGuide AI card enters the app with the chat open. The shield navigation button and the CyberGuide AI chat button are part of the application and are not shown on the landing page, so if you cannot see them, press Get Started.
Your place is kept only for the current browser session. Refreshing or reopening the page starts a new session and shows the landing page again; press Get Started to re-enter. There is no separate link back to the landing page from inside the app.
Page: dashboard

## How to generate a QR code
Open QR Code Generator from the shield navigation sidebar.
1. Choose the content type: URL, Text, Wi-Fi or Email.
2. Fill in the fields for that type. URLs must start with http:// or https://.
3. Pick a color preset or choose Custom to set foreground and background colors.
4. Choose the output size, quiet-zone border and error-correction level.
5. Optionally upload a PNG or JPG logo. A logo forces error correction to H.
6. Check the live preview. The download uses the exact same settings.
7. Read the "Decode check", which scans the generated image to confirm it decodes to your content.
8. Choose PNG, JPG or SVG and press the download button.
9. Test-scan the downloaded image with a phone before sharing it.
Page: qr_generator

## QR code limitations
A QR code stores text, usually a URL. It cannot contain an entire PDF or DOCX file. To share a document, upload it somewhere that already gives a public link, then make a URL QR code from that link. This app does not host files, so it never creates links to local files.
Supported exports are PNG, JPG and SVG. SVG export does not support logos, and the option is disabled when a logo is uploaded. Frames, captions, PDF export, and contact-card (vCard) codes are not implemented. Light-on-dark colors and low contrast may not scan on every phone, so the app shows warnings and recommends a test scan.
Page: qr_generator

## How to analyze a suspicious URL
Open URL Security Scanner.
1. Paste the URL. The app never visits it.
2. Press "Analyze URL" to run offline heuristics on the text of the address.
3. Review the signal level and the findings. The link is shown in a defanged form (hxxp and [.]) so it cannot be clicked by accident.
4. Optionally press "Look up on VirusTotal" if a VirusTotal key is configured. This sends the URL text to VirusTotal.
5. Optionally press "Explain findings with AI" if OpenRouter is configured. This sends the hostname and the finding titles, not the full URL.
6. Follow the recommended actions. When unsure, do not open the link; reach the organization through a website or app you already trust.
Page: url_scanner

## How to read URL heuristic findings
Heuristic findings come from the shape of the URL only. Examples: an IP address instead of a domain, punycode (xn--) hostnames, an '@' that hides the real host, URL shorteners, brand names inside unrelated domains, many subdomains or hyphens, account-related wording, unusual ports, plain http, very long URLs, and redirect URLs inside query strings.
The signal levels are "No strong heuristic signals", "Some suspicious signals" and "Many suspicious signals". None of them means safe or malicious. A clean result can still be a dangerous site, and a flagged result can be legitimate. The registered-domain detection is an approximation and does not use the full Public Suffix List.
Page: url_scanner

## How to interpret a VirusTotal report
A VirusTotal report shows how many security engines labeled the item malicious, suspicious, harmless or undetected, and how many timed out. Malicious means engines flagged it as a threat. Suspicious means weaker or uncertain flags. Undetected means the engine found nothing, which is not the same as confirmed safe. Harmless means the engine considered it clean.
Zero detections do not prove an item is safe. Newly created threats are often not detected yet. "No report found" means VirusTotal has no existing analysis for that item. This app only reads existing reports and does not submit URLs or files, so a missing report stays missing. A report with no engine results is pending.
Single-engine detections can be false positives. Look at how many engines agree and the report date.
Page: url_scanner

## How to hash a file and verify a download
Open File Hash Analyzer.
1. Upload a file up to 25 MB. It is hashed locally with SHA-256, SHA-1 and MD5. It is never executed and never uploaded anywhere by hashing.
2. SHA-256 is the primary identifier. Copy it from the code box.
3. To verify a download, paste the hash published by the vendor into "Compare with a known hash". The app tells you whether it matches.
4. Optionally press "Look up on VirusTotal" to check the SHA-256 for an existing report. Only the hash is sent, not the file.
A matching hash proves the file is identical to what the publisher hashed. It does not prove the file is harmless. You can also paste a hash directly to look it up without uploading a file. This app does not upload files to VirusTotal.
Page: file_analyzer

## How to inspect a QR code safely
Open QR Code Security Analyzer and upload a PNG, JPG, WebP or BMP image of the code.
1. The app decodes the image locally and shows the content as plain text. It does not open anything.
2. If the content is a URL, the same offline heuristics as the URL Security Scanner run automatically, and you can request a VirusTotal lookup.
3. Wi-Fi, email, phone and SMS codes are labeled by type so you can see what scanning them would do.
Never scan or open codes from unknown sources, and be careful with codes stuck over other codes in public places. If no code is found, try a sharper, well-lit, tightly cropped image.
Page: qr_analyzer

## Security Learning Center
The Security Learning Center has short static lessons: recognizing phishing, reading a URL, hashes and file integrity, QR code risks, interpreting VirusTotal results, passwords and multi-factor authentication, and using this toolkit responsibly. It is reading material, not interactive exercises. The interactive Phishing Awareness Lab is planned.
Page: learning_center

## How to configure OpenRouter for CyberGuide AI
CyberGuide AI answers with an AI model through OpenRouter. The only required secret is OPENROUTER_API_KEY. OPENROUTER_MODEL is optional and defaults to openai/gpt-4o-mini. OPENROUTER_BASE_URL is optional and defaults to https://openrouter.ai/api/v1.
Locally, copy .env.example to .env or .streamlit/secrets.toml.example to .streamlit/secrets.toml and fill in the values. On Streamlit Community Cloud, paste the same keys into App settings, then Secrets. Restart or reboot the app after changing secrets. Never commit real keys to GitHub.
Without a key, CyberGuide AI still answers from this documentation but cannot write AI-generated explanations.
Page: settings

## How to configure VirusTotal
The only required secret is VIRUSTOTAL_API_KEY. Create a free VirusTotal account to get a key. Set it as described for OpenRouter: .env or secrets.toml locally, App settings then Secrets on Streamlit Community Cloud.
The free public API allows 4 requests per minute and 500 per day, and may not be used for commercial purposes. The app also applies its own 4 per minute guard. Without a key, the VirusTotal buttons are disabled and every local tool still works.
Page: settings

## Troubleshooting: VirusTotal is not working
CyberGuide AI cannot test your connection. It can only see whether the key is set. Check these in order.
1. Settings & API Configuration shows whether VIRUSTOTAL_API_KEY is detected. If it says not configured, the secret name is wrong or the app was not restarted after adding it. The name must be exactly VIRUSTOTAL_API_KEY.
2. "VirusTotal rejected the API key" means the key is invalid, revoked, or has extra spaces or quotes.
3. A rate-limit message means the free quota (4 per minute, 500 per day) was used. Wait and retry.
4. "No report found" is not an error. VirusTotal has no existing report for that item.
5. Network or timeout messages mean VirusTotal could not be reached from the host running the app.
Page: settings

## Troubleshooting: CyberGuide AI or OpenRouter errors
1. If the answer is labeled "documentation", the AI was not used. The label states the reason, for example the key is missing.
2. "rejected the API key": check OPENROUTER_API_KEY.
3. "rejected the request": OPENROUTER_MODEL is probably not a valid model id on OpenRouter. Pick one from the OpenRouter models list.
4. Rate-limit or timeout messages are temporary. Wait and retry. Local tools are unaffected.
5. Messages over 1000 characters are cut off, and text that looks like a secret is redacted before it is sent.
Page: settings

## Troubleshooting: QR codes and uploads
A generated QR code will not scan: raise contrast, avoid inverted colors, enlarge the quiet zone, use higher error correction, or shorten the content. An upload is rejected: the limit is 25 MB for hashing and about 25 megapixels for QR images. A QR image will not decode: use a flat, sharp, well-lit image with the whole code visible. SVG download is disabled: remove the logo or use PNG/JPG.
Page: qr_generator

## Privacy and external data sharing
Local-only operations: URL heuristics, file hashing, QR generation, QR decoding. These send nothing anywhere.
Sent to VirusTotal only when you press a lookup button: a hash, or the URL text. Files are never uploaded.
Sent to OpenRouter only when you use CyberGuide AI or "Explain findings with AI": your chat message (secret-like text redacted), recent chat turns, relevant documentation, and for URL explanations the hostname and finding titles. Uploaded files and QR images are never sent.
The app does not store uploads or chat history on a server beyond the active browser session. Do not paste passwords or API keys into any field.
Page: about

## Security limitations
CyberShield AI is educational. URL analysis is heuristic and offline and never visits links. Hashes identify content; they do not decide whether it is malicious. VirusTotal results can lag behind new threats. AI explanations can be wrong and are not scan results. The app does not provide complete protection or guarantee safety.
Page: about

## Run locally and deploy
Local run: install Python 3.10 or newer, create a virtual environment, run pip install -r requirements.txt, then streamlit run streamlit_app.py. Optionally add keys as described in the configuration topics.
Deploy: push the repository to GitHub without secrets, create an app on Streamlit Community Cloud pointing at streamlit_app.py, and paste secrets into App settings. Deployment preparation is included in this project, but whether any particular instance is live can only be confirmed by opening it.
Page: settings

## Planned features
These are planned and not implemented: AI Security Assistant full page, Phishing Awareness Lab, Security Reports (exportable session reports), QR frames and captions, PDF export for QR codes, file submission to VirusTotal, and URL submission to VirusTotal. CyberGuide AI cannot perform them today.
Page: dashboard

## Frequently asked questions
Why don't I see the shield button or CyberGuide AI? You are on the landing page. Press Get Started to enter the app, where both appear. After a refresh you return to the landing page.
Where did the ☰ Menu go? It was replaced by the 🛡️ shield button, which opens the navigation sidebar.
Can CyberGuide AI scan a URL or run a tool for me? No. It explains how to use the tools and answers from documentation. Scans happen only when you press the buttons on the tool pages.
Does the app open the links I analyze? No, never.
Is a URL with no findings safe? Not necessarily. No heuristic signals is not a safety guarantee.
Can I put a PDF inside a QR code? No. Link to a hosted copy instead.
Does hashing upload my file? No. Hashing is local.
