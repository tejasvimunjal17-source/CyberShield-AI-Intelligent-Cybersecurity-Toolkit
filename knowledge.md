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
Open QR Code Generator from the shield navigation sidebar. The page runs top to bottom: Content, Preview, setting groups, then Export & Download.
1. Choose a Category and a Content type. Types: URL, Text, Email (optional subject and message), Phone call, SMS, Wi-Fi, WhatsApp chat link, Contact card (vCard), Instagram, Facebook, YouTube, LinkedIn, Other social profile (URL), Business contact (vCard), Link to a hosted file (PDF, Word, Excel, PowerPoint, text, CSV, ZIP, Python or another permitted document), Google Drive share link, and Calendar event.
2. Fill in the fields. The page validates them, shows the exact text that will be encoded (a Wi-Fi password is hidden on screen) and never opens a link.
3. Check the Preview and the read-back check under it.
4. Optionally open the setting groups. Design & Appearance: module shape (square, rounded, dots, diamonds), position-marker shapes and the presets Classic, Rounded, Circular and Modern geometric. Colors & Gradients: color presets, custom colors by picker or hex value, solid, linear, diagonal or radial gradients, and a transparent background. Logo & Branding: a PNG or JPG logo with size and clear space. Frames & CTA: simple border, rounded rectangle, badge, tag or speech bubble with a label such as Scan Me. Technical Settings: error correction L, M, Q or H, quiet zone, and output size from 512 to 4096 px.
5. Choose a download format (PNG, JPG, TIFF, SVG or PDF) and press the download button. Optionally show HTML embed code.
6. Test-scan the downloaded file with a phone before sharing it.
Page: qr_generator

## QR code limitations
A QR code stores text, usually a URL. It cannot contain an entire PDF or DOCX file. To share a document, upload it somewhere that already gives a public link, then use the Link to a hosted file or Google Drive share link type. CyberShield AI does not host files, so it never creates links to local files, and it never opens the links you enter.
Formats: PNG (can be transparent), JPG (never transparent, so the background color fills it), TIFF (lossless raster), SVG (vector) and PDF (vector). SVG and PDF stay vector, but a logo inside them is an embedded bitmap. EPS is not offered because it could not be checked, and background images are not offered because they cannot be made reliably scannable.
Logos must be PNG or JPG up to 1 MB, judged by file content. Error correction H is applied automatically with a logo unless you untick it, and a logo that would cover a position marker, timing pattern or format information is refused. Label text on frames supports letters, digits and basic punctuation, up to 30 characters.
Decorative shapes, gradients and circular outer marker rings can reduce scan reliability. After each change the app reads the picture back with a built-in decoder and reports whether it could be read. That is evidence, not a guarantee for every phone. Circular outer marker rings were not readable in testing and are labelled unverified. Light-on-dark colors and low contrast may not scan on every phone, so the app shows warnings and recommends a test scan.
Page: qr_generator

## How to analyze a suspicious URL
Open URL Security Scanner.
1. Paste the URL. The app never visits it.
2. Press "Analyze URL" to run offline heuristics on the text of the address.
3. Review the signal level and the findings. The link is shown in a defanged form (hxxp and [.]) so it cannot be clicked by accident.
4. Optionally press "Look up existing report" if a VirusTotal key is configured. This sends an encoded form of the URL to VirusTotal to read a report that already exists. It does not request a new scan. If you want a new analysis, open "Request a new analysis", read the privacy notes, tick the confirmation box, and press Submit. Then press "Check analysis status" later. Submitting shares the URL with VirusTotal and its security community, so avoid URLs with private tokens in them.
5. Optionally press "Explain findings with AI" if OpenRouter is configured. This sends the hostname and the finding titles, not the full URL.
6. Follow the recommended actions. When unsure, do not open the link; reach the organization through a website or app you already trust.
Page: url_scanner

## How to read URL heuristic findings
Heuristic findings come from the shape of the URL only. Examples: an IP address instead of a domain, punycode (xn--) hostnames, an '@' that hides the real host, URL shorteners, brand names inside unrelated domains, many subdomains or hyphens, account-related wording, unusual ports, plain http, very long URLs, and redirect URLs inside query strings.
The signal levels are "No strong heuristic signals", "Some suspicious signals" and "Many suspicious signals". None of them means safe or malicious. A clean result can still be a dangerous site, and a flagged result can be legitimate. The registered-domain detection is an approximation and does not use the full Public Suffix List.
Page: url_scanner

## How to interpret a VirusTotal report
A VirusTotal report shows how many security engines labeled the item malicious, suspicious, harmless or undetected, and how many timed out. Malicious means engines flagged it as a threat. Suspicious means weaker or uncertain flags. Undetected means the engine found nothing, which is not the same as confirmed safe. Harmless means the engine considered it clean.
Zero detections do not prove an item is safe. Newly created threats are often not detected yet. "No report found" means VirusTotal has no existing analysis for that item. Looking up only reads existing reports. A new URL or file analysis is sent to VirusTotal only if you explicitly confirm it for that item, so a missing report stays missing until you do. A report with no engine results is pending. Queued or in-progress analyses are not verdicts.
Single-engine detections can be false positives. Look at how many engines agree and the report date.
Page: url_scanner

## How to hash a file and verify a download
Open File Hash Analyzer.
1. Upload a file up to 25 MB. It is hashed locally with SHA-256, SHA-1 and MD5. It is never executed and never uploaded anywhere by hashing.
2. SHA-256 is the primary identifier. Copy it from the code box.
3. To verify a download, paste the hash published by the vendor into "Compare with a known hash". The app tells you whether it matches.
4. Optionally press "Look up existing report" to check the SHA-256 for an existing report. Only the hash is sent, not the file.
5. If VirusTotal has no report, you can optionally upload the file itself under "Upload this file to VirusTotal". This needs your explicit confirmation after you read the privacy notes. The upload limit is 25 MB. The original file name is not sent.
A matching hash proves the file is identical to what the publisher hashed. It does not prove the file is harmless. You can also paste a hash directly to look it up without uploading a file. A pasted hash cannot be uploaded. Hashing and lookup never upload the file. A file is uploaded to VirusTotal only when you tick the confirmation box and press the upload button, and VirusTotal shares uploaded files with its security community, so never upload personal or confidential files.
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
The free public API allows 4 requests per minute and 500 per day, and may not be used for commercial purposes. The app also applies its own 4 per minute guard. Without a key, the VirusTotal sections show a notice instead of buttons and every local tool still works. Lookups, URL submissions, file uploads and status checks all count toward the same limits.
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
A generated QR code will not scan: use the button that returns to the most reliable style and colors, raise contrast, avoid inverted colors, keep the quiet zone at 4 or more, use error correction Q or H with a logo, shrink the logo, or shorten the content. The read-back message says whether the built-in decoder could read the design and whether the data pattern is intact. A logo is refused: it is not a PNG or JPG, it is over 1 MB, or it would cover essential parts of a small code; use a smaller logo or longer content. A frame label is refused: it is over 30 characters or uses accents or emoji. A 4096 px raster file does not appear: press the button to prepare it, or choose SVG or PDF. An upload is rejected: the limit is 25 MB for hashing and about 25 megapixels for QR images. A QR image will not decode: use a flat, sharp, well-lit image with the whole code visible.
Page: qr_generator

## Privacy and external data sharing
Local-only operations: URL heuristics, file hashing, QR generation, QR decoding. These send nothing anywhere.
Sent to VirusTotal only when you press a button: a lookup sends a hash or an encoded URL. A new URL analysis sends the URL text, and a new file analysis uploads the file, but only after you tick a confirmation box and press the submit or upload button. Hashing, QR decoding and local heuristics send nothing.
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
These are planned and not implemented: AI Security Assistant full page, Phishing Awareness Lab, Security Reports (exportable session reports), EPS export and background images for QR codes (deliberately not offered), and uploads larger than 25 MB to VirusTotal. CyberGuide AI cannot perform them today. URL and file submission to VirusTotal do exist, but only on the tool pages and only after your explicit confirmation.
Page: dashboard

## Frequently asked questions
Why don't I see the shield button or CyberGuide AI? You are on the landing page. Press Get Started to enter the app, where both appear. After a refresh you return to the landing page.
Where did the ☰ Menu go? It was replaced by the 🛡️ shield button, which opens the navigation sidebar.
Can CyberGuide AI scan a URL or run a tool for me? No. It explains how to use the tools and answers from documentation. Scans happen only when you press the buttons on the tool pages.
Does the app open the links I analyze? No, never.
Is a URL with no findings safe? Not necessarily. No heuristic signals is not a safety guarantee.
Can I put a PDF inside a QR code? No. Link to a hosted copy instead.
Does the QR generator send my content anywhere? No. Generation, the preview, the read-back check and every download happen locally.
Which QR download formats exist? PNG, JPG, TIFF, SVG and PDF. SVG and PDF are vector files.
Is a QR code that the app can read back guaranteed to scan? No. It is evidence from one decoder. Test-scan the downloaded file.
Does hashing upload my file? No. Hashing is local.
