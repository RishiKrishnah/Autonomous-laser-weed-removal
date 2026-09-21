from pathlib import Path
from collections import Counter
import subprocess
import argparse


# Files/directories that should NOT be included in the GPT prompt
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "runs",
    "models",
}

EXCLUDED_EXTENSIONS = {
    ".pt",
    ".pth",
    ".onnx",
    ".engine",
    ".bin",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".avi",
    ".mov",
}

IMPORTANT_EXTENSIONS = {
    ".py",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".xml",
    ".ino",
    ".sh",
    ".ps1",
}


def safe_read(path: Path, max_chars=200_000):
    """Read a text file safely."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")

        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[FILE TRUNCATED]\n"

        return text
    except Exception as e:
        return f"[Could not read file: {e}]"


def get_git_info(root: Path):
    """Get basic Git information."""
    try:
        branch = subprocess.check_output(
            ["git", "-C", str(root), "branch", "--show-current"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        return f"Branch: {branch}\nCommit: {commit}"

    except Exception:
        return "Git information unavailable."


def extract_dataset_info(project_root: Path):
    """Extract information from prepared YOLO dataset."""

    data_root = project_root / "data" / "yolo"

    lines = []

    if not data_root.exists():
        return "[Prepared YOLO dataset not found]"

    lines.append("## PREPARED YOLO DATASET")
    lines.append("")

    # dataset.yaml
    yaml_path = data_root / "dataset.yaml"

    if yaml_path.exists():
        lines.append("### dataset.yaml")
        lines.append("```yaml")
        lines.append(safe_read(yaml_path))
        lines.append("```")
        lines.append("")

    # Count images
    for split in ["train", "val", "test"]:
        image_dir = data_root / "images" / split
        label_dir = data_root / "labels" / split

        image_count = len(list(image_dir.glob("*"))) if image_dir.exists() else 0

        label_count = len(list(label_dir.glob("*.txt"))) if label_dir.exists() else 0

        lines.append(f"{split}: {image_count} images, {label_count} label files")

    lines.append("")

    # Class distribution
    class_counts = Counter()

    for split in ["train", "val", "test"]:
        label_dir = data_root / "labels" / split

        if not label_dir.exists():
            continue

        for label_file in label_dir.glob("*.txt"):
            try:
                for line in label_file.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).splitlines():
                    parts = line.strip().split()

                    if len(parts) == 5:
                        class_counts[int(parts[0])] += 1

            except Exception:
                continue

    lines.append("### Annotation class distribution")
    lines.append("")

    for class_id in sorted(class_counts):
        lines.append(f"Class {class_id}: {class_counts[class_id]} annotations")

    lines.append("")

    # Sample annotations
    lines.append("### Sample YOLO annotations")
    lines.append("")

    sample_labels = list((data_root / "labels" / "train").glob("*.txt"))[:10]

    for label_file in sample_labels:
        lines.append(f"#### {label_file.name}")
        lines.append("```text")
        lines.append(safe_read(label_file, max_chars=10_000))
        lines.append("```")
        lines.append("")

    return "\n".join(lines)


def extract_project_files(project_root: Path):
    """Extract relevant project files."""

    sections = []

    # Prioritize important project files
    priority_files = [
        "README.md",
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "LICENSE",
    ]

    for filename in priority_files:
        path = project_root / filename

        if path.exists():
            sections.append(f"\n## FILE: {path.relative_to(project_root)}\n")
            sections.append("```text")
            sections.append(safe_read(path))
            sections.append("```")

    # Walk project
    for path in sorted(project_root.rglob("*")):
        if not path.is_file():
            continue

        relative = path.relative_to(project_root)

        # Skip excluded directories
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue

        # Skip excluded extensions
        if path.suffix.lower() in EXCLUDED_EXTENSIONS:
            continue

        # Only include useful text files
        if path.suffix.lower() not in IMPORTANT_EXTENSIONS:
            continue

        # Avoid duplicating priority files
        if str(relative) in priority_files:
            continue

        # Skip generated dataset images
        if "data" in relative.parts and "images" in relative.parts:
            continue

        # Skip massive generated files
        try:
            if path.stat().st_size > 500_000:
                continue
        except Exception:
            continue

        sections.append(f"\n## FILE: {relative}\n")

        language = path.suffix.lower().replace(".", "")

        if language == "py":
            language = "python"
        elif language in {"yaml", "yml"}:
            language = "yaml"
        elif language == "md":
            language = "markdown"
        elif language == "ino":
            language = "cpp"

        sections.append(f"```{language}")
        sections.append(safe_read(path))
        sections.append("```")

    return "\n".join(sections)


def build_prompt(project_root: Path):

    prompt = []

    prompt.append("# GPT PROJECT CONTEXT\n")

    prompt.append(
        "You are assisting with the following software/robotics project. "
        "Use the provided project files and dataset information as the "
        "primary source of truth.\n"
    )

    prompt.append(
        "Do not invent files, functionality, configurations, dataset "
        "properties, or implementation details that are not supported "
        "by the extracted project context.\n"
    )

    prompt.append(
        "When proposing code changes, preserve the existing architecture "
        "unless there is a clear reason to modify it.\n"
    )

    prompt.append("## PROJECT ROOT\n")

    prompt.append(str(project_root.resolve()))

    prompt.append("\n\n## GIT INFORMATION\n")
    prompt.append(get_git_info(project_root))

    prompt.append("\n\n")
    prompt.append(extract_dataset_info(project_root))

    prompt.append("\n\n")
    prompt.append("## PROJECT FILES\n")
    prompt.append(extract_project_files(project_root))

    return "\n".join(prompt)


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Extract project source, configuration, documentation, "
            "and dataset metadata into a GPT-ready prompt."
        )
    )

    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory",
    )

    parser.add_argument(
        "--output",
        default="GPT_PROJECT_PROMPT.txt",
        help="Output prompt file",
    )

    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = Path(args.output).resolve()

    print(f"Project root: {root}")
    print("Extracting project information...")

    prompt = build_prompt(root)

    output.write_text(
        prompt,
        encoding="utf-8",
    )

    print()
    print("Extraction complete.")
    print(f"Output: {output}")
    print(f"Characters: {len(prompt):,}")
    print(f"Approx. tokens: {len(prompt) // 4:,}")


if __name__ == "__main__":
    main()
