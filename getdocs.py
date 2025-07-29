import os
import json
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from datetime import datetime
import re

ROOT_DIR = "docs"
OUTPUT_JSON = "docs.json"
OUTPUT_HTML = os.path.join(ROOT_DIR, "index.html")

def extract_pdf_metadata(file_path):
    try:
        doc = fitz.open(file_path)
        metadata = doc.metadata or {}
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) > 2000:
                break
        doc.close()
    except Exception as e:
        print(f"[❌ ERROR] PDF read failed: {file_path} → {e}")
        return None

    title = metadata.get("title") or os.path.basename(file_path).rsplit(".", 1)[0].replace("_", " ").title()
    version_match = re.search(r"\b[vV]?(ersion)?\s?(\d+\.\d+)", text)
    version = version_match.group(2) if version_match else "1.0"

    return {
        "title": title.strip(),
        "version": version.strip()
    }

def extract_html_metadata(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
        title = soup.title.string.strip() if soup.title else os.path.basename(file_path).rsplit(".", 1)[0].replace("_", " ").title()
        text = soup.get_text()
        version_match = re.search(r"\b[vV]?(ersion)?\s?(\d+\.\d+)", text)
        version = version_match.group(2) if version_match else "1.0"
    except Exception as e:
        print(f"[❌ ERROR] HTML read failed: {file_path} → {e}")
        return None

    return {
        "title": title,
        "version": version
    }

def get_doc_metadata(full_path, rel_path_from_docs):
    ext = os.path.splitext(full_path)[-1].lower()
    format_ = "PDF" if ext == ".pdf" else "HTML"
    updated_on = datetime.fromtimestamp(os.path.getmtime(full_path)).strftime("%Y-%m-%d")

    if ext == ".pdf":
        extracted = extract_pdf_metadata(full_path)
    elif ext == ".html" and os.path.basename(full_path).lower() == "index.html":
        extracted = extract_html_metadata(full_path)
    else:
        return None

    if not extracted:
        return None

    return {
        "title": extracted["title"],
        "filename": os.path.basename(full_path),
        "format": format_,
        "version": extracted["version"],
        "updated_on": updated_on,
        "path": rel_path_from_docs.replace("\\", "/")
    }

def build_structure_and_index():
    docs = {"sections": {}}
    html_links = []

    print("📁 Scanning folders...\n")

    for dirpath, _, filenames in os.walk(ROOT_DIR):
        for file in filenames:
            ext = os.path.splitext(file)[-1].lower()
            is_index_html = file.lower() == "index.html"
            is_pdf = ext == ".pdf"

            if not (is_pdf or is_index_html):
                continue

            full_path = os.path.join(dirpath, file)
            rel_path_from_docs = os.path.relpath(full_path, ROOT_DIR)
            parts = rel_path_from_docs.split(os.sep)

            if len(parts) < 3:
                print(f"⚠️ Skipped (not deep enough): {rel_path_from_docs}")
                continue

            section = parts[0].capitalize()
            subsection = parts[1].replace("-", " ").replace("_", " ").title()

            print(f"🔍 Processing: {rel_path_from_docs}...")

            doc_metadata = get_doc_metadata(full_path, rel_path_from_docs)
            if not doc_metadata:
                print(f"   ❌ Skipped or failed: {file}")
                continue

            print(f"   ✅ Title: {doc_metadata['title']}, Version: {doc_metadata['version']}, Format: {doc_metadata['format']}")

            # JSON structure
            docs["sections"] \
                .setdefault(section, {}) \
                .setdefault("subsections", {}) \
                .setdefault(subsection, {}) \
                .setdefault("documents", []) \
                .append(doc_metadata)

            # HTML link structure
            link_path = doc_metadata["path"]
            link_title = f"{doc_metadata['title']} (v{doc_metadata['version']})"
            html_links.append(f'<li><a href="{link_path}" target="_blank">{link_title}</a></li>')

    return docs, html_links

def write_index_html(html_links):
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html>\n<html>\n<head>\n<title>Document Index</title>\n</head>\n<body>\n")
        f.write("<h1>Available Documents</h1>\n<ul>\n")
        f.write("\n".join(html_links))
        f.write("\n</ul>\n</body>\n</html>")
    print(f"\n✅ index.html generated at '{OUTPUT_HTML}' with {len(html_links)} entries.")

if __name__ == "__main__":
    structure, html_links = build_structure_and_index()

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(structure, f, indent=2)
    print(f"\n✅ Documentation structure exported to '{OUTPUT_JSON}'")

    write_index_html(html_links)
