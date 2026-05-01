import unittest

from ai_pr_reviewer.github import PullRequestFile, parse_added_lines
from ai_pr_reviewer.review import filter_findings_for_changed_lines, parse_review_response


class ReviewParsingTests(unittest.TestCase):
    def test_parse_added_lines_only_returns_new_lines(self) -> None:
        patch = """@@ -1,4 +1,5 @@
 context
-old line
+new line
 another context
+second new line
"""

        self.assertEqual(parse_added_lines(patch), {2, 4})

    def test_parse_added_lines_ignores_no_newline_marker(self) -> None:
        patch = """@@ -1 +1,2 @@
+first line
\\ No newline at end of file
+second line
"""

        self.assertEqual(parse_added_lines(patch), {1, 2})

    def test_parse_review_response_accepts_fenced_json(self) -> None:
        result = parse_review_response(
            """```json
{
  "summary": "Found an issue.",
  "findings": [
    {
      "path": "app.py",
      "line": 10,
      "severity": "high",
      "message": "Validate this input before using it."
    }
  ]
}
```"""
        )

        self.assertEqual(result.summary, "Found an issue.")
        self.assertEqual(len(result.findings), 1)
        self.assertEqual(result.findings[0].severity, "high")

    def test_filter_findings_keeps_only_added_lines(self) -> None:
        file = PullRequestFile(
            filename="app.py",
            status="modified",
            additions=1,
            deletions=0,
            changes=1,
            patch="""@@ -9,2 +9,2 @@
 context
+new code
""",
        )
        result = parse_review_response(
            """{
  "summary": "Review complete.",
  "findings": [
    {"path": "app.py", "line": 9, "severity": "low", "message": "context"},
    {"path": "app.py", "line": 10, "severity": "medium", "message": "added"}
  ]
}"""
        )

        filtered = filter_findings_for_changed_lines(result, [file])

        self.assertEqual(len(filtered.findings), 1)
        self.assertEqual(filtered.findings[0].line, 10)


if __name__ == "__main__":
    unittest.main()
