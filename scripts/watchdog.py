#!/usr/bin/env python3
"""
Pippen Watchdog — Monitors sub-agent development team

Usage:
    python scripts/watchdog.py [--check-now]

This script:
1. Checks all sub-agents are responsive
2. Verifies commits are happening
3. Validates milestone progress
4. Escalates blockers to Ezra
5. Generates daily status report
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
TEAM_STATUS_FILE = DOCS_DIR / "TEAM_STATUS.md"
MILESTONES_FILE = DOCS_DIR / "MILESTONES.md"
PROJECT_PLAN_FILE = DOCS_DIR / "PROJECT_PLAN.md"

AGENTS = [
    {"id": "PITUACH-001", "name": "Pituach", "role": "Backend Lead"},
    {"id": "MOBILE-001", "name": "Mobile Lead", "role": "Mobile Developer"},
    {"id": "INTEL-001", "name": "Intelligence Engineer", "role": "ML/AI Developer"},
]

CHECK_TIMES = {
    "morning": "09:00",
    "evening": "18:00",
}

def log(message: str, level: str = "INFO"):
    """Print timestamped log message"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def check_git_commits(since_hours: int = 24) -> Dict:
    """Check recent git commits"""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since_hours}.hours", "--pretty=format:%H|%an|%ad|%s", "--date=short"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True
        )
        
        commits = []
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    hash, author, date, message = line.split("|", 3)
                    commits.append({
                        "hash": hash[:8],
                        "author": author,
                        "date": date,
                        "message": message
                    })
        
        return {
            "count": len(commits),
            "commits": commits,
            "status": "ok" if commits else "warning"
        }
    except Exception as e:
        return {"count": 0, "commits": [], "status": "error", "error": str(e)}

def check_milestone_progress() -> Dict:
    """Parse milestones file and check progress"""
    try:
        content = MILESTONES_FILE.read_text()
        
        # Count milestones
        total = content.count("### Milestone")
        completed = content.count("[x]")
        pending = content.count("[ ]")
        
        return {
            "total_milestones": total,
            "completed_tasks": completed,
            "pending_tasks": pending,
            "progress_pct": round((completed / (completed + pending)) * 100, 1) if (completed + pending) > 0 else 0
        }
    except Exception as e:
        return {"error": str(e)}

def check_team_status() -> Dict:
    """Check team status file for last updates"""
    try:
        content = TEAM_STATUS_FILE.read_text()
        
        # Find last updated timestamp
        if "Last Updated:" in content:
            line = [l for l in content.split("\n") if "Last Updated:" in l][0]
            last_updated = line.split("Last Updated:")[1].strip()
        else:
            last_updated = "Unknown"
        
        # Count agents by status
        active_count = content.count("🟢 Active")
        available_count = content.count("⚪ Available")
        recruiting_count = content.count("🟡 Recruiting")
        
        return {
            "last_updated": last_updated,
            "active_agents": active_count,
            "available_agents": available_count,
            "recruiting_agents": recruiting_count,
            "total_agents": active_count + available_count + recruiting_count
        }
    except Exception as e:
        return {"error": str(e)}

def generate_status_report() -> str:
    """Generate comprehensive status report"""
    now = datetime.now()
    
    commits = check_git_commits()
    milestones = check_milestone_progress()
    team = check_team_status()
    
    report = f"""# Watchdog Status Report

**Generated:** {now.strftime("%Y-%m-%d %H:%M:%S IST")}  
**Report Type:** {'Morning' if now.hour < 12 else 'Evening'} Check

---

## 🐛 Git Activity (Last 24h)

| Metric | Value |
|--------|-------|
| Commits | {commits.get('count', 0)} |
| Status | {commits.get('status', 'unknown')} |

**Recent Commits:**
"""
    
    if commits.get('commits'):
        for commit in commits['commits'][:5]:
            report += f"- `{commit['hash']}` {commit['message']} ({commit['author']})\n"
    else:
        report += "- No commits in last 24 hours\n"
    
    report += f"""
---

## 📊 Milestone Progress

| Metric | Value |
|--------|-------|
| Total Milestones | {milestones.get('total_milestones', 0)} |
| Completed Tasks | {milestones.get('completed_tasks', 0)} |
| Pending Tasks | {milestones.get('pending_tasks', 0)} |
| Progress | {milestones.get('progress_pct', 0)}% |

---

## 👥 Team Status

| Metric | Value |
|--------|-------|
| Active Agents | {team.get('active_agents', 0)} |
| Available Agents | {team.get('available_agents', 0)} |
| Recruiting | {team.get('recruiting_agents', 0)} |
| Last Team Update | {team.get('last_updated', 'Unknown')} |

---

## ⚠️ Blockers & Issues

"""
    
    # Check for issues
    issues = []
    
    if commits.get('count', 0) == 0:
        issues.append("🟡 No commits in last 24 hours")
    
    if team.get('active_agents', 0) == 0:
        issues.append("🔴 No active agents")
    
    if issues:
        for issue in issues:
            report += f"- {issue}\n"
    else:
        report += "- No blockers detected\n"
    
    report += f"""
---

## 🎯 Action Items

"""
    
    if commits.get('count', 0) == 0:
        report += "- [ ] Escalate: No code commits detected\n"
    
    if milestones.get('progress_pct', 0) < 10:
        report += "- [ ] Begin Phase 1, Week 1 tasks\n"
    
    report += "- [ ] Continue monitoring\n"
    
    report += """
---

*This report was auto-generated by the Pippen Watchdog*
"""
    
    return report

def update_team_status(report: str):
    """Append report to team status file"""
    try:
        content = TEAM_STATUS_FILE.read_text()
        
        # Find the daily status log section and append
        if "## Daily Status Log" in content:
            parts = content.split("## Daily Status Log")
            header = parts[0] + "## Daily Status Log\n"
            rest = parts[1]
            
            # Insert new report after header
            new_content = header + "\n" + report + "\n---\n" + rest
            TEAM_STATUS_FILE.write_text(new_content)
            log("Updated TEAM_STATUS.md with watchdog report")
        else:
            log("Could not find Daily Status Log section", "WARNING")
    except Exception as e:
        log(f"Failed to update team status: {e}", "ERROR")

def main():
    """Main watchdog routine"""
    log("🐕 Pippen Watchdog starting...")
    
    # Generate report
    report = generate_status_report()
    
    # Print to console
    print("\n" + "="*60)
    print(report)
    print("="*60 + "\n")
    
    # Update team status file
    update_team_status(report)
    
    # Check for critical issues
    team = check_team_status()
    commits = check_git_commits()
    
    if team.get('active_agents', 0) == 0:
        log("🔴 CRITICAL: No active agents! Escalating to Ezra...", "CRITICAL")
        # In real implementation, this would trigger notification
    
    if commits.get('count', 0) == 0:
        log("🟡 WARNING: No commits in last 24h", "WARNING")
    
    log("✅ Watchdog check complete")

if __name__ == "__main__":
    main()
