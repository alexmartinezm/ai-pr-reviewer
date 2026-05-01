import unittest
from unittest.mock import patch

from ai_pr_reviewer.config import _reasoning_effort_env, _reasoning_parameter_env
from ai_pr_reviewer.github import PullRequestFile, parse_added_lines, parse_diff_lines
from ai_pr_reviewer.llm import build_chat_completion_request
from ai_pr_reviewer.review import build_review_prompt, filter_findings_for_changed_lines, parse_review_response


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

    def test_parse_diff_lines_includes_context_and_added(self) -> None:
        patch = """@@ -1,4 +1,5 @@
 context
-old line
+new line
 another context
+second new line
"""
        self.assertEqual(parse_diff_lines(patch), {1, 2, 3, 4})

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

    def test_filter_findings_keeps_diff_visible_lines(self) -> None:
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
    {"path": "app.py", "line": 9, "severity": "low", "message": "context line"},
    {"path": "app.py", "line": 10, "severity": "medium", "message": "added line"},
    {"path": "app.py", "line": 99, "severity": "high", "message": "not in diff"}
  ]
}"""
        )

        filtered = filter_findings_for_changed_lines(result, [file])

        self.assertEqual(len(filtered.findings), 2)
        self.assertEqual({f.line for f in filtered.findings}, {9, 10})

    def test_review_prompt_uses_structured_diff_boundaries(self) -> None:
        file = PullRequestFile(
            filename="app.py",
            status="modified",
            additions=1,
            deletions=0,
            changes=1,
            patch="""@@ -1 +1 @@
+new code
""",
        )

        prompt = build_review_prompt([file])

        self.assertIn("<task>", prompt)
        self.assertIn('<file path="app.py"', prompt)
        self.assertIn("```diff", prompt)

    def test_reasoning_effort_accepts_supported_values(self) -> None:
        with patch.dict("os.environ", {"AI_REASONING_EFFORT": "HIGH"}):
            self.assertEqual(_reasoning_effort_env("AI_REASONING_EFFORT"), "high")

    def test_reasoning_effort_rejects_unknown_values(self) -> None:
        with patch.dict("os.environ", {"AI_REASONING_EFFORT": "maximum"}):
            with self.assertRaises(ValueError):
                _reasoning_effort_env("AI_REASONING_EFFORT")

    def test_reasoning_parameter_defaults_to_openai_style_reasoning_object(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(_reasoning_parameter_env("AI_REASONING_PARAMETER"), "reasoning")

    def test_reasoning_parameter_rejects_unknown_values(self) -> None:
        with patch.dict("os.environ", {"AI_REASONING_PARAMETER": "header"}):
            with self.assertRaises(ValueError):
                _reasoning_parameter_env("AI_REASONING_PARAMETER")

    def test_chat_request_uses_reasoning_object_by_default(self) -> None:
        request = build_chat_completion_request("model", "system", "user", 100, "medium")

        self.assertEqual(request["extra_body"], {"reasoning": {"effort": "medium"}})
        self.assertNotIn("reasoning", request)
        self.assertNotIn("reasoning_effort", request)

    def test_chat_request_can_use_reasoning_effort_field_for_compatible_providers(self) -> None:
        request = build_chat_completion_request("model", "system", "user", 100, "high", "reasoning_effort")

        self.assertEqual(request["extra_body"], {"reasoning_effort": "high"})
        self.assertNotIn("reasoning", request)
        self.assertNotIn("reasoning_effort", request)


if __name__ == "__main__":
    unittest.main()
