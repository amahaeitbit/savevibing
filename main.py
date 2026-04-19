from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from fnmatch import fnmatch
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, List, cast
from urllib.parse import parse_qs, urlparse
import webbrowser
import json
import re


@dataclass
class Finding:
    category: str
    severity: str
    title: str
    detail: str


@dataclass
class MetricSnapshot:
    cyclomatic_complexity: int
    cognitive_complexity: int
    maintainability_index: int
    duplication_risk: str
    testability_score: int
    security_risk_score: int
    secure_by_design_score: int
    safe_defaults_score: int
    change_surface: int
    explainability_completeness: int


@dataclass
class ExplainabilityReport:
    intent_understood: str
    assumptions_made: List[str]
    security_implications: List[str]
    design_trade_offs: List[str]
    metrics_impact: List[str]
    recommended_tests: List[str]
    file_deep_dive: List[str]


@dataclass
class DeepDiveRecommendation:
    priority: str
    title: str
    rationale: str
    actions: List[str]


@dataclass
class FileDeepDiveReview:
    attention_score: int
    attention_level: str
    summary: str
    hotspot_reasons: List[str]
    review_focus: List[str]
    recommendations: List[DeepDiveRecommendation]
    positive_signals: List[str]


@dataclass
class RepositoryFocusItem:
    file_path: str
    attention_score: int
    attention_level: str
    reason: str
    next_step: str


@dataclass
class StakeholderView:
    audience: str
    headline: str
    status: str
    summary: str
    priorities: List[str]
    concerns: List[str]
    opportunities: List[str]


@dataclass
class FounderBusinessAnalysis:
    headline: str
    market_position: str
    product_value: str
    go_to_market: List[str]
    business_risks: List[str]
    growth_opportunities: List[str]
    founder_questions: List[str]


@dataclass
class DeliveryRiskItem:
    title: str
    severity: str
    summary: str
    findings: List[str]
    mitigations: List[str]


@dataclass
class DeliveryRiskAnalysis:
    headline: str
    summary: str
    items: List[DeliveryRiskItem]


@dataclass
class HackathonShowcase:
    project_tagline: str
    innovation_score: int
    judge_hook: str
    winning_reasons: List[str]
    wow_metrics: List[str]
    demo_script: List[str]
    next_build_moves: List[str]


@dataclass
class AgentMissionBrief:
    agent_name: str
    agent_role: str
    mission: str
    operating_mode: str
    workflow_steps: List[str]
    autonomous_actions: List[str]
    handoff_message: str


@dataclass
class RemediationPrompt:
    title: str
    prompt: str
    focus_points: List[str]
    group: str = "security"


@dataclass
class ReviewOptions:
    audience: str = "balanced"
    review_depth: str = "balanced"
    focus_mode: str = "balanced"
    max_files: int | None = None
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    demo_goal: str = ""

    def normalized(self) -> "ReviewOptions":
        audience = self.audience if self.audience in {"balanced", "judges", "founders", "engineers"} else "balanced"
        review_depth = self.review_depth if self.review_depth in {"fast", "balanced", "deep"} else "balanced"
        focus_mode = self.focus_mode if self.focus_mode in {"balanced", "security", "architecture", "demo"} else "balanced"
        max_files = self.max_files if self.max_files is None or self.max_files > 0 else None
        return ReviewOptions(
            audience=audience,
            review_depth=review_depth,
            focus_mode=focus_mode,
            max_files=max_files,
            include_patterns=self.include_patterns,
            exclude_patterns=self.exclude_patterns,
            demo_goal=self.demo_goal.strip(),
        )

    def effective_max_files(self) -> int:
        depth_defaults = {
            "fast": 12,
            "balanced": 30,
            "deep": 75,
        }
        return self.max_files or depth_defaults[self.review_depth]

    def to_dict(self) -> dict:
        return {
            "audience": self.audience,
            "review_depth": self.review_depth,
            "focus_mode": self.focus_mode,
            "max_files": self.effective_max_files(),
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
            "demo_goal": self.demo_goal,
        }


@dataclass
class FileInsight:
    responsibility_summary: str
    business_logic_summary: str
    technical_highlights: List[str]
    code_smells: List[str]
    complexity_notes: List[str]


@dataclass
class ReviewResult:
    rewritten_prompt: str
    file_path: str = ""
    findings: List[Finding] = field(default_factory=list)
    metrics: MetricSnapshot | None = None
    explainability: ExplainabilityReport | None = None
    deep_dive: FileDeepDiveReview | None = None
    file_insight: FileInsight | None = None
    decision: str = "allow"
    risk_label: str = "low"

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "rewritten_prompt": self.rewritten_prompt,
            "risk_label": self.risk_label,
            "decision": self.decision,
            "findings": [finding.__dict__ for finding in self.findings],
            "metrics": None if self.metrics is None else self.metrics.__dict__,
            "explainability": None if self.explainability is None else self.explainability.__dict__,
            "deep_dive": None if self.deep_dive is None else {
                "attention_score": self.deep_dive.attention_score,
                "attention_level": self.deep_dive.attention_level,
                "summary": self.deep_dive.summary,
                "hotspot_reasons": self.deep_dive.hotspot_reasons,
                "review_focus": self.deep_dive.review_focus,
                "recommendations": [recommendation.__dict__ for recommendation in self.deep_dive.recommendations],
                "positive_signals": self.deep_dive.positive_signals,
            },
            "file_insight": None if self.file_insight is None else self.file_insight.__dict__,
        }


@dataclass
class RepositoryReviewResult:
    source: str
    resolved_path: str
    options: ReviewOptions = field(default_factory=ReviewOptions)
    reviewed_files: List[ReviewResult] = field(default_factory=list)
    deep_dive_focus: List[RepositoryFocusItem] = field(default_factory=list)
    aggregated_metrics: MetricSnapshot | None = None
    decision: str = "allow"
    risk_label: str = "low"
    summary: List[str] = field(default_factory=list)
    technical_leader_view: StakeholderView | None = None
    business_view: StakeholderView | None = None
    founder_business_analysis: FounderBusinessAnalysis | None = None
    delivery_risk_analysis: DeliveryRiskAnalysis | None = None
    hackathon_showcase: HackathonShowcase | None = None
    agent_brief: AgentMissionBrief | None = None
    remediation_prompt: RemediationPrompt | None = None
    file_remediation_prompts: List[RemediationPrompt] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "resolved_path": self.resolved_path,
            "options": self.options.to_dict(),
            "decision": self.decision,
            "risk_label": self.risk_label,
            "summary": self.summary,
            "aggregated_metrics": None if self.aggregated_metrics is None else self.aggregated_metrics.__dict__,
            "deep_dive_focus": [item.__dict__ for item in self.deep_dive_focus],
            "technical_leader_view": None if self.technical_leader_view is None else self.technical_leader_view.__dict__,
            "business_view": None if self.business_view is None else self.business_view.__dict__,
            "founder_business_analysis": None if self.founder_business_analysis is None else self.founder_business_analysis.__dict__,
            "delivery_risk_analysis": None if self.delivery_risk_analysis is None else {
                "headline": self.delivery_risk_analysis.headline,
                "summary": self.delivery_risk_analysis.summary,
                "items": [item.__dict__ for item in self.delivery_risk_analysis.items],
            },
            "hackathon_showcase": None if self.hackathon_showcase is None else self.hackathon_showcase.__dict__,
            "agent_brief": None if self.agent_brief is None else self.agent_brief.__dict__,
            "remediation_prompt": None if self.remediation_prompt is None else self.remediation_prompt.__dict__,
            "file_remediation_prompts": [prompt.__dict__ for prompt in self.file_remediation_prompts],
            "reviewed_files": [review.to_dict() for review in self.reviewed_files],
        }


class RepositorySourceError(ValueError):
    pass


class RepositoryLoader:
    supported_suffixes = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".kt", ".go", ".rb", ".php", ".rs", ".cs"}
    ignored_directories = {".git", ".idea", ".venv", "venv", "node_modules", "dist", "build", "__pycache__", ".pytest_cache"}
    max_file_size = 128_000

    def load(self, source: str) -> tuple[Path, bool, tempfile.TemporaryDirectory[str] | None]:
        if self._is_github_url(source):
            return self._clone_github_repo(source)

        local_path = Path(source).expanduser().resolve()
        if not local_path.exists():
            raise RepositorySourceError(f"Local repository path does not exist: {local_path}")
        if not local_path.is_dir():
            raise RepositorySourceError(f"Local repository path must be a directory: {local_path}")
        return local_path, False, None

    def iter_code_files(self, repo_path: Path, options: ReviewOptions | None = None) -> List[Path]:
        options = (options or ReviewOptions()).normalized()
        code_files: List[Path] = []
        for path in repo_path.rglob("*"):
            if not path.is_file():
                continue
            if any(part in self.ignored_directories for part in path.parts):
                continue
            if path.suffix.lower() not in self.supported_suffixes:
                continue
            if path.stat().st_size > self.max_file_size:
                continue
            relative_path = str(path.relative_to(repo_path))
            if options.include_patterns and not any(fnmatch(relative_path, pattern) for pattern in options.include_patterns):
                continue
            if options.exclude_patterns and any(fnmatch(relative_path, pattern) for pattern in options.exclude_patterns):
                continue
            code_files.append(path)
        return sorted(code_files)

    def _is_github_url(self, source: str) -> bool:
        parsed = urlparse(source)
        return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == "github.com"

    def _clone_github_repo(self, source: str) -> tuple[Path, bool, tempfile.TemporaryDirectory[str]]:
        if shutil.which("git") is None:
            raise RepositorySourceError("`git` is required to load GitHub repositories but was not found on this machine.")
        parsed = urlparse(source)
        path_parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(path_parts) < 2:
            raise RepositorySourceError("GitHub repository URLs must look like https://github.com/<owner>/<repo>.")

        owner, repo = path_parts[0], path_parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        clone_url = f"https://github.com/{owner}/{repo}.git"
        temp_dir = tempfile.TemporaryDirectory(prefix="safevibing_repo_")
        target_dir = Path(temp_dir.name) / repo
        completed = subprocess.run(
            ["git", "clone", "--depth", "1", clone_url, str(target_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            temp_dir.cleanup()
            stderr = completed.stderr.strip() or "Unknown git clone error"
            raise RepositorySourceError(f"Failed to clone GitHub repository: {stderr}")
        return target_dir, True, temp_dir


class HtmlReportRenderer:
    default_prompt = "Review vibe-coded repository output for security, design quality, explainability, and engineering metrics."

    def render(
        self,
        review: RepositoryReviewResult | None,
        source_value: str = "",
        prompt_value: str = "",
        error_message: str = "",
        options: ReviewOptions | None = None,
    ) -> str:
        resolved_options = review.options if review is not None else (options or ReviewOptions()).normalized()
        form_html = self._render_submission_form(source_value, prompt_value, resolved_options)
        if review is None:
            return self._render_shell(
                hero_title="SafeVibing Browser Command Center",
                hero_subtitle="Drop in a local repo path or GitHub URL to launch a colorful safe-vibing review.",
                hero_meta='<span class="pill neutral">Browser intake ready</span>',
                body_sections=f"{self._render_error_banner(error_message)}{form_html}",
            )

        summary_items = "".join(f"<li>{escape(item)}</li>" for item in review.summary)
        file_sections = "".join(self._render_file_review(file_review) for file_review in review.reviewed_files)
        metrics = review.aggregated_metrics
        metrics_html = ""
        if metrics is not None:
            metrics_html = self._render_metrics_grid(metrics)
        founder_business_panel = self._render_founder_business_panel(review)
        delivery_risk_panel = self._render_delivery_risk_panel(review)
        repository_focus = self._render_repository_focus(review)
        priority_actions = self._render_priority_actions(review)
        report_toolbar = self._render_report_toolbar(review)
        remediation_prompt = self._render_remediation_prompt(review)
        file_remediation_prompts = self._render_file_remediation_prompts(review)

        overview_cards = self._render_overview_cards(review)
        body_sections = f"""
        {self._render_error_banner(error_message)}
        {form_html}
        <section class=\"panel summary-panel\" id=\"repository-summary\" data-story-section=\"proof\">
          <div class=\"section-heading\">
            <div>
              <p class=\"eyebrow\">Mission control</p>
              <h2>Repository Summary</h2>
            </div>
            <div class=\"badge-row\">
              <span class=\"pill risk-{escape(review.risk_label)}\">Risk: {escape(review.risk_label.upper())}</span>
              <span class=\"pill decision-{escape(review.decision)}\">Decision: {escape(review.decision.upper())}</span>
            </div>
          </div>
          <div class=\"hero-grid\">{overview_cards}</div>
          <div class=\"two-column\">
            <div class=\"subpanel\">
              <h3>Top Findings</h3>
              <ul class=\"summary-list\">{summary_items}</ul>
            </div>
            <div class=\"subpanel\">
              <h3>Metrics Snapshot</h3>
              {metrics_html}
            </div>
          </div>
        </section>
        {priority_actions}
        {founder_business_panel}
        {delivery_risk_panel}
        {remediation_prompt}
        {repository_focus}
        {file_remediation_prompts}
        <section class=\"panel\" id=\"file-reviews\" data-story-section=\"proof\">
          <div class=\"section-heading\">
            <div>
              <p class=\"eyebrow\">Deep dive</p>
              <h2>Per-file Reviews</h2>
            </div>
            <span class=\"pill neutral\">Files reviewed: {len(review.reviewed_files)}</span>
          </div>
          {report_toolbar}
          <div class=\"file-review-list\">{file_sections}</div>
        </section>
        """

        return self._render_shell(
            hero_title="SafeVibing Safety Report",
            hero_subtitle="A hackathon-friendly review of secure-by-design code quality, explainability, and engineering risk.",
            hero_meta=(
                f'<p class="hero-meta"><span class="muted">Source</span> <code>{escape(review.source)}</code></p>'
                f'<p class="hero-meta"><span class="muted">Resolved path</span> <code>{escape(review.resolved_path)}</code></p>'
            ),
            body_sections=body_sections,
            review_payload=json.dumps(review.to_dict()).replace("</", "<\\/"),
        )

    def _render_agent_brief(self, review: RepositoryReviewResult) -> str:
        if review.agent_brief is None:
            return ""
        brief = review.agent_brief
        workflow_steps = "".join(f"<li>{escape(item)}</li>" for item in brief.workflow_steps)
        autonomous_actions = "".join(f"<li>{escape(item)}</li>" for item in brief.autonomous_actions)
        return f"""
        <section class=\"panel\">
          <div class=\"section-heading\">
            <div>
              <p class=\"eyebrow\">Agent mode</p>
              <h2>Meet your review agent</h2>
            </div>
            <div class=\"badge-row\">
              <span class=\"pill neutral\">{escape(brief.agent_name)}</span>
              <span class=\"pill risk-{escape(review.risk_label)}\">Mode: {escape(brief.operating_mode)}</span>
            </div>
          </div>
          <div class=\"two-column\">
            <div class=\"subpanel\">
              <h3>{escape(brief.agent_role)}</h3>
              <p>{escape(brief.mission)}</p>
              <p class=\"muted\">{escape(brief.handoff_message)}</p>
            </div>
            <div class=\"subpanel\">
              <h3>Autonomous workflow</h3>
              <ul class=\"summary-list\">{workflow_steps}</ul>
            </div>
          </div>
          <div class=\"subpanel\" style=\"margin-top: 16px;\">
            <h3>Actions this agent takes for you</h3>
            <ul class=\"summary-list\">{autonomous_actions}</ul>
          </div>
        </section>
        """

    def _render_shell(
        self,
        hero_title: str,
        hero_subtitle: str,
        hero_meta: str,
        body_sections: str,
        review_payload: str = "",
    ) -> str:
        return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>SafeVibing Safety Report</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #050816;
      --panel: rgba(15, 23, 42, 0.84);
      --panel-strong: rgba(17, 24, 39, 0.96);
      --border: rgba(148, 163, 184, 0.18);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #8b5cf6;
      --accent-2: #22d3ee;
      --high: #ef4444;
      --medium: #f59e0b;
      --low: #22c55e;
      --neutral: #334155;
      --shadow: 0 24px 60px rgba(15, 23, 42, 0.45);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: radial-gradient(circle at top, rgba(34, 211, 238, 0.14), transparent 25%), radial-gradient(circle at right top, rgba(139, 92, 246, 0.18), transparent 30%), linear-gradient(180deg, #020617 0%, #0f172a 55%, #020617 100%); color: var(--text); }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 32px 20px 64px; }}
    .hero {{ position: relative; overflow: hidden; padding: 32px; border-radius: 28px; margin-bottom: 24px; background: linear-gradient(135deg, rgba(30, 41, 59, 0.96), rgba(15, 23, 42, 0.92)); border: 1px solid rgba(148, 163, 184, 0.18); box-shadow: var(--shadow); }}
    .hero::after {{ content: ''; position: absolute; inset: auto -80px -80px auto; width: 260px; height: 260px; background: radial-gradient(circle, rgba(34, 211, 238, 0.2), transparent 70%); pointer-events: none; }}
    .hero h1 {{ margin: 0 0 12px; font-size: clamp(2.2rem, 4vw, 3.8rem); line-height: 1.05; }}
    .hero p {{ margin: 0 0 12px; max-width: 720px; }}
    .hero-meta {{ margin: 8px 0; }}
    .panel, .review-card, .subpanel {{ background: var(--panel); backdrop-filter: blur(16px); border: 1px solid var(--border); border-radius: 22px; box-shadow: var(--shadow); }}
    .panel {{ padding: 24px; margin-bottom: 22px; }}
    .subpanel {{ padding: 18px; }}
    .section-heading {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 18px; }}
    .section-heading h2, .subpanel h3, .review-card h3, .form-panel h2 {{ margin: 0; }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: 0.16em; font-size: 0.72rem; color: var(--accent-2); margin: 0 0 6px; font-weight: 700; }}
    .pill {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 999px; font-size: 0.9rem; font-weight: 700; margin-right: 8px; border: 1px solid transparent; }}
    .badge-row {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .neutral {{ background: rgba(51, 65, 85, 0.6); color: #dbeafe; border-color: rgba(148, 163, 184, 0.25); }}
    .risk-high, .decision-block {{ background: rgba(127, 29, 29, 0.6); color: #fecaca; border-color: rgba(239, 68, 68, 0.4); }}
    .risk-medium, .decision-warn {{ background: rgba(120, 53, 15, 0.58); color: #fde68a; border-color: rgba(245, 158, 11, 0.4); }}
    .risk-low, .decision-allow {{ background: rgba(20, 83, 45, 0.62); color: #bbf7d0; border-color: rgba(34, 197, 94, 0.35); }}
    .hero-grid, .metrics-grid, .finding-grid, .file-review-list, .two-column, .stakeholder-grid, .focus-grid, .recommendation-grid, .explainability-grid, .clarity-grid {{ display: grid; gap: 16px; }}
    .hero-grid {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-bottom: 18px; }}
    .two-column {{ grid-template-columns: minmax(260px, 1fr) minmax(320px, 1.2fr); align-items: start; }}
    .stakeholder-grid {{ grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); margin-bottom: 22px; }}
    .focus-grid {{ grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); margin-bottom: 22px; }}
    .recommendation-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-top: 16px; }}
    .explainability-grid {{ grid-template-columns: minmax(280px, 1.2fr) minmax(260px, 1fr); margin-top: 12px; }}
    .clarity-grid {{ grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }}
    .overview-card {{ padding: 18px; border-radius: 18px; background: linear-gradient(180deg, rgba(15, 23, 42, 0.9), rgba(15, 23, 42, 0.7)); border: 1px solid rgba(148, 163, 184, 0.16); }}
    .overview-card strong {{ display: block; color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; }}
    .overview-card span {{ display: block; margin-top: 8px; font-size: 1.9rem; font-weight: 800; }}
    .stakeholder-card {{ padding: 24px; border-radius: 24px; background: linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(15, 23, 42, 0.76)); border: 1px solid rgba(148, 163, 184, 0.16); }}
    .stakeholder-card h3 {{ margin: 6px 0 12px; font-size: 1.6rem; }}
    .stakeholder-card p {{ margin: 0 0 12px; }}
    .stakeholder-card ul {{ margin: 0; padding-left: 18px; }}
    .stakeholder-card li + li {{ margin-top: 8px; }}
    .stakeholder-meta {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 14px; }}
    .technical-card {{ border-top: 4px solid rgba(34, 211, 238, 0.8); }}
    .business-card {{ border-top: 4px solid rgba(139, 92, 246, 0.8); }}
    .stakeholder-section {{ margin-bottom: 22px; }}
    .stakeholder-columns {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-top: 18px; }}
    .metrics-grid {{ grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); }}
    .metric-card {{ padding: 14px; border-radius: 16px; background: rgba(2, 6, 23, 0.55); border: 1px solid rgba(148, 163, 184, 0.14); }}
    .metric-card strong {{ display: block; font-size: 0.85rem; color: var(--muted); }}
    .metric-card span {{ display: block; margin-top: 10px; font-size: 1.3rem; font-weight: 800; }}
    .metric-card small {{ display: inline-block; margin-top: 10px; padding: 4px 8px; border-radius: 999px; font-weight: 700; }}
    .summary-list, .explain-list {{ margin: 0; padding-left: 18px; }}
    .review-card {{ padding: 0; overflow: hidden; }}
    .review-body {{ padding: 0 22px 22px; }}
    .focus-card, .recommendation-card, .clarity-card, .insight-card, .prompt-card {{ padding: 18px; border-radius: 18px; background: rgba(2, 6, 23, 0.62); border: 1px solid rgba(148, 163, 184, 0.14); }}
    .focus-card p, .recommendation-card p, .clarity-card p, .insight-card p, .prompt-card p {{ margin: 0 0 12px; }}
    .focus-card ul, .recommendation-card ul, .insight-card ul, .prompt-card ul {{ margin: 0; padding-left: 18px; }}
    .review-header {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 14px; }}
    details.review-card > summary {{ list-style: none; cursor: pointer; padding: 22px; }}
    details.review-card > summary::-webkit-details-marker {{ display: none; }}
    .review-prompt {{ padding: 14px; border-radius: 14px; background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(148, 163, 184, 0.16); margin: 14px 0; }}
    .finding-grid {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin: 18px 0; }}
    .finding {{ padding: 16px; border-radius: 16px; background: rgba(2, 6, 23, 0.72); border: 1px solid rgba(148, 163, 184, 0.12); border-left: 5px solid var(--high); }}
    .finding.design {{ border-left-color: var(--accent-2); }}
    .finding.low {{ box-shadow: inset 0 0 0 1px rgba(34, 197, 94, 0.12); }}
    .finding.medium {{ box-shadow: inset 0 0 0 1px rgba(245, 158, 11, 0.14); }}
    .finding.high {{ box-shadow: inset 0 0 0 1px rgba(239, 68, 68, 0.18); }}
    .finding-header {{ display: flex; justify-content: space-between; gap: 10px; margin-bottom: 10px; }}
    .severity-high {{ color: #fecaca; }}
    .severity-medium {{ color: #fde68a; }}
    .severity-low {{ color: #bbf7d0; }}
    .form-panel {{ padding: 24px; margin-bottom: 22px; }}
    .control-grid, .toolbar-grid {{ display: grid; gap: 14px; }}
    .control-grid {{ grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-top: 16px; }}
    .toolbar-grid {{ grid-template-columns: minmax(220px, 1.2fr) repeat(2, minmax(180px, 0.9fr)); margin-bottom: 18px; }}
    .input-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-top: 18px; }}
    label {{ display: block; font-size: 0.9rem; color: var(--muted); margin-bottom: 8px; font-weight: 600; }}
    input[type=text], input[type=url], input[type=number], select, textarea {{ width: 100%; padding: 14px 16px; border-radius: 14px; border: 1px solid rgba(148, 163, 184, 0.2); background: rgba(15, 23, 42, 0.85); color: var(--text); font: inherit; }}
    textarea {{ min-height: 120px; resize: vertical; }}
    .form-actions {{ display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 16px; }}
    button {{ appearance: none; border: 0; cursor: pointer; border-radius: 14px; padding: 14px 18px; font-weight: 800; color: white; background: linear-gradient(135deg, var(--accent), var(--accent-2)); box-shadow: 0 14px 28px rgba(34, 211, 238, 0.18); }}
    .ghost-button, .filter-button {{ background: rgba(15, 23, 42, 0.72); color: var(--text); border: 1px solid rgba(148, 163, 184, 0.2); box-shadow: none; }}
    .filter-button.active, .ghost-button.active {{ border-color: rgba(34, 211, 238, 0.55); color: #a5f3fc; }}
    .helper-text, .muted {{ color: var(--muted); }}
    .error-banner {{ padding: 16px 18px; border-radius: 18px; margin-bottom: 18px; background: rgba(127, 29, 29, 0.45); border: 1px solid rgba(239, 68, 68, 0.35); color: #fecaca; }}
    code {{ background: rgba(2, 6, 23, 0.92); padding: 3px 7px; border-radius: 8px; word-break: break-all; }}
    .focus-list, .signal-list {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }}
    .focus-chip, .signal-chip {{ display: inline-flex; align-items: center; padding: 8px 12px; border-radius: 999px; font-size: 0.85rem; font-weight: 700; }}
    .focus-chip {{ background: rgba(34, 211, 238, 0.12); border: 1px solid rgba(34, 211, 238, 0.25); color: #a5f3fc; }}
    .signal-chip {{ background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.25); color: #bbf7d0; }}
    .clarity-card strong, .insight-card strong {{ display: block; margin-bottom: 8px; color: var(--accent-2); font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; }}
    .clarity-card p:last-child {{ margin-bottom: 0; }}
    .preset-row, .filter-row, .story-row {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .toolbar-panel {{ padding: 18px; border-radius: 18px; background: rgba(2, 6, 23, 0.62); border: 1px solid rgba(148, 163, 184, 0.14); }}
    .setup-card {{ padding: 18px; border-radius: 18px; background: rgba(2, 6, 23, 0.62); border: 1px solid rgba(148, 163, 184, 0.14); }}
    .setup-card ul {{ margin: 0; padding-left: 18px; }}
    .review-card[hidden], .panel[hidden], .stakeholder-card[hidden] {{ display: none !important; }}
    .spotlight {{ outline: 2px solid rgba(34, 211, 238, 0.65); box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.1); }}
    .copy-status {{ min-height: 1.2rem; }}
    .prompt-block {{ white-space: pre-wrap; line-height: 1.5; }}
    @media (max-width: 860px) {{ .two-column, .toolbar-grid {{ grid-template-columns: 1fr; }} main {{ padding-inline: 14px; }} .hero, .panel, .form-panel, .review-card {{ padding: 20px; }} }}
  </style>
</head>
<body>
  <main>
    <section class=\"hero\">
      <p class=\"eyebrow\">Safe Vibing · Security · Design · Explainability · Metrics</p>
      <h1>{escape(hero_title)}</h1>
      <p class=\"muted\">{escape(hero_subtitle)}</p>
      {hero_meta}
    </section>
    {body_sections}
  </main>
  <script id="review-payload" type="application/json">{review_payload}</script>
  <script>
    (() => {{
      const sourceMode = document.getElementById("source_mode");
      const githubSource = document.getElementById("github_source");
      const localSource = document.getElementById("local_source");
      const promptField = document.getElementById("prompt");
      const audienceField = document.getElementById("audience");
      const focusField = document.getElementById("focus_mode");
      const goalField = document.getElementById("demo_goal");
      const maxFilesField = document.getElementById("max_files");
      const reportCards = Array.from(document.querySelectorAll(".review-card"));
      const copyButton = document.getElementById("copy-report-json");
      const copyStatus = document.getElementById("copy-status");
      const syncSourceFields = () => {{
        if (!sourceMode || !githubSource || !localSource) return;
        const githubSelected = sourceMode.value === "github";
        githubSource.disabled = !githubSelected;
        localSource.disabled = githubSelected;
      }};

      syncSourceFields();
      if (sourceMode) {{
        sourceMode.addEventListener("change", syncSourceFields);
      }}

      document.querySelectorAll("[data-prompt-preset]").forEach((button) => {{
        button.addEventListener("click", () => {{
          if (promptField) promptField.value = button.getAttribute("data-prompt-preset") || "";
          if (audienceField && button.getAttribute("data-audience-preset")) audienceField.value = button.getAttribute("data-audience-preset");
          if (focusField && button.getAttribute("data-focus-preset")) focusField.value = button.getAttribute("data-focus-preset");
          if (goalField && button.getAttribute("data-goal-preset")) goalField.value = button.getAttribute("data-goal-preset");
          if (maxFilesField && button.getAttribute("data-max-files")) maxFilesField.value = button.getAttribute("data-max-files");
        }});
      }});

      const searchInput = document.getElementById("report-search");
      const riskButtons = Array.from(document.querySelectorAll("[data-risk-filter]"));
      const focusSelect = document.getElementById("report-focus-filter");

      const applyCardFilters = () => {{
        const riskValue = riskButtons.find((button) => button.classList.contains("active"))?.getAttribute("data-risk-filter") || "all";
        const searchValue = (searchInput?.value || "").toLowerCase();
        const focusValue = focusSelect?.value || "all";
        reportCards.forEach((card) => {{
          const file = card.getAttribute("data-file") || "";
          const risk = card.getAttribute("data-risk") || "";
          const focus = card.getAttribute("data-focus") || "";
          const matchesRisk = riskValue === "all" || risk === riskValue;
          const matchesSearch = !searchValue || file.includes(searchValue);
          const matchesFocus = focusValue === "all" || focus.includes(focusValue);
          card.hidden = !(matchesRisk && matchesSearch && matchesFocus);
        }});
      }};

      riskButtons.forEach((button) => {{
        button.addEventListener("click", () => {{
          riskButtons.forEach((item) => item.classList.remove("active"));
          button.classList.add("active");
          applyCardFilters();
        }});
      }});
      if (searchInput) searchInput.addEventListener("input", applyCardFilters);
      if (focusSelect) focusSelect.addEventListener("change", applyCardFilters);
      applyCardFilters();

      document.querySelectorAll("[data-story-target]").forEach((button) => {{
        button.addEventListener("click", () => {{
          document.querySelectorAll(".spotlight").forEach((node) => node.classList.remove("spotlight"));
          const targetId = button.getAttribute("data-story-target");
          if (!targetId) return;
          const target = document.getElementById(targetId);
          if (!target) return;
          target.classList.add("spotlight");
          target.scrollIntoView({{ behavior: "smooth", block: "start" }});
        }});
      }});

      if (copyButton) {{
        copyButton.addEventListener("click", async () => {{
          const payloadNode = document.getElementById("review-payload");
          if (!payloadNode?.textContent) return;
          try {{
            await navigator.clipboard.writeText(payloadNode.textContent);
            if (copyStatus) copyStatus.textContent = "Copied JSON snapshot for judges and teammates.";
          }} catch (_error) {{
            if (copyStatus) copyStatus.textContent = "Clipboard access failed in this browser.";
          }}
        }});
      }}

      document.querySelectorAll("[data-copy-target]").forEach((button) => {{
        button.addEventListener("click", async () => {{
          const targetId = button.getAttribute("data-copy-target");
          const statusId = button.getAttribute("data-copy-status");
          const promptNode = targetId ? document.getElementById(targetId) : null;
          const promptStatus = statusId ? document.getElementById(statusId) : null;
          if (!promptNode?.textContent) return;
          try {{
            await navigator.clipboard.writeText(promptNode.textContent);
            if (promptStatus) promptStatus.textContent = "Copied VibeCoder remediation prompt.";
          }} catch (_error) {{
            if (promptStatus) promptStatus.textContent = "Clipboard access failed in this browser.";
          }}
        }});
      }});
    }})();
  </script>
</body>
</html>
"""

    def _render_submission_form(self, source_value: str, prompt_value: str, options: ReviewOptions) -> str:
        source_mode = "github" if RepositoryLoader()._is_github_url(source_value) else "local"
        github_value = source_value if source_mode == "github" else ""
        local_value = source_value if source_mode == "local" else ""
        include_value = ", ".join(options.include_patterns)
        exclude_value = ", ".join(options.exclude_patterns)
        return f"""
        <section class=\"panel form-panel\">
          <p class=\"eyebrow\">Browser intake</p>
          <h2>Analyze a vibe-coded repository</h2>
          <p class=\"helper-text\">Choose how you want to provide the repository, then launch a full colorful review in the browser.</p>
          <div class="preset-row">
            <button type="button" class="ghost-button" data-prompt-preset="Review this repository for founder readiness: identify delivery risk, trust blockers, and the strongest business narrative for launch." data-audience-preset="founders" data-focus-preset="demo" data-goal-preset="Make the launch story crisp enough for customers, mentors, and investors." data-max-files="18">Founder Story</button>
            <button type="button" class="ghost-button" data-prompt-preset="Review this repository for engineering action: prioritize the biggest security, architecture, and testing fixes required before shipping." data-audience-preset="engineers" data-focus-preset="security" data-goal-preset="Leave the team with an obvious first fix and a credible ship plan." data-max-files="30">Engineer Triage</button>
          </div>
          <form method=\"post\" action=\"/review\">
            <div class=\"input-grid\">
              <div>
                <label for=\"source_mode\">Repository input option</label>
                <select id=\"source_mode\" name=\"source_mode\">
                  <option value=\"github\"{' selected' if source_mode == 'github' else ''}>GitHub repository URL</option>
                  <option value=\"local\"{' selected' if source_mode == 'local' else ''}>Local repository path</option>
                </select>
                <label for=\"github_source\">GitHub repository URL</label>
                <input id=\"github_source\" name=\"github_source\" type=\"url\" value=\"{escape(github_value)}\" placeholder=\"https://github.com/owner/repo\">
                <label for=\"local_source\">Local repository path</label>
                <input id=\"local_source\" name=\"local_source\" type=\"text\" value=\"{escape(local_value)}\" placeholder=\"/Users/you/project\">
              </div>
              <div>
                <label for=\"prompt\">Review prompt</label>
                <textarea id=\"prompt\" name=\"prompt\">{escape(prompt_value or self.default_prompt)}</textarea>
              </div>
            </div>
            <div class="control-grid">
              <div>
                <label for="audience">Story audience</label>
                <select id="audience" name="audience">
                  <option value="balanced"{' selected' if options.audience == 'balanced' else ''}>Balanced team view</option>
                  <option value="judges"{' selected' if options.audience == 'judges' else ''}>Hackathon judges</option>
                  <option value="founders"{' selected' if options.audience == 'founders' else ''}>Founders and operators</option>
                  <option value="engineers"{' selected' if options.audience == 'engineers' else ''}>Engineering team</option>
                </select>
              </div>
              <div>
                <label for="review_depth">Review depth</label>
                <select id="review_depth" name="review_depth">
                  <option value="fast"{' selected' if options.review_depth == 'fast' else ''}>Fast scan</option>
                  <option value="balanced"{' selected' if options.review_depth == 'balanced' else ''}>Balanced</option>
                  <option value="deep"{' selected' if options.review_depth == 'deep' else ''}>Deep inspection</option>
                </select>
              </div>
              <div>
                <label for="focus_mode">Review focus</label>
                <select id="focus_mode" name="focus_mode">
                  <option value="balanced"{' selected' if options.focus_mode == 'balanced' else ''}>Balanced</option>
                  <option value="security"{' selected' if options.focus_mode == 'security' else ''}>Security hotspots</option>
                  <option value="architecture"{' selected' if options.focus_mode == 'architecture' else ''}>Architecture clarity</option>
                  <option value="demo"{' selected' if options.focus_mode == 'demo' else ''}>Demo readiness</option>
                </select>
              </div>
              <div>
                <label for="max_files">Max files to inspect</label>
                <input id="max_files" name="max_files" type="number" min="1" max="200" value="{options.effective_max_files()}">
              </div>
              <div>
                <label for="include_patterns">Include patterns</label>
                <input id="include_patterns" name="include_patterns" type="text" value="{escape(include_value)}" placeholder="src/*.py, api/*.ts">
              </div>
              <div>
                <label for="exclude_patterns">Exclude patterns</label>
                <input id="exclude_patterns" name="exclude_patterns" type="text" value="{escape(exclude_value)}" placeholder="tests/*, docs/*">
              </div>
            </div>
            <div style="margin-top: 16px;">
              <label for="demo_goal">Demo goal</label>
              <textarea id="demo_goal" name="demo_goal" style="min-height: 84px;">{escape(options.demo_goal)}</textarea>
            </div>
            <div class=\"form-actions\">
              <button type=\"submit\">Run review</button>
              <span class=\"helper-text\">The agent keeps all findings, metrics, and approval decisions together on one browser page.</span>
            </div>
          </form>
        </section>
        """

    def _render_error_banner(self, error_message: str) -> str:
        if not error_message:
            return ""
        return f'<div class="error-banner"><strong>Review failed:</strong> {escape(error_message)}</div>'

    def _render_overview_cards(self, review: RepositoryReviewResult) -> str:
        findings_total = sum(len(file_review.findings) for file_review in review.reviewed_files)
        return "".join(
            self._render_overview_card(title, value)
            for title, value in [
                ("Files reviewed", str(len(review.reviewed_files))),
                ("Total findings", str(findings_total)),
                ("Overall risk", review.risk_label.upper()),
                ("Approval", review.decision.upper()),
            ]
        )

    def _render_overview_card(self, title: str, value: str) -> str:
        return f'<div class="overview-card"><strong>{escape(title)}</strong><span>{escape(value)}</span></div>'

    def _render_priority_actions(self, review: RepositoryReviewResult) -> str:
        focus_items = review.deep_dive_focus[:3]
        actions = [
            f"Start with {item.file_path}: {item.next_step}." for item in focus_items
        ] or ["No urgent file-level action was surfaced by the current review."]
        if review.delivery_risk_analysis is not None:
            actions.extend(
                f"{item.title}: {item.findings[0]}" for item in review.delivery_risk_analysis.items[:2] if item.findings
            )
        action_list = "".join(f"<li>{escape(item)}</li>" for item in actions[:5])
        return f"""
        <section class="panel" id="priority-actions" data-story-section="proof">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Top actions</p>
              <h2>What matters now</h2>
            </div>
            <span class="pill neutral">Concise view</span>
          </div>
          <ul class="summary-list">{action_list}</ul>
        </section>
        """

    def _render_stakeholder_sections(self, review: RepositoryReviewResult) -> str:
        views = [
            (review.technical_leader_view, "technical-card"),
            (review.business_view, "business-card"),
        ]
        cards = "".join(
            self._render_stakeholder_card(view, css_class)
            for view, css_class in views
            if view is not None
        )
        if not cards:
            return ""
        return f"""
        <section class=\"stakeholder-section\" id=\"stakeholder-views\" data-story-section=\"business\">
          <div class=\"section-heading\">
            <div>
              <p class=\"eyebrow\">Dual view</p>
              <h2>Stakeholder Views</h2>
            </div>
            <span class=\"pill neutral\">Audience-aware reporting</span>
          </div>
          <div class=\"stakeholder-grid\">{cards}</div>
        </section>
        """

    def _render_stakeholder_card(self, view: StakeholderView, css_class: str) -> str:
        priorities = "".join(f"<li>{escape(item)}</li>" for item in view.priorities)
        concerns = "".join(f"<li>{escape(item)}</li>" for item in view.concerns)
        opportunities = "".join(f"<li>{escape(item)}</li>" for item in view.opportunities)
        return f"""
        <article class=\"stakeholder-card {escape(css_class)}\">
          <p class=\"eyebrow\">{escape(view.audience)}</p>
          <h3>{escape(view.headline)}</h3>
          <div class=\"stakeholder-meta\">
            <span class=\"pill risk-{escape(view.status)}\">Status: {escape(view.status.upper())}</span>
          </div>
          <p>{escape(view.summary)}</p>
          <div class=\"stakeholder-columns\">
            <div class=\"subpanel\">
              <h3>Priorities</h3>
              <ul>{priorities}</ul>
            </div>
            <div class=\"subpanel\">
              <h3>Concerns</h3>
              <ul>{concerns}</ul>
            </div>
            <div class=\"subpanel\">
              <h3>Opportunities</h3>
              <ul>{opportunities}</ul>
            </div>
          </div>
        </article>
        """

    def _render_founder_business_panel(self, review: RepositoryReviewResult) -> str:
        if review.founder_business_analysis is None:
            return ""
        analysis = review.founder_business_analysis
        go_to_market = "".join(f"<li>{escape(item)}</li>" for item in analysis.go_to_market)
        business_risks = "".join(f"<li>{escape(item)}</li>" for item in analysis.business_risks)
        growth_opportunities = "".join(f"<li>{escape(item)}</li>" for item in analysis.growth_opportunities)
        founder_questions = "".join(f"<li>{escape(item)}</li>" for item in analysis.founder_questions)
        return f"""
        <section class="panel" id="founder-business-analysis" data-story-section="business">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Founder view</p>
              <h2>High-Level Founder Business Analysis</h2>
            </div>
            <span class="pill neutral">Separate from coding review</span>
          </div>
          <div class="two-column">
            <div class="subpanel">
              <h3>{escape(analysis.headline)}</h3>
              <p><strong>Market position:</strong> {escape(analysis.market_position)}</p>
              <p><strong>Product value:</strong> {escape(analysis.product_value)}</p>
            </div>
            <div class="subpanel">
              <h3>Go-to-market angle</h3>
              <ul class="summary-list">{go_to_market}</ul>
            </div>
          </div>
          <div class="stakeholder-columns" style="margin-top: 16px;">
            <div class="subpanel">
              <h3>Business Risks</h3>
              <ul>{business_risks}</ul>
            </div>
            <div class="subpanel">
              <h3>Growth Opportunities</h3>
              <ul>{growth_opportunities}</ul>
            </div>
            <div class="subpanel">
              <h3>Founder Questions</h3>
              <ul>{founder_questions}</ul>
            </div>
          </div>
        </section>
        """

    def _render_delivery_risk_panel(self, review: RepositoryReviewResult) -> str:
        if review.delivery_risk_analysis is None:
            return ""
        analysis = review.delivery_risk_analysis
        cards = "".join(
            f"""
            <article class="prompt-card">
              <div class="badge-row">
                <span class="pill risk-{escape(item.severity)}">{escape(item.severity.upper())}</span>
              </div>
              <h3>{escape(item.title)}</h3>
              <p>{escape(item.summary)}</p>
              <strong>Findings</strong>
              <ul>{"".join(f"<li>{escape(finding)}</li>" for finding in item.findings)}</ul>
              <strong>Mitigations</strong>
              <ul>{"".join(f"<li>{escape(action)}</li>" for action in item.mitigations)}</ul>
            </article>
            """
            for item in analysis.items
        )
        return f"""
        <section class="panel" id="delivery-risk-analysis" data-story-section="risks">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Risk analysis</p>
              <h2>{escape(analysis.headline)}</h2>
            </div>
            <span class="pill neutral">Governance critical</span>
          </div>
          <p>{escape(analysis.summary)}</p>
          <div class="recommendation-grid">{cards}</div>
        </section>
        """

    def _render_repository_focus(self, review: RepositoryReviewResult) -> str:
        if not review.deep_dive_focus:
            return ""
        focus_cards = "".join(self._render_repository_focus_card(item) for item in review.deep_dive_focus)
        return f"""
        <section class=\"panel\" id=\"repo-focus\" data-story-section=\"risks\">
          <div class=\"section-heading\">
            <div>
              <p class=\"eyebrow\">Repository focus queue</p>
              <h2>Repository focus queue</h2>
            </div>
            <span class=\"pill neutral\">Prioritized files: {len(review.deep_dive_focus)}</span>
          </div>
          <div class=\"focus-grid\">{focus_cards}</div>
        </section>
        """

    def _render_hackathon_showcase(self, review: RepositoryReviewResult) -> str:
        if review.hackathon_showcase is None:
            return ""
        showcase = review.hackathon_showcase
        winning_reasons = "".join(f"<li>{escape(item)}</li>" for item in showcase.winning_reasons)
        wow_metrics = "".join(f'<div class="metric-card"><strong>Pitch metric</strong><span>{escape(item)}</span></div>' for item in showcase.wow_metrics)
        demo_script = "".join(f"<li>{escape(item)}</li>" for item in showcase.demo_script)
        next_build_moves = "".join(f"<li>{escape(item)}</li>" for item in showcase.next_build_moves)
        innovation_level = self._metric_level(showcase.innovation_score, 60, 85)
        return f"""
        <section class="panel" id="hackathon-spotlight" data-story-section="judges">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Hackathon spotlight</p>
              <h2>Why this can win the room</h2>
            </div>
            <div class="badge-row">
              <span class="pill risk-{escape(innovation_level)}">Innovation score: {showcase.innovation_score}</span>
              <span class="pill neutral">Judge-ready story</span>
            </div>
          </div>
          <div class="two-column">
            <div class="subpanel">
              <h3>{escape(showcase.project_tagline)}</h3>
              <p>{escape(showcase.judge_hook)}</p>
              <ul class="summary-list">{winning_reasons}</ul>
            </div>
            <div class="subpanel">
              <h3>Pitch-ready metrics</h3>
              <div class="metrics-grid">{wow_metrics}</div>
            </div>
          </div>
          <div class="two-column" style="margin-top: 16px;">
            <div class="subpanel">
              <h3>Live demo script</h3>
              <ul class="summary-list">{demo_script}</ul>
            </div>
            <div class="subpanel">
              <h3>Next build moves</h3>
              <ul class="summary-list">{next_build_moves}</ul>
            </div>
          </div>
        </section>
        """

    def _render_repository_focus_card(self, item: RepositoryFocusItem) -> str:
        return f"""
        <article class=\"focus-card\">
          <div class=\"section-heading\">
            <div>
              <p class=\"eyebrow\">Priority file</p>
              <h3>{escape(item.file_path)}</h3>
            </div>
            <div class=\"badge-row\">
              <span class=\"pill risk-{escape(item.attention_level)}\">Attention: {escape(item.attention_level.upper())}</span>
              <span class=\"pill neutral\">Score: {item.attention_score}</span>
            </div>
          </div>
          <p>{escape(item.reason)}</p>
          <p><strong>Recommended next step:</strong> {escape(item.next_step)}</p>
        </article>
        """

    def _render_metrics_grid(self, metrics: MetricSnapshot) -> str:
        metric_items = [
            ("Cyclomatic complexity", str(metrics.cyclomatic_complexity), self._metric_level(metrics.cyclomatic_complexity, 6, 12)),
            ("Cognitive complexity", str(metrics.cognitive_complexity), self._metric_level(metrics.cognitive_complexity, 10, 18)),
            ("Maintainability index", str(metrics.maintainability_index), self._inverse_metric_level(metrics.maintainability_index, 70, 45)),
            ("Duplication risk", metrics.duplication_risk.upper(), metrics.duplication_risk),
            ("Testability score", str(metrics.testability_score), self._inverse_metric_level(metrics.testability_score, 70, 45)),
            ("Security risk score", str(metrics.security_risk_score), self._metric_level(metrics.security_risk_score, 40, 70)),
            ("Secure-by-design score", str(metrics.secure_by_design_score), self._inverse_metric_level(metrics.secure_by_design_score, 70, 45)),
            ("Safe defaults score", str(metrics.safe_defaults_score), self._inverse_metric_level(metrics.safe_defaults_score, 70, 45)),
            ("Change surface", str(metrics.change_surface), self._metric_level(metrics.change_surface, 8, 16)),
            ("Explainability completeness", str(metrics.explainability_completeness), self._inverse_metric_level(metrics.explainability_completeness, 75, 50)),
        ]
        cards_list: List[str] = []
        for title, value, level in metric_items:
            badge_level = level if level in {"low", "medium", "high"} else "low"
            cards_list.append(
                f'<div class="metric-card"><strong>{escape(title)}</strong><span>{escape(value)}</span>'
                f'<small class="pill risk-{escape(badge_level)}">{escape(level.upper())}</small></div>'
            )
        cards = "".join(cards_list)
        return f'<div class="metrics-grid">{cards}</div>'

    def _metric_level(self, value: int, medium_threshold: int, high_threshold: int) -> str:
        if value >= high_threshold:
            return "high"
        if value >= medium_threshold:
            return "medium"
        return "low"

    def _inverse_metric_level(self, value: int, low_threshold: int, medium_threshold: int) -> str:
        if value <= medium_threshold:
            return "high"
        if value <= low_threshold:
            return "medium"
        return "low"

    def _render_file_review(self, review: ReviewResult) -> str:
        findings_html = "".join(
            f"<div class=\"finding {escape(finding.category)} {escape(finding.severity)}\">"
            f"<div class=\"finding-header\"><strong>{escape(finding.title)}</strong>"
            f"<span class=\"severity-{escape(finding.severity)}\">{escape(finding.category.upper())} · {escape(finding.severity.upper())}</span></div>"
            f"<div>{escape(finding.detail)}</div></div>"
            for finding in review.findings
        ) or "<p class=\"muted\">No findings for this file.</p>"

        explainability_html = ""
        if review.explainability is not None:
            file_deep_dive_cards = "".join(
                f'<article class="clarity-card"><strong>Clarity point {index}</strong><p>{escape(item)}</p></article>'
                for index, item in enumerate(review.explainability.file_deep_dive, start=1)
            )
            explainability_html = f"""
            <div class="explainability-grid">
              <div class="subpanel">
                <p class="eyebrow">Reasoning trace</p>
                <h4>Core explainability</h4>
                <ul class="explain-list">
                  <li><strong>Intent understood:</strong> {escape(review.explainability.intent_understood)}</li>
                  <li><strong>Assumptions:</strong> {escape('; '.join(review.explainability.assumptions_made))}</li>
                  <li><strong>Security implications:</strong> {escape('; '.join(review.explainability.security_implications))}</li>
                  <li><strong>Design trade-offs:</strong> {escape('; '.join(review.explainability.design_trade_offs))}</li>
                  <li><strong>Metrics impact:</strong> {escape('; '.join(review.explainability.metrics_impact))}</li>
                  <li><strong>Recommended tests:</strong> {escape('; '.join(review.explainability.recommended_tests))}</li>
                </ul>
              </div>
              <div class="subpanel">
                <p class="eyebrow">Clarity walkthrough</p>
                <h4>File deep dive for clarity</h4>
                <div class="clarity-grid">{file_deep_dive_cards}</div>
              </div>
            </div>
            """

        deep_dive_html = ""
        if review.deep_dive is not None:
            recommendation_cards = "".join(
                f'<article class="recommendation-card"><div class="badge-row">'
                f'<span class="pill risk-{escape(recommendation.priority)}">{escape(recommendation.priority.upper())}</span></div>'
                f'<h3>{escape(recommendation.title)}</h3><p>{escape(recommendation.rationale)}</p>'
                f'<ul>{"".join(f"<li>{escape(action)}</li>" for action in recommendation.actions)}</ul></article>'
                for recommendation in review.deep_dive.recommendations
            )
            focus_chips = "".join(
                f'<span class="focus-chip">{escape(item.title())}</span>'
                for item in review.deep_dive.review_focus
            )
            positive_signal_chips = "".join(
                f'<span class="signal-chip">{escape(signal)}</span>'
                for signal in review.deep_dive.positive_signals
            )
            hotspot_items = "".join(f"<li>{escape(item)}</li>" for item in review.deep_dive.hotspot_reasons)
            deep_dive_html = f"""
            <div class=\"subpanel\">
              <div class=\"section-heading\">
                <div>
                  <p class=\"eyebrow\">Deep-dive recommendations</p>
                  <h3>Deep-dive recommendations</h3>
                </div>
                <div class=\"badge-row\">
                  <span class=\"pill risk-{escape(review.deep_dive.attention_level)}\">Attention: {escape(review.deep_dive.attention_level.upper())}</span>
                  <span class=\"pill neutral\">Score: {review.deep_dive.attention_score}</span>
                </div>
              </div>
              <p>{escape(review.deep_dive.summary)}</p>
              <ul class=\"summary-list\">{hotspot_items}</ul>
              <div class=\"focus-list\">{focus_chips}</div>
              <div class=\"signal-list\">{positive_signal_chips}</div>
              <div class=\"recommendation-grid\">{recommendation_cards}</div>
            </div>
            """

        review_focus_values = " ".join(review.deep_dive.review_focus if review.deep_dive is not None else [])
        file_insight_html = ""
        if review.file_insight is not None:
            file_insight_html = f"""
            <div class="subpanel">
              <div class="section-heading">
                <div>
                  <p class="eyebrow">Senior engineer brief</p>
                  <h3>What this file does</h3>
                </div>
                <span class="pill neutral">Technical depth</span>
              </div>
              <div class="recommendation-grid">
                <article class="insight-card">
                  <strong>Responsibility</strong>
                  <p>{escape(review.file_insight.responsibility_summary)}</p>
                  <strong>Business Logic</strong>
                  <p>{escape(review.file_insight.business_logic_summary)}</p>
                </article>
                <article class="insight-card">
                  <strong>Technical Highlights</strong>
                  <ul>{"".join(f"<li>{escape(item)}</li>" for item in review.file_insight.technical_highlights)}</ul>
                </article>
                <article class="insight-card">
                  <strong>Code Smells</strong>
                  <ul>{"".join(f"<li>{escape(item)}</li>" for item in review.file_insight.code_smells)}</ul>
                </article>
                <article class="insight-card">
                  <strong>Complexity Notes</strong>
                  <ul>{"".join(f"<li>{escape(item)}</li>" for item in review.file_insight.complexity_notes)}</ul>
                </article>
              </div>
            </div>
            """
        summary_text = review.deep_dive.summary if review.deep_dive is not None else "Open for detailed technical review."
        is_open = " open" if review.risk_label == "high" else ""
        return f"""
        <details class=\"review-card\"{is_open} data-file=\"{escape((review.file_path or 'candidate').lower())}\" data-risk=\"{escape(review.risk_label)}\" data-focus=\"{escape(review_focus_values)}\">
          <summary>
            <div class=\"review-header\">
              <div>
                <p class=\"eyebrow\">File review</p>
                <h3>{escape(review.file_path or 'candidate')}</h3>
                <p class=\"muted\">{escape(summary_text)}</p>
              </div>
              <div class=\"badge-row\">
                <span class=\"pill risk-{escape(review.risk_label)}\">Risk: {escape(review.risk_label.upper())}</span>
                <span class=\"pill decision-{escape(review.decision)}\">Decision: {escape(review.decision.upper())}</span>
              </div>
            </div>
          </summary>
          <div class=\"review-body\">
            <div class=\"review-prompt\"><strong>Rewritten prompt:</strong> {escape(review.rewritten_prompt)}</div>
            {file_insight_html}
            <div class=\"finding-grid\">{findings_html}</div>
            {deep_dive_html}
            <div class=\"subpanel\">
              <h3>Explainability</h3>
              {explainability_html}
            </div>
          </div>
        </details>
        """

    def _render_review_setup(self, review: RepositoryReviewResult) -> str:
        options = review.options.normalized()
        include_summary = ", ".join(options.include_patterns) if options.include_patterns else "All supported files"
        exclude_summary = ", ".join(options.exclude_patterns) if options.exclude_patterns else "No excludes"
        return f"""
        <section class="panel" id="review-setup">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Review setup</p>
              <h2>Interactive review configuration</h2>
            </div>
            <span class="pill neutral">Audience: {escape(options.audience.title())}</span>
          </div>
          <div class="hero-grid">
            <div class="setup-card"><strong>Depth</strong><span>{escape(options.review_depth.title())}</span></div>
            <div class="setup-card"><strong>Focus</strong><span>{escape(options.focus_mode.title())}</span></div>
            <div class="setup-card"><strong>Files capped at</strong><span>{options.effective_max_files()}</span></div>
            <div class="setup-card"><strong>Demo goal</strong><span>{escape(options.demo_goal or 'No custom goal supplied')}</span></div>
          </div>
          <div class="two-column">
            <div class="subpanel">
              <h3>Included paths</h3>
              <p>{escape(include_summary)}</p>
            </div>
            <div class="subpanel">
              <h3>Excluded paths</h3>
              <p>{escape(exclude_summary)}</p>
            </div>
          </div>
        </section>
        """

    def _render_report_toolbar(self, review: RepositoryReviewResult) -> str:
        focus_options = ["all", "security", "design", "testing", "explainability", "regression safety"]
        focus_select_options = "".join(
            f'<option value="{escape(option)}">{escape(option.title() if option != "all" else "All review focuses")}</option>'
            for option in focus_options
        )
        return f"""
        <div class="toolbar-grid">
          <div class="toolbar-panel">
            <label for="report-search">Search file reviews</label>
            <input id="report-search" type="text" placeholder="Filter by filename">
            <div class="story-row" style="margin-top: 12px;">
              <button type="button" class="ghost-button" data-story-target="hackathon-spotlight">Pitch judges</button>
              <button type="button" class="ghost-button" data-story-target="repo-focus">Show risks</button>
              <button type="button" class="ghost-button" data-story-target="repository-summary">Show proof</button>
            </div>
          </div>
          <div class="toolbar-panel">
            <label>Risk filter</label>
            <div class="filter-row">
              <button type="button" class="filter-button active" data-risk-filter="all">All</button>
              <button type="button" class="filter-button" data-risk-filter="high">High</button>
              <button type="button" class="filter-button" data-risk-filter="medium">Medium</button>
              <button type="button" class="filter-button" data-risk-filter="low">Low</button>
            </div>
          </div>
          <div class="toolbar-panel">
            <label for="report-focus-filter">Focus filter</label>
            <select id="report-focus-filter">{focus_select_options}</select>
            <div style="margin-top: 12px;">
              <button type="button" id="copy-report-json" class="ghost-button">Copy JSON snapshot</button>
              <div id="copy-status" class="helper-text copy-status"></div>
            </div>
          </div>
        </div>
        """

    def _render_remediation_prompt(self, review: RepositoryReviewResult) -> str:
        if review.remediation_prompt is None:
            return ""
        focus_points = "".join(f"<li>{escape(item)}</li>" for item in review.remediation_prompt.focus_points)
        return f"""
        <section class="panel" id="remediation-prompt" data-story-section="fixes">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Fix prompt</p>
              <h2>{escape(review.remediation_prompt.title)}</h2>
            </div>
            <span class="pill neutral">Ready for VibeCoder</span>
          </div>
          <div class="two-column">
            <div class="prompt-card">
              <strong>Focus points</strong>
              <ul>{focus_points}</ul>
            </div>
            <div class="prompt-card">
              <strong>Copyable prompt</strong>
              <p id="remediation-prompt-text" class="prompt-block">{escape(review.remediation_prompt.prompt)}</p>
              <button type="button" class="ghost-button" data-copy-target="remediation-prompt-text" data-copy-status="prompt-copy-status">Copy fix prompt</button>
              <div id="prompt-copy-status" class="helper-text copy-status"></div>
            </div>
          </div>
        </section>
        """

    def _render_file_remediation_prompts(self, review: RepositoryReviewResult) -> str:
        if not review.file_remediation_prompts:
            return ""
        grouped_cards: dict[str, List[str]] = {"security": [], "architecture": [], "business logic": []}
        for index, prompt in enumerate(review.file_remediation_prompts, start=1):
            focus_points = "".join(f"<li>{escape(item)}</li>" for item in prompt.focus_points)
            prompt_id = f"file-remediation-prompt-{index}"
            status_id = f"file-remediation-status-{index}"
            card = f"""
            <article class="prompt-card">
              <strong>{escape(prompt.title)}</strong>
              <ul>{focus_points}</ul>
              <p id="{prompt_id}" class="prompt-block">{escape(prompt.prompt)}</p>
              <button type="button" class="ghost-button" data-copy-target="{prompt_id}" data-copy-status="{status_id}">Copy file prompt</button>
              <div id="{status_id}" class="helper-text copy-status"></div>
            </article>
            """
            grouped_cards.setdefault(prompt.group, []).append(card)

        sections: List[str] = []
        for group_name in ["security", "architecture", "business logic"]:
            cards = grouped_cards.get(group_name, [])
            if not cards:
                continue
            sections.append(
                f"""
                <div class="subpanel">
                  <div class="section-heading">
                    <div>
                      <p class="eyebrow">Prompt group</p>
                      <h3>{escape(group_name.title())}</h3>
                    </div>
                    <span class="pill neutral">Files: {len(cards)}</span>
                  </div>
                  <div class="recommendation-grid">{"".join(cards)}</div>
                </div>
                """
            )
        return f"""
        <section class="panel" id="file-remediation-prompts" data-story-section="fixes">
          <div class="section-heading">
            <div>
              <p class="eyebrow">Top risky files</p>
              <h2>Per-file VibeCoder prompts</h2>
            </div>
            <span class="pill neutral">Top {len(review.file_remediation_prompts)} files</span>
          </div>
          {"".join(sections)}
        </section>
        """


class BrowserReviewServer:
    def __init__(self, agent: SafeVibingSafetyAgent, host: str = "127.0.0.1", port: int = 8000) -> None:
        self.agent = agent
        self.host = host
        self.port = port
        self.renderer = agent.html_renderer

    def serve(self, open_browser: bool = True) -> None:
        handler = self._build_handler()
        server = ThreadingHTTPServer((self.host, self.port), cast(Any, handler))
        url = f"http://{self.host}:{self.port}"
        print(f"SafeVibing browser server listening on {url}")
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopping browser server.")
        finally:
            server.server_close()

    def _build_handler(self):
        agent = self.agent
        renderer = self.renderer

        class ReviewHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path not in {"/", "/index.html"}:
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return
                self._send_html(renderer.render(None))

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/review":
                    self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
                    return
                form = self._read_form_data()
                source_mode = form.get("source_mode", "local").strip().lower()
                source = self._select_source(form, source_mode)
                options = self._build_review_options(form)
                prompt = form.get(
                    "prompt",
                    renderer.default_prompt,
                ).strip()
                if not source:
                    option_label = "GitHub repository URL" if source_mode == "github" else "local repository path"
                    self._send_html(
                        renderer.render(
                            None,
                            source_value=form.get("github_source", "").strip() if source_mode == "github" else form.get("local_source", "").strip(),
                            prompt_value=prompt,
                            error_message=f"{option_label.capitalize()} is required.",
                            options=options,
                        ),
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                try:
                    review = agent.review_repository(source, prompt, options)
                except (RepositorySourceError, OSError, subprocess.SubprocessError, ValueError) as error:
                    self._send_html(
                        renderer.render(None, source_value=source, prompt_value=prompt, error_message=str(error), options=options),
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                self._send_html(renderer.render(review, source_value=source, prompt_value=prompt))

            def log_message(self, format: str, *args: object) -> None:
                return

            def _read_form_data(self) -> dict[str, str]:
                content_length = int(self.headers.get("Content-Length", "0"))
                payload = self.rfile.read(content_length)
                if not payload:
                    return {}
                parsed = parse_qs(payload.decode("utf-8", errors="ignore"), keep_blank_values=True)
                return {key: values[0] if values else "" for key, values in parsed.items()}

            def _select_source(self, form: dict[str, str], source_mode: str) -> str:
                if source_mode == "github":
                    return form.get("github_source", "").strip()
                if source_mode == "local":
                    return form.get("local_source", "").strip()
                return form.get("source", "").strip()

            def _build_review_options(self, form: dict[str, str]) -> ReviewOptions:
                max_files_value = form.get("max_files", "").strip()
                max_files = int(max_files_value) if max_files_value.isdigit() else None
                return ReviewOptions(
                    audience=form.get("audience", "balanced").strip().lower(),
                    review_depth=form.get("review_depth", "balanced").strip().lower(),
                    focus_mode=form.get("focus_mode", "balanced").strip().lower(),
                    max_files=max_files,
                    include_patterns=self._parse_patterns(form.get("include_patterns", "")),
                    exclude_patterns=self._parse_patterns(form.get("exclude_patterns", "")),
                    demo_goal=form.get("demo_goal", "").strip(),
                ).normalized()

            def _parse_patterns(self, raw_value: str) -> List[str]:
                return [part.strip() for part in raw_value.split(",") if part.strip()]

            def _send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
                encoded = html.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return ReviewHandler


class SafePromptMode:
    def rewrite(self, prompt: str, options: ReviewOptions | None = None) -> str:
        options = (options or ReviewOptions()).normalized()
        focus_clause = {
            "balanced": "balanced risk, design, and engineering quality",
            "security": "security hotspots, exploit paths, and trust boundaries",
            "architecture": "architecture clarity, maintainability, and module boundaries",
            "demo": "demo readiness, differentiation, and the strongest live narrative",
        }[options.focus_mode]
        audience_clause = {
            "balanced": "a mixed technical and business audience",
            "judges": "hackathon judges",
            "founders": "founders and operators",
            "engineers": "an engineering team",
        }[options.audience]
        goal_clause = f" Optimize for this demo goal: {options.demo_goal}." if options.demo_goal else ""
        return (
            "Generate secure, testable, least-privilege code for the following request: "
            f"{prompt.strip()}. Emphasize {focus_clause} for {audience_clause}.{goal_clause} "
            "Include input validation, error handling, and recommended tests."
        )


class SecurityPolicyEngine:
    secret_pattern = re.compile(r"(api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]+['\"]", re.IGNORECASE)

    def review(self, code: str) -> List[Finding]:
        findings: List[Finding] = []
        if self.secret_pattern.search(code):
            findings.append(
                Finding(
                    category="security",
                    severity="high",
                    title="Hardcoded secret detected",
                    detail="Move credentials to environment variables or a secure secret store.",
                )
            )
        if "eval(" in code or "pickle.loads" in code or "yaml.load(" in code:
            findings.append(
                Finding(
                    category="security",
                    severity="high",
                    title="Unsafe deserialization or evaluation",
                    detail="Avoid `eval` and unsafe loaders. Prefer safe parsers and explicit schemas.",
                )
            )
        if "SELECT" in code and "%" in code:
            findings.append(
                Finding(
                    category="security",
                    severity="high",
                    title="Potential SQL injection",
                    detail="Use parameterized queries instead of string interpolation in SQL statements.",
                )
            )
        if "os.system(" in code or "subprocess.run(" in code and "shell=True" in code:
            findings.append(
                Finding(
                    category="security",
                    severity="high",
                    title="Potential command injection",
                    detail="Avoid shell execution with untrusted input. Use argument lists and validation.",
                )
            )
        if "auth = True" in code or "allow_all" in code:
            findings.append(
                Finding(
                    category="security",
                    severity="medium",
                    title="Weak authentication or insecure default",
                    detail="Require explicit authentication and secure defaults before enabling access.",
                )
            )
        return findings


class DesignReviewEngine:
    def review(self, code: str) -> List[Finding]:
        findings: List[Finding] = []
        if code.count("if ") >= 4:
            findings.append(
                Finding(
                    category="design",
                    severity="medium",
                    title="Branch-heavy implementation",
                    detail="High branching suggests rising complexity; consider decomposition into smaller units.",
                )
            )
        if code.count(".") > 30:
            findings.append(
                Finding(
                    category="design",
                    severity="medium",
                    title="High coupling signal",
                    detail="Frequent object chaining may indicate tight coupling and unclear boundaries.",
                )
            )
        if "class" not in code and code.count("def ") > 4:
            findings.append(
                Finding(
                    category="design",
                    severity="low",
                    title="Low cohesion signal",
                    detail="Several free functions may benefit from clearer module boundaries or service objects.",
                )
            )
        return findings


class MetricsEngine:
    def calculate(self, code: str, findings: List[Finding]) -> MetricSnapshot:
        cyclomatic = 1 + sum(code.count(token) for token in ["if ", "for ", "while ", " and ", " or "])
        cognitive = cyclomatic + code.count("try:") + code.count("except")
        maintainability = max(0, 100 - cyclomatic * 4 - len(findings) * 6)
        duplication_risk = "high" if len(re.findall(r"\n\s{4,}[^\n]+", code)) > 12 else "medium" if len(code) > 350 else "low"
        testability = max(0, 100 - code.count("print(") * 10 - code.count("global ") * 15)
        security_risk = min(100, sum(35 if finding.severity == "high" else 20 for finding in findings if finding.category == "security"))
        secure_by_design = max(
            0,
            100
            - security_risk
            - sum(8 for finding in findings if finding.category == "design")
            - (10 if 'except:' in code else 0)
            - (8 if "auth = True" in code or "allow_all" in code else 0),
        )
        safe_defaults = max(
            0,
            100
            - (25 if any(finding.title == "Weak authentication or insecure default" for finding in findings) else 0)
            - (20 if any(finding.title == "Hardcoded secret detected" for finding in findings) else 0)
            - (15 if "debug=True" in code or "DEBUG = True" in code else 0)
            - (10 if "except:" in code else 0),
        )
        change_surface = max(1, code.count("def ") + code.count("class "))
        explainability = 100 if '"""' in code or "#" in code else 55
        return MetricSnapshot(
            cyclomatic_complexity=cyclomatic,
            cognitive_complexity=cognitive,
            maintainability_index=maintainability,
            duplication_risk=duplication_risk,
            testability_score=testability,
            security_risk_score=security_risk,
            secure_by_design_score=secure_by_design,
            safe_defaults_score=safe_defaults,
            change_surface=change_surface,
            explainability_completeness=explainability,
        )


class ExplainabilityEngine:
    def explain(
        self,
        prompt: str,
        findings: List[Finding],
        metrics: MetricSnapshot,
        file_path: str = "",
        deep_dive: FileDeepDiveReview | None = None,
    ) -> ExplainabilityReport:
        security_implications = [finding.title for finding in findings if finding.category == "security"]
        if not security_implications:
            security_implications = ["No immediate critical security pattern detected by the lightweight policy engine."]
        design_trade_offs = [finding.title for finding in findings if finding.category == "design"]
        if not design_trade_offs:
            design_trade_offs = ["Current structure appears acceptable for a prototype, but deeper architectural review may still be needed."]
        metrics_impact = [
            f"Cyclomatic complexity is {metrics.cyclomatic_complexity}.",
            f"Maintainability index is {metrics.maintainability_index}.",
            f"Security risk score is {metrics.security_risk_score}.",
            f"Secure-by-design score is {metrics.secure_by_design_score}.",
            f"Safe defaults score is {metrics.safe_defaults_score}.",
        ]
        recommended_tests = [
            "Add unit tests for valid and invalid inputs.",
            "Add security-focused tests for injection and secrets handling.",
            "Add regression tests for approval decisions at low, medium, and high risk.",
        ]
        file_label = file_path or "candidate"
        file_deep_dive = [f"File in focus: {file_label}."]
        if deep_dive is None:
            file_deep_dive.append("Deep-dive review has not been generated yet for this file.")
        else:
            primary_hotspot = deep_dive.hotspot_reasons[0] if deep_dive.hotspot_reasons else deep_dive.summary
            first_move = deep_dive.recommendations[0].title if deep_dive.recommendations else "Keep monitoring this file"
            file_deep_dive.extend(
                [
                    f"Attention level is {deep_dive.attention_level.upper()} with score {deep_dive.attention_score}.",
                    f"Clarity summary: {deep_dive.summary}",
                    f"Primary hotspot: {primary_hotspot}",
                    f"Review focus: {', '.join(deep_dive.review_focus)}.",
                    f"Recommended first move: {first_move}.",
                ]
            )
            if deep_dive.hotspot_reasons:
                file_deep_dive.append(f"Key hotspots: {'; '.join(deep_dive.hotspot_reasons)}")
            if deep_dive.positive_signals:
                file_deep_dive.append(f"Positive signal: {deep_dive.positive_signals[0]}")
        return ExplainabilityReport(
            intent_understood=f"The request is interpreted as: {prompt.strip()}",
            assumptions_made=[
                "The generated code may contain insecure defaults unless explicitly constrained.",
                "The agent should block high-risk changes before insertion.",
                "Metrics are approximate but useful for pre-insert guidance.",
            ],
            security_implications=security_implications,
            design_trade_offs=design_trade_offs,
            metrics_impact=metrics_impact,
            recommended_tests=recommended_tests,
            file_deep_dive=file_deep_dive,
        )


class FileInsightEngine:
    def describe(self, file_path: str, code: str, findings: List[Finding], metrics: MetricSnapshot) -> FileInsight:
        path_lower = file_path.lower()
        function_count = code.count("def ")
        class_count = code.count("class ")
        responsibility_summary = self._responsibility_summary(path_lower, function_count, class_count)
        business_logic_summary = self._business_logic_summary(path_lower, code)
        technical_highlights = self._technical_highlights(code, findings, metrics)
        code_smells = self._code_smells(findings, metrics, function_count)
        complexity_notes = self._complexity_notes(metrics, function_count, class_count)
        return FileInsight(
            responsibility_summary=responsibility_summary,
            business_logic_summary=business_logic_summary,
            technical_highlights=technical_highlights,
            code_smells=code_smells,
            complexity_notes=complexity_notes,
        )

    def _responsibility_summary(self, path_lower: str, function_count: int, class_count: int) -> str:
        if any(token in path_lower for token in ("auth", "login", "session", "permission")):
            return "This file appears to own authentication or access-control behavior."
        if any(token in path_lower for token in ("api", "route", "controller", "handler")):
            return "This file appears to orchestrate request handling and external interface flow."
        if any(token in path_lower for token in ("service", "domain", "use_case", "workflow")):
            return "This file appears to carry core domain workflow or service orchestration."
        if any(token in path_lower for token in ("model", "schema", "entity", "dto")):
            return "This file appears to define data contracts or domain shape."
        if any(token in path_lower for token in ("util", "helper", "string", "date")):
            return "This file appears to provide shared utility behavior."
        if class_count > 0:
            return "This file appears to package behavior behind class-based boundaries."
        if function_count > 0:
            return "This file appears to expose procedural application logic through free functions."
        return "This file appears to provide supporting code, but its dominant responsibility is not obvious from lightweight heuristics."

    def _business_logic_summary(self, path_lower: str, code: str) -> str:
        if any(token in path_lower for token in ("auth", "login", "session")):
            return "Business logic is centered on identity checks, trust boundaries, and who is allowed to act."
        if "SELECT " in code or "INSERT " in code or any(token in path_lower for token in ("repo", "dao", "db")):
            return "Business logic likely mixes persistence rules with application flow; check whether data access is isolated cleanly."
        if any(token in path_lower for token in ("payment", "billing", "invoice")):
            return "Business logic appears tied to money movement or billing state, so correctness and auditability matter."
        if any(token in path_lower for token in ("service", "workflow", "domain")):
            return "Business logic appears to live here directly, so this file is likely a change hotspot when product rules evolve."
        if any(token in path_lower for token in ("api", "route", "controller", "handler")):
            return "Business logic may be leaking into the request layer; verify that orchestration is separated from domain rules."
        if any(token in path_lower for token in ("util", "helper")):
            return "This looks more like shared support logic than primary business logic."
        return "Business logic footprint is moderate or unclear; inspect how much policy and decision-making sits in this file versus delegated collaborators."

    def _technical_highlights(self, code: str, findings: List[Finding], metrics: MetricSnapshot) -> List[str]:
        highlights = [
            f"Function count is {code.count('def ')} and class count is {code.count('class ')}.",
            f"Cyclomatic complexity is {metrics.cyclomatic_complexity} and cognitive complexity is {metrics.cognitive_complexity}.",
            f"Maintainability is {metrics.maintainability_index} with testability at {metrics.testability_score}.",
            f"Secure-by-design is {metrics.secure_by_design_score} and safe defaults score is {metrics.safe_defaults_score}.",
        ]
        if any(finding.category == "security" for finding in findings):
            highlights.append("Security-sensitive behavior is present, so review should include abuse cases and trust boundaries.")
        if code.count("try:") > 0 or code.count("except") > 0:
            highlights.append("Error handling branches exist here, which often become silent failure points if not tested.")
        return highlights

    def _code_smells(self, findings: List[Finding], metrics: MetricSnapshot, function_count: int) -> List[str]:
        smells: List[str] = []
        smell_titles = {
            "Branch-heavy implementation",
            "High coupling signal",
            "Low cohesion signal",
            "Potential SQL injection",
            "Potential command injection",
            "Unsafe deserialization or evaluation",
            "Hardcoded secret detected",
            "Weak authentication or insecure default",
        }
        for finding in findings:
            if finding.title in smell_titles:
                smells.append(finding.title)
        if metrics.duplication_risk == "high":
            smells.append("High duplication risk")
        if metrics.maintainability_index < 50:
            smells.append("Low maintainability")
        if function_count >= 6:
            smells.append("Function sprawl")
        return smells or ["No strong code smell signal was detected by the current heuristics."]

    def _complexity_notes(self, metrics: MetricSnapshot, function_count: int, class_count: int) -> List[str]:
        notes: List[str] = []
        if metrics.cyclomatic_complexity >= 10:
            notes.append("Branching is high enough that senior review should inspect control flow directly.")
        elif metrics.cyclomatic_complexity >= 6:
            notes.append("Complexity is elevated and should be decomposed before the file keeps growing.")
        else:
            notes.append("Complexity is currently manageable under lightweight heuristics.")
        if metrics.change_surface >= 6:
            notes.append(f"Change surface is {metrics.change_surface}, so fixes here may ripple across multiple entry points.")
        if class_count == 0 and function_count >= 5:
            notes.append("Behavior is spread across several free functions, which can hide ownership and sequencing issues.")
        if metrics.testability_score < 70:
            notes.append("Test seams are weak, so regression risk is higher than the file size alone suggests.")
        return notes


class DeepDiveReviewEngine:
    def build(self, file_path: str, findings: List[Finding], metrics: MetricSnapshot) -> FileDeepDiveReview:
        attention_score = min(100, self._attention_score(findings, metrics))
        attention_level = self._attention_level(attention_score, findings, metrics)
        hotspot_reasons = self._hotspot_reasons(findings, metrics)
        review_focus = self._review_focus(findings, metrics)
        recommendations = self._recommendations(findings, metrics)
        positive_signals = self._positive_signals(findings, metrics)
        summary = self._build_summary(file_path, attention_level, findings, hotspot_reasons)
        return FileDeepDiveReview(
            attention_score=attention_score,
            attention_level=attention_level,
            summary=summary,
            hotspot_reasons=hotspot_reasons,
            review_focus=review_focus,
            recommendations=recommendations,
            positive_signals=positive_signals,
        )

    def build_repository_focus(self, reviews: List[ReviewResult]) -> List[RepositoryFocusItem]:
        ranked_reviews = sorted(
            (review for review in reviews if review.deep_dive is not None),
            key=lambda review: (review.deep_dive.attention_score, review.file_path),
            reverse=True,
        )
        focus_items: List[RepositoryFocusItem] = []
        for review in ranked_reviews:
            if review.deep_dive is None:
                continue
            primary_reason = review.deep_dive.hotspot_reasons[0] if review.deep_dive.hotspot_reasons else review.deep_dive.summary
            next_step = review.deep_dive.recommendations[0].title if review.deep_dive.recommendations else "Keep monitoring this file"
            focus_items.append(
                RepositoryFocusItem(
                    file_path=review.file_path or "candidate",
                    attention_score=review.deep_dive.attention_score,
                    attention_level=review.deep_dive.attention_level,
                    reason=primary_reason,
                    next_step=next_step,
                )
            )
        return focus_items[:8]

    def _attention_score(self, findings: List[Finding], metrics: MetricSnapshot) -> int:
        score = sum(35 if finding.severity == "high" else 20 if finding.severity == "medium" else 10 for finding in findings)
        score += metrics.security_risk_score // 2
        score += max(0, metrics.cyclomatic_complexity - 5) * 3
        score += 20 if metrics.maintainability_index < 45 else 10 if metrics.maintainability_index < 70 else 0
        score += 10 if metrics.change_surface >= 8 else 0
        score += 10 if metrics.testability_score < 70 else 0
        return score

    def _attention_level(self, attention_score: int, findings: List[Finding], metrics: MetricSnapshot) -> str:
        if any(finding.category == "security" and finding.severity == "high" for finding in findings):
            return "high"
        if attention_score >= 70 or metrics.security_risk_score >= 70:
            return "high"
        if attention_score >= 30 or findings:
            return "medium"
        return "low"

    def _hotspot_reasons(self, findings: List[Finding], metrics: MetricSnapshot) -> List[str]:
        reasons = [finding.title for finding in findings if finding.severity in {"high", "medium"}]
        if metrics.cyclomatic_complexity >= 6:
            reasons.append(f"Cyclomatic complexity is elevated at {metrics.cyclomatic_complexity}.")
        if metrics.maintainability_index < 70:
            reasons.append(f"Maintainability index dropped to {metrics.maintainability_index}.")
        if metrics.testability_score < 70:
            reasons.append(f"Testability score is only {metrics.testability_score}.")
        return reasons[:5] or ["No urgent hotspots were detected by the current review heuristics."]

    def _review_focus(self, findings: List[Finding], metrics: MetricSnapshot) -> List[str]:
        focus: List[str] = []
        if any(finding.category == "security" for finding in findings) or metrics.security_risk_score >= 40:
            focus.append("security")
        if any(finding.category == "design" for finding in findings) or metrics.cyclomatic_complexity >= 6:
            focus.append("design")
        if metrics.testability_score < 80:
            focus.append("testing")
        if metrics.explainability_completeness < 75:
            focus.append("explainability")
        return focus or ["regression safety"]

    def _recommendations(self, findings: List[Finding], metrics: MetricSnapshot) -> List[DeepDiveRecommendation]:
        recommendations: List[DeepDiveRecommendation] = []
        seen_titles: set[str] = set()
        recommendation_map = {
            "Hardcoded secret detected": DeepDiveRecommendation(
                priority="high",
                title="Remove hardcoded secrets",
                rationale="Secrets in source code create direct compromise risk and leak into demos, logs, and version control.",
                actions=[
                    "Move credentials to environment variables or a managed secret store.",
                    "Rotate the exposed secret before further sharing or deployment.",
                ],
            ),
            "Unsafe deserialization or evaluation": DeepDiveRecommendation(
                priority="high",
                title="Replace unsafe execution paths",
                rationale="Dynamic evaluation and unsafe deserialization expand the attack surface for arbitrary code execution.",
                actions=[
                    "Replace unsafe loaders with explicit safe parsers and validated schemas.",
                    "Reject untrusted payloads unless they match an approved contract.",
                ],
            ),
            "Potential SQL injection": DeepDiveRecommendation(
                priority="high",
                title="Parameterize data access",
                rationale="Interpolated queries couple business input directly to database commands.",
                actions=[
                    "Use parameterized queries or a safe ORM abstraction.",
                    "Add injection-focused tests for hostile input strings.",
                ],
            ),
            "Potential command injection": DeepDiveRecommendation(
                priority="high",
                title="Replace unsafe execution paths",
                rationale="Shell-based command construction with user input can allow arbitrary command execution.",
                actions=[
                    "Use argument arrays instead of shell execution and validate inputs.",
                    "Constrain allowed commands and add tests for malicious command payloads.",
                ],
            ),
            "Weak authentication or insecure default": DeepDiveRecommendation(
                priority="medium",
                title="Enforce secure-by-default access",
                rationale="Weak auth and permissive defaults erode trust boundaries before other controls can help.",
                actions=[
                    "Require explicit authentication and authorization decisions.",
                    "Default new paths to deny access until policy is configured.",
                ],
            ),
            "Branch-heavy implementation": DeepDiveRecommendation(
                priority="medium",
                title="Break down branch-heavy logic",
                rationale="Dense branching raises review cost and makes failure paths harder to reason about.",
                actions=[
                    "Extract smaller helper functions for distinct decision branches.",
                    "Cover each branch with focused unit tests.",
                ],
            ),
            "High coupling signal": DeepDiveRecommendation(
                priority="medium",
                title="Reduce coupling across boundaries",
                rationale="Tight chaining and boundary drift make safe changes slower and riskier.",
                actions=[
                    "Introduce clearer interfaces or service boundaries.",
                    "Separate orchestration from IO-heavy operations.",
                ],
            ),
            "Low cohesion signal": DeepDiveRecommendation(
                priority="low",
                title="Tighten module cohesion",
                rationale="Grouping unrelated free functions in one module makes intent and ownership less obvious.",
                actions=[
                    "Group related responsibilities behind a clearer module boundary.",
                    "Name files and services after a single dominant responsibility.",
                ],
            ),
        }
        for finding in findings:
            recommendation = recommendation_map.get(finding.title)
            if recommendation is None or recommendation.title in seen_titles:
                continue
            recommendations.append(recommendation)
            seen_titles.add(recommendation.title)
        if metrics.maintainability_index < 60 and "Lower maintenance burden" not in seen_titles:
            recommendations.append(
                DeepDiveRecommendation(
                    priority="medium",
                    title="Lower maintenance burden",
                    rationale="Low maintainability slows iteration and increases the cost of fixing security issues.",
                    actions=[
                        "Refactor long or dense functions into smaller units.",
                        "Add regression coverage before structural changes.",
                    ],
                )
            )
            seen_titles.add("Lower maintenance burden")
        if metrics.testability_score < 80 and "Increase test seams" not in seen_titles:
            recommendations.append(
                DeepDiveRecommendation(
                    priority="medium",
                    title="Increase test seams",
                    rationale="Low testability makes it harder to prove that risky fixes stay correct.",
                    actions=[
                        "Separate pure logic from side effects for easier tests.",
                        "Add negative-path and abuse-case tests around this file.",
                    ],
                )
            )
            seen_titles.add("Increase test seams")
        if not recommendations:
            recommendations.append(
                DeepDiveRecommendation(
                    priority="low",
                    title="Keep the current quality bar",
                    rationale="This file looks relatively stable under the current lightweight heuristics.",
                    actions=[
                        "Preserve current validation and regression checks as the file evolves.",
                        "Re-run the review after behavior or dependency changes.",
                    ],
                )
            )
        return recommendations

    def _positive_signals(self, findings: List[Finding], metrics: MetricSnapshot) -> List[str]:
        signals: List[str] = []
        if not any(finding.category == "security" and finding.severity == "high" for finding in findings):
            signals.append("No immediate high-risk security patterns were detected.")
        if metrics.maintainability_index >= 80:
            signals.append(f"Maintainability remains strong at {metrics.maintainability_index}.")
        if metrics.testability_score >= 80:
            signals.append(f"Testability is healthy at {metrics.testability_score}.")
        if metrics.explainability_completeness >= 80:
            signals.append(f"Explainability signals are strong at {metrics.explainability_completeness}.")
        return signals or ["The file has at least one stable signal, but it still needs targeted remediation."]

    def _build_summary(self, file_path: str, attention_level: str, findings: List[Finding], hotspot_reasons: List[str]) -> str:
        file_label = file_path or "candidate"
        findings_count = len(findings)
        primary_reason = hotspot_reasons[0] if hotspot_reasons else "No urgent hotspots were detected."
        return (
            f"{file_label} is rated {attention_level.upper()} attention with {findings_count} finding"
            f"{'s' if findings_count != 1 else ''}. Primary reason: {primary_reason}"
        )


class ApprovalWorkflow:
    def decide(self, findings: List[Finding], metrics: MetricSnapshot) -> tuple[str, str]:
        has_high_security = any(f.category == "security" and f.severity == "high" for f in findings)
        if has_high_security or metrics.security_risk_score >= 70:
            return "block", "high"
        if findings or metrics.cyclomatic_complexity >= 6:
            return "warn", "medium"
        return "allow", "low"


class RemediationPromptEngine:
    def build(self, reviews: List[ReviewResult], metrics: MetricSnapshot | None, options: ReviewOptions) -> RemediationPrompt:
        metrics = metrics or MetricSnapshot(0, 0, 100, "low", 100, 0, 100, 100, 0, 100)
        sorted_reviews = self._sort_reviews(reviews)
        top_files = [review.file_path for review in sorted_reviews[:3] if review.file_path]
        distinct_findings: List[str] = []
        for review in sorted_reviews:
            for finding in review.findings:
                if finding.title not in distinct_findings:
                    distinct_findings.append(finding.title)
        focus_points = [
            f"Fix the highest-risk files first: {', '.join(top_files) if top_files else 'current review hotspots'}.",
            f"Reduce security risk from {metrics.security_risk_score} while raising secure-by-design from {metrics.secure_by_design_score}.",
            f"Improve safe defaults from {metrics.safe_defaults_score} and maintainability from {metrics.maintainability_index}.",
            "Preserve behavior with targeted tests before and after refactors.",
        ]
        issues_text = ", ".join(distinct_findings[:6]) if distinct_findings else "the reported code smells and safety issues"
        include_text = ", ".join(options.include_patterns) if options.include_patterns else "all in-scope code files"
        prompt = (
            "Act as a senior software engineer improving this repository.\n"
            f"Prioritize these issues: {issues_text}.\n"
            f"Work on these files first: {', '.join(top_files) if top_files else 'the highest-risk files surfaced by the report'}.\n"
            f"Scope: inspect {include_text} with a {options.focus_mode} focus for an {options.audience} audience.\n"
            "Goals:\n"
            f"- raise secure-by-design score above {max(85, metrics.secure_by_design_score)}\n"
            f"- raise safe defaults score above {max(85, metrics.safe_defaults_score)}\n"
            f"- lower security risk below {min(25, metrics.security_risk_score)}\n"
            f"- improve maintainability above {max(75, metrics.maintainability_index)}\n"
            "- reduce code smells and unnecessary complexity without changing intended business behavior\n"
            "- keep or improve testability and explainability\n"
            "Explicitly address these risks in your plan and implementation:\n"
            "- security risk with specification\n"
            "- false confidence in bad code or bad analysis\n"
            "- too much autonomy of the agent\n"
            "- weak governance\n"
            "Implementation rules:\n"
            "- remove hardcoded secrets, unsafe execution paths, insecure defaults, and risky trust-boundary violations\n"
            "- isolate business logic from transport, persistence, and shell/IO orchestration when mixed together\n"
            "- refactor branch-heavy or tightly coupled code into smaller composable units\n"
            "- add governance checkpoints so risky changes require explicit human verification\n"
            "- add or update regression, abuse-case, and negative-path tests for each fix\n"
            "- summarize the exact changes, risks removed, and remaining follow-ups"
        )
        return RemediationPrompt(
            title="VibeCoder Remediation Prompt",
            prompt=prompt,
            focus_points=focus_points,
        )

    def build_per_file_prompts(self, reviews: List[ReviewResult], options: ReviewOptions, limit: int = 10) -> List[RemediationPrompt]:
        prompts: List[RemediationPrompt] = []
        for review in self._sort_reviews(reviews)[:limit]:
            if not review.file_path:
                continue
            metrics = review.metrics or MetricSnapshot(0, 0, 100, "low", 100, 0, 100, 100, 0, 100)
            findings = [finding.title for finding in review.findings]
            recommendation_titles = [item.title for item in review.deep_dive.recommendations] if review.deep_dive is not None else []
            group = self._group_for_review(review)
            focus_points = [
                f"File: {review.file_path}",
                f"Group: {group.title()}",
                f"Risk: {review.risk_label.upper()} with decision {review.decision.upper()}",
                f"Top issues: {', '.join(findings[:4]) if findings else 'reduce complexity and preserve current quality bar'}",
                f"Target secure-by-design {metrics.secure_by_design_score} -> 85+, safe defaults {metrics.safe_defaults_score} -> 85+",
            ]
            prompt = (
                f"Act as a senior software engineer and improve only `{review.file_path}` first.\n"
                f"Current risk is {review.risk_label.upper()} and the approval decision is {review.decision.upper()}.\n"
                f"Primary findings: {', '.join(findings[:6]) if findings else 'no explicit findings, but improve structure and safety posture'}.\n"
                f"Recommended remediation themes: {', '.join(recommendation_titles[:4]) if recommendation_titles else 'simplify logic and strengthen safety checks'}.\n"
                "Required outcomes:\n"
                f"- raise secure-by-design above {max(85, metrics.secure_by_design_score)}\n"
                f"- raise safe defaults above {max(85, metrics.safe_defaults_score)}\n"
                f"- lower security risk below {min(25, metrics.security_risk_score)}\n"
                f"- improve maintainability above {max(75, metrics.maintainability_index)}\n"
                "- remove code smells, reduce complexity, and keep intended business behavior intact\n"
                "- add or update focused tests for abuse cases, regression paths, and failure handling\n"
                "Explicitly address these risks while fixing this file:\n"
                "- security risk with specification\n"
                "- false confidence in bad code or bad analysis\n"
                "- too much autonomy of the agent\n"
                "- weak governance\n"
                f"Review focus should stay on {options.focus_mode} concerns for an {options.audience} audience.\n"
                "Return the code changes, tests added, risks removed, and any follow-up work still required."
            )
            prompts.append(
                RemediationPrompt(
                    title=f"Fix {review.file_path}",
                    prompt=prompt,
                    focus_points=focus_points,
                    group=group,
                )
            )
        return prompts

    def _sort_reviews(self, reviews: List[ReviewResult]) -> List[ReviewResult]:
        def risk_priority(label: str) -> int:
            return 0 if label == "high" else 1 if label == "medium" else 2

        def attention_score(review: ReviewResult) -> int:
            return review.deep_dive.attention_score if review.deep_dive is not None else 0

        return sorted(
            reviews,
            key=lambda review: (
                risk_priority(review.risk_label),
                -attention_score(review),
                -(review.metrics.security_risk_score if review.metrics is not None else 0),
                review.file_path,
            ),
        )

    def _group_for_review(self, review: ReviewResult) -> str:
        file_path = review.file_path.lower()
        findings = {finding.title for finding in review.findings}
        focus = set(review.deep_dive.review_focus) if review.deep_dive is not None else set()
        if any(finding in findings for finding in {
            "Hardcoded secret detected",
            "Unsafe deserialization or evaluation",
            "Potential SQL injection",
            "Potential command injection",
            "Weak authentication or insecure default",
        }) or "security" in focus:
            return "security"
        if any(token in file_path for token in ("service", "domain", "workflow", "billing", "payment", "invoice")):
            return "business logic"
        if any(token in file_path for token in ("api", "route", "controller", "handler")) and review.file_insight is not None:
            if "Business logic may be leaking into the request layer" in review.file_insight.business_logic_summary:
                return "business logic"
        if any(finding in findings for finding in {"Branch-heavy implementation", "High coupling signal", "Low cohesion signal"}) or "design" in focus:
            return "architecture"
        if review.file_insight is not None and "Business logic appears to live here directly" in review.file_insight.business_logic_summary:
            return "business logic"
        return "architecture"


class SafeVibingSafetyAgent:
    def __init__(self) -> None:
        self.prompt_mode = SafePromptMode()
        self.security_engine = SecurityPolicyEngine()
        self.design_engine = DesignReviewEngine()
        self.metrics_engine = MetricsEngine()
        self.explainability_engine = ExplainabilityEngine()
        self.file_insight_engine = FileInsightEngine()
        self.deep_dive_engine = DeepDiveReviewEngine()
        self.approval_workflow = ApprovalWorkflow()
        self.remediation_prompt_engine = RemediationPromptEngine()
        self.repository_loader = RepositoryLoader()
        self.html_renderer = HtmlReportRenderer()

    def review_candidate(self, prompt: str, code: str, file_path: str = "", options: ReviewOptions | None = None) -> ReviewResult:
        normalized_options = (options or ReviewOptions()).normalized()
        rewritten_prompt = self.prompt_mode.rewrite(prompt, normalized_options)
        findings = self.security_engine.review(code)
        findings.extend(self.design_engine.review(code))
        metrics = self.metrics_engine.calculate(code, findings)
        deep_dive = self.deep_dive_engine.build(file_path, findings, metrics)
        file_insight = self.file_insight_engine.describe(file_path, code, findings, metrics)
        explainability = self.explainability_engine.explain(prompt, findings, metrics, file_path, deep_dive)
        decision, risk_label = self.approval_workflow.decide(findings, metrics)
        return ReviewResult(
            file_path=file_path,
            rewritten_prompt=rewritten_prompt,
            findings=findings,
            metrics=metrics,
            explainability=explainability,
            deep_dive=deep_dive,
            file_insight=file_insight,
            decision=decision,
            risk_label=risk_label,
        )

    def review_repository(self, source: str, prompt: str, options: ReviewOptions | None = None) -> RepositoryReviewResult:
        normalized_options = (options or ReviewOptions()).normalized()
        repo_path, is_temporary, temporary_dir = self.repository_loader.load(source)
        try:
            files = self.repository_loader.iter_code_files(repo_path, normalized_options)
            files = self._prioritize_files(files, repo_path, normalized_options)
            files = files[:normalized_options.effective_max_files()]
            if not files:
                summary = [
                    "Reviewed 0 code files.",
                    "Detected 0 total findings.",
                    "No supported source files were found for the configured extensions.",
                ]
                empty_metrics = MetricSnapshot(
                    cyclomatic_complexity=0,
                    cognitive_complexity=0,
                    maintainability_index=100,
                    duplication_risk="low",
                    testability_score=100,
                    security_risk_score=0,
                    secure_by_design_score=100,
                    safe_defaults_score=100,
                    change_surface=0,
                    explainability_completeness=100,
                )
                return RepositoryReviewResult(
                    source=source,
                    resolved_path=str(repo_path),
                    options=normalized_options,
                    reviewed_files=[],
                    deep_dive_focus=[],
                    aggregated_metrics=empty_metrics,
                    decision="warn",
                    risk_label="medium",
                    summary=summary,
                    technical_leader_view=self._build_technical_leader_view([], empty_metrics, "warn", "medium", normalized_options),
                    business_view=self._build_business_view([], empty_metrics, "warn", "medium", normalized_options),
                    founder_business_analysis=self._build_founder_business_analysis([], empty_metrics, "warn", "medium", normalized_options),
                    delivery_risk_analysis=self._build_delivery_risk_analysis([], empty_metrics, "warn", "medium"),
                    agent_brief=self._build_agent_brief([], empty_metrics, "warn", "medium", normalized_options),
                )

            reviews: List[ReviewResult] = []
            for file_path in files:
                code = file_path.read_text(encoding="utf-8", errors="ignore")
                relative_path = str(file_path.relative_to(repo_path))
                reviews.append(self.review_candidate(prompt, code, relative_path, normalized_options))
            return self._aggregate_repository_review(source, repo_path, reviews, normalized_options)
        finally:
            if is_temporary and temporary_dir is not None:
                temporary_dir.cleanup()

    def export_report(self, review: RepositoryReviewResult, output_path: str = "vibe_safety_report.html") -> Path:
        report_path = Path(output_path).expanduser().resolve()
        report_path.write_text(self.html_renderer.render(review), encoding="utf-8")
        return report_path

    def open_report_in_browser(self, report_path: Path) -> None:
        webbrowser.open(report_path.as_uri())

    def _aggregate_repository_review(
        self,
        source: str,
        repo_path: Path,
        reviews: List[ReviewResult],
        options: ReviewOptions,
    ) -> RepositoryReviewResult:
        metrics_list = [review.metrics for review in reviews if review.metrics is not None]
        aggregated_metrics = None
        if metrics_list:
            aggregated_metrics = MetricSnapshot(
                cyclomatic_complexity=sum(metric.cyclomatic_complexity for metric in metrics_list),
                cognitive_complexity=sum(metric.cognitive_complexity for metric in metrics_list),
                maintainability_index=sum(metric.maintainability_index for metric in metrics_list) // len(metrics_list),
                duplication_risk=self._highest_duplication_risk([metric.duplication_risk for metric in metrics_list]),
                testability_score=sum(metric.testability_score for metric in metrics_list) // len(metrics_list),
                security_risk_score=min(100, sum(metric.security_risk_score for metric in metrics_list)),
                secure_by_design_score=sum(metric.secure_by_design_score for metric in metrics_list) // len(metrics_list),
                safe_defaults_score=sum(metric.safe_defaults_score for metric in metrics_list) // len(metrics_list),
                change_surface=sum(metric.change_surface for metric in metrics_list),
                explainability_completeness=sum(metric.explainability_completeness for metric in metrics_list) // len(metrics_list),
            )

        overall_decision = "allow"
        risk_label = "low"
        if any(review.decision == "block" for review in reviews):
            overall_decision = "block"
            risk_label = "high"
        elif any(review.decision == "warn" for review in reviews):
            overall_decision = "warn"
            risk_label = "medium"

        category_counter = Counter(finding.category for review in reviews for finding in review.findings)
        severity_counter = Counter(finding.severity for review in reviews for finding in review.findings)
        summary = [
            f"Reviewed {len(reviews)} code files.",
            f"Detected {sum(len(review.findings) for review in reviews)} total findings.",
            f"Security findings: {category_counter.get('security', 0)}; design findings: {category_counter.get('design', 0)}.",
            f"Severity mix — high: {severity_counter.get('high', 0)}, medium: {severity_counter.get('medium', 0)}, low: {severity_counter.get('low', 0)}.",
            f"Configured for {options.audience} audience with {options.focus_mode} focus at {options.review_depth} depth.",
        ]
        deep_dive_focus = self.deep_dive_engine.build_repository_focus(reviews)

        return RepositoryReviewResult(
            source=source,
            resolved_path=str(repo_path),
            options=options,
            reviewed_files=reviews,
            deep_dive_focus=deep_dive_focus,
            aggregated_metrics=aggregated_metrics,
            decision=overall_decision,
            risk_label=risk_label,
            summary=summary,
            technical_leader_view=self._build_technical_leader_view(reviews, aggregated_metrics, overall_decision, risk_label, options),
            business_view=self._build_business_view(reviews, aggregated_metrics, overall_decision, risk_label, options),
            founder_business_analysis=self._build_founder_business_analysis(reviews, aggregated_metrics, overall_decision, risk_label, options),
            delivery_risk_analysis=self._build_delivery_risk_analysis(reviews, aggregated_metrics, overall_decision, risk_label),
            hackathon_showcase=self._build_hackathon_showcase(reviews, aggregated_metrics, overall_decision, risk_label, options),
            agent_brief=self._build_agent_brief(reviews, aggregated_metrics, overall_decision, risk_label, options),
            remediation_prompt=self.remediation_prompt_engine.build(reviews, aggregated_metrics, options),
            file_remediation_prompts=self.remediation_prompt_engine.build_per_file_prompts(reviews, options, limit=10),
        )

    def _prioritize_files(self, files: List[Path], repo_path: Path, options: ReviewOptions) -> List[Path]:
        security_tokens = ("auth", "login", "api", "token", "secret", "db", "payment", "admin")
        architecture_tokens = ("service", "core", "app", "controller", "model", "client", "router")
        demo_tokens = ("main", "app", "index", "server", "api", "demo", "home")
        focus_tokens = {
            "balanced": (),
            "security": security_tokens,
            "architecture": architecture_tokens,
            "demo": demo_tokens,
        }[options.focus_mode]

        def priority(path: Path) -> tuple[int, str]:
            relative = str(path.relative_to(repo_path)).lower()
            token_score = sum(1 for token in focus_tokens if token in relative)
            return (-token_score, relative)

        return sorted(files, key=priority)

    def _highest_duplication_risk(self, risks: List[str]) -> str:
        if "high" in risks:
            return "high"
        if "medium" in risks:
            return "medium"
        return "low"

    def _build_technical_leader_view(
        self,
        reviews: List[ReviewResult],
        metrics: MetricSnapshot | None,
        decision: str,
        risk_label: str,
        options: ReviewOptions,
    ) -> StakeholderView:
        security_findings = sum(1 for review in reviews for finding in review.findings if finding.category == "security")
        design_findings = sum(1 for review in reviews for finding in review.findings if finding.category == "design")
        metrics = metrics or MetricSnapshot(0, 0, 100, "low", 100, 0, 100, 100, 0, 100)
        status = "high" if decision == "block" else "medium" if decision == "warn" else "low"
        hotspot_files = [review.file_path for review in reviews if review.deep_dive is not None and review.deep_dive.attention_level == "high"]
        smell_count = sum(
            1
            for review in reviews
            if review.file_insight is not None
            for smell in review.file_insight.code_smells
            if "No strong code smell signal" not in smell
        )
        summary = (
            f"Approval is {decision.upper()} with {security_findings} security findings and {design_findings} design findings. "
            f"Maintainability is {metrics.maintainability_index}, security risk is {metrics.security_risk_score}, and detectable code-smell signals total {smell_count}."
        )
        priorities = [
            f"Stabilize the {security_findings} security issues before merge or demo cut-off.",
            f"Reduce complexity hotspots now that cyclomatic complexity totals {metrics.cyclomatic_complexity}.",
            f"Protect delivery flow by reviewing {metrics.change_surface} functions/classes in scope.",
        ]
        concerns = [
            f"Current repository risk is {risk_label.upper()}, so the approval workflow is not yet release-ready.",
            f"Design findings count is {design_findings}, which may indicate coupling or boundary drift in AI-generated changes.",
            f"Duplication risk is {metrics.duplication_risk.upper()} and may slow refactoring if left unchecked.",
        ]
        if hotspot_files:
            concerns.append(f"Highest-attention files currently include {', '.join(hotspot_files[:3])}.")
        opportunities = [
            "Convert repeated findings into policy rules or templates for future SafeVibing review output.",
            "Use the explainability and recommended tests to guide code review and pair-programming sessions.",
            f"Track this {options.review_depth}-depth view per review to create an engineering governance dashboard for technical leadership.",
        ]
        return StakeholderView(
            audience="Technical project leader",
            headline="Engineering governance cockpit",
            status=status,
            summary=summary,
            priorities=priorities,
            concerns=concerns,
            opportunities=opportunities,
        )

    def _build_business_view(
        self,
        reviews: List[ReviewResult],
        metrics: MetricSnapshot | None,
        decision: str,
        risk_label: str,
        options: ReviewOptions,
    ) -> StakeholderView:
        files_reviewed = len(reviews)
        total_findings = sum(len(review.findings) for review in reviews)
        metrics = metrics or MetricSnapshot(0, 0, 100, "low", 100, 0, 100, 100, 0, 100)
        status = "high" if risk_label == "high" else "medium" if risk_label == "medium" else "low"
        release_message = {
            "block": "not safe to accept as-is",
            "warn": "usable for learning or triage, but needs review before shipping",
            "allow": "in a healthy enough state for the next workflow step",
        }[decision]
        summary = (
            f"The current SafeVibing repo review says the project is {release_message}. "
            f"{files_reviewed} files were checked with {total_findings} findings, and the overall risk is {risk_label.upper()}."
        )
        priorities = [
            "Focus first on the issues that block trust: secrets, injections, or unsafe defaults.",
            "Use the risk label and approval decision as a quick go/no-go signal for demos and internal adoption.",
            f"Plan follow-up work around maintainability ({metrics.maintainability_index}) and testability ({metrics.testability_score}).",
        ]
        concerns = [
            "High-risk output can create security, compliance, and delivery credibility problems if copied directly.",
            f"A change surface of {metrics.change_surface} means fixes may touch multiple functions or classes.",
            "Business momentum drops when generated code needs repeated manual correction after insertion.",
        ]
        opportunities = [
            "Turn this browser report into a stakeholder-ready artifact for demos, hackathons, and steering updates.",
            "Use safe prompt mode to help non-technical users ask for secure, testable features upfront.",
            f"Use the metrics snapshot to compare repo health over time and show quality improvement trends for {options.audience}-facing demos.",
        ]
        return StakeholderView(
            audience="Business-side SafeVibing operator",
            headline="Project value and delivery pulse",
            status=status,
            summary=summary,
            priorities=priorities,
            concerns=concerns,
            opportunities=opportunities,
        )

    def _build_founder_business_analysis(
        self,
        reviews: List[ReviewResult],
        metrics: MetricSnapshot | None,
        decision: str,
        risk_label: str,
        options: ReviewOptions,
    ) -> FounderBusinessAnalysis:
        metrics = metrics or MetricSnapshot(0, 0, 100, "low", 100, 0, 100, 100, 0, 100)
        files_reviewed = len(reviews)
        top_focus = next((review.file_path for review in reviews if review.deep_dive is not None), "the current product surface")
        risk_posture = "trusted for pilot conversations" if risk_label == "low" else "credible for discovery but not broad rollout" if risk_label == "medium" else "not ready for scaled trust"
        headline = "AI engineering governance with a founder-readable business narrative"
        market_position = (
            "SafeVibing sits between code review tooling and buyer-facing governance: it helps teams show that AI-generated software is understandable, reviewable, and safer to ship."
        )
        product_value = (
            f"The current repo review shows a {risk_label.upper()} posture across {files_reviewed} files, which gives founders a concrete trust story: where the product is strong, where it is risky, and what must change before customer-facing use. "
            f"Right now it is {risk_posture}."
        )
        go_to_market = [
            "Sell first to teams shipping AI-assisted code who need a fast governance layer before enterprise procurement pushes back.",
            "Position the report as a bridge between engineering reality and founder/customer language, not just another static scanner.",
            f"Demo the product by starting at {top_focus} and then showing the separate founder panel before deep technical evidence.",
        ]
        business_risks = [
            f"Current product credibility is constrained by a {risk_label.upper()} repo posture and approval status of {decision.upper()}.",
            f"Maintainability at {metrics.maintainability_index} and safe defaults at {metrics.safe_defaults_score} can affect delivery trust and sales confidence.",
            "If the product stays too technical, founders may struggle to turn review output into customer-facing value and pricing language.",
        ]
        growth_opportunities = [
            "Package founder/business analysis as a recurring governance report for pilots, board updates, and enterprise security reviews.",
            "Use repo health trends and remediation prompts as a retained workflow rather than a one-off scanner.",
            f"Tune the report for {options.audience} and different company stages to expand beyond a single engineering persona.",
        ]
        founder_questions = [
            "Which buyer feels this pain first: startup CTOs, AI product teams, or compliance-sensitive software organizations?",
            "What proof point closes deals fastest: prevented risk, faster remediation, or clearer buyer trust narrative?",
            "Which parts of this report become the paid product, and which parts stay as acquisition or demo surface?",
        ]
        return FounderBusinessAnalysis(
            headline=headline,
            market_position=market_position,
            product_value=product_value,
            go_to_market=go_to_market,
            business_risks=business_risks,
            growth_opportunities=growth_opportunities,
            founder_questions=founder_questions,
        )

    def _build_delivery_risk_analysis(
        self,
        reviews: List[ReviewResult],
        metrics: MetricSnapshot | None,
        decision: str,
        risk_label: str,
    ) -> DeliveryRiskAnalysis:
        metrics = metrics or MetricSnapshot(0, 0, 100, "low", 100, 0, 100, 100, 0, 100)
        findings_total = sum(len(review.findings) for review in reviews)
        explainability = metrics.explainability_completeness
        high_risk_files = sum(1 for review in reviews if review.risk_label == "high")
        security_titles = sorted(
            {
                finding.title
                for review in reviews
                for finding in review.findings
                if finding.category == "security"
            }
        )
        design_titles = sorted(
            {
                finding.title
                for review in reviews
                for finding in review.findings
                if finding.category == "design"
            }
        )
        autonomous_scope = sum(1 for review in reviews if review.deep_dive is not None and review.deep_dive.attention_level in {"high", "medium"})
        governance_hotspots = [review.file_path for review in reviews if review.risk_label == "high"][:3]
        items = [
            DeliveryRiskItem(
                title="Security risk with specification",
                severity="high" if metrics.security_risk_score >= 40 or risk_label == "high" else "medium",
                summary=(
                    f"Security posture is only partially specified by the current implementation. Security risk is {metrics.security_risk_score}/100, "
                    f"with {high_risk_files} high-risk file(s), which means product behavior may drift beyond intended trust boundaries."
                ),
                findings=[
                    f"Security risk score is {metrics.security_risk_score}/100.",
                    f"High-risk files identified: {high_risk_files}.",
                    f"Observed security finding types: {', '.join(security_titles[:4]) if security_titles else 'none explicitly detected by the current heuristics'}.",
                ],
                mitigations=[
                    "Make security requirements explicit in prompts, code paths, and acceptance tests.",
                    "Require secure-by-design and safe-default checks before merge or demo use.",
                ],
            ),
            DeliveryRiskItem(
                title="False confidence in bad code or bad analysis",
                severity="high" if explainability < 70 or findings_total == 0 else "medium",
                summary=(
                    f"A report can create false confidence if unsafe code passes lightweight heuristics or if analysis depth is mistaken for correctness. "
                    f"Explainability is {explainability}/100 and total findings are {findings_total}."
                ),
                findings=[
                    f"Explainability completeness is {explainability}/100.",
                    f"Total surfaced findings are {findings_total}.",
                    f"Design/code-smell signals observed: {', '.join(design_titles[:4]) if design_titles else 'limited explicit design findings'}.",
                ],
                mitigations=[
                    "Force evidence-backed review output with test updates, concrete diffs, and explicit residual risks.",
                    "Treat low finding counts as a signal to verify, not as proof the code is safe.",
                ],
            ),
            DeliveryRiskItem(
                title="Too much autonomy of the agent",
                severity="high" if decision == "allow" and metrics.safe_defaults_score < 85 else "medium",
                summary=(
                    "Agentic generation and remediation can outrun review if the system acts with broad autonomy but weak checkpoints. "
                    "That creates the risk of polished but unsafe implementation changes."
                ),
                findings=[
                    f"Files eligible for medium/high-attention autonomous remediation: {autonomous_scope}.",
                    f"Current approval decision is {decision.upper()}.",
                    "Per-file remediation prompts can drive direct implementation changes if not kept under human review.",
                ],
                mitigations=[
                    "Require human approval before high-risk changes, security-sensitive edits, or broad refactors land.",
                    "Constrain remediation prompts to scoped files, explicit goals, and mandatory regression tests.",
                ],
            ),
            DeliveryRiskItem(
                title="Weak governance",
                severity="high" if metrics.safe_defaults_score < 70 or metrics.secure_by_design_score < 70 else "medium",
                summary=(
                    f"Governance is weak when approval, safe defaults, and remediation workflow are not tied together tightly enough. "
                    f"Secure-by-design is {metrics.secure_by_design_score}/100 and safe defaults are {metrics.safe_defaults_score}/100."
                ),
                findings=[
                    f"Secure-by-design score is {metrics.secure_by_design_score}/100.",
                    f"Safe defaults score is {metrics.safe_defaults_score}/100.",
                    f"Current governance hotspots: {', '.join(governance_hotspots) if governance_hotspots else 'no high-risk files currently flagged'}.",
                ],
                mitigations=[
                    "Make approval status, top risks, and remediation ownership part of the operating workflow.",
                    "Track trend lines for secure-by-design, safe defaults, and unresolved high-risk files across runs.",
                ],
            ),
        ]
        return DeliveryRiskAnalysis(
            headline="Security and Governance Risk Analysis",
            summary="These are the failure modes most likely to distort trust in AI-assisted software delivery, even when the interface looks polished.",
            items=items,
        )

    def _build_hackathon_showcase(
        self,
        reviews: List[ReviewResult],
        metrics: MetricSnapshot | None,
        decision: str,
        risk_label: str,
        options: ReviewOptions,
    ) -> HackathonShowcase:
        metrics = metrics or MetricSnapshot(0, 0, 100, "low", 100, 0, 100, 100, 0, 100)
        files_reviewed = len(reviews)
        total_findings = sum(len(review.findings) for review in reviews)
        blocked_files = sum(1 for review in reviews if review.decision == "block")
        top_focus = next((review.file_path for review in reviews if review.deep_dive is not None), "the current repo")
        judge_hook = (
            "SafeVibing turns raw AI-generated repository output into a boardroom-clean, engineer-useful safety cockpit "
            "with explainability, hotspot ranking, and demo-friendly decision support in one browser report."
        )
        if options.demo_goal:
            judge_hook = f"{judge_hook} Demo goal: {options.demo_goal}"
        innovation_score = max(
            55,
            min(
                98,
                62
                + min(files_reviewed, 8) * 3
                + min(metrics.explainability_completeness, 100) // 8
                + min(metrics.testability_score, 100) // 10
                + (10 if total_findings > 0 else 6)
                + (4 if any(review.deep_dive is not None for review in reviews) else 0),
            ),
        )
        if options.focus_mode == "demo":
            innovation_score = min(99, innovation_score + 3)
        winning_reasons = [
            "It transforms messy repo inspection into an instantly understandable command center for judges, founders, and engineers.",
            "It combines safety scoring, explainability, stakeholder storytelling, and file-level deep dives in one shareable artifact.",
            f"It already proves real value by reviewing {files_reviewed} file(s) and surfacing {total_findings} finding(s) without extra setup.",
        ]
        if risk_label == "high":
            winning_reasons.append("It creates drama in a demo by catching risky AI-generated code before it ships, which makes the problem and solution obvious fast.")
        else:
            winning_reasons.append("It shows maturity beyond a prototype by pairing clean metrics with low-friction governance guidance.")
        wow_metrics = [
            f"{files_reviewed} code files reviewed in one pass",
            f"{len([review for review in reviews if review.deep_dive is not None])} ranked deep dives for explainable triage",
            f"{metrics.explainability_completeness}/100 explainability completeness",
            f"{metrics.testability_score}/100 testability score with {decision.upper()} approval guidance",
            f"{options.effective_max_files()} file cap tuned for {options.review_depth} mode",
        ]
        demo_script = [
            "Start with the browser command center and drop in a local path or GitHub URL.",
            f"Show the interactive filters and explain that the report is tuned for {options.audience} with a {options.focus_mode} lens.",
            "Show the stakeholder cards and pitch this as an AI safety co-pilot for hackathon teams shipping fast.",
            f"Open the repository focus queue and highlight {top_focus} as the fastest path to insight.",
            "Drill into the explainability and clarity walkthrough to prove the tool is transparent, not a black box.",
        ]
        if blocked_files > 0:
            demo_script.append(f"Close with the approval decision to show the product prevented {blocked_files} high-risk file(s) from slipping through.")
        else:
            demo_script.append("Close with the approval decision and next-build moves to show how the tool supports safe acceleration, not just criticism.")
        next_build_moves = [
            "Add trend tracking across multiple review runs so teams can show measurable quality improvement over time.",
            "Layer in team collaboration features such as exportable judge summaries and remediation ownership.",
            "Turn the live report into a lightweight launch funnel with saved reports for mentors, judges, and customers.",
        ]
        return HackathonShowcase(
            project_tagline="AI repo reviews that feel like a winning demo, not a lint dump.",
            innovation_score=innovation_score,
            judge_hook=judge_hook,
            winning_reasons=winning_reasons,
            wow_metrics=wow_metrics,
            demo_script=demo_script,
            next_build_moves=next_build_moves,
        )

    def _build_agent_brief(
        self,
        reviews: List[ReviewResult],
        metrics: MetricSnapshot | None,
        decision: str,
        risk_label: str,
        options: ReviewOptions,
    ) -> AgentMissionBrief:
        metrics = metrics or MetricSnapshot(0, 0, 100, "low", 100, 0, 100, 100, 0, 100)
        findings_total = sum(len(review.findings) for review in reviews)
        top_focus = next((item.file_path for item in self.deep_dive_engine.build_repository_focus(reviews)), "the current repository")
        operating_mode = {
            "block": "Contain and coach",
            "warn": "Guide and verify",
            "allow": "Observe and accelerate",
        }[decision]
        workflow_steps = [
            "Ingest the repository path or GitHub URL and map the candidate code surface.",
            f"Inspect each supported file for security issues, design smells, and engineering metrics with a {options.focus_mode} focus.",
            "Rank hotspots, explain the reasoning, and translate the result for both technical and business audiences.",
            f"Recommend the next best action around {top_focus} before the team ships or demos the code.",
        ]
        autonomous_actions = [
            f"Flag {findings_total} finding(s) with a {risk_label.upper()} overall risk label and {decision.upper()} approval guidance.",
            f"Maintain explainability coverage at {metrics.explainability_completeness}/100 so the review stays transparent.",
            f"Prioritize testability at {metrics.testability_score}/100 while keeping security risk visible at {metrics.security_risk_score}/100.",
        ]
        if reviews:
            autonomous_actions.append(f"Push the reviewer directly toward {top_focus} as the most valuable file to inspect first.")
        else:
            autonomous_actions.append("Stay ready for the next repository intake even when no supported files are detected.")
        return AgentMissionBrief(
            agent_name="SafeVibing Safety Agent",
            agent_role="Autonomous repository reviewer for fast-moving AI and hackathon teams",
            mission=(
                "I act like an AI review agent: I scan generated code, surface risks, explain my reasoning, and hand back an action plan "
                "the team can use immediately."
            ),
            operating_mode=operating_mode,
            workflow_steps=workflow_steps,
            autonomous_actions=autonomous_actions,
            handoff_message=(
                f"Current recommendation: {decision.upper()} the repo state and start with {top_focus}."
            ),
        )


def demo_snippet_review() -> None:
    prompt = "Create a login endpoint quickly for internal users"
    generated_code = '''
import os
import pickle

API_KEY = "demo-secret"

def login(user_input):
    query = "SELECT * FROM users WHERE name = '%s'" % user_input
    os.system("echo " + user_input)
    return pickle.loads(user_input)
'''
    agent = SafeVibingSafetyAgent()
    result = agent.review_candidate(prompt, generated_code)
    print(json.dumps(result.to_dict(), indent=2))


def run_repository_review(source: str, prompt: str, output: str, open_browser: bool) -> RepositoryReviewResult:
    agent = SafeVibingSafetyAgent()
    result = agent.review_repository(source, prompt)
    report_path = agent.export_report(result, output)
    if open_browser:
        agent.open_report_in_browser(report_path)
    print(json.dumps({**result.to_dict(), "report_path": str(report_path)}, indent=2))
    return result


def serve_browser_app(host: str, port: int, open_browser: bool) -> None:
    agent = SafeVibingSafetyAgent()
    server = BrowserReviewServer(agent, host=host, port=port)
    server.serve(open_browser=open_browser)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review a local or GitHub repo and generate a browser report.")
    parser.add_argument("source", nargs="?", help="Local repository path or GitHub repository URL.")
    parser.add_argument("--github-url", help="Review a public GitHub repository URL.")
    parser.add_argument("--local-repo", help="Review a local repository path from this machine.")
    parser.add_argument(
        "--prompt",
        default=HtmlReportRenderer.default_prompt,
        help="Prompt used to frame the review.",
    )
    parser.add_argument("--output", default="vibe_safety_report.html", help="HTML report output path.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Generate the HTML report without opening the browser.",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the original single-snippet demo instead of repository review.",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start a local browser app that accepts repository URLs or local paths and renders results live.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface for browser server mode.")
    parser.add_argument("--port", type=int, default=8000, help="Port for browser server mode.")
    return parser


if __name__ == '__main__':
    parser = build_argument_parser()
    args = parser.parse_args()
    selected_sources = [value for value in [args.source, args.github_url, args.local_repo] if value]
    if args.serve:
        serve_browser_app(args.host, args.port, open_browser=not args.no_browser)
    elif args.demo:
        demo_snippet_review()
    elif len(selected_sources) > 1:
        parser.error("choose only one repository input: positional source, --github-url, or --local-repo")
    elif not selected_sources:
        parser.error("the following arguments are required unless using --demo or --serve: source")
    else:
        run_repository_review(selected_sources[0], args.prompt, args.output, open_browser=not args.no_browser)
