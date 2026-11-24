#!/usr/bin/env python3
"""Bring the TerraLens presentation up to date with the final application and add a QR-code closing slide.

What changed in the project since the earlier deck (all of it is unsupervised ML, no outside API):
  - Map my image: unsupervised segmentation of one satellite image, regions named by a 30-group land model
    or, for close-up screenshots, by colour and texture.
  - Sort my photos: groups a batch of satellite images, number of groups chosen by the elbow method.
  - The earlier scene scanner, change tracking and survey dossier were removed.
  - Live site moved to a new address; dataset link added.

Run after the earlier deck exists in output/presentation/ (it edits that file in place):
    .venv/bin/python scripts/update_presentation_final.py
Needs: python-pptx, segno, pymupdf, Pillow; Keynote (macOS) for the PDF export.

Modifies output/presentation/TerraLens_Presentation.pptx and .pdf, .build/deliverables/slide-*.png.
"""
import json
import subprocess
from pathlib import Path

import pptx
import pymupdf
import segno
from PIL import Image
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Pt

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / ".build" / "deliverables"
PPTX_PATH = ROOT / "output" / "presentation" / "TerraLens_Presentation.pptx"
PDF_PATH = ROOT / "output" / "presentation" / "TerraLens_Presentation.pdf"
SHOTS = ROOT / "docs" / "screenshots"

LINKS = json.loads((ROOT / "links.json").read_text())
LIVE, GITHUB, DATASET = LINKS["deployment"], LINKS["github"], LINKS["dataset"]

C_FOREST = RGBColor(14, 58, 47)
C_PAPER = RGBColor(246, 244, 238)
C_INK = RGBColor(26, 37, 31)
C_MUTED = RGBColor(85, 100, 91)
C_TEAL = RGBColor(32, 91, 77)
C_CARD_BG = RGBColor(229, 234, 223)
C_CARD_ALT = RGBColor(245, 242, 233)
C_WHITE = RGBColor(255, 255, 255)
C_TERRA = RGBColor(180, 83, 56)
C_BORDER = RGBColor(183, 197, 185)
C_SOFT = RGBColor(204, 216, 201)
FONT = "Arial"


def emu(pt):
    return int(pt * 9525)


def format_tf(tf, text, size=20, bold=False, color=C_INK, align=PP_ALIGN.LEFT):
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    for r in p.runs:
        r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), bold, color


def add_paragraph(tf, text, size=18, bold=False, color=C_INK, align=PP_ALIGN.LEFT, space_before=0):
    p = tf.add_paragraph()
    p.text = text
    p.alignment = align
    if space_before:
        p.space_before = Pt(space_before)
    for r in p.runs:
        r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), bold, color


def add_box(slide, left, top, width, height, fill=C_CARD_BG, border=C_BORDER):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, emu(left), emu(top), emu(width), emu(height))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if border:
        shape.line.color.rgb = border
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    shape.shadow.inherit = False
    return shape


def add_text_box(slide, left, top, width, height):
    box = slide.shapes.add_textbox(emu(left), emu(top), emu(width), emu(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Pt(6)
    tf.margin_top = tf.margin_bottom = Pt(4)
    return box


def clear_body_shapes(slide):
    """Remove everything between the title block (top < 90 pt) and the footer (top > 650 pt)."""
    for shape in list(slide.shapes):
        top = shape.top / 9525.0
        if 90 <= top <= 650:
            shape._element.getparent().remove(shape._element)


def set_title(slide, text, size=32):
    for shape in slide.shapes:
        if shape.has_text_frame and shape.top / 9525.0 < 100:
            format_tf(shape.text_frame, text, size=size, bold=True, color=C_FOREST)
            shape.width, shape.height = emu(1152), emu(45)
            return


def set_notes(slide, text):
    format_tf(slide.notes_slide.notes_text_frame, text, size=14, color=C_INK)


def card(slide, left, top, width, height, heading, lines, border=C_TEAL, head_color=C_FOREST, body_size=14, head_size=17):
    add_box(slide, left, top, width, height, border=border)
    tb = add_text_box(slide, left + 8, top + 6, width - 16, height - 12)
    format_tf(tb.text_frame, heading, size=head_size, bold=True, color=head_color)
    for line in lines:
        add_paragraph(tb.text_frame, line, size=body_size, color=C_INK, space_before=5)
    return tb


def footnote(slide, text, top=612, size=18, color=C_MUTED, bold=False):
    tb = add_text_box(slide, 64, top, 1152, 40)
    format_tf(tb.text_frame, text, size=size, color=color, bold=bold)


def picture(slide, path, left, top, width):
    pic = slide.shapes.add_picture(str(path), emu(left), emu(top), width=emu(width))
    pic.line.color.rgb = C_BORDER
    pic.line.width = Pt(1)
    return pic


def table(slide, left, top, width, height, values, col_widths, font_size=14):
    shape = slide.shapes.add_table(len(values), len(values[0]), emu(left), emu(top), emu(width), emu(height))
    tbl = shape.table
    for i, w in enumerate(col_widths):
        tbl.columns[i].width = emu(w)
    for r, row in enumerate(values):
        for c, text in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = text
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            cell.fill.fore_color.rgb = C_FOREST if r == 0 else (C_CARD_ALT if r % 2 else C_CARD_BG)
            for p in cell.text_frame.paragraphs:
                p.alignment = PP_ALIGN.LEFT
                for run in p.runs:
                    run.font.name, run.font.size = FONT, Pt(font_size + (1 if r == 0 else 0))
                    run.font.bold = r == 0
                    run.font.color.rgb = C_WHITE if r == 0 else C_INK
    return shape


def qr_png(url, name):
    BUILD.mkdir(parents=True, exist_ok=True)
    path = BUILD / f"qr-{name}.png"
    segno.make(url, error="m").save(str(path), scale=14, border=2, dark="#0E3A2F", light="#FFFFFF")
    return path


prs = pptx.Presentation(PPTX_PATH)
slides = prs.slides

# --- crop the app screenshots (drop the sidebar) ---------------------------------------------------
cropped = {}
for name in ("map-my-image", "sort-my-photos"):
    target = BUILD / f"deck-{name}.png"
    Image.open(SHOTS / f"{name}.jpg").crop((250, 0, 1440, 1050)).save(target)
    cropped[name] = target

# ===== 01 Title ========================================================================================
s = slides[0]
for shape in s.shapes:
    if not shape.has_text_frame:
        continue
    t = shape.text_frame.text.strip()
    if t.startswith("Unsupervised Land-Type Grouping"):
        format_tf(shape.text_frame, "Unsupervised Land-Type Grouping\n& Everyday Earth-Observation Tools", size=34, color=C_PAPER)
    elif t.startswith("1. Lovejeet"):
        tf = shape.text_frame
        tf.clear()
        tf.paragraphs[0].text = ("1. Lovejeet Singh (12521613)  —  Slides 01–05: Problem, Data & PCA\n"
                                 "2. Mohammad Asim (12518421)  —  Slides 06–10: Platform & Everyday Tools\n"
                                 "3. Reshu Kumar (12508208)    —  Slides 11–15: K-Means, Audit & Deliverables")
        for p in tf.paragraphs:
            p.font.name, p.font.size, p.font.color.rgb = FONT, Pt(16), C_SOFT
    elif t.startswith("Examination Date"):
        format_tf(shape.text_frame, "INT396 Capstone Defense  ·  November 2026", size=14, color=RGBColor(146, 167, 146))
set_notes(s, "[Presenter: Lovejeet Singh] Respected faculty, welcome to our INT396 capstone presentation for project SIH26142. TerraLens is an unsupervised machine learning system that groups satellite images by how they look, without a single label, and turns that into everyday tools anyone can use. I will cover the problem, the data and PCA. Mohammad Asim will present manifold learning, the platform and our two everyday tools, Map my image and Sort my photos. Reshu Kumar will cover K-Means clustering, validation, the post-selection audit and our deliverables. The whole project is unsupervised machine learning and uses no outside API.")

# ===== 02 Problem and objectives =======================================================================
s = slides[1]
clear_body_shapes(s)
tb = add_text_box(s, 64, 150, 1150, 110)
format_tf(tb.text_frame, "Can visual similarity alone organise satellite imagery,\nand can ordinary people use the result without labels?", size=28, bold=True, color=C_INK)
tb = add_text_box(s, 64, 300, 1150, 300)
tf = tb.text_frame
format_tf(tf, "01   Extract label-blind 78-feature descriptors across 27,000 EuroSAT patches", size=24)
add_paragraph(tf, "02   Apply the 95% Scree rule (78 → 28 PCs) and discover 10 land-cover groups with K-Means++", size=24, space_before=22)
add_paragraph(tf, "03   Turn the frozen models into everyday tools, all unsupervised and with no outside API:\n       Map my image · Sort my photos · a finer 30-group land model", size=24, space_before=22)
set_notes(s, "[Presenter: Lovejeet Singh] Satellites capture far more imagery than anyone can label by hand. We ask two questions: can visual similarity alone organise the imagery, and can an ordinary person use the result? We pursue three objectives: first, extract 78 deterministic colour, texture and edge descriptors without labels from 27,000 Sentinel-2 patches; second, reduce them with the 95% Scree rule to 28 principal components and discover 10 land-cover groups with K-Means++; third, reuse those frozen models in everyday tools: Map my image, Sort my photos and a finer 30-group land model. Our teacher required machine learning only, so no tool calls an outside API.")

# ===== 04 Methodology ==================================================================================
s = slides[3]
for shape in s.shapes:
    if not shape.has_text_frame:
        continue
    t = shape.text_frame.text.strip()
    if t.startswith("Operational Tools"):
        format_tf(shape.text_frame, "Everyday tools\n(Map my image · Sort my photos)", size=18, bold=True, color=C_FOREST, align=PP_ALIGN.CENTER)
    elif t.startswith("Strict label-blind"):
        format_tf(shape.text_frame, "Strict label-blind protocol from ingestion to the live tools. Labels are opened only afterwards, to name and score groups.", size=24, color=C_MUTED)
set_notes(s, "[Presenter: Lovejeet Singh] Our methodology enforces strict mathematical isolation. We extract features and split the data 80/20 before any model is fitted. The scaler and the 28-component PCA are fitted on the study cohort only, K-Means finds the groups, and then the models are frozen. The reference labels are opened only afterwards, to give groups everyday names and to score them. The same frozen models power our two everyday tools. Now I hand over to Mohammad Asim for manifold learning and the platform.")

# ===== 07 Architecture ================================================================================
s = slides[6]
clear_body_shapes(s)
set_title(s, "System architecture: one frozen model, many tools", size=30)
table(s, 64, 115, 1152, 340, [
    ["Tier", "Technology", "What it does"],
    ["Machine learning core", "Python · scikit-learn · scikit-image · NumPy", "78 descriptors, 28-PC PCA (95% variance), K=10 reference model, 30-group land model, elbow-method K selection"],
    ["Service API", "FastAPI · SQLite", "Routers for study data, experiments, Patch analyzer, /api/map-regions and /api/sort-photos; bounded uploads, rate limits"],
    ["Interactive workbench", "React 19 · TypeScript · Vite", "Observatory, Map my image, Sort my photos, Patch analyzer, Cluster atlas and Model lab"],
    ["Deployment & quality", "Docker · Render · pytest", "Container on the free Render tier; 52 automated tests; no outside calls or API keys (tested)"],
], [230, 330, 592], font_size=15)
footnote(s, "Everything runs on our own server: the models are fitted offline and only applied when someone uploads an image.", top=520, size=22)
set_notes(s, "[Presenter: Mohammad Asim] Slide 7 shows the architecture. The machine learning core is fitted offline and then frozen. FastAPI serves it through small bounded endpoints, including the two new ones for Map my image and Sort my photos. The React interface has six pages. It is deployed as one Docker container on Render. We have 52 automated tests, and one of them checks that no application code imports a network client or reads an API key, which is how we prove there is no outside API.")

# ===== 08 Map my image ================================================================================
s = slides[7]
clear_body_shapes(s)
set_title(s, "Map my image: unsupervised segmentation of one photo", size=30)
card(s, 64, 108, 520, 92, "1. Cut into squares", ["24 squares along the short side (up to 40 along the long side), each described by the study's 78 descriptors."], body_size=13)
card(s, 64, 208, 520, 122, "2. Cluster inside the image", ["Standardise within the image, cap at ±3 SD, per-image PCA (95%), K-Means++. K = 2–8 by the elbow method; a 3×3 majority filter tidies lone squares."], body_size=13)
card(s, 64, 338, 520, 130, "3. Name the regions", ["30-group land model when the image resembles the training data; otherwise colour & texture rules (greenness, brightness, smoothness, field rows, dark water)."], body_size=13)
add_box(s, 64, 476, 520, 164, fill=C_FOREST, border=None)
tb = add_text_box(s, 72, 482, 504, 152)
format_tf(tb.text_frame, "Measured on 30 test scenes (held-out patches)", size=14, bold=True, color=C_PAPER)
add_paragraph(tb.text_frame, "Region agreement ARI 0.51 · area shares within ±11 points · land-model names right 100% when given.", size=13, color=C_SOFT, space_before=6)
add_paragraph(tb.text_frame, "Real close-up map screenshots: names right for 83% of regions (14 views, judged by eye).", size=13, color=C_SOFT, space_before=6)
picture(s, cropped["map-my-image"], 616, 108, 600)
set_notes(s, "[Presenter: Mohammad Asim] Map my image takes one satellite image and splits it into regions of similar land, by itself. The image is cut into a grid of squares, each described by our 78 descriptors. The important detail is that we standardise within the image: in the study's own space, a detailed close-up has a few extreme squares that capture whole clusters, and a real village screenshot came out as one 82 percent region. Standardising within the image fixed that. K-Means picks the regions and the elbow method picks how many. Each region is then named: by the 30-group land model if the image looks like our training data, otherwise from colour and texture rules. On 30 test scenes built from held-out patches, region agreement is 0.51 and shares are within 11 points; names are right every time the land model gives one. On 14 real map screenshots judged by eye, colour-and-texture names are right for 83 percent of regions. The screenshot shows a demo scene.")

# ===== 09 Sort my photos + land model =================================================================
s = slides[8]
clear_body_shapes(s)
set_title(s, "Sort my photos and the 30-group land model", size=30)
picture(s, cropped["sort-my-photos"], 64, 108, 600)
card(s, 692, 108, 524, 168, "Sort my photos", ["Drop 4–300 satellite images; no categories are given. Frozen scaler and PCA, then K-Means++ with the number of groups chosen by the elbow method.", "On held-out batches the elbow rule beat the silhouette rule (mean ARI 0.37 vs 0.26; knowing the true K gives 0.38)."], body_size=13)
card(s, 692, 284, 524, 128, "Test folder: 30 held-out images", ["Auto finds 5 groups that are 83% pure (ARI 0.68). Forest and water partly share a group because both look dark and smooth in RGB."], body_size=13, border=C_TERRA, head_color=C_TERRA)
card(s, 692, 420, 524, 216, "30-group land model", ["K-Means with 30 groups in the same frozen PCA space; groups are named only afterwards from the held-back labels.", "On 5,400 holdout patches: strict accuracy 69.6% vs 54.8% for the 10 groups; it names 89% of patches and is right 78% of the time when it names one."], body_size=13)
set_notes(s, "[Presenter: Mohammad Asim] Sort my photos groups a batch of your own satellite images. We project them with the frozen scaler and PCA and cluster with K-Means++. The number of groups is chosen by the elbow method, which we tested against silhouette, gap statistic, Calinski-Harabasz, Davies-Bouldin and GMM-BIC on held-out batches with a known number of land types. The elbow rule won, with mean ARI 0.37 against 0.26 for silhouette. Our 30-photo test folder gives 5 groups that are 83 percent pure. Behind the everyday names sits a 30-group land model: the same K-Means idea with 30 groups, named afterwards. On the 5,400 held-out patches it is right 69.6 percent of the time, against 54.8 percent for the original 10 groups.")

# ===== 10 Patch analyzer, offline design, limits =====================================================
s = slides[9]
clear_body_shapes(s)
set_title(s, "Patch analyzer, no-API design and honest limits", size=30)
card(s, 64, 115, 365, 360, "Patch analyzer", ["Upload one patch: 78 descriptors → frozen scaler → 28-PC PCA → distance to the 10 centroids.", "Shows the assigned group, the runner-up margin (d2 − d1) and the nearest reference patches.", "Answers in well under a second (POST /api/analyze)."], body_size=17)
card(s, 457, 115, 365, 360, "Unsupervised and offline", ["No outside API, no pretrained or labelled model: every result comes from our own PCA and K-Means pipeline.", "52 automated tests, including one that fails if any code imports a network client or reads an API key.", "Labels are opened only after fitting, to name and score."], body_size=17, border=C_FOREST)
card(s, 850, 115, 366, 360, "Honest limits", ["Forest and dark water can share a region.", "Trees vs crop fields is the pair most often confused by the colour-and-texture names, which are marked \"best guess\" when close.", "The tool tends to find about one region more than there are land types."], body_size=17, border=C_TERRA, head_color=C_TERRA)
footnote(s, "Use: land-cover shares of a farm, town or reservoir, and tidy archives of satellite images, first look without labels.", top=510, size=20, color=C_FOREST, bold=True)
set_notes(s, "[Presenter: Mohammad Asim] The Patch analyzer applies the frozen pipeline to one patch and shows its group, how close the runner-up group is, and the nearest reference patches. The middle card is important for our teacher's requirement: the project is machine learning only. No outside API and no pretrained or labelled model is used, and a test enforces it. The right card is the honest part: forest and dark water look alike in plain RGB, trees and crop fields are the most confused pair when names come from colour and texture, and the tool tends to find about one extra region. Now I hand over to Reshu Kumar.")

# ===== 12 Contributions ===============================================================================
s = slides[11]
clear_body_shapes(s)
set_title(s, "Individual contributions and completed work", size=32)
table(s, 64, 115, 1152, 350, [
    ["Member / Registration", "Assigned role & objective", "Key completed deliverables"],
    ["Lovejeet Singh\n12521613\n(Presenter 1)", "ML Architecture & PCA\n[Objectives 1 & 2 · CO2, CO4]", "• Engineered 47 colour descriptors (RGB/HSV moments & circular hue bins)\n• Fitted the 28-PC PCA model (95% variance), <0.75% generalization delta, numerical test suites"],
    ["Mohammad Asim\n12518421\n(Presenter 2)", "Manifold Learning & Full-Stack\n[Objective 2 · CO4]", "• Engineered 23 texture & 8 edge descriptors; implemented t-SNE (0.968)\n• Built the FastAPI/React platform, Map my image and Sort my photos"],
    ["Reshu Kumar\n12508208\n(Presenter 3)", "Clustering, Validation & Audit\n[Objectives 2 & 3 · CO4, CO5]", "• Implemented the 80/20 protocol and K-Means++ (K=10); post-hoc reference audit\n• Built the 30-group land model, the elbow rule and the region benchmark"],
], [250, 300, 602], font_size=15)
footnote(s, "Equal 33.3% contribution across all phases. Individual contributions are verified and assessed separately.", top=540, size=21)
set_notes(s, "[Presenter: Reshu Kumar] Our team divided the work equally across all objectives. Lovejeet Singh led data hygiene, the 47 colour descriptors and the 28-component PCA. Mohammad Asim engineered the texture and edge features, implemented t-SNE and built the platform including Map my image and Sort my photos. I led the 80/20 protocol, K-Means clustering, the post-selection audit, the 30-group land model, the elbow rule and the region benchmark. Individual contributions are assessed separately in our verified deliverables.")

# ===== 13 Results: move the finding below the table so they do not touch =============================
for shape in slides[12].shapes:
    if shape.has_text_frame:
        t = shape.text_frame.text.strip()
        if t.startswith("Finding"):
            shape.top = emu(548)
        elif t.startswith("Verification"):
            shape.top = emu(600)

# ===== 15 Links and deliverables ======================================================================
s = slides[14]
clear_body_shapes(s)
set_title(s, "Project links, live deployment and deliverables", size=32)
tb = add_text_box(s, 64, 98, 1152, 28)
format_tf(tb.text_frame, "Everything is public and reproducible; scan the QR codes on the final slide", size=18, bold=True, color=C_TEAL)
cw, ch, cy, gap = 355, 360, 140, 43
cards15 = [
    ("Live web application", "Cloud deployment", [f"• {LIVE.replace('https://', '')}", "• Docker container on Render's free tier", "• All six pages, Map my image and Sort my photos included", "• Free instances sleep when idle: the first load can take about a minute"], C_FOREST),
    ("GitHub repository", "Code, tests and guide", [f"• {GITHUB.replace('https://', '')}", "• 52 pytest tests passing", "• README with step-by-step install for macOS, Linux and Windows", "• Test folders to try Map my image and Sort my photos"], C_TEAL),
    ("Dataset & documents", "EuroSAT RGB (27,000 patches)", [f"• {DATASET.replace('https://', '')}", "• Project report and viva study guide (PDF)", "• This presentation deck", "• One submission ZIP per team member"], C_INK),
]
for i, (hd, sub, items, color) in enumerate(cards15):
    x = 64 + i * (cw + gap)
    add_box(s, x, cy, cw, ch, border=color)
    tb = add_text_box(s, x + 10, cy + 10, cw - 20, ch - 20)
    format_tf(tb.text_frame, hd, size=20, bold=True, color=color)
    add_paragraph(tb.text_frame, sub, size=15, bold=True, color=C_MUTED, space_before=4)
    for item in items:
        add_paragraph(tb.text_frame, item, size=14, color=C_INK, space_before=10)
footnote(s, "Source code, test suites, live deployment and documentation are available for evaluation.", top=530, size=21)
set_notes(s, "[Presenter: Reshu Kumar] Slide 15 collects our deliverables. The live application is hosted on Render, the code and its 52 passing tests are on GitHub with a step-by-step installation guide, and the dataset is the public EuroSAT RGB collection. The documentation consists of the project report, the viva study guide and this deck. The next slide has QR codes for the three links.")

# ===== 16 Thank you + QR codes ========================================================================
s = slides[15]
for shape in list(s.shapes):
    shape._element.getparent().remove(shape._element)
tb = add_text_box(s, 64, 52, 1152, 100)
format_tf(tb.text_frame, "Thank You", size=64, bold=True, color=C_PAPER, align=PP_ALIGN.CENTER)
tb = add_text_box(s, 64, 148, 1152, 36)
format_tf(tb.text_frame, "TerraLens  ·  Questions & Discussion", size=22, color=C_SOFT, align=PP_ALIGN.CENTER)
qr_items = [("Live application", LIVE, "live"), ("GitHub repository", GITHUB, "github"), ("EuroSAT dataset", DATASET, "dataset")]
size, gap = 250, 120
x0 = (1280 - (3 * size + 2 * gap)) / 2
for i, (label, url, key) in enumerate(qr_items):
    x = x0 + i * (size + gap)
    add_box(s, x - 10, 225, size + 20, size + 20, fill=C_WHITE, border=None)
    s.shapes.add_picture(str(qr_png(url, key)), emu(x), emu(235), width=emu(size))
    tb = add_text_box(s, x - 40, 495, size + 80, 34)
    format_tf(tb.text_frame, label, size=20, bold=True, color=C_PAPER, align=PP_ALIGN.CENTER)
    tb = add_text_box(s, x - 60, 530, size + 120, 50)
    format_tf(tb.text_frame, url.replace("https://", "").replace("www.", ""), size=11, color=C_SOFT, align=PP_ALIGN.CENTER)
tb = add_text_box(s, 64, 670, 1152, 25)
format_tf(tb.text_frame, "Lovely Professional University  ·  INT396 Unsupervised Learning  ·  SIH26142", size=14, color=RGBColor(146, 167, 146), align=PP_ALIGN.CENTER)
set_notes(s, "[All Presenters] Thank you for your time and evaluation. The three QR codes open the live application, the GitHub repository and the EuroSAT dataset. We are happy to answer any questions.")

# ===== Corrections: bring older slides in line with the saved study results ============================
SWAPS = {"0.771": "0.968", "across 5 random seeds": "across three random seeds (42, 17, 91)"}


def swap_frame(tf):
    for paragraph in tf.paragraphs:
        for run in paragraph.runs:
            for old, new in SWAPS.items():
                if old in run.text:
                    run.text = run.text.replace(old, new)


for slide_item in prs.slides:
    for shape in slide_item.shapes:
        if shape.has_text_frame:
            swap_frame(shape.text_frame)
        if getattr(shape, "has_table", False) and shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    swap_frame(cell.text_frame)
    if slide_item.has_notes_slide:
        swap_frame(slide_item.notes_slide.notes_text_frame)

prs.save(PPTX_PATH)
print(f"Saved {PPTX_PATH}")
(BUILD / "presentation_notes.json").write_text(json.dumps(
    [{"slide": i + 1, "notes": sl.notes_slide.notes_text_frame.text if sl.has_notes_slide else ""} for i, sl in enumerate(prs.slides)], indent=2))

# Export to PDF through Keynote, then render slide PNGs
script = f'''
tell application "Keynote"
    set theDoc to open POSIX file "{PPTX_PATH}"
    export theDoc to POSIX file "{PDF_PATH}" as PDF
    close theDoc saving no
end tell
'''
result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
print("PDF export:", "ok" if result.returncode == 0 else result.stderr)
if result.returncode == 0:
    doc = pymupdf.open(str(PDF_PATH))
    for index, page in enumerate(doc):
        page.get_pixmap(dpi=192).save(str(BUILD / f"slide-{index + 1:02d}.png"))
    print(f"Rendered {len(doc)} slide PNGs to {BUILD}")
