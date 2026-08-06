from __future__ import annotations

import json
import os
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER = os.getenv("GITHUB_REPOSITORY_OWNER", "AHANA000000045")
TOKEN = os.getenv("GITHUB_TOKEN", "")
API = "https://api.github.com"
ROOT = Path(__file__).resolve().parents[1]


def get(path: str):
    request = urllib.request.Request(f"{API}{path}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("User-Agent", "profile-observatory")
    if TOKEN:
        request.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def esc(value: object) -> str:
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(data: dict, dark: bool) -> str:
    bg, panel, border, text, muted, accent = (("#0d1117", "#111820", "#30363d", "#e6edf3", "#7d8590", "#58a6ff") if dark else ("#ffffff", "#f6f8fa", "#d0d7de", "#1f2328", "#57606a", "#0969da"))
    cards = [("REPOSITORIES", data["repositories"]), ("30D COMMITS", data["recent_commits"]), ("OPEN ISSUES", data["open_issues"]), ("OPEN PRS", data["open_prs"]), ("STARS / FORKS", f'{data["stars"]} / {data["forks"]}')]
    blocks = []
    for index, (label, value) in enumerate(cards):
        x = 40 + index * 230
        blocks.append(f'<g transform="translate({x} 75)"><rect class="p" width="210" height="100" rx="8"/><text class="l" x="20" y="30">{label}</text><text class="v" x="20" y="72">{value}</text></g>')
    points = data["activity"]
    max_value = max(points or [1])
    coords = " ".join(f"{70 + i * 35},{340 - (value / max_value) * 90:.1f}" for i, value in enumerate(points))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 420"><style>svg{{background:{bg}}}text{{font-family:monospace;fill:{text}}}.p{{fill:{panel};stroke:{border}}}.l{{fill:{muted};font-size:12px}}.v{{font-size:28px}}.a{{stroke:{accent};fill:none;stroke-width:2}}</style><text x="40" y="42">REPOSITORY OBSERVATORY</text><text class="l" x="1160" y="42" text-anchor="end">UPDATED {esc(data["generated_at"])}</text>{''.join(blocks)}<rect class="p" x="40" y="200" width="1120" height="170" rx="8"/><text class="l" x="65" y="232">30-DAY ACTIVITY</text><polyline class="a" points="{coords}"/><text class="l" x="65" y="360">LATEST UPDATE: {esc(data["latest_update"])}</text><text class="l" x="40" y="402">SOURCE: GITHUB REST API · REPOSITORY FRESHNESS: {esc(data["freshness_days"])} DAYS</text></svg>'''


def main() -> None:
    repos = [repo for repo in get(f"/users/{USER}/repos?per_page=100&sort=updated") if not repo["fork"]]
    since = datetime.now(timezone.utc) - timedelta(days=30)
    activity = Counter()
    commits = issues = prs = 0
    for repo in repos:
        name = repo["name"]
        try:
            repo_commits = get(f"/repos/{USER}/{name}/commits?since={since.isoformat()}&per_page=100")
            commits += len(repo_commits)
            for commit in repo_commits:
                day = commit["commit"]["author"]["date"][:10]
                activity[day] += 1
        except Exception:
            pass
        try:
            open_items = get(f"/repos/{USER}/{name}/issues?state=open&per_page=100")
            prs += sum(1 for item in open_items if "pull_request" in item)
            issues += sum(1 for item in open_items if "pull_request" not in item)
        except Exception:
            pass
    days = [(since + timedelta(days=index)).date().isoformat() for index in range(30)]
    latest = max((repo["pushed_at"] for repo in repos), default="n/a")
    latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00")) if latest != "n/a" else datetime.now(timezone.utc)
    data = {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "repositories": len(repos), "recent_commits": commits, "open_issues": issues, "open_prs": prs, "stars": sum(repo["stargazers_count"] for repo in repos), "forks": sum(repo["forks_count"] for repo in repos), "latest_update": latest, "freshness_days": (datetime.now(timezone.utc) - latest_dt).days, "activity": [activity[day] for day in days]}
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "dashboard").mkdir(exist_ok=True)
    (ROOT / "data" / "dashboard.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (ROOT / "dashboard" / "observatory-dark.svg").write_text(render(data, True), encoding="utf-8")
    (ROOT / "dashboard" / "observatory-light.svg").write_text(render(data, False), encoding="utf-8")


if __name__ == "__main__":
    main()
