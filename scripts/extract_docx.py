#!/usr/bin/env python3
"""Extract text from PLAN/*.docx (XML-decl-broken variant) and dump to stdout.

Usage: python3 scripts/extract_docx.py PLAN/02_lane_A_gold_standard.docx
"""
import sys, zipfile, re
from pathlib import Path
import xml.etree.ElementTree as ET

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

def extract(docx_path):
    z = zipfile.ZipFile(docx_path)
    xml_bytes = z.read("word/document.xml")
    z.close()
    # Strip ALL leading <?xml ... ?> declarations (some docx have 2 of them)
    text = xml_bytes.decode("utf-8", errors="replace")
    # Remove ALL <?xml ...?> declarations anywhere in the text (these docx
    # have 2 of them inline; ET can't handle that)
    text = re.sub(r"<\?xml[^?]*\?>", "", text)
    text = text.strip()
    root = ET.fromstring(text)
    body = root.find("w:body", NS) or root.find("ns0:body", {"ns0": NS["w"]}) or root
    lines = []
    for p in body.iter():
        tag = p.tag.split("}")[-1]
        if tag == "p":
            style_el = p.find("w:pPr/w:pStyle", NS) or p.find("ns0:pPr/ns0:pStyle", {"ns0": NS["w"]})
            style = style_el.get(f"{{{NS['w']}}}val") if style_el is not None else None
            text_runs = []
            for t in p.iter():
                ttag = t.tag.split("}")[-1]
                if ttag == "t" and t.text:
                    text_runs.append(t.text)
            line = "".join(text_runs).strip()
            if not line:
                lines.append("")
                continue
            if style and "Heading" in style:
                # Extract heading level and number from style like "Heading1" or "Heading2"
                m = re.match(r"Heading(\d+)", style)
                if m:
                    level = int(m.group(1))
                    prefix = "#" * level
                    lines.append(f"\n{prefix} {line}")
                else:
                    lines.append(f"\n{line}")
            else:
                lines.append(line)
    # Trim leading blank lines
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(f"========== {arg} ==========")
        print(extract(Path(arg)))
        print()