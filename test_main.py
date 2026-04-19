import tempfile
import unittest
from pathlib import Path

from main import BrowserReviewServer, HtmlReportRenderer, ReviewOptions, SafeVibingSafetyAgent, build_argument_parser


class DeepDiveReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = SafeVibingSafetyAgent()
        self.renderer = HtmlReportRenderer()

    def test_review_candidate_builds_actionable_deep_dive_for_risky_file(self) -> None:
        code = '''
import os
import pickle

API_KEY = "demo-secret"

def login(user_input):
    query = "SELECT * FROM users WHERE name = '%s'" % user_input
    os.system("echo " + user_input)
    return pickle.loads(user_input)
'''

        review = self.agent.review_candidate("Create a login endpoint quickly", code, "auth/login.py")

        self.assertIsNotNone(review.deep_dive)
        assert review.deep_dive is not None
        self.assertEqual("high", review.deep_dive.attention_level)
        self.assertGreater(review.deep_dive.attention_score, 0)
        self.assertIn("security", review.deep_dive.review_focus)
        self.assertTrue(review.explainability.file_deep_dive)
        self.assertIn("File in focus: auth/login.py.", review.explainability.file_deep_dive)
        self.assertTrue(any("Attention level is HIGH" in item for item in review.explainability.file_deep_dive))
        self.assertTrue(any("Recommended first move: Remove hardcoded secrets." == item for item in review.explainability.file_deep_dive))
        recommendation_titles = [item.title for item in review.deep_dive.recommendations]
        self.assertIn("Remove hardcoded secrets", recommendation_titles)
        self.assertIn("Replace unsafe execution paths", recommendation_titles)
        review_dict = review.to_dict()
        self.assertIn("deep_dive", review_dict)
        self.assertEqual("high", review_dict["deep_dive"]["attention_level"])
        self.assertIsNotNone(review.file_insight)
        assert review.file_insight is not None
        self.assertIn("authentication", review.file_insight.responsibility_summary.lower())
        self.assertTrue(review.file_insight.code_smells)
        self.assertIn("file_insight", review_dict)
        self.assertIsNotNone(review.metrics)
        assert review.metrics is not None
        self.assertLess(review.metrics.secure_by_design_score, 100)
        self.assertLess(review.metrics.safe_defaults_score, 100)

    def test_review_candidate_builds_low_attention_deep_dive_for_clean_file(self) -> None:
        code = '''
def normalize_email(value: str) -> str:
    return value.strip().lower()
'''

        review = self.agent.review_candidate("Normalize input", code, "utils/strings.py")

        self.assertIsNotNone(review.deep_dive)
        assert review.deep_dive is not None
        self.assertEqual("low", review.deep_dive.attention_level)
        self.assertTrue(review.deep_dive.positive_signals)
        self.assertIn("No immediate high-risk security patterns were detected.", review.deep_dive.positive_signals)
        self.assertTrue(any(item.startswith("Positive signal: ") for item in review.explainability.file_deep_dive))
        self.assertTrue(review.deep_dive.recommendations)
        self.assertIsNotNone(review.file_insight)
        assert review.file_insight is not None
        self.assertTrue(review.file_insight.complexity_notes)

    def test_repository_review_prioritizes_high_risk_files_and_renders_deep_dive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "risky.py").write_text(
                '''
import os

TOKEN = "abc123"

def deploy(user_input):
    os.system("echo " + user_input)
''',
                encoding="utf-8",
            )
            (repo_path / "clean.py").write_text(
                '''
def add(a: int, b: int) -> int:
    return a + b
''',
                encoding="utf-8",
            )

            review = self.agent.review_repository(
                str(repo_path),
                "Review vibe-coded repository output for security, design quality, explainability, and engineering metrics.",
            )

        self.assertTrue(review.deep_dive_focus)
        self.assertEqual("risky.py", review.deep_dive_focus[0].file_path)
        self.assertEqual("high", review.deep_dive_focus[0].attention_level)
        self.assertIsNotNone(review.hackathon_showcase)
        assert review.hackathon_showcase is not None
        self.assertIn("winning demo", review.hackathon_showcase.project_tagline)
        self.assertGreaterEqual(review.hackathon_showcase.innovation_score, 55)
        review_dict = review.to_dict()
        self.assertIn("hackathon_showcase", review_dict)
        self.assertEqual(
            review.hackathon_showcase.project_tagline,
            review_dict["hackathon_showcase"]["project_tagline"],
        )
        self.assertIsNotNone(review.agent_brief)
        assert review.agent_brief is not None
        self.assertEqual("SafeVibing Safety Agent", review.agent_brief.agent_name)
        self.assertIn("AI review agent", review.agent_brief.mission)
        self.assertTrue(review.agent_brief.workflow_steps)
        self.assertTrue(review.agent_brief.autonomous_actions)
        self.assertIsNotNone(review.remediation_prompt)
        assert review.remediation_prompt is not None
        self.assertIn("senior software engineer", review.remediation_prompt.prompt)
        self.assertTrue(review.remediation_prompt.focus_points)
        self.assertTrue(review.file_remediation_prompts)
        self.assertLessEqual(len(review.file_remediation_prompts), 10)
        self.assertIn("risky.py", review.file_remediation_prompts[0].title)
        self.assertEqual("security", review.file_remediation_prompts[0].group)
        self.assertIn("agent_brief", review_dict)
        self.assertEqual(
            review.agent_brief.agent_name,
            review_dict["agent_brief"]["agent_name"],
        )
        self.assertIn("remediation_prompt", review_dict)
        self.assertIn("file_remediation_prompts", review_dict)
        html = self.renderer.render(review)
        self.assertIn("Meet your review agent", html)
        self.assertIn("VibeCoder Remediation Prompt", html)
        self.assertIn("Copy fix prompt", html)
        self.assertIn("Per-file VibeCoder prompts", html)
        self.assertIn("Copy file prompt", html)
        self.assertIn("Security", html)
        self.assertIn("Autonomous workflow", html)
        self.assertIn("Actions this agent takes for you", html)
        self.assertIn("Hackathon spotlight", html)
        self.assertIn("Why this can win the room", html)
        self.assertIn("Live demo script", html)
        self.assertIn("Repository focus queue", html)
        self.assertIn("Interactive review configuration", html)
        self.assertIn("Search file reviews", html)
        self.assertIn("Copy JSON snapshot", html)
        self.assertIn("Senior engineer brief", html)
        self.assertIn("What this file does", html)
        self.assertIn("Business Logic", html)
        self.assertIn("Code Smells", html)
        self.assertIn("Complexity Notes", html)
        self.assertIn("Secure-by-design score", html)
        self.assertIn("Safe defaults score", html)
        self.assertIn("Deep-dive recommendations", html)
        self.assertIn("Clarity walkthrough", html)
        self.assertIn("File deep dive for clarity", html)
        self.assertIn("File in focus: risky.py.", html)
        self.assertIn("risky.py", html)

    def test_repository_review_respects_include_patterns_and_max_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            (repo_path / "auth.py").write_text(
                """
TOKEN = "abc123"
def login(user_input):
    return user_input
""",
                encoding="utf-8",
            )
            (repo_path / "notes.py").write_text(
                """
def add(a, b):
    return a + b
""",
                encoding="utf-8",
            )
            (repo_path / "ui.ts").write_text("export const ready = true;\n", encoding="utf-8")

            review = self.agent.review_repository(
                str(repo_path),
                "Review for a live demo",
                ReviewOptions(include_patterns=["*.py"], exclude_patterns=["notes.py"], max_files=1, focus_mode="security"),
            )

        self.assertEqual(1, len(review.reviewed_files))
        self.assertEqual("auth.py", review.reviewed_files[0].file_path)
        self.assertEqual(["*.py"], review.options.include_patterns)
        self.assertEqual(["notes.py"], review.options.exclude_patterns)
        self.assertEqual(1, review.options.effective_max_files())

    def test_repository_review_caps_file_prompts_to_top_ten_risky_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)
            for index in range(12):
                (repo_path / f"risky_{index}.py").write_text(
                    f'''
TOKEN = "abc{index}"
def deploy_{index}(user_input):
    return eval(user_input)
''',
                    encoding="utf-8",
                )

            review = self.agent.review_repository(
                str(repo_path),
                "Review this repository for deep technical remediation.",
            )

        self.assertEqual(10, len(review.file_remediation_prompts))
        self.assertTrue(all(prompt.title.startswith("Fix risky_") for prompt in review.file_remediation_prompts))
        self.assertTrue(all(prompt.group == "security" for prompt in review.file_remediation_prompts))

    def test_browser_form_shows_explicit_github_and_local_repository_options(self) -> None:
        html = self.renderer.render(None, source_value="https://github.com/octocat/Hello-World")

        self.assertIn("Repository input option", html)
        self.assertIn("GitHub repository URL", html)
        self.assertIn("Local repository path", html)
        self.assertIn('name="github_source"', html)
        self.assertIn('name="local_source"', html)
        self.assertIn('name="audience"', html)
        self.assertIn('name="review_depth"', html)
        self.assertIn('name="focus_mode"', html)
        self.assertIn('name="max_files"', html)
        self.assertIn('name="include_patterns"', html)
        self.assertIn('name="exclude_patterns"', html)
        self.assertIn('name="demo_goal"', html)
        self.assertNotIn("Judge Demo", html)
        self.assertIn("Engineer Triage", html)
        self.assertIn('option value="github" selected', html)

    def test_cli_accepts_explicit_repository_option_flags(self) -> None:
        parser = build_argument_parser()

        github_args = parser.parse_args(["--github-url", "https://github.com/octocat/Hello-World", "--no-browser"])
        local_args = parser.parse_args(["--local-repo", "/tmp/demo-repo"])

        self.assertEqual("https://github.com/octocat/Hello-World", github_args.github_url)
        self.assertIsNone(github_args.local_repo)
        self.assertEqual("/tmp/demo-repo", local_args.local_repo)
        self.assertIsNone(local_args.github_url)

    def test_browser_handler_selects_source_from_chosen_option(self) -> None:
        server = BrowserReviewServer(self.agent)
        handler_class = server._build_handler()
        handler = handler_class.__new__(handler_class)

        github_source = handler._select_source(
            {
                "github_source": "https://github.com/octocat/Hello-World",
                "local_source": "/tmp/ignored",
            },
            "github",
        )
        local_source = handler._select_source(
            {
                "github_source": "https://github.com/octocat/Hello-World",
                "local_source": "/tmp/demo-repo",
            },
            "local",
        )

        self.assertEqual("https://github.com/octocat/Hello-World", github_source)
        self.assertEqual("/tmp/demo-repo", local_source)

    def test_browser_handler_builds_review_options_from_form(self) -> None:
        server = BrowserReviewServer(self.agent)
        handler_class = server._build_handler()
        handler = handler_class.__new__(handler_class)

        options = handler._build_review_options(
            {
                "audience": "judges",
                "review_depth": "deep",
                "focus_mode": "demo",
                "max_files": "9",
                "include_patterns": "src/*.py, api/*.ts",
                "exclude_patterns": "tests/*, docs/*",
                "demo_goal": "Give judges one unforgettable save.",
            }
        )

        self.assertEqual("judges", options.audience)
        self.assertEqual("deep", options.review_depth)
        self.assertEqual("demo", options.focus_mode)
        self.assertEqual(9, options.max_files)
        self.assertEqual(["src/*.py", "api/*.ts"], options.include_patterns)
        self.assertEqual(["tests/*", "docs/*"], options.exclude_patterns)
        self.assertEqual("Give judges one unforgettable save.", options.demo_goal)


if __name__ == "__main__":
    unittest.main()
