from pathlib import Path
import sys


sys.path.append(str(Path(__file__).resolve().parent.parent / "scripts" / "changelog"))

import build_changelog


def test_rebuild_changelog_writes_summary_backed_alt_output(monkeypatch, tmp_path):
    current_path = tmp_path / "CHANGELOG.json"
    archive_path = tmp_path / "CHANGELOG.archive.json"
    output_path = tmp_path / "CHANGELOG.release-please.md"

    current_path.write_text("[]", encoding="utf-8")
    archive_path.write_text(
        """
[
  {
    "id": "CHG-abc12345",
    "change_group": "release-tooling",
    "plugin_version": "1.2.1",
    "date": "2026-03-10",
    "summary_tags": ["Bug Fix"],
    "summary": "Fix release body generation",
    "details": ["Use cached changelog summaries for release output"]
  }
]
""".strip(),
        encoding="utf-8",
    )

    summary_text = "### Overview\n\nSummary from cached changelog summaries."
    archived_entries = build_changelog.load_entries(archive_path)
    summary_key = f"1.2.1:{build_changelog._entries_hash(archived_entries)}"

    monkeypatch.setattr(build_changelog, "CHANGELOG_JSON", current_path)
    monkeypatch.setattr(build_changelog, "CHANGELOG_ARCHIVE_JSON", archive_path)
    monkeypatch.setattr(build_changelog, "load_summaries", lambda: {summary_key: summary_text})

    rc = build_changelog.rebuild_changelog_markdown(output_path=output_path, quiet=True)

    assert rc == 0
    rendered = output_path.read_text(encoding="utf-8")
    assert "## v1.2.1" in rendered
    assert summary_text in rendered
