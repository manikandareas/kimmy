import hashlib
from datetime import date
from pathlib import Path

from kimmy.knowledge.schemas import Document, Section

SOURCES = ("maintenance-policy.md", "breakdown-procedure.md", "fuel-investigation.md")


def read_documents(directory: Path) -> list[Document]:
    return [read_document(directory / filename) for filename in SOURCES]


def read_document(path: Path) -> Document:
    filename = path.name
    raw = path.read_text(encoding="utf-8")
    if len(raw) > 60000:
        raise ValueError("SOP exceeds the 60000 character ingestion limit")
    lines = raw.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError(f"{filename}: metadata header is required")
    end = lines.index("---", 1)
    metadata = dict(line.split(": ", 1) for line in lines[1:end])
    if set(metadata) != {"title", "version", "effective_date"} or not all(
        metadata.values()
    ):
        raise ValueError(f"{filename}: title, version and effective_date are required")
    sections: list[Section] = []
    heading = ""
    body: list[str] = []

    def flush() -> None:
        content = "\n".join(body).strip()
        if heading and content:
            if len(content) > 6000:
                raise ValueError(
                    f"{filename}: split long sections below 6000 characters"
                )
            sections.append(Section(title=heading, content=content))

    for line in lines[end + 1 :]:
        if line.startswith("## "):
            flush()
            heading, body = line[3:].strip(), []
        elif heading:
            body.append(line)
        elif line.strip() and not line.startswith("# "):
            raise ValueError(f"{filename}: content must be under a section heading")
    flush()
    if not sections or len(sections) > 30:
        raise ValueError(f"{filename}: expected 1 to 30 sections")
    return Document(
        slug=filename,
        title=metadata["title"],
        version=metadata["version"],
        effective_date=date.fromisoformat(metadata["effective_date"]),
        content_hash=hashlib.sha256(raw.encode()).hexdigest(),
        sections=sections,
    )
