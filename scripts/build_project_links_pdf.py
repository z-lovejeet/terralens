#!/usr/bin/env python3
"""Build a one-page PDF of the project links with scannable QR codes (same design as the last slide).

    .venv/bin/python scripts/build_project_links_pdf.py
Reads links.json (and team.json if present) and writes output/project-links/TerraLens_Project_Links.pdf.
Needs reportlab and segno. The QR codes and the printed addresses are also clickable links in the PDF.
"""
import io
import json
from pathlib import Path

import segno
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "project-links"
PAGE = (960, 540)  # 16:9, the same shape as the presentation slides

FOREST, PAPER, SOFT, MUTED, WHITE = HexColor("#173D31"), HexColor("#F6F4EE"), HexColor("#CCD8C9"), HexColor("#92A792"), HexColor("#FFFFFF")


def fonts():
    for regular, bold in (("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
                          ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")):
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("Body", regular))
            pdfmetrics.registerFont(TTFont("Body-Bold", bold))
            return "Body", "Body-Bold"
    return "Helvetica", "Helvetica-Bold"


def qr_image(url: str) -> ImageReader:
    buffer = io.BytesIO()
    segno.make(url, error="m").save(buffer, kind="png", scale=14, border=2, dark="#0E3A2F", light="#FFFFFF")
    buffer.seek(0)
    return ImageReader(buffer)


def main() -> None:
    links = json.loads((ROOT / "links.json").read_text())
    members = []
    team_file = ROOT / "team.json"
    if team_file.exists():
        members = [f"{m['name']} ({m['registration_number']})" for m in json.loads(team_file.read_text()).get("members", []) if m.get("name")]
    items = [("Live application", links["deployment"]), ("GitHub repository", links["github"]), ("EuroSAT dataset", links["dataset"])]

    regular, bold = fonts()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "TerraLens_Project_Links.pdf"
    pdf = canvas.Canvas(str(target), pagesize=PAGE)
    pdf.setTitle("TerraLens - Project Links")
    pdf.setAuthor(", ".join(members) or "TerraLens project team")
    pdf.setSubject("INT396 Unsupervised Learning, SIH26142")

    pdf.setFillColor(FOREST)
    pdf.rect(0, 0, *PAGE, fill=1, stroke=0)
    pdf.setFillColor(PAPER)
    pdf.setFont(bold, 50)
    pdf.drawCentredString(480, 458, "Project Links")
    pdf.setFont(bold, 21)
    pdf.drawCentredString(480, 424, "TerraLens")
    pdf.setFillColor(SOFT)
    pdf.setFont(regular, 14)
    pdf.drawCentredString(480, 400, "Unsupervised Land-Type Grouping of Satellite Image Patches Using Clustering")
    pdf.setFont(regular, 12)
    pdf.drawCentredString(480, 380, "INT396 Unsupervised Learning  ·  SIH26142  ·  Lovely Professional University")

    size, gap = 180, 90
    x0 = (PAGE[0] - (3 * size + 2 * gap)) / 2
    top = 335
    for index, (label, url) in enumerate(items):
        x = x0 + index * (size + gap)
        pdf.setFillColor(WHITE)
        pdf.roundRect(x - 8, top - size - 8, size + 16, size + 16, 6, fill=1, stroke=0)
        pdf.drawImage(qr_image(url), x, top - size, width=size, height=size)
        pdf.linkURL(url, (x - 8, top - size - 8, x + size + 8, top + 8), relative=0)
        pdf.setFillColor(PAPER)
        pdf.setFont(bold, 16)
        pdf.drawCentredString(x + size / 2, top - size - 32, label)
        pdf.setFillColor(SOFT)
        pdf.setFont(regular, 8.5)
        shown = url.replace("https://", "").replace("www.", "")
        pdf.drawCentredString(x + size / 2, top - size - 48, shown)
        width = pdf.stringWidth(shown, regular, 8.5)
        pdf.linkURL(url, (x + size / 2 - width / 2, top - size - 52, x + size / 2 + width / 2, top - size - 40), relative=0)

    pdf.setFillColor(MUTED)
    pdf.setFont(regular, 10)
    pdf.drawCentredString(480, 58, "Scan a code with a phone camera, or click it in this PDF. The live site runs on a free server and may take up to a minute to wake.")
    if members:
        pdf.setFillColor(SOFT)
        pdf.setFont(regular, 11)
        pdf.drawCentredString(480, 36, "  ·  ".join(members))
    pdf.showPage()
    pdf.save()
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
