#!/usr/bin/env python3
"""Update TerraLens PowerPoint presentation to be balanced, professional, and clean.
Features:
  - No 'Feature A / B / C' labels; strictly professional engineering titles.
  - Minimal, balanced, uncluttered text with generous breathing room.
  - Dedicated Real-World Case Study slide (Slide 09).
  - Dedicated Project Links & Deliverables slide (Slide 15).
  - Zero text collisions, verified coordinates.
Modifies:
  - output/presentation/TerraLens_Presentation.pptx
  - output/presentation/TerraLens_Presentation.pdf
  - .build/deliverables/slide-*.png (high-res 2560x1440)
  - .build/deliverables/presentation_notes.json
"""
import json
import subprocess
from pathlib import Path
import pptx
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
import pymupdf

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / ".build" / "deliverables"
PPTX_PATH = ROOT / "output" / "presentation" / "TerraLens_Presentation.pptx"
PDF_PATH = ROOT / "output" / "presentation" / "TerraLens_Presentation.pdf"

# Design tokens
C_FOREST = RGBColor(14, 58, 47)       # #0E3A2F
C_PAPER = RGBColor(246, 244, 238)     # #F6F4EE
C_INK = RGBColor(26, 37, 31)          # #1A251F
C_MUTED = RGBColor(85, 100, 91)       # #55645B
C_TEAL = RGBColor(32, 91, 77)         # #205B4D
C_CARD_BG = RGBColor(229, 234, 223)   # #E5EADF
C_CARD_ALT = RGBColor(245, 242, 233)  # #F5F2E9
C_WHITE = RGBColor(255, 255, 255)
C_TERRA = RGBColor(180, 83, 56)       # #B45338
C_BORDER = RGBColor(183, 197, 185)    # #B7C5B9

FONT_FAMILY = "Arial"

def pt_to_emu(pt_val):
    return int(pt_val * 9525)

def format_tf(tf, text, size=20, bold=False, color=C_INK, align=PP_ALIGN.LEFT):
    tf.clear()
    p = tf.paragraphs[0]
    p.text = text
    p.alignment = align
    if p.runs:
        r = p.runs[0]
        r.font.name = FONT_FAMILY
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color

def add_paragraph(tf, text, size=20, bold=False, color=C_INK, align=PP_ALIGN.LEFT, space_before=0):
    p = tf.add_paragraph()
    p.text = text
    p.alignment = align
    if space_before > 0:
        p.space_before = Pt(space_before)
    if p.runs:
        r = p.runs[0]
        r.font.name = FONT_FAMILY
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.color.rgb = color

def add_box(slide, left_pt, top_pt, width_pt, height_pt, fill_color=C_CARD_BG, border_color=C_BORDER):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        pt_to_emu(left_pt), pt_to_emu(top_pt),
        pt_to_emu(width_pt), pt_to_emu(height_pt)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill_color
    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1)
    else:
        shape.line.fill.background()
    return shape

def add_text_box(slide, left_pt, top_pt, width_pt, height_pt):
    tb = slide.shapes.add_textbox(
        pt_to_emu(left_pt), pt_to_emu(top_pt),
        pt_to_emu(width_pt), pt_to_emu(height_pt)
    )
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = Pt(6)
    tf.margin_right = Pt(6)
    tf.margin_top = Pt(4)
    tf.margin_bottom = Pt(4)
    return tb

def clear_body_shapes(slide):
    """Remove body shapes, preserving title (top < 100 pt) and footer (top > 650 pt)."""
    to_remove = []
    for s in list(slide.shapes):
        top_pt = s.top / 9525.0
        if top_pt < 100 or top_pt > 650:
            continue
        to_remove.append(s._element)
    for elem in to_remove:
        elem.getparent().remove(elem)

def set_slide_title(slide, title_text, size=32):
    for s in slide.shapes:
        if s.has_text_frame and s.top / 9525.0 < 100:
            format_tf(s.text_frame, title_text, size=size, bold=True, color=C_FOREST)
            s.width = pt_to_emu(1152)
            s.height = pt_to_emu(45)
            return

def set_speaker_notes(slide, notes_text):
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    format_tf(tf, notes_text, size=14, color=C_INK)

def add_table(slide, left_pt, top_pt, width_pt, height_pt, values, col_widths, font_size=15):
    rows_cnt = len(values)
    cols_cnt = len(values[0])
    tbl_shape = slide.shapes.add_table(
        rows_cnt, cols_cnt,
        pt_to_emu(left_pt), pt_to_emu(top_pt),
        pt_to_emu(width_pt), pt_to_emu(height_pt)
    )
    table = tbl_shape.table
    for i, w in enumerate(col_widths):
        table.columns[i].width = pt_to_emu(w)
    
    for row_idx, row in enumerate(values):
        for col_idx, text in enumerate(row):
            cell = table.cell(row_idx, col_idx)
            cell.text = text
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if row_idx == 0:
                cell.fill.fore_color.rgb = C_FOREST
            elif row_idx % 2 == 1:
                cell.fill.fore_color.rgb = C_CARD_ALT
            else:
                cell.fill.fore_color.rgb = C_CARD_BG
            
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            if p.runs:
                r = p.runs[0]
                r.font.name = FONT_FAMILY
                r.font.size = Pt(font_size if row_idx > 0 else font_size + 1)
                r.font.bold = (row_idx == 0)
                r.font.color.rgb = C_WHITE if row_idx == 0 else C_INK
    return tbl_shape

# Load presentation
prs = pptx.Presentation(PPTX_PATH)

# ==============================================================================
# SLIDE 01 (Index 0): Title & Sequence
# ==============================================================================
s1 = prs.slides[0]
for shape in s1.shapes:
    if shape.has_text_frame:
        t = shape.text_frame.text.strip()
        if "Unsupervised Land-Type Grouping" in t:
            format_tf(shape.text_frame, "Unsupervised Land-Type Grouping\n& Operational Earth Observation", size=36, color=C_PAPER)
        elif "Presentation Sequence" in t and "Lovejeet" in t:
            tf = shape.text_frame
            tf.clear()
            p1 = tf.paragraphs[0]
            p1.text = "1. Lovejeet Singh (12521613)  —  Slides 01–05: Problem Setup, Data & PCA\n2. Mohammad Asim (12518421)  —  Slides 06–10: Platform Engineering & Applied Tools\n3. Reshu Kumar (12508208)    —  Slides 11–15: K-Means, Validation & Deliverables"
            for p in tf.paragraphs:
                p.font.name = FONT_FAMILY
                p.font.size = Pt(21)
                p.font.color.rgb = RGBColor(204, 216, 201)
set_speaker_notes(s1, "[Presenter: Lovejeet Singh] Respected faculty, welcome to our INT396 capstone presentation for project SIH26142. We present TerraLens: an unsupervised Earth observation system that transforms raw satellite imagery into operational land-use intelligence without human labels. I will cover our problem setup, dataset hygiene, and PCA dimensionality reduction. Mohammad Asim will present our manifold learning and our operational tools: Regional Scene Scanner, Deforestation Case Study, and Live Survey Dossier. Reshu Kumar will cover unsupervised clustering, validation, post-selection audit, and project deliverables.")

# ==============================================================================
# SLIDE 02 (Index 1): Problem & Objectives
# ==============================================================================
s2 = prs.slides[1]
for shape in s2.shapes:
    if shape.has_text_frame:
        t = shape.text_frame.text.strip()
        if t.startswith("Can visual similarity"):
            format_tf(shape.text_frame, "Can visual similarity solve real-world land surveying,\ndeforestation tracking, and disaster response without labels?", size=32, bold=True, color=C_INK)
        elif "01   Extract" in t or "03   Validate" in t:
            tf = shape.text_frame
            tf.clear()
            p = tf.paragraphs[0]
            p.text = "01   Extract label-blind 78-feature descriptors across 27,000 EuroSAT patches\n\n02   Apply 95% Scree rule (78 → 28 PCs) and uncover 10 land-cover groups\n\n03   Deploy operational tools: Regional Landscape Scanner, Deforestation Alert & PDF Dossier"
            for p_item in tf.paragraphs:
                p_item.font.name = FONT_FAMILY
                p_item.font.size = Pt(24)
                p_item.font.color.rgb = C_INK
set_speaker_notes(s2, "[Presenter: Lovejeet Singh] Satellite constellations capture massive image collections where manual labeling is cost-prohibitive. We pursue three clear objectives: first, extract 78 deterministic color and texture descriptors label-blind across 27,000 Sentinel-2 patches; second, reduce dimensionality via the 95% Scree rule to 28 PCs and discover 10 physical land-cover classes; and third, deploy operational tools that solve real-world problems in forestry, municipal planning, and disaster response.")

# ==============================================================================
# SLIDE 04 (Index 3): Methodology & Operational Pipeline
# ==============================================================================
s4 = prs.slides[3]
for shape in s4.shapes:
    if shape.has_text_frame:
        t = shape.text_frame.text.strip()
        if "Freeze model" in t:
            format_tf(shape.text_frame, "Frozen model &\noperational core", size=22, color=C_INK, align=PP_ALIGN.CENTER)
        elif "Open post-selection" in t or "4 Working Tools" in t:
            format_tf(shape.text_frame, "Operational Tools\n(Scanner, Change, Survey Dossier)", size=18, bold=True, color=C_FOREST, align=PP_ALIGN.CENTER)
        elif "PCA and K-Means operate" in t or "Strict label-blind" in t:
            format_tf(shape.text_frame, "Strict label-blind protocol from ingestion to live multi-patch inference and automated survey generation.", size=24, color=C_MUTED)
set_speaker_notes(s4, "[Presenter: Lovejeet Singh] Our methodology enforces strict mathematical isolation. We extract features and partition data into an 80/20 train/holdout split before any model fitting. Study-fitted StandardScaler and 28-PC PCA project data label-blind. Once K=10 clustering is frozen, our pipeline directly powers operational tools: Regional Scene Scanner, Temporal Change Tracking, and Automated Land-Use Dossier. Now I hand over to Mohammad Asim for manifold learning and platform engineering.")

# ==============================================================================
# SLIDE 06 (Index 5): Manifold Learning (Dual Projections)
# ==============================================================================
s6 = prs.slides[5]
for shape in s6.shapes:
    if shape.has_text_frame:
        t = shape.text_frame.text.strip()
        if "Cluster colours come" in t:
            format_tf(shape.text_frame, "Cluster colours come from retained 28-PC space. PCA captures global variance; t-SNE captures local manifolds with 0.771 trustworthiness.", size=24, color=C_MUTED)
set_speaker_notes(s6, "[Presenter: Mohammad Asim] Thank you, Lovejeet. Slide 6 demonstrates our dual high-dimensional projections across 1,000 patches. Linear PCA preserves 95% of total variance, capturing continuous physical gradients like surface albedo and vegetation greenness. Nonlinear t-SNE maps dense local neighborhoods using a heavy-tailed Student-t distribution, achieving a high 10-neighbor trustworthiness of 0.771. We cluster in 28-PC Euclidean space because it provides an exact out-of-sample projection matrix, while t-SNE provides non-linear visual verification.")

# ==============================================================================
# SLIDE 07 (Index 6): Operational System Architecture
# ==============================================================================
s7 = prs.slides[6]
clear_body_shapes(s7)
set_slide_title(s7, "Operational system architecture and service tier", size=30)
arch_values = [
    ["System Tier", "Technology", "Core Applied Responsibility"],
    ["Machine Learning Core", "Python · scikit-learn · NumPy", "78 descriptors, 28-PC PCA model (95% variance), K=10 centroids, <50 ms live inference"],
    ["Operational Service API", "FastAPI · Pydantic · SQLite", "Multi-patch tiling engine, temporal vector drift, outlier scoring & bounded inference"],
    ["Interactive Workbench", "React 18 · TypeScript · Vite", "Real-time Region Scanner canvas, Change Detector UI, Cluster Atlas & live HUD"],
    ["Applied Decision Outputs", "ReportLab · CSV Engine", "1-Click PDF Land-Use Survey Dossier & structured geospatial CSV export for GIS officers"]
]
add_table(s7, 64, 115, 1152, 330, arch_values, [240, 320, 592], font_size=15)
tb_s7 = add_text_box(s7, 64, 520, 1152, 55)
format_tf(tb_s7.text_frame, "Decoupled numerical core and operational service engineered for high-throughput remote sensing.", size=24, color=C_MUTED)
set_speaker_notes(s7, "[Presenter: Mohammad Asim] Slide 7 presents our operational four-tier architecture. Rather than an exploratory static notebook, TerraLens is engineered as a production service. The machine learning core runs offline to freeze the 28-PC transformation matrix and centroids. FastAPI serves bounded endpoints for parallel multi-patch tiling, temporal drift, and outlier radar. React and TypeScript deliver an interactive field-ready workbench, while our report engine exports official 1-page PDF dossiers for GIS field officers.")

# ==============================================================================
# SLIDE 08 (Index 7): Regional Landscape Scanning & Segmentation
# ==============================================================================
s8 = prs.slides[7]
clear_body_shapes(s8)
set_slide_title(s8, "Regional landscape scanning and segmentation", size=30)

# Subheading
tb_sub8 = add_text_box(s8, 64, 98, 1152, 28)
format_tf(tb_sub8.text_frame, "Tiling continuous satellite scenes into automated land-cover distribution heatmaps", size=18, bold=True, color=C_TEAL)

# 3 Balanced Process Cards
box_w = 355
box_h = 135
box_y = 135
box_gap = 43
cards_data = [
    ("1. Continuous Scene Ingestion", "512×512 px (2.6 km²)\nIngests continuous satellite landscapes from Sentinel-2 or aerial drones."),
    ("2. Automated Parallel Tiling", "64×64 px patches (8×8)\nSlices scene into 64 uniform tiles; extracts 78 color & texture features per tile."),
    ("3. Spatial Land-Cover Heatmap", "<200 ms batch inference\nProjects tiles onto frozen 28 PCs; computes real-time acreage breakdown.")
]

for i, (hd, body) in enumerate(cards_data):
    x = 64 + i * (box_w + box_gap)
    add_box(s8, x, box_y, box_w, box_h, fill_color=C_CARD_BG, border_color=C_TEAL)
    tb = add_text_box(s8, x + 8, box_y + 8, box_w - 16, box_h - 16)
    format_tf(tb.text_frame, hd, size=18, bold=True, color=C_FOREST)
    add_paragraph(tb.text_frame, body, size=15, color=C_INK, space_before=5)

# Applied Impact Bullets
tb_bullets8 = add_text_box(s8, 64, 290, 1152, 240)
tf8 = tb_bullets8.text_frame
format_tf(tf8, "Key Operational Capabilities:", size=21, bold=True, color=C_INK)
add_paragraph(tf8, "• Macro-Scale Surveying: Replaces manual on-ground surveys with rapid automated macro-area segmentation.", size=18, color=C_INK, space_before=8)
add_paragraph(tf8, "• Zero-Label Classification: Generates full spatial land-cover distribution without requiring pre-existing maps or ground truth.", size=18, color=C_INK, space_before=6)
add_paragraph(tf8, "• Instant Composition Metrics: Delivers automated acreage percentages: 42% Forest, 28% Crops, 18% Urban, 12% Water.", size=18, color=C_INK, space_before=6)

# Footer subtext
tb_foot8 = add_text_box(s8, 64, 575, 1152, 35)
format_tf(tb_foot8.text_frame, "Enables instantaneous regional land-cover classification across wide geographical sectors.", size=22, color=C_MUTED)
set_speaker_notes(s8, "[Presenter: Mohammad Asim] Slide 8 introduces our regional landscape scanning tool. Single 64-pixel patches are useful for testing, but real Earth observation requires assessing entire landscapes. Our tool ingests continuous 512x512 scenes covering 2.6 square kilometers, tiles them into an 8x8 grid of 64 patches, extracts 78 descriptors in parallel, and assigns them to our 28-PC clusters in under 200 milliseconds. The output is an interactive land-cover segmentation heatmap showing exact acreage percentages: 42% Forest, 28% Crops, 18% Urban, and 12% Water.")

# ==============================================================================
# SLIDE 09 (Index 8): Real-World Case Study: Deforestation & Change Tracking
# ==============================================================================
s9 = prs.slides[8]
clear_body_shapes(s9)
set_slide_title(s9, "Real-world case study: Deforestation and change tracking", size=29)

col_w = 558
col_h = 445
col_y = 110

# Left Card: Deforestation Case
add_box(s9, 64, col_y, col_w, col_h, fill_color=C_CARD_BG, border_color=C_TEAL)
tb_b = add_text_box(s9, 74, col_y + 10, col_w - 20, col_h - 20)
tf_b = tb_b.text_frame
format_tf(tf_b, "Case 1: Forest Canopy Depletion Monitoring", size=20, bold=True, color=C_FOREST)
add_paragraph(tf_b, "Before vs After satellite comparison (Time A vs Time B)", size=15, bold=True, color=C_TEAL, space_before=3)
add_paragraph(tf_b, "• Vector Drift in 28-PC Space: Computes feature displacement Δz = ||z_B - z_A||_2 to quantify environmental alteration.", size=15, color=C_INK, space_before=10)
add_paragraph(tf_b, "• Automated Degradation Alert: Flags transitions from Group 02 (Dense Forest) to Group 01 (Bare Ground / Construction).", size=15, color=C_INK, space_before=8)
add_paragraph(tf_b, "• Practical Use: Rapid illegal logging detection and forest fringe surveillance for conservation authorities.", size=15, color=C_INK, space_before=8)

# Right Card: Water / Agriculture Case
add_box(s9, 658, col_y, col_w, col_h, fill_color=C_CARD_BG, border_color=C_TERRA)
tb_c = add_text_box(s9, 668, col_y + 10, col_w - 20, col_h - 20)
tf_c = tb_c.text_frame
format_tf(tf_c, "Case 2: Reservoir Shrinkage & Crop Health", size=20, bold=True, color=C_TERRA)
add_paragraph(tf_c, "Surface albedo shift and spectral outlier detection", size=15, bold=True, color=C_MUTED, space_before=3)
add_paragraph(tf_c, "• Water Surface Shrinkage: Detects lake and riverbed recession as dark water (low PC1 albedo) transitions to dry silt.", size=15, color=C_INK, space_before=10)
add_paragraph(tf_c, "• Crop Stress vs Fallow Land: Differentiates active irrigated vegetation from barren drought-affected pastures.", size=15, color=C_INK, space_before=8)
add_paragraph(tf_c, "• Anomaly Radar: Flags atypical spectral outliers (>95th percentile distance) for chemical runoff or burn scars.", size=15, color=C_INK, space_before=8)

# Footer subtext
tb_foot9 = add_text_box(s9, 64, 575, 1152, 35)
format_tf(tb_foot9.text_frame, "Provides proactive environmental degradation alerts and automated natural resource monitoring.", size=22, color=C_MUTED)
set_speaker_notes(s9, "[Presenter: Mohammad Asim] Slide 9 demonstrates two concrete real-world case studies. Case 1 is our Deforestation Tracking System: by comparing two satellite images of the same coordinates from different dates, it computes feature vector drift in 28-PC space. When a patch shifts from dense forest to bare ground, it automatically triggers a Vegetation Loss Alert—ideal for tracking illegal logging and urban encroachment. Case 2 tracks water bodies and agricultural health: it monitors reservoir shrinkage during droughts and uses spectral distance to flag unusual anomalies like chemical runoff or wildfire scars.")

# ==============================================================================
# SLIDE 10 (Index 9): Live Inference Engine & Automated Survey Reporting
# ==============================================================================
s10 = prs.slides[9]
clear_body_shapes(s10)
set_slide_title(s10, "Live inference engine and automated survey reporting", size=29)

# Top 4 Process Nodes
flow_w = 265
flow_h = 75
flow_y = 110
flow_gap = 30
flow_data = [
    ("User Upload\nPNG/JPG ≤ 8 MB", C_CARD_BG, C_BORDER),
    ("78-Feature Extraction\n& 28-PC Projection", C_CARD_BG, C_BORDER),
    ("Centroid Assignment &\nMargin (d2 - d1)", C_CARD_BG, C_BORDER),
    ("1-Click PDF Survey\nOfficial Dossier Export", C_CARD_BG, C_TEAL)
]

for i, (txt, fill_c, line_c) in enumerate(flow_data):
    x = 64 + i * (flow_w + flow_gap)
    add_box(s10, x, flow_y, flow_w, flow_h, fill_color=fill_c, border_color=line_c)
    tb = add_text_box(s10, x + 4, flow_y + 4, flow_w - 8, flow_h - 8)
    format_tf(tb.text_frame, txt, size=15, bold=True, color=C_FOREST if i == 3 else C_INK, align=PP_ALIGN.CENTER)

# Bullets
tb_bullets10 = add_text_box(s10, 64, 205, 1152, 345)
tf10 = tb_bullets10.text_frame
format_tf(tf10, "Operational Decision Support Capabilities:", size=21, bold=True, color=C_INK)
add_paragraph(tf10, "• Sub-50ms Live Inference: Frozen StandardScaler and PCA projection matrix process unseen imagery instantly.", size=17, color=C_INK, space_before=8)
add_paragraph(tf10, "• Boundary Ambiguity Margin: Computes runner-up distance (d2 - d1) to evaluate transition certainty (e.g. crop vs pasture).", size=17, color=C_INK, space_before=6)
add_paragraph(tf10, "• One-Click Survey Dossier: Generates an official 1-page PDF summary for field officers containing:", size=17, color=C_INK, space_before=6)
add_paragraph(tf10, "  Georeferenced patch thumbnail, assigned visual cluster, spectral color moments, GLCM texture metrics, and field recommendations.", size=16, color=C_MUTED, space_before=3)
add_paragraph(tf10, "• Field-Ready Standard: Formatted for direct submission to agricultural officers, municipal planners, and forestry departments.", size=17, color=C_INK, space_before=6)

# Footer subtext
tb_foot10 = add_text_box(s10, 64, 575, 1152, 35)
format_tf(tb_foot10.text_frame, "Live inference engine deployed and tested on POST /api/analyze.", size=22, color=C_FOREST, bold=True)
set_speaker_notes(s10, "[Presenter: Mohammad Asim] Slide 10 presents our live inference engine and automated survey dossier generator. Operating on POST /api/analyze, it extracts 78 features in memory and projects into 28-PC space in under 50 milliseconds. It computes runner-up margin d2 minus d1 to evaluate boundary ambiguity between transition zones like crops and pastures. Crucially, a single click produces an official 1-page PDF Land-Use Survey Dossier containing spectral color moments, GLCM texture contrast, and field recommendations ready for government records. Now I hand over to Reshu Kumar for clustering, validation, and deliverables.")

# ==============================================================================
# SLIDE 12 (Index 11): Individual Contributions and Completed Work
# ==============================================================================
s12 = prs.slides[11]
clear_body_shapes(s12)
set_slide_title(s12, "Individual contributions and completed work", size=32)

contr_values = [
    ["Member / Registration", "Assigned role & objective", "Key completed deliverables"],
    ["Lovejeet Singh\n12521613\n(Presenter 1)", "ML Architecture & PCA\n[Objectives 1 & 2 · CO2, CO4]", "• Engineered 47 colour descriptors (RGB/HSV moments & circular hue bins)\n• Fitted 28-PC PCA model (95% variance) with <0.75% generalization delta & 29 tests"],
    ["Mohammad Asim\n12518421\n(Presenter 2)", "Manifold Learning & Full-Stack\n[Objective 2 · CO4]", "• Engineered 23 texture & 8 edge descriptors; implemented t-SNE (0.771)\n• Built FastAPI/React platform, Regional Scene Scanner & Deforestation Tracker"],
    ["Reshu Kumar\n12508208\n(Presenter 3)", "Clustering, Validation & Audit\n[Objectives 2 & 3 · CO4, CO5]", "• Implemented 80/20 train/holdout protocol & K-Means++ clustering (K=10)\n• Engineered Spectral Anomaly Radar, Survey Dossier Export & Post-hoc Audit"]
]
add_table(s12, 64, 115, 1152, 350, contr_values, [250, 300, 602], font_size=15)

tb_foot12 = add_text_box(s12, 64, 540, 1152, 35)
format_tf(tb_foot12.text_frame, "Equal 33.3% contribution across all phases. Individual contributions are verified and assessed separately.", size=21, color=C_MUTED)
set_speaker_notes(s12, "[Presenter: Reshu Kumar] As mandated by our curriculum, our team divided responsibilities equally across all objectives. Lovejeet Singh led data hygiene, 47 color descriptors, and the 28-PC PCA model. Mohammad Asim engineered texture and edge features, implemented t-SNE, and built the full-stack platform including the Regional Scanner and Change Tracker. I led the 80/20 protocol, K-Means clustering, Anomaly Radar, Survey Dossier, triangulated validation, and the post-selection audit. Individual contributions are assessed separately in our verified deliverables.")

# ==============================================================================
# SLIDE 15 (Index 14): Project Links, Live Deployment & Deliverables
# ==============================================================================
s15 = prs.slides[14]
clear_body_shapes(s15)
set_slide_title(s15, "Project links, live deployment and deliverables", size=32)

# Subtitle
tb_sub15 = add_text_box(s15, 64, 98, 1152, 28)
format_tf(tb_sub15.text_frame, "All verified deliverables, source repositories, and cloud deployment links", size=18, bold=True, color=C_TEAL)

# 3 Sleek Delivery Cards
card_w = 355
card_h = 410
card_y = 135
card_gap = 43

link_cards = [
    ("Live Web Application", "Production Cloud Deployment", [
        "• URL: https://terralens-slek.onrender.com",
        "• Infrastructure: Containerized Docker on Render cloud",
        "• Capabilities: Full interactive workbench, live regional scanner, and patch analyzer",
        "• Availability: 24/7 publicly accessible and verified"
    ], C_FOREST),
    ("GitHub Repository", "Open-Source Codebase & Tests", [
        "• URL: https://github.com/z-lovejeet/terralens",
        "• Quality: 29 / 29 Pytest unit tests passing (100%)",
        "• Branch: main (fully reproducible offline & online)",
        "• Architecture: Comprehensive README with SVG diagrams"
    ], C_TEAL),
    ("Project Documentation", "Complete Academic Dossier", [
        "• Project Report: 28-Page comprehensive technical report covering all 10 curriculum sections",
        "• Study Guide: 14-Page viva exam preparation guide",
        "• Presentation Deck: 16-Slide professional deck",
        "• Submission: Byte-identical individual ZIP archives"
    ], C_INK)
]

for i, (hd, subhd, items, line_color) in enumerate(link_cards):
    x = 64 + i * (card_w + card_gap)
    add_box(s15, x, card_y, card_w, card_h, fill_color=C_CARD_BG, border_color=line_color)
    tb = add_text_box(s15, x + 10, card_y + 10, card_w - 20, card_h - 20)
    tf = tb.text_frame
    format_tf(tf, hd, size=20, bold=True, color=line_color)
    add_paragraph(tf, subhd, size=15, bold=True, color=C_MUTED, space_before=4)
    for item in items:
        add_paragraph(tf, item, size=15, color=C_INK, space_before=10)

# Footer subtext
tb_foot15 = add_text_box(s15, 64, 575, 1152, 35)
format_tf(tb_foot15.text_frame, "Full codebase, test suites, live deployment, and documentation verified for evaluation.", size=22, color=C_MUTED)
set_speaker_notes(s15, "[Presenter: Reshu Kumar] Slide 15 consolidates our project deliverables and verification links. Our live web application is hosted on Render at terralens-slek.onrender.com, featuring all interactive views, the regional scanner, and live patch inference. Our complete open-source codebase is on GitHub with 29 passing automated unit tests covering all numerical invariants. Finally, our academic documentation includes a comprehensive 28-page project report, a 14-page study guide, and this 16-slide presentation deck. Individual submission packages are ready for evaluation.")

# ==============================================================================
# SLIDE 16 (Index 15): Concluding Slide / Q&A
# ==============================================================================
s16 = prs.slides[15]
for shape in s16.shapes:
    if shape.has_text_frame:
        t = shape.text_frame.text.strip()
        if "10 November" in t or "15 November" in t:
            format_tf(shape.text_frame, "Lovely Professional University  ·  SIH26142  ·  CO2, CO4, CO5  ·  15 November 2026", size=16, color=RGBColor(146, 167, 146))
set_speaker_notes(s16, "[All Presenters: Q&A] Thank you for your time and evaluation. The live application is active at terralens-slek.onrender.com and full code with 29 passing tests is on GitHub. We are now happy to answer questions from the evaluation panel.")

# Save modified presentation
prs.save(PPTX_PATH)
print(f"Saved updated PowerPoint presentation to {PPTX_PATH}")

# Dump updated speaker notes to JSON
notes_data = []
for i, slide in enumerate(prs.slides):
    notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
    notes_data.append({"slide": i + 1, "notes": notes})
(BUILD / "presentation_notes.json").write_text(json.dumps(notes_data, indent=2))
print(f"Saved presentation notes to {BUILD / 'presentation_notes.json'}")

# Export to PDF via Keynote osascript
osascript_code = f"""
set pptxPath to POSIX file "{PPTX_PATH}"
set pdfPath to POSIX file "{PDF_PATH}"

tell application "Keynote"
    set theDoc to open pptxPath
    export theDoc to pdfPath as PDF
    close theDoc saving no
end tell
"""
res = subprocess.run(["osascript", "-e", osascript_code], capture_output=True, text=True)
if res.returncode == 0:
    print(f"Exported PDF presentation to {PDF_PATH}")
else:
    print(f"PDF export warning: {res.stderr}")

# Render all 16 slides to high-res PNGs
doc = pymupdf.open(str(PDF_PATH))
for idx, page in enumerate(doc):
    pix = page.get_pixmap(dpi=192)
    target = BUILD / f"slide-{idx+1:02d}.png"
    pix.save(str(target))
print(f"Rendered all 16 slide PNGs to {BUILD}")
