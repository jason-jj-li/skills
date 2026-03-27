#!/usr/bin/env python3
"""
Bootstrap an MD-first research project for vibe-research.

Example:
  python bootstrap_md_research_os.py /path/to/project_name --submit --sample-notes
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


CORE_DIRS = [
    "01_question",
    "02_literature/cards",
    "03_design",
    "04_data",
    "05_analysis",
    "06_draft",
    "07_output",
    "meetings",
    "process",
]

CORE_TEMPLATES = {
    "templates/agents.template.md": "AGENTS.md",
    "templates/state.template.md": "STATE.md",
    "templates/tasks.template.md": "TASKS.md",
    "templates/changelog.template.md": "CHANGELOG.md",
}

SUBMIT_TEMPLATES = {
    "templates/spec.template.md": "process/spec.md",
    "templates/claims.template.md": "process/claims.md",
    "templates/checklist.template.md": "process/submission_checklist.md",
}

OPTIONAL_TEMPLATES = {
    "templates/literature-card.template.md": "02_literature/cards/example_card.md",
    "templates/meeting-note.template.md": "meetings/example_meeting.md",
}


def copy_template(skill_dir: Path, project_root: Path, src_rel: str, dst_rel: str, force: bool) -> None:
    src = skill_dir / src_rel
    dst = project_root / dst_rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not force:
        return
    shutil.copyfile(src, dst)


def ensure_gitkeep(path: Path) -> None:
    if any(path.iterdir()):
        return
    (path / ".gitkeep").touch()


def git_toplevel(path: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip()).resolve()


def git_identity_configured(path: Path) -> bool:
    name = subprocess.run(
        ["git", "config", "--get", "user.name"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    email = subprocess.run(
        ["git", "config", "--get", "user.email"],
        cwd=path,
        capture_output=True,
        text=True,
    )
    return bool(name.stdout.strip() and email.stdout.strip())


def init_git_checkpoint(project_root: Path, stage_targets: list[str]) -> None:
    toplevel = git_toplevel(project_root)
    if toplevel is None:
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True, text=True)
        repo_root = project_root
        print("[ok] Initialized Git repository")
    elif toplevel != project_root:
        print(f"[warn] Skipped --git-init because {project_root} is inside existing repo {toplevel}")
        return
    else:
        repo_root = project_root

    subprocess.run(["git", "add", "--", *stage_targets], cwd=repo_root, check=True)

    staged_diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_root)
    if staged_diff.returncode == 0:
        print("[ok] Bootstrap files already staged and committed; no new bootstrap commit created")
        return

    if not git_identity_configured(repo_root):
        print("[warn] Git identity is not configured; staged bootstrap files but did not create a commit")
        return

    subprocess.run(
        ["git", "commit", "-m", "Bootstrap MD-first research OS"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    print("[ok] Created bootstrap commit")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap an MD-first research project.")
    parser.add_argument("project_root", type=Path, help="Target project directory.")
    parser.add_argument("--submit", action="store_true", help="Add Submit-mode templates under process/.")
    parser.add_argument("--sample-notes", action="store_true", help="Add example literature and meeting note templates.")
    parser.add_argument("--git-init", action="store_true", help="Initialize Git and create a bootstrap commit when safe to do so.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing template files.")
    args = parser.parse_args()

    project_root = args.project_root.resolve()
    skill_dir = Path(__file__).resolve().parents[1]

    project_root.mkdir(parents=True, exist_ok=True)
    for rel in CORE_DIRS:
        (project_root / rel).mkdir(parents=True, exist_ok=True)

    for src_rel, dst_rel in CORE_TEMPLATES.items():
        copy_template(skill_dir, project_root, src_rel, dst_rel, args.force)

    if args.submit:
        for src_rel, dst_rel in SUBMIT_TEMPLATES.items():
            copy_template(skill_dir, project_root, src_rel, dst_rel, args.force)

    if args.sample_notes:
        for src_rel, dst_rel in OPTIONAL_TEMPLATES.items():
            copy_template(skill_dir, project_root, src_rel, dst_rel, args.force)

    for rel in CORE_DIRS:
        ensure_gitkeep(project_root / rel)

    stage_targets = [
        "AGENTS.md",
        "STATE.md",
        "TASKS.md",
        "CHANGELOG.md",
        *CORE_DIRS,
    ]
    if args.submit:
        stage_targets.extend(SUBMIT_TEMPLATES.values())
    if args.sample_notes:
        stage_targets.extend(OPTIONAL_TEMPLATES.values())

    print(f"[ok] Bootstrapped MD-first research project at {project_root}")
    print("[ok] Core control layer: AGENTS.md, STATE.md, TASKS.md, CHANGELOG.md")
    print("[ok] Empty directories were marked with .gitkeep for Git checkpoints")
    if args.submit:
        print("[ok] Added Submit-mode templates under process/")
    if args.sample_notes:
        print("[ok] Added example literature and meeting note templates")
    if args.git_init:
        init_git_checkpoint(project_root, stage_targets)


if __name__ == "__main__":
    main()
