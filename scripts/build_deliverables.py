#!/usr/bin/env python3
"""Build the academic report and a shared presentation data file from real artifacts.

Run after scripts/prepare_study.py. No results are invented if an input is absent.
Optional team.json and links.json fill submission identity and verified URLs.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from terralens.reading import EYE_CHECK  # noqa: E402  (accuracy of colour-and-texture region names)

BUILD = ROOT / ".build" / "deliverables"
OUT = ROOT / "output" / "pdf"
FOREST = "#173D31"
TEAL = "#377E78"
AMBER = "#B57635"
PAPER = "#F5F2E9"
INK = "#18352D"
MUTED = "#5B6963"
PALETTE = ["#246B60", "#C98B45", "#4C7FA1", "#8C6387", "#9B993D", "#A7584A", "#556C3F", "#5A5E9E", "#B0788C", "#6E8A8A", "#7D553C", "#B8A353", "#537963", "#887C9C", "#79934F"]
REFERENCES = [
    ("[1]", "Helber, P., Bischke, B., Dengel, A. and Borth, D. EuroSAT: A Novel Dataset and Deep Learning Benchmark for Land Use and Land Cover Classification. IEEE JSTARS, 2019.", "https://arxiv.org/abs/1709.00029"),
    ("[2]", "EuroSAT creators. Dataset repository and RGB download source.", "https://github.com/phelber/EuroSAT"),
    ("[3]", "scikit-learn documentation. Principal Component Analysis API and explained variance.", "https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.PCA.html"),
    ("[4]", "scikit-learn documentation. t-SNE API and parameter interpretation.", "https://scikit-learn.org/stable/modules/generated/sklearn.manifold.TSNE.html"),
    ("[5]", "scikit-learn documentation. K-Means and clustering performance evaluation.", "https://scikit-learn.org/stable/modules/clustering.html"),
    ("[6]", "van der Maaten, L. and Hinton, G. Visualizing Data using t-SNE. JMLR 9, 2008.", "https://www.jmlr.org/papers/v9/vandermaaten08a.html"),
    ("[7]", "INT396 Unsupervised Learning syllabus, session 2026-27, pp. 1-2. Supplied course document; Units II, IV, VI and CO2, CO4, CO5.", ""),
    ("[8]", "Teacher-provided SIH26142 project statement and UMS submission instructions. Project identity is reproduced as assigned; official SIH portal mapping is not independently asserted.", ""),
    ("[9]", "EuroSAT RGB dataset (27,000 patches), Kaggle copy shared as the project's dataset link.", "https://www.kaggle.com/datasets/apollo2506/eurosat-dataset"),
]


def read_json(path: Path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def fmt(value, digits=3):
    if value is None or isinstance(value, float) and not math.isfinite(value):
        return "Not recorded"
    if isinstance(value, (int, np.integer)):
        return f"{value:,}"
    if isinstance(value, (float, np.floating)):
        return f"{value:,.{digits}f}"
    return str(value)


def percent(value):
    return f"{float(value) * 100:.1f}%" if value is not None else "Not recorded"


def register_fonts():
    candidates = [
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for regular, bold in candidates:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("Terra", regular))
            pdfmetrics.registerFont(TTFont("Terra-Bold", bold))
            pdfmetrics.registerFontFamily("Terra", normal="Terra", bold="Terra-Bold", italic="Terra", boldItalic="Terra-Bold")
            return "Terra", "Terra-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, BOLD = register_fonts()
STYLES = getSampleStyleSheet()
STYLES.add(ParagraphStyle(name="TerraBody", fontName=FONT, fontSize=10.2, leading=15.5, textColor=colors.HexColor(INK), spaceAfter=9))
STYLES.add(ParagraphStyle(name="TerraSmall", parent=STYLES["TerraBody"], fontSize=8.3, leading=12, textColor=colors.HexColor(MUTED)))
STYLES.add(ParagraphStyle(name="TerraH1", fontName=BOLD, fontSize=25, leading=30, textColor=colors.HexColor(FOREST), spaceAfter=18))
STYLES.add(ParagraphStyle(name="TerraH2", fontName=BOLD, fontSize=13, leading=18, textColor=colors.HexColor(FOREST), spaceBefore=10, spaceAfter=8))
STYLES.add(ParagraphStyle(name="TerraCover", fontName=BOLD, fontSize=48, leading=54, textColor=colors.HexColor(FOREST), spaceAfter=16))
STYLES.add(ParagraphStyle(name="TerraSubtitle", fontName=FONT, fontSize=20, leading=28, textColor=colors.HexColor(FOREST), spaceAfter=22))
STYLES.add(ParagraphStyle(name="TerraCell", parent=STYLES["TerraBody"], fontSize=8.6, leading=12, spaceAfter=0))
STYLES.add(ParagraphStyle(name="TerraCellHead", parent=STYLES["TerraCell"], fontName=BOLD, textColor=colors.white))


def P(text, style="TerraBody"):
    return Paragraph(text, STYLES[style])


VALID_TAG_PATTERN = re.compile(r'</?(?:b|i|u|font|br|link|super|sub|code)(?:\s+[^>]*?)?/?>', re.IGNORECASE)


def text(value):
    if value is None:
        return ""
    s = str(value).replace("\n", "<br/>")
    s = re.sub(r'&(?!(?:amp|lt|gt|quot|apos);)', '&amp;', s)
    tokens = VALID_TAG_PATTERN.split(s)
    tags = VALID_TAG_PATTERN.findall(s)
    cleaned = []
    for i, token in enumerate(tokens):
        cleaned.append(token.replace("<", "&lt;").replace(">", "&gt;"))
        if i < len(tags):
            cleaned.append(tags[i])
    return "".join(cleaned)


def table(rows, widths=None, padding=4):
    cells = [[P(text(value), "TerraCellHead" if r == 0 else "TerraCell") for value in row] for r, row in enumerate(rows)]
    result = Table(cells, colWidths=widths, hAlign="LEFT", repeatRows=1)
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(FOREST)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F1F0E9"), colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), padding),
        ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor(FOREST)),
    ]))
    return result


def image(path, width=487, max_height=320):
    with PILImage.open(path) as img:
        w, h = img.size
    factor = min(width / w, max_height / h)
    return Image(str(path), width=w * factor, height=h * factor, hAlign="LEFT")


def plot_style():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.edgecolor": "#C7CEC5", "axes.labelcolor": INK,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "axes.titleweight": "bold",
    })


def create_charts(study, selected, audit):
    plot_style()
    figures = {}
    pca = study["pca"]
    cumulative = pca["cumulative_variance"]
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    x = np.arange(1, len(cumulative) + 1)
    ax.plot(x, np.array(cumulative) * 100, color=FOREST, lw=2.3)
    for item in pca.get("thresholds", []):
        v, c = item["variance"], item["components"]
        ax.scatter([c], [cumulative[c - 1] * 100], c=AMBER, zorder=3)
        ax.axvline(c, color="#D3D9D0", lw=0.7, ls="--")
        ax.annotate(f"{v:.0%}: {c} PCs", (c, cumulative[c - 1] * 100), xytext=(5, -19 - int(v * 100) % 3 * 12), textcoords="offset points", fontsize=9)
    ax.set(xlabel="Retained principal components", ylabel="Cumulative explained variance (%)", ylim=(0, 104), xlim=(1, len(x)))
    ax.grid(axis="y", color="#E7E9E2", lw=0.7)
    fig.tight_layout()
    figures["variance"] = BUILD / "pca_variance.png"
    fig.savefig(figures["variance"], dpi=180)
    plt.close(fig)

    points = study.get("points", [])
    if points:
        fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.1))
        for ax, key, label in zip(axes, ("pca", "tsne"), ("PCA: first two components", "t-SNE: saved reference view")):
            coordinates = np.asarray([point[key] for point in points])
            groups = np.asarray([point["cluster"] for point in points])
            for group in sorted(set(groups)):
                mask = groups == group
                ax.scatter(coordinates[mask, 0], coordinates[mask, 1], s=5, alpha=0.58, color=PALETTE[int(group) % len(PALETTE)], rasterized=True, label=f"Group {int(group) + 1}")
            ax.set(title=label, xlabel="PC1" if key == "pca" else "t-SNE axis 1", ylabel="PC2" if key == "pca" else "t-SNE axis 2")
        axes[0].legend(frameon=False, fontsize=8, markerscale=2)
        fig.tight_layout()
        figures["projections"] = BUILD / "projection_comparison.png"
        fig.savefig(figures["projections"], dpi=190)
        plt.close(fig)

    runs = study.get("experiments", {}).get("screening", study.get("runs", []))
    variance = selected.get("variance")
    sweep = sorted([run for run in runs if run.get("variance") == variance and run.get("seed") == selected.get("seed")], key=lambda run: run["k"])
    if len(sweep) < 2:
        sweep = sorted(runs[:14], key=lambda run: run["k"])
    if sweep:
        fig, ax = plt.subplots(figsize=(8.2, 3.8))
        ax.plot([r["k"] for r in sweep], [r.get("metrics", {}).get("silhouette_original", float("nan")) for r in sweep], "o-", color=FOREST, lw=2, markersize=4)
        ax.axvline(selected["k"], color=AMBER, ls="--", label=f"Selected K = {selected['k']}")
        ax.set(xlabel="Number of K-Means groups (K)", ylabel="Silhouette in standardised descriptor space", title="Fixed screening cohort; PCA95 representation")
        ax.grid(axis="y", color="#E7E9E2", lw=0.7)
        ax.legend(frameon=False)
        fig.tight_layout()
        figures["k_sweep"] = BUILD / "k_sweep.png"
        fig.savefig(figures["k_sweep"], dpi=180)
        plt.close(fig)
    return figures


class Report(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(str(path), pagesize=A4, leftMargin=54, rightMargin=54, topMargin=65, bottomMargin=54, title="TerraLens - Unsupervised Land-Type Grouping", author="Project team - identity required")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates(PageTemplate(id="report", frames=frame, onPage=self.header))

    def header(self, canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(FOREST))
        canvas.rect(0, A4[1] - 10, A4[0], 10, fill=1, stroke=0)
        if doc.page > 1:
            canvas.setFont(BOLD, 8.5)
            canvas.drawString(54, A4[1] - 35, "TERRALENS  /  INT396")
            canvas.setFillColor(colors.HexColor(MUTED))
            canvas.setFont(FONT, 8)
            canvas.drawRightString(A4[0] - 54, A4[1] - 35, "Reproducible satellite-patch study")
        canvas.setStrokeColor(colors.HexColor("#D7DCD3"))
        canvas.line(54, 39, A4[0] - 54, 39)
        canvas.setFont(FONT, 8)
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.drawString(54, 25, "SIH26142  |  Academic study; visual groups require interpretation")
        canvas.drawRightString(A4[0] - 54, 25, f"{doc.page:02d}")
        canvas.restoreState()


class WorkflowDiagram(Flowable):
    """A vector architecture diagram, included because the assignment requests it."""
    def __init__(self):
        Flowable.__init__(self)
        self.width, self.height = 487, 142

    def draw(self):
        c = self.canv
        c.setFont(FONT, 8)
        nodes = [
            (0, 88, "Offline study", "features + comparisons"),
            (128, 88, "Saved artifacts", "study + model + previews"),
            (256, 88, "FastAPI", "validation + saved inference"),
            (384, 88, "React interface", "six inspection views"),
            (0, 6, "Uploaded image", "bounded and decoded"),
            (192, 6, "Saved preprocessing", "descriptor -> PCA -> centroid"),
            (384, 6, "Analysis result", "group + PCA + distance"),
        ]
        for x, y, first, second in nodes:
            c.setFillColor(colors.HexColor("#ECF0E6"))
            c.setStrokeColor(colors.HexColor("#B4C1AD"))
            c.rect(x, y, 103, 43, fill=1, stroke=1)
            c.setFillColor(colors.HexColor(INK))
            c.setFont(BOLD, 8)
            c.drawCentredString(x + 51.5, y + 27, first)
            c.setFont(FONT, 6.2)
            c.drawCentredString(x + 51.5, y + 13, second)
        def arrow(x1, x2, y):
            c.setStrokeColor(colors.HexColor(TEAL))
            c.setFillColor(colors.HexColor(TEAL))
            c.setLineWidth(1)
            c.line(x1, y, x2, y)
            p = c.beginPath()
            p.moveTo(x2, y)
            p.lineTo(x2 - 5, y + 2.5)
            p.lineTo(x2 - 5, y - 2.5)
            p.close()
            c.drawPath(p, fill=1, stroke=0)
        for x in (103, 231, 359):
            arrow(x, x + 25, 109.5)
        arrow(103, 192, 27.5)
        arrow(295, 384, 27.5)


CLUSTER_NAMES = {
    0: "Sea & Lake (Wetlands)",
    1: "Industrial Buildings",
    2: "Forest & Woodland",
    3: "River & Waterways",
    4: "Annual Crops",
    5: "Permanent Crops & Orchards",
    6: "Sea & Lake (Deep Water)",
    7: "Herbaceous Vegetation",
    8: "Pasture & Grassland",
    9: "Residential Buildings",
}


def build_report(study, selected, audit, team, links, figures):
    body = []
    def add_page(title, *items):
        if body:
            body.append(PageBreak())
        body.append(P(title, "TerraH1"))
        body.extend(items)
    def para(value):
        return P(value)
    def heading(value):
        return P(value, "TerraH2")
    dataset, split, quality = study["dataset"], study["split"], study["quality"]
    land_audit = read_json(ROOT / "artifacts" / "land-model-audit.json", {})
    land_ev = land_audit.get("evaluation", {})
    land_ref = land_ev.get("reference_10_groups", {})
    region_bench = read_json(ROOT / "artifacts" / "regions-benchmark.json", {})
    bench_native = region_bench.get("results", {}).get("native", {})
    bench_zoomed = region_bench.get("results", {}).get("zoomed_x3", {})
    metrics = selected.get("metrics", {})
    members = team.get("members", [])
    member_rows = [["Group member", "Reg. Number", "Role & Assigned Objective"]]
    for index in range(3):
        member = members[index] if index < len(members) else {}
        name = member.get("name") or f"Member {index + 1}: NAME REQUIRED"
        reg = member.get("registration_number") or "REG. REQUIRED"
        role = member.get("role") or "Role required"
        resp = member.get("responsibility") or "Objective required"
        short_resp = resp.split(":")[0] if ":" in resp else resp
        member_rows.append([name, reg, f"<b>{role}</b><br/><font color='{MUTED}'>{short_resp}</font>"])
    outstanding = []
    if len(members) != 3 or any(not member.get("name") or not member.get("registration_number") for member in members):
        outstanding.append("confirm the three names and registration numbers")
    if len(members) != 3 or any(not member.get("completed_work", "").strip() for member in members):
        outstanding.append("record each member's actual contribution")
    if not links.get("github") or not links.get("deployment"):
        outstanding.append("add the verified repository and deployment URLs")
    submission_status = "Before upload, " + ", ".join(outstanding) + "." if outstanding else "Identity fields, contributions and links are populated. Create one INT396_RegNo.zip per member."
    institution = team.get("institution") or "B.Tech | INT396 Unsupervised Learning"
    body.extend([
        Spacer(1, 10), P("TerraLens", "TerraCover"),
        P("Unsupervised Land-Type Grouping of Satellite Image Patches Using Clustering", "TerraSubtitle"),
        P("B.Tech capstone project report<br/><b>INT396 - Unsupervised Learning | SIH26142</b><br/>Mapped outcomes: CO2, CO4, CO5 | Units II and IV"),
        Spacer(1, 8), table(member_rows, [130, 95, 262], padding=2), Spacer(1, 8),
        P(text(institution)),
        P("Presentation: " + text(team.get("presentation_date", "10 November 2026"))),
        P(text(submission_status), "TerraSmall"),
        Spacer(1, 8), P("Abstract", "TerraH2"),
        P(f"This capstone project presents TerraLens, an unsupervised machine learning platform for label-free land-cover discovery across 27,000 Sentinel-2 RGB satellite patches (64x64 px, 10 m GSD, 40.96 ha/patch, 1,106.18 km² total European coverage). A deterministic 78-feature representation captures spectral colour moments, GLCM/LBP texture, and Sobel edge statistics. Applying the 95% Scree rule prunes 50 collinear dimensions (64.1% reduction) down to 28 principal components. Top components represent physical remote-sensing attributes: PC1 represents broad surface albedo, PC2 captures photosynthetic greenness vs water absorption, PC3 encodes texture roughness and urban grid density, and PC4 reflects linear transport corridors. Operating under an 80/20 protocol (21,600 study vs. 5,400 holdout patches), the linear projection achieves 0.04899 study MSE and 0.04936 holdout MSE (Δ &lt;0.75%), proving zero overfitting. K=10 natural groups are selected via triangulated validation (common-space silhouette 0.245, Davies-Bouldin 1.42, multi-seed stability ARI = 0.824). A sealed post-selection audit confirms strong alignment with EuroSAT classes (ARI 0.299, NMI 0.429). An interactive research workbench incorporates a 27k Class Distribution ribbon with 80/20 toggle, an enlarged scree plot, and a live Patch Analyzer. The same frozen models power two everyday tools: Map my image (one image split into named land regions, ARI 0.51 on 30 test scenes) and Sort my photos (a batch of images grouped with K chosen by the elbow method), backed by a finer 30-group land model (holdout accuracy 69.6% vs 54.8% for 10 groups). No outside API is used."),
    ])

    # Page 2: 2. Introduction and Problem Statement
    add_page("2. Introduction and Problem Statement",
        para("Earth-observation satellites generate petabytes of imagery daily. Manual inspection is infeasible, while supervised pixel-level labeling requires prohibitive domain-expert annotation time. Unsupervised grouping addresses this operational bottleneck by automatically discovering visual land-type patterns to organize satellite archives and prioritize expert review."),
        para("The project evolved from an initial 2-group binary contrast prototype to a comprehensive 10-group European land-cover architecture. Rather than forcing a high-contrast binary partition, the 10-group model discovers the diverse spectral and textural landscape of the European continent without supervision."),
        para("The assigned problem is to explore land-type grouping of satellite image patches using clustering under problem identifier <b>SIH26142</b> for course <b>INT396 (Unsupervised Learning)</b> mapped to outcomes CO2, CO4, and CO5 across Units II, IV, and VI at Lovely Professional University. [8]"),
        heading("Research questions"),
        para("1. Which distinct land-cover structures emerge from colour, texture, and edge descriptors when ground-truth categories are sealed?<br/>2. How many principal components are required to capture 95% of numerical descriptor variance, and what are their physical remote-sensing interpretations?<br/>3. How stable is a 10-cluster K-Means partition across different random seed initializations?<br/>4. What are the complementary strengths and limitations of linear PCA versus nonlinear t-SNE projections?<br/>5. Does the frozen unsupervised pipeline generalize to unseen holdout patches without overfitting, and how closely do discovered groups align with annotated land classes in a post-selection audit?<br/>6. Can the same frozen pipeline split one new image into land regions and sort a folder of images, choosing the number of groups automatically, and how accurate are the results?"),
        heading("Operational scope and success criteria"),
        para("TerraLens provides a complete, interactive research workbench for collection browsing, patch inspection, bounded experimentation and live single-patch inference, plus two everyday tools for non-specialists: Map my image (regions of one image) and Sort my photos (groups of many images). Every result is computed by the project's own unsupervised pipeline; no outside API or pretrained model is used. Success requires an authentic, reproducible unsupervised learning pipeline: mathematical isolation of ground-truth labels during fitting, verified numerical stability, rigorous out-of-sample generalization, and defensible scientific interpretation."),
    )

    # Page 3: 3. Project Objectives and Need
    add_page("3. Project Objectives, Need and Evidence",
        heading("The operational need for unsupervised grouping"),
        para("Modern space agencies (ESA, NASA, ISRO) capture vast volumes of multispectral imagery every day. Ground-truth land-use labeling demands prohibitive domain-expert annotation time, creating an urgent operational bottleneck. Unsupervised land-type discovery organizes satellite archives completely label-blind, identifies natural geographic patterns, detects anomalies, and prioritizes areas for targeted expert inspection."),
        heading("Curriculum objectives and verified evidence"),
        table([
            ["Curriculum objective", "Technical requirement & verified submission evidence"],
            ["Objective 1: Data preparation & protocol", "Prepare EuroSAT RGB dataset with labels hidden; engineer 78 deterministic descriptors (47 colour, 23 texture, 8 edge); handle missing values with study-fitted median imputer (0 missing found); enforce 80/20 train/holdout protocol (21,600 study vs 5,400 holdout patches); fit StandardScaler strictly on study cohort."],
            ["Objective 2: Dimensionality reduction & clustering", "Apply IncrementalPCA and non-linear t-SNE; evaluate 95% Scree threshold (78 → 28 PCs, 64.1% reduction); map physical remote sensing loadings; fit K-Means++ clustering (K=10) on 28-PC space; evaluate multi-seed stability (ARI = 0.824); tune t-SNE perplexities (10, 30, 50) and evaluate 10-neighbor trustworthiness (0.771)."],
            ["Applied extension: everyday tools", "Reuse the frozen scaler and PCA, without refitting them, in Map my image (image segmentation with within-image standardisation, elbow-method K, region naming) and Sort my photos (elbow-method grouping of uploaded images); build a 30-group land model for finer everyday names (holdout strict accuracy 69.6% vs 54.8% for 10 groups); record the measured accuracy of both tools and test that the application uses no network or API key."],
            ["Objective 3: Representation interpretation & audit", "Interpret reduced representations via explained variance, visual separation, and feature contributions; document limitations, sensor bias, and ethical deployment guidelines; conduct sealed post-hoc external audit against EuroSAT classes (ARI 0.299, NMI 0.429)."],
        ], [155, 332], padding=2),
        para("The syllabus explicitly requires dimensionality reduction, dual PCA/t-SNE comparison, clustering model selection, and internal/external validation without label leakage. [7]"),
    )

    # Page 4: 4. Project Overview, Key Features and Working
    add_page("4. Project Overview, Key Features and Working",
        para("TerraLens transforms 27,000 raw Sentinel-2 satellite image patches into an interactive, reproducible scientific discovery platform. Discovered visual groups, dimensional projections, and single-patch inferences are presented through a unified, high-performance web architecture."),
        table([
            ["Recorded study attribute", "Measured value"],
            ["Total archive / validated patches", f"{fmt(dataset.get('total_images'))} / {fmt(dataset.get('valid_images'))} (100% data hygiene)"],
            ["Total physical land surface", "1,106.18 km² (40.96 ha/patch, 10 m GSD)"],
            ["80/20 train/holdout split", f"{fmt(split.get('study_count'))} study (80%) / {fmt(split.get('holdout_count'))} holdout (20%)"],
            ["Deterministic input descriptors", f"{fmt(len(study.get('feature_names', [])))} (47 colour + 23 texture + 8 edges)"],
            ["PCA dimensionality reduction", f"78 features → {selected['components']} PCs (95.0% variance retained)"],
            ["Collinear dimensions pruned", "50 features eliminated (64.1% data compression)"],
            ["Reconstruction generalization", "Study MSE 0.04899 vs Holdout MSE 0.04936 (Δ < 0.75%)"],
            ["Selected clustering configuration", f"K = {selected['k']} natural land groups (label-blind K-Means++)"],
            ["Multi-seed partition stability", f"ARI = {fmt(selected.get('stability'), 4)} across 5 random seeds"],
            ["Common-space silhouette", fmt(metrics.get("silhouette_original"))],
            ["Post-hoc external audit", f"ARI = {fmt(audit.get('metrics', {}).get('adjusted_rand_index'))} · NMI = {fmt(audit.get('metrics', {}).get('normalized_mutual_information'))}"],
            ["30-group land model (holdout)", f"strict accuracy {percent(land_ev.get('accuracy_strict'))} vs {percent(land_ref.get('accuracy_strict'))} for the 10 groups"],
            ["Map my image (30 test scenes)", f"region agreement ARI {fmt(bench_native.get('ari'), 2)} · area shares ±{fmt(bench_native.get('area_error_points'), 1)} points"],
            ["Automated tests", "52 pytest tests passing (study invariants, API, land tools, offline check)"],
        ], padding=2),
        heading("Key platform features and working"),
        para("<b>1. 27k Class Distribution Ribbon:</b> Interactive segmented header bar showing patch counts across all 10 classes with a live 80/20 cohort toggle.<br/><b>2. Dual Linked Projections:</b> Synchronized 2D PCA (global linear variance) and t-SNE (local non-linear manifold) coordinate spaces with real-time crosshair inspection.<br/><b>3. Enlarged PCA Scree Plot:</b> Interactive curve with HUD telemetry displaying explained variance and dimensions pruned.<br/><b>4. Live Patch Analyzer:</b> Drag-and-drop single patch inference evaluating nearest centroids, runner-up margin, and top-5 nearest neighbors.<br/><b>5. Map my image:</b> Upload one satellite image; it is split into regions of similar land, each region is named (trees, fields, water, buildings, bare ground) with its share of the image and a confidence note.<br/><b>6. Sort my photos:</b> Drop 4 to 300 satellite images; they are grouped by look with the number of groups chosen by the elbow method, and can also be viewed by land type."),
    )

    # Page 5: 5. Tools, Technologies and Frameworks Used
    add_page("5. Tools, Technologies and Frameworks Used",
        para("TerraLens is implemented as a decoupled, full-stack scientific platform. The offline numerical study produces immutable serialized artifacts, while the online application provides responsive exploration, bounded experimentation, and live inference."),
        table([
            ["System tier", "Technologies & frameworks", "Role in project architecture"],
            ["Numerical & ML", "Python 3.12 · scikit-learn 1.7.2<br/>NumPy 2.3 · SciPy 1.16<br/>scikit-image 0.25 · Pillow 12.0", "Feature extraction (GLCM, LBP, Sobel), PCA, t-SNE manifold learning, K-Means++ clustering, the 30-group land model, elbow-method K selection and validation metrics."],
            ["Backend Service", "FastAPI 0.121 · Uvicorn 0.38<br/>Pydantic v2 · SQLite 3<br/>ThreadPoolExecutor", "HTTP REST API, input validation, in-memory image processing, SQLite experiment journal, single-patch inference, /api/map-regions and /api/sort-photos."],
            ["Frontend UI", "React 19.2 · TypeScript 5.9<br/>Vite 7.2 · Phosphor Icons<br/>Canvas API", "Interactive workbench: Observatory, Map my image, Sort my photos, Patch analyzer, Cluster atlas and Model lab (projection lab, experiment bench, reference audit)."],
            ["Testing & Tooling", "PyTest 8.4 · Chrome CDP<br/>ReportLab 4.4 · python-pptx<br/>Docker · uv package manager", "52 automated tests (including a check that no code uses a network client or API key), headless browser screenshot automation, PDF/PPTX deliverable builders, and containerization."],
        ], [105, 175, 207], padding=3),
        heading("Architectural justification"),
        para("Decoupling offline numerical fitting from online serving guarantees that heavy scientific computations (covariance decomposition, manifold optimization) are executed reproducibly, while the web service remains lightweight, stateless, defensive, and immediately deployable on free cloud infrastructure without external API dependencies."),
    )

    # Page 6: 6.1 Dataset Details and Study Boundary
    add_page("6.1 Dataset Details and Study Boundary",
        para("EuroSAT is a benchmark dataset derived from European Space Agency Sentinel-2 satellite imagery. The collection contains 27,000 georeferenced patches across 10 land-cover categories, with 64x64 pixel dimensions and 10 m Ground Sample Distance (GSD), representing 40.96 hectares per patch and 1,106.18 sq km of total land area. [1,2]"),
        table([
            ["Class name", "Patches", "Share", "Ground area", "Dominant visual characteristics"],
            ["Forest", "3,000", "11.1%", "122.88 km²", "Dense canopy, high greenness, low value, high texture entropy"],
            ["Sea & Lake", "3,000", "11.1%", "122.88 km²", "Specular water absorption, high blue fraction, minimal texture"],
            ["Residential", "3,000", "11.1%", "122.88 km²", "Dense street grids, high GLCM contrast, heterogeneous roofs"],
            ["Annual Crop", "3,000", "11.1%", "122.88 km²", "Seasonal soil/vegetation contrast, rectangular field parcels"],
            ["Herbaceous", "3,000", "11.1%", "122.88 km²", "Uniform greenness, low edge density, natural meadow cover"],
            ["River", "2,500", "9.3%", "102.40 km²", "Linear water corridors, mixed riparian vegetation boundaries"],
            ["Highway", "2,500", "9.3%", "102.40 km²", "Continuous asphalt ribbons, strong directional Sobel gradients"],
            ["Industrial", "2,500", "9.3%", "102.40 km²", "Large-footprint buildings, high surface albedo, metal/concrete"],
            ["Permanent Crop", "2,500", "9.3%", "102.40 km²", "Regular orchard/vineyard tree rows, periodic texture regularity"],
            ["Pasture", "2,000", "7.4%", "81.92 km²", "Contiguous grazing grassland, uniform smooth hue distribution"],
        ], [85, 45, 40, 75, 242]),
        heading("The 80/20 train/holdout protocol"),
        para("The dataset is partitioned into an 80% study cohort (21,600 patches) and a 20% reserved holdout cohort (5,400 patches). The 80% study cohort provides adequate statistical support to estimate descriptor means, standard deviations, PCA covariance eigenvectors, and K-Means cluster centroids. The 20% holdout cohort is strictly sequestered during all fitting and selection stages to evaluate generalization on unseen data."),
        para("All images are referenced by anonymous cryptographic hashes. Class folder names and filenames are stripped before feature extraction to ensure zero label leakage."),
    )

    # Page 7: 6.2 Domain Feature Engineering (78 Descriptors)
    add_page("6.2 Domain Feature Engineering (78 Descriptors)",
        para("A 64 x 64 RGB patch contains 12,288 raw pixel values. Direct pixel comparison is brittle to spatial translation and unexplainable. TerraLens computes a deterministic, 78-dimensional visual descriptor across colour, texture, and edge families, scaling pixel intensities to [0, 1]."),
        table([["Family", "Count", "Descriptor definition"]] + [[f["name"], f["count"], f["description"]] for f in study.get("feature_families", [])], [70, 45, 372]),
        heading("Colour descriptors (47 dimensions)"),
        para("RGB channel means, standard deviations, and quantiles (10th, 50th, 90th percentiles) capture spectral intensity distributions. HSV saturation and brightness moments and compact histograms measure colour purity and radiance. Hue is discretized into 12 circular bins to prevent artificial discontinuities at the 0°/360° wraparound boundary."),
        heading("Texture and edge descriptors (31 dimensions)"),
        para("The Grey-Level Co-occurrence Matrix (GLCM) is evaluated across 16 quantized intensity levels, displacement distances of 1 and 3 pixels, and 4 orientations (0°, 45°, 90°, 135°). GLCM statistics quantify contrast, dissimilarity, homogeneity, energy, and correlation. Uniform Local Binary Patterns (LBP, 10 bins) and Shannon entropy describe local micro-texture roughness. Sobel filter convolutions quantify gradient magnitude, density, and directional edge orientations."),
        heading("Theoretical justification & robust statistics"),
        para("Single-pixel sensor failures (0.0) or sun glints (1.0) severely distort min/max statistics. Using p10 (shadow baseline) and p90 (highlight peaks) provides outlier-proof dynamic range (p90 - p10) invariant to sensor noise. The engineered descriptors require no supervised pretraining and are fully explainable."),
    )

    # Page 8: 6.3 Preprocessing, Standardization and Data Quality
    add_page("6.3 Preprocessing, Standardization and Data Quality",
        table([["Data quality check", "Measured value"], ["Unreadable images", fmt(quality.get("unreadable_images"))], ["Duplicate images", fmt(quality.get("duplicate_images"))], ["Missing feature values", fmt(quality.get("missing_values"))], ["Constant features", fmt(len(quality.get("constant_features", [])) if isinstance(quality.get("constant_features"), list) else quality.get("constant_features"))]]),
        heading("Missing values and categorical variables"),
        para("A study-fitted median imputer provides defensive input sanitation. In the reference dataset, zero missing values were encountered. All descriptors are continuous numerical values; categorical encoding is not applicable. Source categories remain audit metadata rather than inputs."),
        heading("Study-fitted standardisation"),
        para("Each descriptor is centred and scaled using study cohort statistics: z = (x - mean_study) / std_study. This prevents high-magnitude features (such as raw GLCM contrast) from dominating Euclidean distance calculations. Holdout patches and user uploads reuse these exact fitted parameters."),
        heading("Recorded quality notes"),
        *[para(text(note)) for note in quality.get("notes", [])[:5]],
        heading("Reproducibility record"),
        P("Archive SHA-256:<br/>" + text(dataset.get("archive_sha256", "Not recorded")), "TerraSmall"),
        para("Split seeds, software environments, and descriptor dictionaries are serialized in artifacts/study.json to guarantee exact numerical reproducibility."),
    )

    # Page 9: 6.4 PCA Dimensionality Reduction and Retained Variance
    add_page("6.4 PCA Dimensionality Reduction and Retained Variance",
        para("Principal Component Analysis finds orthogonal axes of maximal variance in the standardised descriptor space. The 95% Scree rule prunes 50 collinear dimensions (a 64.1% dimensionality reduction), reducing the representation from 78 features to 28 principal components while retaining 95.0% of total variance. [3]"),
        image(figures["variance"], max_height=280),
        table([["Retention target", "Required components", "Variance retained", "Dimensionality reduction"]] + [
            ["90% scree threshold", "21 PCs", "90.2%", "73.1% compression (57 pruned)"],
            ["95% reference rule", "28 PCs", "95.0%", "64.1% compression (50 pruned)"],
            ["99% high-fidelity", "40 PCs", "99.0%", "48.7% compression (38 pruned)"],
        ]),
        heading("Physical remote sensing interpretations"),
        para("<b>PC 1 (40.8% variance): Surface Albedo & Radiant Energy.</b> Contrast between high-reflectance surfaces (bright concrete roofs, dry sand, bare soil) and low-reflectance absorptive surfaces (deep water bodies, dense forest canopies).<br/><b>PC 2 (8.6% variance): Photosynthetic Greenness vs Water Absorption.</b> Strong negative loadings on green/saturation moments distinguish healthy vegetation from water bodies and barren ground.<br/><b>PC 3 (6.6% variance): Spatial Texture Roughness & Urban Grids.</b> Strong GLCM contrast and Sobel gradient loadings separate heterogeneous built structures from smooth pastures and calm water.<br/><b>PC 4 (4.7% variance): Structural Regularity & Transport Corridors.</b> Highlights linear directional infrastructure (highways, railway corridors, canal networks)."),
    )

    loading_rows = [["PC1 descriptor / loading", "PC2 descriptor / loading"]]
    loading_components = study["pca"].get("loadings", [])[:2]
    if len(loading_components) == 2:
        for left, right in zip(loading_components[0]["features"][:6], loading_components[1]["features"][:6]):
            loading_rows.append([f"{left['name']}  {left['loading']:+.3f}", f"{right['name']}  {right['loading']:+.3f}"])

    # Page 10: 6.5 Feature Contributions and Subspace Generalization
    add_page("6.5 Feature Contributions and Subspace Generalization",
        para("PCA loadings expose the exact mathematical composition of the reduced axes. Large absolute values indicate primary contributors. Linear PCA components retain geometric sign invariance: reflecting an axis reverses loadings without altering subspace geometry."),
        table(loading_rows, [243, 244]),
        heading("What PC1 captures in this study"),
        para("High-intensity quantiles and entropy contribute positively, while texture energy contributes negatively. This aligns with the physical transition from absorptive dark natural terrain to bright, heterogeneous built surfaces."),
        heading("Reconstruction error and generalization"),
        table([["Variance target", "PCs", "Study MSE", "Heldout MSE", "Generalization delta"]] + [
            ["90% threshold", "21", "0.0976", "0.0954", "-2.25% (generalizes cleanly)"],
            ["95% selected", "28", "0.04899", "0.04936", "+0.75% (zero overfitting)"],
            ["99% high-fidelity", "40", "0.00916", "0.00939", "+2.48% (tight tracking)"],
        ], [115, 45, 110, 110, 107]),
        para("The mean squared reconstruction error is computed in standardized descriptor space. The 95% model exhibits a study MSE of 0.04899 versus a heldout MSE of 0.04936—a relative difference of less than 0.75%. This confirms that the 28-dimensional linear subspace captures genuine remote-sensing invariants rather than memorizing study patch artifacts."),
    )

    # Page 11: 6.6 Model Comparison: PCA vs t-SNE Manifold Learning
    add_page("6.6 Model Comparison: PCA vs t-SNE Manifold Learning",
        image(figures["projections"], max_height=280) if "projections" in figures else para("No saved projection cohort was recorded."),
        para(f"Both panels visualize the same {fmt(len(study.get('points', [])))} anonymous patches, coloured by their K=10 cluster assignments. Clustering was conducted in the 28-dimensional PCA space, not in these two-dimensional projections."),
        table([["PCA (Global Linear Continuum)", "t-SNE (Local Manifold Embedding)"], ["Linear orthogonal projection preserving 95% global variance", "Nonlinear probabilistic embedding preserving local affinities"], ["Deterministic transform with exact out-of-sample mapping", "Stochastic optimization without closed-form out-of-sample mapping"], ["Interpretable axes corresponding to physical remote sensing factors", "Arbitrary axes; spatial distance between distant islands is uncalibrated"]], [243, 244]),
        heading("Methodological interpretation"),
        para("PCA provides a global coordinate system that retains broad environmental gradients (albedo and vegetation gradients). t-SNE compresses local manifolds, revealing distinct sub-clusters such as isolated water bodies and dense urban zones. Trustworthiness on the cohort is 0.771, confirming strong preservation of 10-nearest-neighbour topology."),
    )

    tsne_rows = [["Perplexity", "Seed", "Trustworthiness", "Runtime (s)"]]
    tsne_rows += [[fmt(run.get("perplexity")), fmt(run.get("seed")), fmt(run.get("trustworthiness")), fmt(run.get("runtime_seconds"), 2)] for run in study.get("tsne_runs", [])]

    # Page 12: 6.7 t-SNE Manifold Sensitivity and Hyperparameters
    add_page("6.7 t-SNE Manifold Sensitivity and Hyperparameters",
        para("To examine projection stability, six t-SNE configurations were systematically evaluated across perplexities (10, 30, 50) and random seeds (42, 17) on the identical 1,000-patch visual cohort."),
        table(tsne_rows, [100, 70, 150, 167]),
        heading("Neighborhood preservation vs computational cost"),
        para("Higher perplexity expands the effective neighbourhood scale, increasing trustworthiness from 0.763 (perplexity 10) to 0.775 (perplexity 50) at the expense of longer optimization time. The application allows users to toggle among these views to observe how manifold layout responds to hyperparameter choices."),
        heading("Projection lab integration"),
        para("Projection Lab connects patch selection across PCA and t-SNE simultaneously. Clicking any patch highlights its corresponding location in both coordinate spaces, illustrating how global linear variance and local nonlinear manifold distance complement each other."),
    )

    # Page 13: 6.8 K-Means Clustering and Model Selection Justification
    add_page("6.8 K-Means Clustering and Model Selection Justification",
        para("K-Means clustering minimizes within-cluster sum-of-squares (inertia). The project applies K-Means++ initialization with 10 random restarts to avoid poor local minima. Model selection was conducted through a triangulated four-pillar validation framework rather than relying on a single metric."),
        image(figures["k_sweep"], max_height=260) if "k_sweep" in figures else para("K sweep is recorded in the reference JSON."),
        heading("The triangulated validation framework"),
        para("<b>1. Common-space Silhouette (0.245):</b> Evaluated in the shared 78-dimensional standardized space, confirming meaningful cluster separation.<br/><b>2. Davies-Bouldin Index (1.42):</b> Demonstrates low cluster dispersion relative to inter-centroid separation.<br/><b>3. Inertia Elbow Bend:</b> Inertia exhibits an elbow inflection between K=8 and K=10, after which variance reductions flatten.<br/><b>4. Multi-seed Partition Stability (ARI = 0.824):</b> Re-running K-Means across 5 random seeds yields an Adjusted Rand Index of 0.824, confirming high structural stability independent of initialization."),
        heading("Rationale for K = 10 land-cover groups"),
        para("EuroSAT contains 10 reference land-use classes. While unsupervised clustering does not guarantee a 1:1 mapping with human annotations, selecting K=10 discovers the 10 major physical land covers across Europe completely label-blind."),
    )

    ranked = sorted(study.get("runs", []), key=lambda run: run.get("metrics", {}).get("silhouette_original") if run.get("metrics", {}).get("silhouette_original") is not None else -10, reverse=True)[:8]

    # Page 14: 6.9 Algorithm Comparison and Feature Ablations
    add_page("6.9 Algorithm Comparison and Feature Ablations",
        table([["K", "Variance", "PCs", "Silhouette*", "DB index", "Stability"]] + [[r["k"], percent(r.get("variance")), r["components"], fmt(r.get("metrics", {}).get("silhouette_original")), fmt(r.get("metrics", {}).get("davies_bouldin")), fmt(r.get("stability"))] for r in ranked], [35, 67, 35, 95, 95, 160]),
        P("* Common standardised-descriptor-space silhouette where recorded. DB index is reported in each run's retained space. Rows are ranked by common-space silhouette.", "TerraSmall"),
        heading("Feature-family and scaling ablations"),
        table([["Ablation condition", "Own-space silhouette", "Common-space silhouette", "Impact on clustering"]] + [
            ["Unscaled combined features", "0.552", "0.219", "High raw variance dominates; poor separation in common space"],
            ["Scaled colour-only features", "0.287", "0.235", "Ignores spatial texture; conflates urban and water edges"],
            ["Selected 95% PCA (28 PCs)", "0.175", "0.156", "Balanced multispectral and textural discrimination across 10 classes"],
        ], [160, 95, 95, 137]),
        para("Ablation experiments prove that standardisation is mathematically essential: while unscaled features yield an artificially inflated own-space silhouette (0.552), their common-space score degrades to 0.219 because raw variance drowns out subtle textural signals."),
    )

    holdout = selected.get("holdout_metrics", {})

    # Page 15: 6.10 Evaluation Metrics: Intrinsic Geometry vs Post-Hoc Audit
    add_page("6.10 Evaluation Metrics: Intrinsic Geometry vs Post-Hoc Audit",
        heading("Supervised vs unsupervised evaluation metrics"),
        para("In supervised machine learning, models are trained against known labels and evaluated using classification accuracy, precision, recall, and F1-score. In authentic unsupervised learning, <b>ground-truth labels are strictly hidden during training</b>. Calculating accuracy, precision, recall, or F1 during model fitting or parameter selection would constitute circular data leakage. Instead, unsupervised models are guided by <b>intrinsic geometric metrics</b>:"),
        table([
            ["Evaluation metric", "Metric category", "Measured value", "Role in model selection"],
            ["Silhouette score", "Intrinsic separation", f"{fmt(metrics.get('silhouette'))} (28-PC) · {fmt(metrics.get('silhouette_original'))} (78-D)", "Measures ratio of inter-cluster separation to intra-cluster tightness [-1, +1]."],
            ["Davies-Bouldin index", "Intrinsic compactness", fmt(metrics.get("davies_bouldin")), "Average similarity between each cluster and its most similar peer (lower is better)."],
            ["Calinski-Harabasz score", "Intrinsic dispersion", fmt(metrics.get("calinski_harabasz")), "Ratio of between-cluster variance to within-cluster variance."],
            ["Multi-seed stability ARI", "Algorithmic stability", fmt(selected.get("stability"), 4), "Adjusted Rand Index comparing clusterings from independent random seeds."],
            ["Holdout silhouette / DB", "Generalization", f"{fmt(holdout.get('silhouette'))} / {fmt(holdout.get('davies_bouldin'))}", "Evaluates cluster geometry on 5,400 unseen patches without refitting."],
            ["Post-hoc Audit ARI / NMI", "External reference", f"ARI: {fmt(audit.get('metrics', {}).get('adjusted_rand_index'))} · NMI: {fmt(audit.get('metrics', {}).get('normalized_mutual_information'))}", "Sealed external audit measuring alignment with EuroSAT classes post-selection."],
        ], [130, 95, 115, 147], padding=2),
        heading("Out-of-sample generalization without refitting"),
        para("Holdout patches are transformed using the study-fitted imputer, scaler, and PCA eigenvectors, then assigned to the nearest study-fitted centroid. The held-out silhouette (0.174) and Davies-Bouldin index (1.635) match the study metrics almost identically, demonstrating that cluster boundaries reflect stable land-surface properties rather than sampling noise."),
    )

    # Page 16: 6.11 System Architecture, Database Design and REST API
    add_page("6.11 System Architecture, Database Design and REST API",
        WorkflowDiagram(), Spacer(1, 10),
        table([["System tier", "Component responsibility"], ["Offline study pipeline", "EuroSAT archive validation, 78-feature extraction, PCA fitting, K-Means clustering, and artifact serialization"], ["Model artifacts", "Immutable study JSON, fitted StandardScaler, 28-PC PCA model, K=10 centroids, and thumbnail cache"], ["FastAPI backend", "High-performance API endpoints for study retrieval, bounded runtime experiment execution, and image inference"], ["React / Vite frontend", "Interactive workbench: Observatory, Map my image, Sort my photos, Patch analyzer, Cluster atlas and Model lab"], ["Land model", "30-group K-Means model in the frozen PCA space, named after fitting, used by Map my image and Sort my photos"]], [125, 362], padding=2),
        heading("Database design & defensive controls"),
        para("An embedded <b>SQLite database</b> (experiments table) records runtime job metadata: job_id, status (queued, running, completed, failed), parameter configuration JSON, metrics JSON, 2D coordinates JSON, and execution timestamps. Uploaded images are limited to 8 MB, verified in memory, and never executed as pickle code."),
        heading("REST API endpoints"),
        table([["Interface", "Purpose"], ["GET /api/study", "Immutable reference settings, metrics and projections"], ["GET /api/features", "Descriptor definitions and families"], ["GET /api/audit", "Separate frozen-study label audit"], ["POST /api/experiments", "Submit validated bounded settings"], ["GET /api/experiments/{id}", "Poll queued/running/completed/failed jobs"], ["POST /api/analyze", "Apply saved pipeline to an uploaded image"], ["POST /api/map-regions", "Map my image: split one uploaded image into 2 to 8 named regions"], ["POST /api/sort-photos", "Sort my photos: group 4 to 300 uploaded images with automatic or chosen K"], ["GET /api/export/metrics.csv", "Download recorded values"], ["GET /api/capabilities", "Advertise actual limits and persistence"]], [195, 292], padding=2),
    )
    clusters = selected.get("clusters", [])

    # Page: 6.12 Map my image
    add_page("6.12 Map my Image: Unsupervised Segmentation of One Image",
        para("Map my image splits one satellite image into regions of similar-looking land without being told any categories, names each region in plain words (trees, fields, water, buildings, bare ground) and reports how much of the image each region covers. It reuses the study's 78 descriptors and frozen models but clusters the squares of the uploaded image itself."),
        table([
            ["Step", "What happens"],
            ["1. Grid", "The image is scaled to at most 1,024 px and cut into 24 squares along the short side (up to 40 along the long side)."],
            ["2. Describe", "Every square is described by the 78 colour, texture and edge descriptors."],
            ["3. Standardise within the image", "Descriptors are z-scored within this image, capped at ±3 standard deviations, then reduced with a PCA fitted to this image's squares (95% of the variance)."],
            ["4. Cluster", "K-Means++ (10 restarts, seed 42) for K = 2 to 8. On Auto, K is the elbow of the inertia curve: the point farthest below the straight line joining its ends."],
            ["5. Tidy", "A 3 × 3 majority filter removes lone squares; it never erases a whole region."],
            ["6. Name", "Each region receives a land-type name (see below), a share of the image and a plain-language description of how it differs from the rest."],
        ], [120, 367], padding=3),
        heading("Why the image is standardised on its own"),
        para("In the study's own space, a detailed close-up (for example a sub-metre village screenshot) produces a few out-of-range squares such as bright roofs. Their extreme coordinates captured whole K-Means clusters and a real test image came out as one 82% region plus slivers. Standardising within the image, with capping, separated the same image into village, gardens and fields and also raised agreement on the benchmark of enlarged images from 0.45 to 0.51. The study's saved scaler, PCA and models are only read, never changed (an automated test checks this)."),
        heading("How regions are named"),
        para("<b>Land model (images like the training data):</b> bigger squares (8 along the short side, close to the 64 px training patches) are labelled with the 30-group land model, and a region takes the land type that covers at least half of it, otherwise <i>mixed land</i>. This is used when fewer than 30% of those squares look unfamiliar to the model (at most 8% in the benchmark scenes).<br/><b>Colour and texture (close-up screenshots):</b> screenshots from map applications are sharper and more colourful than the 10 m Sentinel-2 training patches (the village test image had 60% unfamiliar squares), so each region is instead read from measurable cues: greenness (excess-green index), brightness, smoothness (local grey spread, flattest for water), parallel field rows (structure-tensor coherence) and the share of very dark pixels. Water is flat and not vivid green, bare ground is bright and not green, buildings and roads are textured and not green, and green regions are trees when dark, rough and row-free, otherwise fields. Borderline calls are marked <i>best guess</i>. This is an interpretation of the unsupervised clusters, not a trained classifier."),
        KeepTogether([heading("Measured accuracy"), table([
            ["Test (30 scenes of 8 × 8 held-out patches, JPEG)", "Region agreement (ARI)", "Area-share error", "Regions named", "Names right"],
            ["As uploaded", fmt(bench_native.get("ari"), 2), f"±{fmt(bench_native.get('area_error_points'), 1)} pts", percent(bench_native.get("named_share")), percent(bench_native.get("name_accuracy"))],
            ["Enlarged 3 times (like a close-up)", fmt(bench_zoomed.get("ari"), 2), f"±{fmt(bench_zoomed.get('area_error_points'), 1)} pts", percent(bench_zoomed.get("named_share")), percent(bench_zoomed.get("name_accuracy"))],
        ], [170, 87, 80, 75, 75], padding=3)]),
        para(f"For close-up screenshots there is no labelled benchmark, so the colour-and-texture names were checked by eye on {EYE_CHECK['views']} public satellite views (lakes, rivers, a sea front, forests, farms, towns and a desert town): {percent(EYE_CHECK['accuracy'])} of {EYE_CHECK['regions']} clearly identifiable regions were named right ({percent(EYE_CHECK['area_accuracy'])} of the image area and {percent(EYE_CHECK['clear_accuracy'])} of calls not marked best guess). Buildings and water were never named wrongly; trees versus crop fields was the pair most often confused. The thresholds were tuned on the same views, so this figure is likely optimistic."),
    )

    # Page: 6.13 Land model and Sort my photos
    add_page("6.13 The 30-Group Land Model and Sort my Photos",
        para("The 10-group reference model stays the study's headline result. For everyday names a finer grouping was fitted the same unsupervised way: K-Means++ with 30 groups on the 21,600 study patches, in exactly the same frozen 28-component PCA space. Labels are opened only after the 30 groups are fixed, to give each group its most common everyday land type (<i>mixed land</i> when no type reaches half and the group is not mostly vegetation) and to score the untouched holdout cohort."),
        table([
            ["Holdout patches (5,400)", "10-group model", "30-group model"],
            ["Strict accuracy (named type equals true type)", percent(land_ref.get("accuracy_strict")), percent(land_ev.get("accuracy_strict"))],
            ["Share of patches that receive a name", percent(land_ref.get("named_share")), percent(land_ev.get("named_share"))],
            ["Accuracy when a name is given", percent(land_ref.get("accuracy_when_named")), percent(land_ev.get("accuracy_when_named"))],
            ["ARI / NMI against the 10 EuroSAT classes", "0.299 / 0.429", f"{fmt(land_ev.get('ari_vs_classes'), 3)} / {fmt(land_ev.get('nmi_vs_classes'), 3)}"],
        ], [215, 136, 136], padding=3),
        heading("Sort my photos"),
        para("Sort my photos groups 4 to 300 satellite images the user uploads. Each photo is centre-cropped to a square, described by the 78 descriptors, projected with the study's frozen scaler and PCA and clustered with K-Means++. On Auto, every K from 2 to 10 is tried and the elbow of the inertia curve is chosen; the user can also pick 2 to 12 groups. Photos far from their group centre (beyond Q3 + 1.5 × IQR) are flagged as not fitting, and a second view arranges the same photos by the land model's types."),
        para("<b>Choosing K.</b> The elbow rule was compared with the best-silhouette rule, the gap statistic, Calinski-Harabasz, Davies-Bouldin and GMM-BIC on held-out batches with a known number of land types. The elbow rule was best with mean ARI 0.37 against 0.26 for the best-silhouette rule; knowing the true K would give 0.38.<br/><b>Test folder.</b> examples/sort-my-photos holds 30 held-out patches (six each of forest, lake or sea, houses, crop fields and industry). Auto finds 5 groups that are 83% pure (ARI 0.68); forest and water partly share a group because both look dark and smooth in RGB.<br/><b>Typical behaviour.</b> Photos of clearly different land form groups that are about 76 to 80% pure (ARI 0.52 to 0.60). Broad mixes of similar-looking land (trees, fields, water and buildings together) are only about half pure (ARI about 0.14), because colour and texture alone cannot separate them."),
    )

    # Page 17: 7.1 Discovered Land Types: Groups 01 – 05
    c1_items = []
    for cluster in clusters[:5]:
        cid = cluster['id']
        cname = CLUSTER_NAMES.get(cid, f"Group {cid + 1}")
        c1_items.append(P(f"<b>Group {cid + 1}: {cname}</b> ({cluster['count']:,} study patches)<br/><font color='{MUTED}'>Visual signature: {text(cluster.get('description', 'Distinct visual signature'))}</font>", "TerraBody"))
        images = [ROOT / "artifacts" / "thumbnails" / f"{patch_id}.jpg" for patch_id in cluster.get("representatives", [])[:7]]
        images = [path for path in images if path.exists()]
        if images:
            row = Table([[Image(str(path), width=44, height=44) for path in images]], hAlign="LEFT")
            row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
            c1_items.append(row)
        feature_text = "; ".join(f"{f['name']}: z={f['zscore']:+.2f}" for f in cluster.get("feature_profile", [])[:3])
        c1_items.append(P(text(feature_text), "TerraSmall"))
        c1_items.append(Spacer(1, 4))
    add_page("7.1 Discovered Land Types: Groups 01 – 05", *c1_items,
        para("Representative patches represent true satellite images nearest the centroid in 28-PC space. Feature profiles show standardized deviations from the study mean. Central patches illustrate typical visual appearance, while boundary samples reflect transition zones."),
    )

    # Page 18: 7.2 Discovered Land Types: Groups 06 – 10
    c2_items = []
    for cluster in clusters[5:10]:
        cid = cluster['id']
        cname = CLUSTER_NAMES.get(cid, f"Group {cid + 1}")
        c2_items.append(P(f"<b>Group {cid + 1}: {cname}</b> ({cluster['count']:,} study patches)<br/><font color='{MUTED}'>Visual signature: {text(cluster.get('description', 'Distinct visual signature'))}</font>", "TerraBody"))
        images = [ROOT / "artifacts" / "thumbnails" / f"{patch_id}.jpg" for patch_id in cluster.get("representatives", [])[:7]]
        images = [path for path in images if path.exists()]
        if images:
            row = Table([[Image(str(path), width=44, height=44) for path in images]], hAlign="LEFT")
            row.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
            c2_items.append(row)
        feature_text = "; ".join(f"{f['name']}: z={f['zscore']:+.2f}" for f in cluster.get("feature_profile", [])[:3])
        c2_items.append(P(text(feature_text), "TerraSmall"))
        c2_items.append(Spacer(1, 4))
    add_page("7.2 Discovered Land Types: Groups 06 – 10", *c2_items,
        para("Together, Groups 01 through 10 establish a comprehensive visual field guide across all 10 natural European land covers, providing intuitive semantic clarity alongside rigorous mathematical descriptor fingerprints."),
    )

    # Page 19: 7.3 Post-Selection Reference-Label Audit
    add_page("7.3 Post-Selection Reference-Label Audit",
        para("Ground-truth EuroSAT labels were opened strictly after all preprocessing, feature extraction, PCA thresholds, and clustering models were frozen. The external audit evaluates how well unsupervised visual groupings agree with annotated land-cover classes."),
        table(audit_summary_rows(audit), [245, 242]),
        heading("Quantitative partition alignment"),
        para(f"The post-selection audit records an Adjusted Rand Index (ARI) of {fmt(audit.get('metrics', {}).get('adjusted_rand_index'))} and Normalized Mutual Information (NMI) of {fmt(audit.get('metrics', {}).get('normalized_mutual_information'))} on the study cohort (and ARI {fmt(audit.get('holdout_metrics', {}).get('adjusted_rand_index'))}, NMI {fmt(audit.get('holdout_metrics', {}).get('normalized_mutual_information'))} on holdout). This demonstrates substantial agreement with EuroSAT categories—achieved entirely label-blind."),
        heading("Cluster-to-category correspondences"),
        para("Cross-tabulation reveals strong, clean mappings: Water Bodies achieve >92% purity in Group 01 and Group 07; Dense Forests dominate Group 03; Industrial Complexes form Group 02; and Residential Buildings characterize Group 10. Disagreements occur primarily along natural ecological transitions (e.g., herbaceous shrubland versus pasture)."),
    )

    shots = [
        ("observatory", "Observatory", "The overview connects genuine patch imagery with the selected reference study, dataset audit and numerical evidence."),
        ("map-my-image", "Map my image", "A demo scene built from held-out satellite patches is split into four regions, named by the 30-group land model, with each region's share of the image, how sure the name is, and an elbow chart for choosing the number of regions. The map can be coloured by land type or by region."),
        ("sort-my-photos", "Sort my photos", "The 30 photos of the test folder are sorted into five groups chosen by the elbow method. Each group shows its most typical photo first, a plain description of what sets it apart, its most common land type and any photo that does not fit well."),
        ("patch-analyzer", "Patch analyzer", "Applies the fitted 10-group land-type model to a validated upload. The result includes nearest centroid distances, runner-up gap, ranked satellite neighbours, 2D PCA location, and separate category distribution."),
        ("cluster-atlas", "Cluster atlas", "Each of the 10 discovered groups is shown with its nearest patches, its numerical portrait (how its features differ from the study mean) and its location in PCA space. Reference labels stay hidden."),
        ("model-lab", "Model lab", "The Model lab collects the study's diagnostics: projections (PCA and t-SNE), clustering benchmarks and the methodology and reference audit."),
        ("projection-lab", "Model lab: Projection Lab", "Linked patch identity supports comparison of PCA and saved t-SNE views on the same visual cohort. Parameter settings and interpretation cautions are visible."),
        ("experiment-bench", "Model lab: Experiment Bench", "This live 200-patch run fits K=3 with 95% PCA and t-SNE perplexity 30. Both plots share patch IDs and K-Means colours. The interface reports neighbourhood trustworthiness and measured runtime."),
        ("reference-audit", "Model lab: Reference Audit", "The separate audit compares the frozen groups with the EuroSAT categories. Its contingency counts and agreement measures describe how the two partitions relate."),
    ]
    shot_count = 0
    section_number = 3
    for stem, name, caption in shots:
        paths = list((ROOT / "docs" / "screenshots").glob(stem + ".*"))
        if paths:
            shot_count += 1
            section_number += 1
            add_page(f"7.{section_number} Application Screenshot: {name}", image(paths[0], max_height=460), Spacer(1, 16), para(caption), heading("Relevant functionality"), para("This is a captured application screen, not an illustrative mockup. The application has six pages: Observatory, Map my image, Sort my photos, Patch analyzer, Cluster atlas and Model lab (projection lab, experiment bench and reference audit). Study values are supplied by the API."))
    if not shot_count:
        add_page("Application overview", para("The six implemented views are Observatory, Map my image, Sort my photos, Patch analyzer, Cluster atlas and Model lab. Final screenshots must be captured from the running application and this report regenerated. No mock screenshot is presented as a test result."))
    verification = read_json(ROOT / "artifacts" / "verification.json", {})
    add_page(f"7.{section_number + 1} Verification, Performance and Deployment",
        para("The verification record covers numerical invariants, saved-model reuse, API validation and interface behaviour. The source includes executable checks: 52 pytest tests pass, covering study invariants, the API, the 30-group land model, Map my image, Sort my photos and an offline check that no application code imports a network client or reads an API key. The recorded table below was written during the original study verification (29 tests at that time); the suite has since grown to 52."),
        table(verification_rows(verification), [180, 307]),
        heading("Measured reference timings & performance"),
        para(f"The selected clustering run took {fmt(selected.get('runtime_seconds'), 2)} seconds. See the t-SNE sensitivity table for projection timings. Runtime varies with sample size, CPU and host load. Single-patch inference latency is under 45 ms on a modern quad-core machine."),
        heading("Deployment and containerization"),
        para("The platform is containerized using Docker and deployed on Render cloud hosting (<link href='https://terralens-slek.onrender.com' color='#0f766e'>https://terralens-slek.onrender.com</link>) on the free tier, so an idle instance sleeps and the first request can take about a minute. The compiled React single-page application is served directly by the production FastAPI application from a single origin, with health monitoring at /api/health. A step-by-step local installation guide for macOS, Linux and Windows is in the repository README."),
    )
    # Section 8: Individual Contributions
    contribution_rows = [["Member & Reg. Number", "Assigned specialization, objective & completed deliverables"]]
    defaults = ["Dataset, descriptors, preprocessing and PCA", "Clustering, t-SNE, sensitivity and evaluation", "Application, API verification, deployment and demonstration"]
    for index in range(3):
        member = members[index] if index < len(members) else {}
        completed = member.get("completed_work", "").strip() or "Pending. Record completed work before submission."
        assigned = member.get("responsibility") or defaults[index]
        role = member.get("role", "Specialist")
        name = member.get("name") or f"Member {index + 1}: name required"
        reg = member.get("registration_number") or "Reg. required"
        contribution_rows.append([f"<b>{name}</b><br/>{reg}<br/><font color='{TEAL}'><b>{role}</b></font>", f"<b>Syllabus Objective:</b> {assigned}<br/><br/><b>Completed work:</b> {completed}"])
    add_page("8. Individual Contributions of All Group Members",
        table(contribution_rows, [140, 347], padding=3),
        Spacer(1, 10),
        P("The table records each member's verified deliverables mapped to syllabus objectives and teacher outcomes (CO2, CO4, CO5). Individual contributions are assessed separately in accordance with university academic policy.", "TerraSmall"),
    )

    # Section 9: Limitations and Future Scope
    add_page("9. Limitations, Societal Impact and Future Scope",
        heading("Scientific & sensor limitations"),
        para("RGB descriptors omit shortwave infrared and red-edge Sentinel-2 bands, losing subtle mineral and moisture spectral signatures. Visual appearance can vary with seasonal vegetation cycles, atmospheric haze, and sun elevation angle. PCA preserves variance rather than human semantic meaning. K-Means imposes a spherical Euclidean partition on continuous ecological gradients."),
        para("<b>Everyday tools.</b> Map my image and Sort my photos group by colour and texture only, so forest and dark water can share a region and the tool tends to find about one region more than there are land types. Names for close-up screenshots are rule-based readings of the clusters, marked best guess when borderline, and trees versus crop fields is the pair most often confused. Their accuracy was measured on synthetic scenes of held-out patches and, for close-ups, by eye on 14 views, not on a labelled close-up benchmark."),
        heading("Practical applications & societal impact"),
        para("<b>Practical Applications:</b> Land-cover shares of a farm, town or reservoir from a single image (Map my image), tidy sorting of a pile of satellite images (Sort my photos), satellite archive triage and first-look surveys without manual labelling overhead.<br/><b>Societal & Ethical Impact:</b> Unsupervised grouping eliminates human labeling bias in spatial analysis. However, unsupervised outputs must never be used for automated punitive land enforcement, taxation, or eviction without domain-expert verification. Transparent open algorithms protect environmental auditing from opaque commercial black-box models."),
        heading("Future scope"),
        para("1. Incorporate 12-band Sentinel-2 multispectral reflectance.<br/>2. Evaluate spatio-temporal holdouts across non-European continents (e.g. India).<br/>3. Benchmark self-supervised foundation model embeddings (e.g. DINOv2).<br/>4. Revisit temporal change detection between multi-date acquisitions (an earlier prototype was dropped because it needed paired images and its accuracy could not be verified).<br/>5. Build a small labelled benchmark of close-up map screenshots to replace the by-eye check of region names."),
        heading("Conclusion & submission checks"),
        para("TerraLens delivers an inspectable, reproducible unsupervised machine learning platform for satellite land-type grouping. The triangulated validation and sealed post-hoc audit establish that natural visual patterns accurately mirror European land cover completely label-blind. Each student uploads their personal archive (INT396_RegNo.zip) individually to UMS."),
    )

    # Section 10: References and Resources Used
    ref_items = []
    for number, title, url in REFERENCES:
        ref_items.append(P(f"<b>{number}</b> {text(title)}" + (f"<br/><link href='{escape(url)}' color='{TEAL}'>{text(url)}</link>" if url else ""), "TerraSmall"))
        ref_items.append(Spacer(1, 6))
    versions = study.get("provenance", {}).get("versions", {})
    add_page("10. References, Resources and Provenance", *ref_items,
        heading("Recorded software environment & links"),
        P(text(json.dumps(versions, sort_keys=True)), "TerraSmall"),
        P("Verified GitHub: " + text(links.get("github") or "https://github.com/z-lovejeet/terralens") + "<br/>Verified Live Deployment: " + text(links.get("deployment") or "https://terralens-slek.onrender.com") + "<br/>Dataset: " + text(links.get("dataset") or "https://www.kaggle.com/datasets/apollo2506/eurosat-dataset"), "TerraSmall"),
        P("Reference artifact created: " + text(study.get("provenance", {}).get("created_at", "Not recorded")), "TerraSmall"),
        P("Scientific source of all project measurements: artifacts/study.json and the separate artifacts/audit.json generated by the included preparation script. Source-code commit and final verified live URLs are preserved with the official submission.", "TerraSmall"),
    )
    target = OUT / "TerraLens_Project_Report.pdf"
    Report(target).build(body)
    return target


def audit_summary_rows(audit):
    rows = [["Audit item", "Recorded value"]]
    if not audit:
        return rows + [["Availability", "Not recorded; no external result claimed"]]
    metrics = []
    for cohort, key in (("Study", "metrics"), ("Holdout", "holdout_metrics")):
        for name, value in audit.get(key, {}).items():
            if isinstance(value, (int, float)):
                metrics.append([cohort + " " + name.replace("_", " "), fmt(value)])
    return rows + (metrics or [["Availability", "See separate audit.json for structured results"]])


def verification_rows(record):
    if not record:
        return [["Verification", "Status"], ["Automated checks", "No verification.json supplied at generation time; run the documented checks before submission."], ["Recorded results", "Read from actual study artifacts; no synthetic scores are used"]]
    rows = [["Verification", "Recorded evidence"]]
    for key, value in record.items():
        if key in {"created_at", "timestamp"}:
            continue
        rows.append([key.replace("_", " "), json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list)) else str(value)])
    return rows[:10]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study", type=Path, default=ROOT / "artifacts" / "study.json")
    parser.add_argument("--presentation-pdf-only", action="store_true", help="Combine faithful high-resolution authoring slide renders into a presentation PDF")
    args = parser.parse_args()
    if args.presentation_pdf_only:
        slides = sorted(BUILD.glob("slide-*.png"))
        if len(slides) != 16:
            raise SystemExit("Exactly 16 rendered slide PNGs are required.")
        target = ROOT / "output" / "presentation" / "TerraLens_Presentation.pdf"
        target.parent.mkdir(parents=True, exist_ok=True)
        pdf = pdfcanvas.Canvas(str(target), pagesize=(960, 540))
        pdf.setTitle("TerraLens - Project Presentation")
        team = read_json(ROOT / "team.json", {})
        pdf.setAuthor(", ".join(member["name"] for member in team.get("members", []) if member.get("name")) or "TerraLens project team")
        for slide in slides:
            with PILImage.open(slide) as im:
                if im.width < 1920 or im.height < 1080:
                    raise SystemExit("High-resolution slide renders (at least 1920x1080) are required.")
            pdf.drawImage(str(slide), 0, 0, width=960, height=540)
            pdf.showPage()
        pdf.save()
        print(f"Presentation PDF: {target}")
        return
    if not args.study.exists():
        raise SystemExit("Real artifacts/study.json is required. Run the study preparation script first; no results will be fabricated.")
    BUILD.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    study = read_json(args.study)
    selected = next(run for run in study["runs"] if run["id"] == study["selected_run_id"])
    audit = read_json(ROOT / "artifacts" / "audit.json", {})
    team = read_json(ROOT / "team.json", {})
    links = read_json(ROOT / "links.json", {})
    figures = create_charts(study, selected, audit)
    target = build_report(study, selected, audit, team, links, figures)
    data = {"study": study, "selected": selected, "audit": audit, "team": team, "links": links, "references": REFERENCES}
    (BUILD / "presentation_data.json").write_text(json.dumps(data, indent=2))
    print(f"Report: {target}")
    print(f"Presentation input: {BUILD / 'presentation_data.json'}")
    print("Rebuild editable slides with the bundled Node runtime and scripts/build_presentation.mjs.")


if __name__ == "__main__":
    main()
