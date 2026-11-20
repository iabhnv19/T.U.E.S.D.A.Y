"""modules/file_tools.py
Phase 5: Local file search, document reading (PDF/DOCX), indexing, RAG, and file manipulation.
"""

import os
import shutil
import subprocess
import time
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.config import Config
from core.tools import tool, record_undo_action, pop_last_undo_action

# Optional PDF & DOCX libraries
try:
    import PyPDF2
    HAS_PYPDF = True
except ImportError:
    try:
        import pypdf as PyPDF2
        HAS_PYPDF = True
    except ImportError:
        HAS_PYPDF = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# ChromaDB knowledge store
try:
    import chromadb
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False


def _get_search_roots(root_dir: Optional[str] = None) -> List[Path]:
    """Determine root directories to search."""
    if root_dir and os.path.exists(root_dir):
        return [Path(root_dir)]

    env_dirs = os.getenv("SEARCH_DIRS", "")
    if env_dirs:
        dirs = [Path(d.strip()) for d in env_dirs.split(",") if os.path.exists(d.strip())]
        if dirs:
            return dirs

    user_home = Path.home()
    candidates = [
        user_home / "Desktop",
        user_home / "Documents",
        user_home / "Downloads",
        Config.PROJECT_ROOT,
    ]
    return [d for d in candidates if d.exists()]


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# ── File Search & Discovery ────────────────────────────────────────────────

@tool(
    name="search_files",
    description="Search for files across user folders (Desktop, Documents, Downloads, or custom path) by name pattern, extension, or modification date.",
    params_schema={
        "query": {
            "type": "string",
            "description": "Filename keyword or wildcard pattern (e.g. 'invoice', 'report', '*.py').",
        },
        "extension": {
            "type": "string",
            "description": "Optional file extension filter without dot (e.g. 'pdf', 'docx', 'txt').",
        },
        "modified_since_days": {
            "type": "integer",
            "description": "Optional filter for files modified within the last N days.",
        },
        "root_dir": {
            "type": "string",
            "description": "Optional specific directory to search within.",
        },
    },
    risk="low",
)
def search_files(
    query: str,
    extension: Optional[str] = None,
    modified_since_days: Optional[int] = None,
    root_dir: Optional[str] = None,
) -> str:
    """Find files on disk using fast scan."""
    query_lower = query.lower().strip()
    ext_filter = f".{extension.lower().lstrip('.')}" if extension else None
    cutoff_time = 0.0
    if modified_since_days:
        cutoff_time = (datetime.now() - timedelta(days=modified_since_days)).timestamp()

    # Try Everything CLI (es.exe) if available on PATH
    try:
        cmd = ["es", "-n", "30", query]
        if ext_filter:
            cmd.extend(["-ext", extension.lstrip('.')])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().splitlines()
            return f"Found {len(lines)} files via Everything:\n" + "\n".join(lines[:20])
    except Exception:
        pass

    # Fallback to local scandir over root directories
    search_dirs = _get_search_roots(root_dir)
    matches: List[str] = []

    for s_dir in search_dirs:
        try:
            for root, dirs, files in os.walk(s_dir):
                # Ignore noisy folders
                dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "__pycache__", "AppData")]
                for f in files:
                    if ext_filter and not f.lower().endswith(ext_filter):
                        continue
                    if query_lower and query_lower not in f.lower():
                        continue

                    full_path = Path(root) / f
                    try:
                        stat = full_path.stat()
                        if cutoff_time and stat.st_mtime < cutoff_time:
                            continue
                        size_str = _format_size(stat.st_size)
                        matches.append(f"{full_path} ({size_str})")
                    except Exception:
                        matches.append(str(full_path))

                    if len(matches) >= 30:
                        break
                if len(matches) >= 30:
                    break
        except Exception:
            continue

    if not matches:
        return f"'{query}' se match karne wali koi file nahi mili."

    return f"Found {len(matches)} matching file(s):\n" + "\n".join(matches[:20])


# ── File Content Reading (Text, PDF, DOCX) ────────────────────────────────

@tool(
    name="read_file_content",
    description="Read text or code content from a local file.",
    params_schema={
        "file_path": {
            "type": "string",
            "description": "Absolute or relative path to the file.",
        },
        "max_chars": {
            "type": "integer",
            "description": "Maximum number of characters to read (default 4000).",
        },
    },
    risk="low",
)
def read_file_content(file_path: str, max_chars: int = 4000) -> str:
    """Read textual content of a file."""
    p = Path(file_path)
    if not p.exists():
        return f"File nahi mili: {file_path}"
    if not p.is_file():
        return f"Path is not a regular file: {file_path}"

    ext = p.suffix.lower()
    if ext == ".pdf":
        return read_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return read_docx(file_path)

    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars)
        truncated = len(content) >= max_chars
        res = f"Contents of {p.name}:\n\n{content}"
        if truncated:
            res += "\n\n... [File truncated for brevity]"
        return res
    except Exception as e:
        return f"File read karne mein error aaya: {e}"


@tool(
    name="read_pdf",
    description="Extract text from a PDF file.",
    params_schema={
        "file_path": {
            "type": "string",
            "description": "Path to the PDF file.",
        },
        "max_pages": {
            "type": "integer",
            "description": "Maximum pages to extract (default 10).",
        },
    },
    risk="low",
)
def read_pdf(file_path: str, max_pages: int = 10) -> str:
    """Extract text from PDF."""
    if not HAS_PYPDF:
        return "PDF reader (PyPDF2) library install nahi hai Sir."

    p = Path(file_path)
    if not p.exists():
        return f"PDF file nahi mili: {file_path}"

    try:
        reader = PyPDF2.PdfReader(str(p))
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, max_pages)

        extracted: List[str] = []
        for i in range(pages_to_read):
            text = reader.pages[i].extract_text() or ""
            if text.strip():
                extracted.append(f"--- Page {i+1} ---\n{text.strip()}")

        if not extracted:
            return f"PDF '{p.name}' mein koi readable text nahi mila (ho sakta hai scanned image PDF ho)."

        full_doc = "\n\n".join(extracted)
        if len(full_doc) > 4000:
            full_doc = full_doc[:4000] + "\n... [Truncated]"

        return f"Extracted text from {p.name} ({pages_to_read}/{total_pages} pages):\n\n{full_doc}"
    except Exception as e:
        return f"PDF read karte waqt error: {e}"


@tool(
    name="read_docx",
    description="Extract text from a Word document (.docx).",
    params_schema={
        "file_path": {
            "type": "string",
            "description": "Path to the .docx file.",
        }
    },
    risk="low",
)
def read_docx(file_path: str) -> str:
    """Extract text from Word document."""
    if not HAS_DOCX:
        return "DOCX reader (python-docx) library install nahi hai Sir."

    p = Path(file_path)
    if not p.exists():
        return f"Word document nahi mila: {file_path}"

    try:
        doc = docx.Document(str(p))
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n".join(paras)

        if not full_text.strip():
            return f"Document '{p.name}' empty hai."

        if len(full_text) > 4000:
            full_text = full_text[:4000] + "\n... [Truncated]"

        return f"Document text from {p.name}:\n\n{full_text}"
    except Exception as e:
        return f"Word document read karte waqt error: {e}"


# ── File Operations & Undo ────────────────────────────────────────────────

@tool(
    name="create_file",
    description="Create or overwrite a file with specified content.",
    params_schema={
        "file_path": {
            "type": "string",
            "description": "Path where the file should be created.",
        },
        "content": {
            "type": "string",
            "description": "Content to write into the file.",
        },
    },
    risk="medium",
)
def create_file(file_path: str, content: str) -> str:
    """Create a new file with text content."""
    try:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File create kar di: {p.resolve()}"
    except Exception as e:
        return f"File create karne mein error aaya: {e}"


@tool(
    name="move_file",
    description="Move a file or folder from source path to destination path. Supports undo.",
    params_schema={
        "source_path": {
            "type": "string",
            "description": "Path of the file to move.",
        },
        "destination_path": {
            "type": "string",
            "description": "Target folder or path to move into.",
        },
    },
    risk="medium",
)
def move_file(source_path: str, destination_path: str) -> str:
    """Move file with undo tracking."""
    src = Path(source_path)
    dest = Path(destination_path)
    if not src.exists():
        return f"Source file nahi mili: {source_path}"

    try:
        actual_dest = shutil.move(str(src), str(dest))
        record_undo_action("file_move", {
            "src": str(src.resolve()),
            "dest": str(Path(actual_dest).resolve()),
        })
        return f"Moved '{src.name}' to '{actual_dest}'. (Say 'undo file move' to reverse)."
    except Exception as e:
        return f"File move nahi ho payi: {e}"


@tool(
    name="rename_file",
    description="Rename a file or folder. Supports undo.",
    params_schema={
        "file_path": {
            "type": "string",
            "description": "Path of the file to rename.",
        },
        "new_name": {
            "type": "string",
            "description": "New name for the file (just filename, not full path).",
        },
    },
    risk="medium",
)
def rename_file(file_path: str, new_name: str) -> str:
    """Rename a file with undo support."""
    src = Path(file_path)
    if not src.exists():
        return f"File nahi mili: {file_path}"

    target = src.parent / new_name
    if target.exists():
        return f"Target name '{new_name}' already exists in that folder."

    try:
        src.rename(target)
        record_undo_action("file_rename", {
            "src": str(src.resolve()),
            "dest": str(target.resolve()),
        })
        return f"Renamed '{src.name}' to '{new_name}'. (Say 'undo rename' to reverse)."
    except Exception as e:
        return f"File rename nahi ho payi: {e}"


@tool(
    name="undo_file_action",
    description="Undo the last file move or file rename action.",
    params_schema={},
    risk="low",
)
def undo_file_action() -> str:
    """Revert last recorded file move or rename."""
    entry = pop_last_undo_action()
    if not entry:
        return "Koi recent file action undo karne ke liye nahi mila."

    tool_type = entry.get("tool")
    data = entry.get("data", {})

    if tool_type in ("file_move", "file_rename"):
        src = Path(data.get("src", ""))
        dest = Path(data.get("dest", ""))
        if not dest.exists():
            return f"Moved file '{dest.name}' target location par nahi mili."

        try:
            shutil.move(str(dest), str(src))
            return f"Undone! Restored '{dest.name}' back to '{src}'."
        except Exception as e:
            return f"Undo karte waqt error: {e}"

    elif tool_type == "organize_desktop":
        moves = data.get("moves", [])
        restored = 0
        for m in moves:
            s = Path(m["src"])
            d = Path(m["dest"])
            if d.exists():
                try:
                    shutil.move(str(d), str(s))
                    restored += 1
                except Exception:
                    pass
        return f"Desktop organization undone! {restored} files restored."

    return f"Last action '{tool_type}' cannot be undone by this tool."


@tool(
    name="zip_folder",
    description="Compress a directory into a .zip archive.",
    params_schema={
        "folder_path": {
            "type": "string",
            "description": "Path to the folder to compress.",
        },
        "zip_path": {
            "type": "string",
            "description": "Optional destination path for the .zip file. Defaults to folder_name.zip next to it.",
        },
    },
    risk="low",
)
def zip_folder(folder_path: str, zip_path: Optional[str] = None) -> str:
    """Compress directory into zip archive."""
    src = Path(folder_path)
    if not src.exists() or not src.is_dir():
        return f"Folder nahi mila: {folder_path}"

    target_zip = Path(zip_path) if zip_path else src.parent / f"{src.name}.zip"

    try:
        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(src):
                for file in files:
                    full = Path(root) / file
                    rel = full.relative_to(src)
                    zf.write(full, arcname=str(rel))

        size_str = _format_size(target_zip.stat().st_size)
        return f"Folder compressed successfully: '{target_zip.name}' ({size_str})."
    except Exception as e:
        return f"Zip create karne mein error aaya: {e}"


@tool(
    name="open_file",
    description="Open any file or document with its default Windows application.",
    params_schema={
        "file_path": {
            "type": "string",
            "description": "Path to the file to open.",
        }
    },
    risk="low",
)
def open_file(file_path: str) -> str:
    """Open file using Windows default handler."""
    p = Path(file_path)
    if not p.exists():
        return f"File nahi mili: {file_path}"

    try:
        os.startfile(str(p.resolve()))
        return f"Opening '{p.name}' in default app."
    except Exception as e:
        return f"File open nahi ho saki: {e}"


# ── Document Summarization & RAG Knowledge Store ──────────────────────────

@tool(
    name="summarize_file",
    description="Read and generate a smart Hinglish summary of a text, PDF, DOCX, or code file.",
    params_schema={
        "file_path": {
            "type": "string",
            "description": "Path to the document to summarize.",
        }
    },
    risk="low",
)
def summarize_file(file_path: str) -> str:
    """Read document and summarize using Groq."""
    content = read_file_content(file_path, max_chars=6000)
    if content.startswith("File nahi mili") or content.startswith("Error"):
        return content

    is_local = Config.LLM_PROVIDER in ("ollama", "lmstudio")
    if not Config.LLM_API_KEY and not is_local:
        return "AI API key missing hai, document summarize nahi kar sakti."

    try:
        from core.llm import UniversalLLMClient
        client = UniversalLLMClient(
            provider=Config.LLM_PROVIDER,
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            default_model=Config.LLM_MODEL,
        )
        resp = client.chat.completions.create(
            model=client.default_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are T.U.E.S.D.A.Y, a sharp, witty Hinglish assistant. Summarize the following document in 3-5 concise bullet points with key highlights.",
                },
                {"role": "user", "content": content},
            ],
            max_tokens=300,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Summary generate karne mein error aaya: {e}"


def _get_doc_collection():
    """Helper to get ChromaDB collection for documents."""
    if not HAS_CHROMADB:
        return None
    try:
        persist_path = str(Config.PROJECT_ROOT / "memory" / "chroma_db")
        client = chromadb.PersistentClient(path=persist_path)
        return client.get_or_create_collection(
            name="document_knowledge",
            metadata={"hnsw:space": "cosine"}
        )
    except Exception:
        return None


@tool(
    name="index_folder",
    description="Index all documents (txt, md, py, pdf, docx) in a folder into Tuesday's semantic knowledge base.",
    params_schema={
        "folder_path": {
            "type": "string",
            "description": "Directory containing documents to index.",
        }
    },
    risk="low",
)
def index_folder(folder_path: str) -> str:
    """Chunk and embed local documents for RAG search."""
    col = _get_doc_collection()
    if not col:
        return "ChromaDB memory store ready nahi hai Sir."

    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return f"Folder nahi mila: {folder_path}"

    valid_exts = {".txt", ".md", ".py", ".pdf", ".docx", ".json"}
    total_chunks = 0
    total_files = 0

    for root, _, files in os.walk(folder):
        for fname in files:
            p = Path(root) / fname
            if p.suffix.lower() not in valid_exts:
                continue

            try:
                text = ""
                if p.suffix.lower() == ".pdf":
                    text = read_pdf(str(p), max_pages=5)
                elif p.suffix.lower() == ".docx":
                    text = read_docx(str(p))
                else:
                    with open(p, "r", encoding="utf-8", errors="replace") as f:
                        text = f.read(8000)

                if not text or len(text.strip()) < 30:
                    continue

                # Simple chunking by paragraphs (approx 500 chars)
                paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
                chunks = []
                curr = ""
                for pa in paras:
                    if len(curr) + len(pa) < 600:
                        curr += "\n" + pa
                    else:
                        if curr:
                            chunks.append(curr.strip())
                        curr = pa
                if curr:
                    chunks.append(curr.strip())

                if not chunks:
                    chunks = [text[:600]]

                # Add to chroma
                doc_ids = [f"{p.stem}_{idx}_{int(time.time())}" for idx in range(len(chunks))]
                metas = [{"source": str(p), "file": p.name, "chunk": i} for i in range(len(chunks))]

                col.add(
                    documents=chunks,
                    ids=doc_ids,
                    metadatas=metas,
                )
                total_chunks += len(chunks)
                total_files += 1
            except Exception:
                continue

    return f"Folder indexed! Processed {total_files} file(s) into {total_chunks} semantic chunks in 'document_knowledge' collection."


@tool(
    name="ask_documents",
    description="Ask a question and search Tuesday's indexed document knowledge base.",
    params_schema={
        "query": {
            "type": "string",
            "description": "Question to search across indexed documents.",
        }
    },
    risk="low",
)
def ask_documents(query: str) -> str:
    """Retrieve semantic excerpts from indexed documents."""
    col = _get_doc_collection()
    if not col:
        return "Document knowledge base unavailable hai."

    try:
        results = col.query(query_texts=[query], n_results=3)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]

        if not docs:
            return "Indexed documents mein is query ke baare mein kuch nahi mila. Pehle 'index folder' tool se documents index kar lo."

        excerpts = []
        for i, doc_chunk in enumerate(docs):
            src = metas[i].get("file", "unknown") if i < len(metas) else "unknown"
            excerpts.append(f"[{src}]:\n{doc_chunk[:300]}")

        return "Matching document excerpts found:\n\n" + "\n\n".join(excerpts)
    except Exception as e:
        return f"Documents search karte waqt error: {e}"
