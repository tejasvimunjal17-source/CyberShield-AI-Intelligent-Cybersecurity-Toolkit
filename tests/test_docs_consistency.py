"""Guards against privacy claims drifting out of date after Parts 6 and 7.

CyberGuide AI answers from knowledge.md, so a stale sentence there becomes a wrong
answer about what the app sends to third parties.
"""

import unittest

from cyberguide.knowledge_base import load_sections, retrieve


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


STALE = (
    "does not submit urls or files",
    "this app does not upload files to virustotal",
    "files are never uploaded",
    "look up on virustotal",              # button was renamed in Part 6
    "file submission to virustotal, and url submission",
)


class StaleClaimTests(unittest.TestCase):
    def test_no_stale_claims_in_user_facing_text(self):
        for path in ("knowledge.md", "README.md", "views/about.py", "views/file_analyzer.py",
                     "views/url_scanner.py", "docs/security.md"):
            text = _read(path).lower()
            for phrase in STALE:
                self.assertNotIn(phrase, text, f"{path}: {phrase!r}")

    def test_knowledge_describes_confirmation_for_both_submissions(self):
        text = _read("knowledge.md").lower()
        for needle in ("request a new analysis", "upload this file to virustotal", "confirmation box",
                       "security community", "original file name is not sent", "pasted hash cannot be uploaded"):
            self.assertIn(needle, text, needle)

    def test_planned_section_no_longer_lists_submission_as_missing(self):
        planned = next(s for s in load_sections() if s.title == "Planned features").body.lower()
        not_implemented_list = planned.split("cyberguide ai cannot perform")[0]
        self.assertNotIn("submission to virustotal", not_implemented_list)
        self.assertIn("uploads larger than 25 mb", not_implemented_list)
        self.assertIn("after your explicit confirmation", planned)

    def test_about_table_discloses_new_analysis_uploads(self):
        about = _read("views/about.py")
        self.assertIn("VirusTotal new analysis", about)
        self.assertIn("unless you confirm a VirusTotal upload", about)
        self.assertNotIn('"Sent to third parties": "Never"}', about)


class CyberGuideRetrievalTests(unittest.TestCase):
    def test_upload_question_retrieves_the_confirmation_rules(self):
        top = " ".join(s.body for s in retrieve("Does the app upload my file to VirusTotal?", k=3)).lower()
        self.assertIn("confirmation", top)
        self.assertIn("security community", top)

    def test_url_submission_question_retrieves_opt_in_text(self):
        top = " ".join(s.body for s in retrieve("Can I submit a URL for a new scan on VirusTotal?", k=3)).lower()
        self.assertIn("request a new analysis", top)


if __name__ == "__main__":
    unittest.main()
