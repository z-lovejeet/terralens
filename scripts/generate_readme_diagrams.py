#!/usr/bin/env python3
"""Generate high-resolution modern SVG diagrams for the TerraLens documentation and README."""
from pathlib import Path

OUT_DIR = Path("docs/diagrams")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 1. Pipeline Architecture SVG
def build_pipeline_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 680" width="100%" height="100%" style="background:#090d16; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#151d2f"/>
      <stop offset="100%" stop-color="#0e1424"/>
    </linearGradient>
    <linearGradient id="emeraldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#059669"/>
    </linearGradient>
    <linearGradient id="tealGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#14b8a6"/>
      <stop offset="100%" stop-color="#0f766e"/>
    </linearGradient>
    <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3b82f6"/>
      <stop offset="100%" stop-color="#1d4ed8"/>
    </linearGradient>
    <linearGradient id="amberGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#b45309"/>
    </linearGradient>
    <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#8b5cf6"/>
      <stop offset="100%" stop-color="#6d28d9"/>
    </linearGradient>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="115%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.4"/>
    </filter>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#38bdf8"/>
    </marker>
    <marker id="arrowEmerald" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#10b981"/>
    </marker>
  </defs>

  <!-- Title Badge -->
  <rect x="40" y="30" width="1120" height="70" rx="12" fill="#131b2e" stroke="#1e293b" stroke-width="1.5" filter="url(#shadow)"/>
  <text x="65" y="62" fill="#38bdf8" font-size="12" font-weight="700" letter-spacing="1.5">END-TO-END SYSTEM ARCHITECTURE</text>
  <text x="65" y="86" fill="#f8fafc" font-size="20" font-weight="700">TerraLens: Unsupervised Land-Cover Discovery &amp; Scientific Audit Pipeline</text>
  <rect x="990" y="47" width="145" height="34" rx="6" fill="#064e3b" stroke="#059669" stroke-width="1"/>
  <text x="1005" y="69" fill="#34d399" font-size="12" font-weight="600">INT396 · SIH26142</text>

  <!-- Stage 1: Ingestion & Anonymization -->
  <g transform="translate(40, 130)" filter="url(#shadow)">
    <rect width="210" height="490" rx="12" fill="url(#cardGrad)" stroke="#1e293b" stroke-width="1.5"/>
    <rect x="15" y="15" width="180" height="32" rx="6" fill="#1e293b"/>
    <text x="25" y="36" fill="#94a3b8" font-size="12" font-weight="700">STAGE 1: INGESTION</text>
    
    <circle cx="105" cy="95" r="32" fill="#1e293b" stroke="#38bdf8" stroke-width="2"/>
    <path d="M 95 85 L 115 85 L 115 105 L 95 105 Z" fill="none" stroke="#38bdf8" stroke-width="2"/>
    <path d="M 90 95 L 120 95" stroke="#38bdf8" stroke-width="2"/>
    <text x="105" y="145" fill="#f8fafc" font-size="14" font-weight="700" text-anchor="middle">EuroSAT RGB</text>
    <text x="105" y="165" fill="#64748b" font-size="12" text-anchor="middle">27,000 Patches (64×64×3)</text>
    <text x="105" y="180" fill="#64748b" font-size="11" text-anchor="middle">10 Reference Classes</text>

    <line x1="25" y1="205" x2="185" y2="205" stroke="#1e293b" stroke-width="1.5"/>

    <!-- Label Hiding Box -->
    <rect x="15" y="220" width="180" height="120" rx="8" fill="#1c1917" stroke="#78350f" stroke-width="1.5"/>
    <text x="25" y="242" fill="#fbbf24" font-size="11" font-weight="700">🔒 CRYPTOGRAPHIC SPLIT</text>
    <text x="25" y="262" fill="#e2e8f0" font-size="11">Raw RGB Pixel Bytes</text>
    <text x="25" y="278" fill="#94a3b8" font-size="10">↳ SHA-256 Hashing</text>
    <text x="25" y="295" fill="#38bdf8" font-size="11" font-family="monospace">patch_id: "pa805..."</text>
    <text x="25" y="322" fill="#ef4444" font-size="10" font-weight="600">Folder &amp; Filenames Stripped</text>

    <!-- Quarantine Box -->
    <rect x="15" y="355" width="180" height="110" rx="8" fill="#1e1b4b" stroke="#4338ca" stroke-width="1.5"/>
    <text x="25" y="377" fill="#a5b4fc" font-size="11" font-weight="700">📦 ISOLATED QUARANTINE</text>
    <text x="25" y="398" fill="#cbd5e1" font-size="11">Ground-Truth Reference</text>
    <text x="25" y="415" fill="#94a3b8" font-size="10">Stored in locked JSON:</text>
    <text x="25" y="432" fill="#818cf8" font-size="9.5" font-family="monospace">reference_labels.json</text>
    <text x="25" y="452" fill="#34d399" font-size="10" font-weight="600">ZERO Label Leakage</text>
  </g>

  <!-- Arrow 1 to 2 -->
  <line x1="250" y1="300" x2="280" y2="300" stroke="#38bdf8" stroke-width="2.5" marker-end="url(#arrow)"/>

  <!-- Stage 2: Feature Engineering -->
  <g transform="translate(285, 130)" filter="url(#shadow)">
    <rect width="210" height="490" rx="12" fill="url(#cardGrad)" stroke="#1e293b" stroke-width="1.5"/>
    <rect x="15" y="15" width="180" height="32" rx="6" fill="#1e293b"/>
    <text x="25" y="36" fill="#94a3b8" font-size="12" font-weight="700">STAGE 2: DESCRIPTORS</text>
    
    <text x="105" y="75" fill="#f8fafc" font-size="15" font-weight="700" text-anchor="middle">78 Engineered Features</text>
    <text x="105" y="93" fill="#64748b" font-size="11" text-anchor="middle">Pruned from 12,288 Pixels</text>

    <!-- Family 1 -->
    <rect x="15" y="110" width="180" height="110" rx="8" fill="#064e3b" stroke="#059669" stroke-width="1.5"/>
    <text x="25" y="132" fill="#34d399" font-size="12" font-weight="700">47 COLOUR DESCRIPTORS</text>
    <text x="25" y="152" fill="#e2e8f0" font-size="11">• 15 RGB Moments (μ, σ, p10, p50, p90)</text>
    <text x="25" y="170" fill="#e2e8f0" font-size="11">• 4 HSV Statistics (Mean &amp; Std)</text>
    <text x="25" y="188" fill="#e2e8f0" font-size="11">• 12 Circular Hue Histogram Bins</text>
    <text x="25" y="206" fill="#e2e8f0" font-size="11">• 16 Saturation &amp; Value Bins</text>

    <!-- Family 2 -->
    <rect x="15" y="235" width="180" height="115" rx="8" fill="#0f172a" stroke="#0284c7" stroke-width="1.5"/>
    <text x="25" y="257" fill="#38bdf8" font-size="12" font-weight="700">23 TEXTURE DESCRIPTORS</text>
    <text x="25" y="277" fill="#e2e8f0" font-size="11">• 12 GLCM Properties (d=1, 3)</text>
    <text x="35" y="293" fill="#94a3b8" font-size="10">Contrast, Energy, Homogeneity</text>
    <text x="25" y="311" fill="#e2e8f0" font-size="11">• 10 Uniform LBP (P=8, R=1)</text>
    <text x="25" y="329" fill="#e2e8f0" font-size="11">• 1 Shannon Greyscale Entropy</text>

    <!-- Family 3 -->
    <rect x="15" y="365" width="180" height="100" rx="8" fill="#311042" stroke="#9333ea" stroke-width="1.5"/>
    <text x="25" y="387" fill="#c084fc" font-size="12" font-weight="700">8 EDGE DESCRIPTORS</text>
    <text x="25" y="407" fill="#e2e8f0" font-size="11">• 4 Sobel Gradient Magnitude Stats</text>
    <text x="35" y="423" fill="#94a3b8" font-size="10">Mean, Std, p90, Edge Density &gt;0.1</text>
    <text x="25" y="441" fill="#e2e8f0" font-size="11">• 4 Magnitude-Weighted Angles</text>
  </g>

  <!-- Arrow 2 to 3 -->
  <line x1="495" y1="300" x2="525" y2="300" stroke="#38bdf8" stroke-width="2.5" marker-end="url(#arrow)"/>

  <!-- Stage 3: Normalization & Partition -->
  <g transform="translate(530, 130)" filter="url(#shadow)">
    <rect width="180" height="490" rx="12" fill="url(#cardGrad)" stroke="#1e293b" stroke-width="1.5"/>
    <rect x="15" y="15" width="150" height="32" rx="6" fill="#1e293b"/>
    <text x="25" y="36" fill="#94a3b8" font-size="11" font-weight="700">STAGE 3: PROTOCOL</text>

    <!-- Partition Box -->
    <rect x="15" y="70" width="150" height="110" rx="8" fill="#172554" stroke="#2563eb" stroke-width="1.5"/>
    <text x="25" y="92" fill="#60a5fa" font-size="12" font-weight="700">80/20 PARTITION</text>
    <text x="25" y="112" fill="#f8fafc" font-size="12" font-weight="600">21,600 Study</text>
    <text x="25" y="128" fill="#94a3b8" font-size="10">Used for model fitting</text>
    <text x="25" y="148" fill="#f8fafc" font-size="12" font-weight="600">5,400 Holdout</text>
    <text x="25" y="164" fill="#94a3b8" font-size="10">Unseen generalisation test</text>

    <!-- Preprocessing Box -->
    <rect x="15" y="200" width="150" height="130" rx="8" fill="#1e293b" stroke="#475569" stroke-width="1.5"/>
    <text x="25" y="222" fill="#cbd5e1" font-size="12" font-weight="700">STANDARDIZATION</text>
    <text x="25" y="244" fill="#38bdf8" font-size="12" font-family="monospace">z = (x - μ) / σ</text>
    <text x="25" y="265" fill="#94a3b8" font-size="10">• μ, σ fitted STRICTLY</text>
    <text x="30" y="279" fill="#94a3b8" font-size="10">on 21,600 study patches</text>
    <text x="25" y="297" fill="#94a3b8" font-size="10">• Applied to holdout</text>
    <text x="25" y="315" fill="#34d399" font-size="10" font-weight="600">0 Data Leakage</text>

    <!-- Generalisation Result -->
    <rect x="15" y="350" width="150" height="115" rx="8" fill="#042f2e" stroke="#0d9488" stroke-width="1.5"/>
    <text x="25" y="372" fill="#2dd4bf" font-size="11" font-weight="700">GENERALISATION</text>
    <text x="25" y="392" fill="#e2e8f0" font-size="11">Study MSE: 0.04899</text>
    <text x="25" y="410" fill="#e2e8f0" font-size="11">Holdout: 0.04936</text>
    <text x="25" y="432" fill="#34d399" font-size="12" font-weight="700">Δ = 0.749% &lt; 0.75%</text>
    <text x="25" y="450" fill="#94a3b8" font-size="9.5">Zero Linear Overfitting</text>
  </g>

  <!-- Arrow 3 to 4 -->
  <line x1="710" y1="300" x2="740" y2="300" stroke="#38bdf8" stroke-width="2.5" marker-end="url(#arrow)"/>

  <!-- Stage 4: PCA & Dimensionality Reduction -->
  <g transform="translate(745, 130)" filter="url(#shadow)">
    <rect width="200" height="490" rx="12" fill="url(#cardGrad)" stroke="#1e293b" stroke-width="1.5"/>
    <rect x="15" y="15" width="170" height="32" rx="6" fill="#1e293b"/>
    <text x="25" y="36" fill="#94a3b8" font-size="11" font-weight="700">STAGE 4: REDUCTION</text>

    <text x="100" y="75" fill="#f8fafc" font-size="15" font-weight="700" text-anchor="middle">28-Component PCA</text>
    <text x="100" y="93" fill="#34d399" font-size="12" font-weight="600" text-anchor="middle">95.006% Retained Variance</text>
    <text x="100" y="108" fill="#64748b" font-size="10" text-anchor="middle">Pruned 50 Collinear Dims (-64.1%)</text>

    <!-- Physical Loadings -->
    <rect x="15" y="125" width="170" height="200" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
    <text x="25" y="147" fill="#f1f5f9" font-size="11" font-weight="700">PHYSICAL PC LOADINGS</text>
    
    <text x="25" y="172" fill="#38bdf8" font-size="11" font-weight="700">PC 1 (40.8%): Surface Albedo</text>
    <text x="25" y="187" fill="#94a3b8" font-size="10">Broadband brightness vs shadow</text>

    <text x="25" y="212" fill="#34d399" font-size="11" font-weight="700">PC 2 (8.6%): Greenness / Water</text>
    <text x="25" y="227" fill="#94a3b8" font-size="10">Vegetation chlorophyll vs absorption</text>

    <text x="25" y="252" fill="#fbbf24" font-size="11" font-weight="700">PC 3 (6.6%): Structural Roughness</text>
    <text x="25" y="267" fill="#94a3b8" font-size="10">Urban roof complexity vs open grass</text>

    <text x="25" y="292" fill="#c084fc" font-size="11" font-weight="700">PC 4 (4.7%): Transport Corridors</text>
    <text x="25" y="307" fill="#94a3b8" font-size="10">Highways, runways &amp; linear gradients</text>

    <!-- Manifold Branch -->
    <rect x="15" y="340" width="170" height="125" rx="8" fill="#1e1b4b" stroke="#6366f1" stroke-width="1.5"/>
    <text x="25" y="362" fill="#a5b4fc" font-size="11" font-weight="700">DUAL PROJECTIONS</text>
    <text x="25" y="382" fill="#e2e8f0" font-size="11">• PCA 2D: Global Geometry</text>
    <text x="25" y="402" fill="#e2e8f0" font-size="11">• t-SNE 2D: Local Manifold</text>
    <text x="35" y="418" fill="#94a3b8" font-size="10">Perplexity: 30 · Iter: 1000</text>
    <text x="35" y="433" fill="#94a3b8" font-size="10">Trustworthiness: 0.771</text>
    <text x="25" y="452" fill="#fbbf24" font-size="9.5">Solves Crowding Problem</text>
  </g>

  <!-- Arrow 4 to 5 -->
  <line x1="945" y1="300" x2="975" y2="300" stroke="#38bdf8" stroke-width="2.5" marker-end="url(#arrow)"/>

  <!-- Stage 5: Clustering & Sealed Audit -->
  <g transform="translate(980, 130)" filter="url(#shadow)">
    <rect width="180" height="490" rx="12" fill="url(#cardGrad)" stroke="#1e293b" stroke-width="1.5"/>
    <rect x="15" y="15" width="150" height="32" rx="6" fill="#1e293b"/>
    <text x="25" y="36" fill="#94a3b8" font-size="11" font-weight="700">STAGE 5: CLUSTERING</text>

    <!-- K-Means Box -->
    <rect x="15" y="70" width="150" height="150" rx="8" fill="#064e3b" stroke="#059669" stroke-width="1.5"/>
    <text x="25" y="92" fill="#34d399" font-size="12" font-weight="700">K-MEANS++ (K=10)</text>
    <text x="25" y="112" fill="#e2e8f0" font-size="11">Fitted in 28-D PCA Space</text>
    <text x="25" y="132" fill="#94a3b8" font-size="10">Intrinsic Validation:</text>
    <text x="25" y="150" fill="#f8fafc" font-size="11">Silhouette: <tspan fill="#34d399" font-weight="700">0.245</tspan></text>
    <text x="25" y="168" fill="#f8fafc" font-size="11">Davies-Bouldin: <tspan fill="#34d399" font-weight="700">1.42</tspan></text>
    <text x="25" y="186" fill="#f8fafc" font-size="11">Calinski-Harabasz: <tspan fill="#34d399" font-weight="700">2,518</tspan></text>
    <text x="25" y="204" fill="#fbbf24" font-size="10.5" font-weight="600">Seed ARI: 0.824 (Stable)</text>

    <!-- Sealed Post-Hoc Audit -->
    <rect x="15" y="235" width="150" height="150" rx="8" fill="#2e1065" stroke="#9333ea" stroke-width="1.5"/>
    <text x="25" y="257" fill="#d8b4fe" font-size="11" font-weight="700">SEALED POST-HOC AUDIT</text>
    <text x="25" y="277" fill="#94a3b8" font-size="10">Opened only AFTER</text>
    <text x="25" y="291" fill="#94a3b8" font-size="10">model is frozen:</text>
    <text x="25" y="315" fill="#f8fafc" font-size="11">Adjusted Rand (ARI):</text>
    <text x="25" y="333" fill="#38bdf8" font-size="13" font-weight="700">0.299 (Study) / 0.301</text>
    <text x="25" y="353" fill="#f8fafc" font-size="11">Mutual Info (NMI):</text>
    <text x="25" y="371" fill="#38bdf8" font-size="13" font-weight="700">0.429 (Study) / 0.435</text>

    <!-- Live Inference Box -->
    <rect x="15" y="400" width="150" height="65" rx="8" fill="#1e293b" stroke="#38bdf8" stroke-width="1.5"/>
    <text x="25" y="420" fill="#38bdf8" font-size="11" font-weight="700">LIVE PATCH INFERENCE</text>
    <text x="25" y="438" fill="#94a3b8" font-size="9.5">POST /api/analyze</text>
    <text x="25" y="452" fill="#34d399" font-size="9.5">Nearest Centroid &amp; Neighbors</text>
  </g>
</svg>'''

# 2. Feature Engineering Hierarchy SVG
def build_features_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1100 520" width="100%" height="100%" style="background:#090d16; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#151d2f"/>
      <stop offset="100%" stop-color="#0e1424"/>
    </linearGradient>
    <filter id="shadow">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.4"/>
    </filter>
  </defs>

  <!-- Title -->
  <text x="40" y="45" fill="#38bdf8" font-size="12" font-weight="700" letter-spacing="1.5">DOMAIN-SPECIFIC FEATURE EXTRACTION PIPELINE</text>
  <text x="40" y="75" fill="#f8fafc" font-size="22" font-weight="700">78 Deterministic Visual Descriptors (backend/terralens/features.py)</text>
  <text x="40" y="98" fill="#94a3b8" font-size="13">Pruned 12,288 raw pixels down to 78 rotation-invariant, physically interpretable remote sensing features.</text>

  <!-- Column 1: Colour Descriptors -->
  <g transform="translate(40, 125)" filter="url(#shadow)">
    <rect width="320" height="355" rx="12" fill="url(#cardBg)" stroke="#059669" stroke-width="2"/>
    <rect x="0" y="0" width="320" height="48" rx="12" fill="#064e3b"/>
    <text x="20" y="30" fill="#34d399" font-size="15" font-weight="700">47 COLOUR DESCRIPTORS</text>
    <text x="270" y="30" fill="#a7f3d0" font-size="12" font-weight="600">60.3%</text>

    <text x="20" y="75" fill="#f8fafc" font-size="13" font-weight="700">15 RGB Moments (5 stats × 3 channels)</text>
    <text x="20" y="95" fill="#94a3b8" font-size="11.5">Mean, Std, p10 (shadow baseline),</text>
    <text x="20" y="112" fill="#94a3b8" font-size="11.5">Median (p50), p90 (highlight peaks).</text>
    <text x="20" y="130" fill="#38bdf8" font-size="10.5" font-family="monospace">red_mean, green_std, blue_p90, ...</text>

    <line x1="20" y1="145" x2="300" y2="145" stroke="#1e293b" stroke-width="1.5"/>

    <text x="20" y="170" fill="#f8fafc" font-size="13" font-weight="700">4 HSV Summary Statistics</text>
    <text x="20" y="190" fill="#94a3b8" font-size="11.5">Saturation mean/std &amp; Value mean/std.</text>
    <text x="20" y="208" fill="#94a3b8" font-size="11">Separates shadow illumination from chromaticity.</text>

    <line x1="20" y1="222" x2="300" y2="222" stroke="#1e293b" stroke-width="1.5"/>

    <text x="20" y="247" fill="#f8fafc" font-size="13" font-weight="700">12 Circular Hue Bins (30° intervals)</text>
    <text x="20" y="267" fill="#94a3b8" font-size="11.5">Eliminates 0°/360° red wraparound singularity</text>
    <text x="20" y="284" fill="#94a3b8" font-size="11">via circular trigonometry histogram.</text>

    <line x1="20" y1="298" x2="300" y2="298" stroke="#1e293b" stroke-width="1.5"/>

    <text x="20" y="323" fill="#f8fafc" font-size="13" font-weight="700">16 Saturation &amp; Brightness Bins</text>
    <text x="20" y="342" fill="#94a3b8" font-size="11.5">8 Saturation bins + 8 Value distribution bins.</text>
  </g>

  <!-- Column 2: Texture Descriptors -->
  <g transform="translate(390, 125)" filter="url(#shadow)">
    <rect width="320" height="355" rx="12" fill="url(#cardBg)" stroke="#0284c7" stroke-width="2"/>
    <rect x="0" y="0" width="320" height="48" rx="12" fill="#0c4a6e"/>
    <text x="20" y="30" fill="#38bdf8" font-size="15" font-weight="700">23 TEXTURE DESCRIPTORS</text>
    <text x="270" y="30" fill="#bae6fd" font-size="12" font-weight="600">29.5%</text>

    <text x="20" y="75" fill="#f8fafc" font-size="13" font-weight="700">12 GLCM Properties (Haralick)</text>
    <text x="20" y="95" fill="#94a3b8" font-size="11.5">Gray-Level Co-occurrence Matrix (16 levels)</text>
    <text x="20" y="112" fill="#94a3b8" font-size="11.5">Averaged across 4 angles (0°, 45°, 90°, 135°)</text>
    <text x="20" y="130" fill="#94a3b8" font-size="11.5">Distances: <tspan fill="#38bdf8" font-weight="600">d = 1 px</tspan> &amp; <tspan fill="#38bdf8" font-weight="600">d = 3 px</tspan></text>
    <text x="20" y="148" fill="#cbd5e1" font-size="10.5">Contrast, Dissimilarity, Homogeneity,</text>
    <text x="20" y="163" fill="#cbd5e1" font-size="10.5">Energy, Correlation, Angular Second Moment (ASM)</text>

    <line x1="20" y1="180" x2="300" y2="180" stroke="#1e293b" stroke-width="1.5"/>

    <text x="20" y="205" fill="#f8fafc" font-size="13" font-weight="700">10 Uniform Local Binary Patterns (LBP)</text>
    <text x="20" y="225" fill="#94a3b8" font-size="11.5">P = 8 sampling points, Radius R = 1 px.</text>
    <text x="20" y="242" fill="#94a3b8" font-size="11.5">Detects micro-texture (spots, edges, corners)</text>
    <text x="20" y="260" fill="#34d399" font-size="11" font-weight="600">Strictly rotation-invariant representation.</text>

    <line x1="20" y1="275" x2="300" y2="275" stroke="#1e293b" stroke-width="1.5"/>

    <text x="20" y="300" fill="#f8fafc" font-size="13" font-weight="700">1 Shannon Greyscale Entropy</text>
    <text x="20" y="320" fill="#94a3b8" font-size="11.5">Statistical information entropy over 32 grey bins.</text>
    <text x="20" y="338" fill="#fbbf24" font-size="11">Differentiates noisy forests from smooth lakes.</text>
  </g>

  <!-- Column 3: Edge Descriptors -->
  <g transform="translate(740, 125)" filter="url(#shadow)">
    <rect width="320" height="355" rx="12" fill="url(#cardBg)" stroke="#9333ea" stroke-width="2"/>
    <rect x="0" y="0" width="320" height="48" rx="12" fill="#4a044e"/>
    <text x="20" y="30" fill="#e879f9" font-size="15" font-weight="700">8 EDGE DESCRIPTORS</text>
    <text x="270" y="30" fill="#f5d0fe" font-size="12" font-weight="600">10.2%</text>

    <text x="20" y="75" fill="#f8fafc" font-size="13" font-weight="700">4 Sobel Gradient Magnitude Stats</text>
    <text x="20" y="95" fill="#94a3b8" font-size="11.5">Derived from horizontal &amp; vertical Sobel filters:</text>
    <text x="20" y="113" fill="#38bdf8" font-size="11" font-family="monospace">gx = Sobel(axis=1), gy = Sobel(axis=0)</text>
    <text x="20" y="131" fill="#38bdf8" font-size="11" font-family="monospace">magnitude = hypot(gx, gy)</text>
    <text x="20" y="153" fill="#cbd5e1" font-size="11.5">• <tspan font-weight="600">edge_mean:</tspan> Average boundary gradient</text>
    <text x="20" y="171" fill="#cbd5e1" font-size="11.5">• <tspan font-weight="600">edge_std:</tspan> Spatial gradient variance</text>
    <text x="20" y="189" fill="#cbd5e1" font-size="11.5">• <tspan font-weight="600">edge_p90:</tspan> 90th percentile peak edge</text>
    <text x="20" y="207" fill="#cbd5e1" font-size="11.5">• <tspan font-weight="600">edge_density:</tspan> Fraction with magnitude &gt; 0.1</text>

    <line x1="20" y1="225" x2="300" y2="225" stroke="#1e293b" stroke-width="1.5"/>

    <text x="20" y="250" fill="#f8fafc" font-size="13" font-weight="700">4 Directional Orientation Bins</text>
    <text x="20" y="270" fill="#94a3b8" font-size="11.5">Gradient-weighted histogram in unoriented</text>
    <text x="20" y="288" fill="#94a3b8" font-size="11.5">angle bins over [0, π]:</text>
    <text x="20" y="310" fill="#e2e8f0" font-size="11">• 0° (horizontal), 45°, 90° (vertical), 135°</text>
    <text x="20" y="333" fill="#34d399" font-size="11" font-weight="600">Captures roads, runways &amp; industrial grids.</text>
  </g>
</svg>'''

# 3. Scree Plot & PCA Variance SVG
def build_scree_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 520" width="100%" height="100%" style="background:#090d16; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <linearGradient id="barGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="100%" stop-color="#0284c7"/>
    </linearGradient>
    <linearGradient id="curveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#34d399"/>
    </linearGradient>
    <filter id="shadow">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.4"/>
    </filter>
  </defs>

  <!-- Title -->
  <text x="50" y="45" fill="#38bdf8" font-size="12" font-weight="700" letter-spacing="1.5">DIMENSIONALITY REDUCTION AUDIT</text>
  <text x="50" y="75" fill="#f8fafc" font-size="22" font-weight="700">PCA Scree Plot &amp; Cumulative Retained Variance</text>
  <text x="50" y="98" fill="#94a3b8" font-size="13">Pruned 50 redundant dimensions (64.1% reduction) while preserving 95.006% of total feature variance.</text>

  <!-- Main Chart Canvas -->
  <g transform="translate(60, 130)">
    <!-- Grid Lines -->
    <line x1="50" y1="300" x2="880" y2="300" stroke="#1e293b" stroke-width="1.5"/>
    <line x1="50" y1="225" x2="880" y2="225" stroke="#1e293b" stroke-width="1" stroke-dasharray="4,4"/>
    <line x1="50" y1="150" x2="880" y2="150" stroke="#1e293b" stroke-width="1" stroke-dasharray="4,4"/>
    <line x1="50" y1="75" x2="880" y2="75" stroke="#1e293b" stroke-width="1" stroke-dasharray="4,4"/>
    <line x1="50" y1="15" x2="880" y2="15" stroke="#059669" stroke-width="1.5" stroke-dasharray="6,4"/>

    <!-- Y-Axis Labels -->
    <text x="40" y="305" fill="#64748b" font-size="11" text-anchor="end">0%</text>
    <text x="40" y="230" fill="#64748b" font-size="11" text-anchor="end">25%</text>
    <text x="40" y="155" fill="#64748b" font-size="11" text-anchor="end">50%</text>
    <text x="40" y="80" fill="#64748b" font-size="11" text-anchor="end">75%</text>
    <text x="40" y="20" fill="#34d399" font-size="11" font-weight="700" text-anchor="end">95%</text>

    <!-- 95% Cutoff Label -->
    <text x="880" y="10" fill="#34d399" font-size="11" font-weight="700" text-anchor="end">95% Scree Threshold (k = 28)</text>

    <!-- Selected k=28 Vertical Line -->
    <line x1="380" y1="15" x2="380" y2="300" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4,4"/>

    <!-- Sample Individual Bars (PC 1 to 28) -->
    <!-- PC1: 40.8% = 122px height -->
    <rect x="65" y="178" width="12" height="122" rx="2" fill="url(#barGrad)"/>
    <!-- PC2: 8.6% = 26px -->
    <rect x="85" y="274" width="12" height="26" rx="2" fill="url(#barGrad)"/>
    <!-- PC3: 6.6% = 20px -->
    <rect x="105" y="280" width="12" height="20" rx="2" fill="url(#barGrad)"/>
    <!-- PC4: 4.7% = 14px -->
    <rect x="125" y="286" width="12" height="14" rx="2" fill="url(#barGrad)"/>
    <!-- PC5: 3.8% = 11px -->
    <rect x="145" y="289" width="12" height="11" rx="2" fill="url(#barGrad)"/>
    <!-- Other small bars trailing off -->
    <rect x="165" y="291" width="10" height="9" rx="1" fill="#334155"/>
    <rect x="180" y="293" width="10" height="7" rx="1" fill="#334155"/>
    <rect x="195" y="294" width="10" height="6" rx="1" fill="#334155"/>
    <rect x="210" y="295" width="10" height="5" rx="1" fill="#334155"/>
    <rect x="225" y="296" width="10" height="4" rx="1" fill="#334155"/>
    <rect x="240" y="296.5" width="10" height="3.5" rx="1" fill="#334155"/>
    <rect x="270" y="297" width="10" height="3" rx="1" fill="#334155"/>
    <rect x="300" y="297.5" width="10" height="2.5" rx="1" fill="#334155"/>
    <rect x="330" y="298" width="10" height="2" rx="1" fill="#334155"/>
    <rect x="360" y="298.5" width="10" height="1.5" rx="1" fill="#334155"/>
    <rect x="375" y="298.8" width="10" height="1.2" rx="1" fill="#f59e0b"/>

    <!-- Cumulative Curve -->
    <path d="M 71 178 Q 120 120, 200 65 T 380 15 Q 500 5, 870 1" fill="none" stroke="url(#curveGrad)" stroke-width="3.5"/>

    <!-- Cutoff Point Marker -->
    <circle cx="380" cy="15" r="6" fill="#f59e0b" stroke="#090d16" stroke-width="2"/>

    <!-- Callout Card on Cutoff -->
    <g transform="translate(400, 25)" filter="url(#shadow)">
      <rect width="260" height="110" rx="8" fill="#1e293b" stroke="#f59e0b" stroke-width="1.5"/>
      <text x="15" y="25" fill="#f59e0b" font-size="12" font-weight="700">OPTIMAL OPERATING POINT</text>
      <text x="15" y="47" fill="#f8fafc" font-size="13" font-weight="700">Components: 28 of 78</text>
      <text x="15" y="68" fill="#34d399" font-size="12" font-weight="600">Variance Retained: 95.006%</text>
      <text x="15" y="88" fill="#94a3b8" font-size="11">Pruned 50 redundant dimensions</text>
      <text x="15" y="103" fill="#cbd5e1" font-size="10.5">Linear holdout MSE delta &lt; 0.75%</text>
    </g>

    <!-- X-Axis Labels -->
    <text x="71" y="325" fill="#94a3b8" font-size="11" text-anchor="middle">PC 1</text>
    <text x="145" y="325" fill="#94a3b8" font-size="11" text-anchor="middle">PC 5</text>
    <text x="225" y="325" fill="#94a3b8" font-size="11" text-anchor="middle">PC 10</text>
    <text x="315" y="325" fill="#94a3b8" font-size="11" text-anchor="middle">PC 20</text>
    <text x="380" y="325" fill="#f59e0b" font-size="12" font-weight="700" text-anchor="middle">PC 28</text>
    <text x="550" y="325" fill="#94a3b8" font-size="11" text-anchor="middle">PC 45</text>
    <text x="870" y="325" fill="#94a3b8" font-size="11" text-anchor="middle">PC 78</text>
  </g>

  <!-- Legend -->
  <g transform="translate(110, 485)">
    <rect x="0" y="0" width="14" height="14" rx="2" fill="url(#barGrad)"/>
    <text x="22" y="12" fill="#e2e8f0" font-size="11.5">Individual PC Variance</text>

    <line x1="200" y1="7" x2="230" y2="7" stroke="#10b981" stroke-width="3"/>
    <text x="238" y="12" fill="#e2e8f0" font-size="11.5">Cumulative Explained Variance</text>

    <line x1="450" y1="7" x2="480" y2="7" stroke="#f59e0b" stroke-width="2" stroke-dasharray="4,4"/>
    <text x="488" y="12" fill="#e2e8f0" font-size="11.5">Selected 95% Cutoff (k=28)</text>
  </g>
</svg>'''

# 4. Cryptographic Quarantine Protocol SVG
def build_quarantine_svg():
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 460" width="100%" height="100%" style="background:#090d16; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#151d2f"/>
      <stop offset="100%" stop-color="#0e1424"/>
    </linearGradient>
    <filter id="shadow">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.4"/>
    </filter>
    <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1 L 8 5 L 0 9 z" fill="#38bdf8"/>
    </marker>
  </defs>

  <text x="40" y="45" fill="#38bdf8" font-size="12" font-weight="700" letter-spacing="1.5">DATA HYGIENE &amp; LEAKAGE PREVENTION</text>
  <text x="40" y="75" fill="#f8fafc" font-size="22" font-weight="700">Cryptographic Label-Quarantine Protocol</text>
  <text x="40" y="98" fill="#94a3b8" font-size="13">Strict separation of raw image pixel features from ground-truth class annotations.</text>

  <!-- Step 1: Raw Image Path -->
  <g transform="translate(40, 130)" filter="url(#shadow)">
    <rect width="250" height="290" rx="10" fill="url(#cardGrad)" stroke="#1e293b" stroke-width="1.5"/>
    <rect x="0" y="0" width="250" height="40" rx="10" fill="#1e293b"/>
    <text x="15" y="26" fill="#f8fafc" font-size="13" font-weight="700">1. Raw EuroSAT Disk Path</text>

    <text x="15" y="70" fill="#ef4444" font-size="11" font-weight="700">POTENTIAL LEAKAGE SOURCE:</text>
    <rect x="15" y="85" width="220" height="50" rx="6" fill="#2d1215" stroke="#ef4444" stroke-width="1"/>
    <text x="25" y="105" fill="#fca5a5" font-size="10" font-family="monospace">EuroSAT_RGB/Forest/</text>
    <text x="25" y="122" fill="#ef4444" font-size="10.5" font-weight="700">Forest_124.jpg</text>

    <text x="15" y="160" fill="#94a3b8" font-size="11">If an unsupervised model reads</text>
    <text x="15" y="177" fill="#94a3b8" font-size="11">the folder name "Forest",</text>
    <text x="15" y="195" fill="#f87171" font-size="11" font-weight="600">it constitutes data cheating!</text>

    <line x1="15" y1="215" x2="235" y2="215" stroke="#1e293b" stroke-width="1.5"/>

    <text x="15" y="240" fill="#34d399" font-size="11" font-weight="700">SOLUTION IN CODE:</text>
    <text x="15" y="258" fill="#94a3b8" font-size="10.5">• Path stripped on ingestion</text>
    <text x="15" y="275" fill="#94a3b8" font-size="10.5">• Only raw RGB bytes read</text>
  </g>

  <!-- Arrow 1 to 2 -->
  <line x1="290" y1="275" x2="330" y2="275" stroke="#38bdf8" stroke-width="2.5" marker-end="url(#arrow)"/>

  <!-- Step 2: SHA-256 Splitting -->
  <g transform="translate(340, 130)" filter="url(#shadow)">
    <rect width="280" height="290" rx="10" fill="url(#cardGrad)" stroke="#1e293b" stroke-width="1.5"/>
    <rect x="0" y="0" width="280" height="40" rx="10" fill="#1e293b"/>
    <text x="15" y="26" fill="#f8fafc" font-size="13" font-weight="700">2. Ingestion Adapter (study.py)</text>

    <!-- Code Block -->
    <rect x="15" y="55" width="250" height="75" rx="6" fill="#090d16" stroke="#334155" stroke-width="1"/>
    <text x="25" y="75" fill="#94a3b8" font-size="10" font-family="monospace">rgb = image.convert("RGB")</text>
    <text x="25" y="93" fill="#38bdf8" font-size="10" font-family="monospace">patch_id = "p" + hashlib.</text>
    <text x="35" y="108" fill="#38bdf8" font-size="10" font-family="monospace">sha256(rgb.tobytes())</text>
    <text x="35" y="122" fill="#38bdf8" font-size="10" font-family="monospace">.hexdigest()[:20]</text>

    <line x1="15" y1="145" x2="265" y2="145" stroke="#1e293b" stroke-width="1.5"/>

    <!-- Forking paths -->
    <text x="15" y="170" fill="#38bdf8" font-size="11" font-weight="700">BRANCH A: Numerical Pipeline</text>
    <text x="15" y="188" fill="#e2e8f0" font-size="10.5">↳ extract_features(rgb) → 78 floats</text>
    <text x="15" y="205" fill="#34d399" font-size="10.5">Saved to: <tspan font-family="monospace">features.npz</tspan> (NO LABELS)</text>

    <text x="15" y="235" fill="#a855f7" font-size="11" font-weight="700">BRANCH B: Quarantined Truth</text>
    <text x="15" y="253" fill="#e2e8f0" font-size="10.5">↳ annotations[patch_id] = "Forest"</text>
    <text x="15" y="270" fill="#c084fc" font-size="10.5">Saved to: <tspan font-family="monospace">reference_labels.json</tspan></text>
  </g>

  <!-- Arrow 2 to 3 -->
  <line x1="620" y1="210" x2="660" y2="210" stroke="#34d399" stroke-width="2.5" marker-end="url(#arrow)"/>
  <line x1="620" y1="350" x2="660" y2="350" stroke="#c084fc" stroke-width="2.5" marker-end="url(#arrow)"/>

  <!-- Step 3: Sealed Execution -->
  <g transform="translate(670, 130)" filter="url(#shadow)">
    <rect width="290" height="150" rx="10" fill="#064e3b" stroke="#059669" stroke-width="1.5"/>
    <text x="15" y="25" fill="#34d399" font-size="12" font-weight="700">3A. STRICTLY BLIND TRAINING</text>
    <text x="15" y="47" fill="#f8fafc" font-size="11.5">• StandardScaler(z = (x - μ)/σ)</text>
    <text x="15" y="67" fill="#f8fafc" font-size="11.5">• PCA Model (28 components, 95% variance)</text>
    <text x="15" y="87" fill="#f8fafc" font-size="11.5">• K-Means++ Clustering (K = 10)</text>
    <text x="15" y="107" fill="#f8fafc" font-size="11.5">• Silhouette (0.245) &amp; Davies-Bouldin (1.42)</text>
    <text x="15" y="132" fill="#6ee7b7" font-size="11" font-weight="700">COMPLETED WITH ZERO LABELS SEEN</text>
  </g>

  <g transform="translate(670, 295)" filter="url(#shadow)">
    <rect width="290" height="125" rx="10" fill="#2e1065" stroke="#9333ea" stroke-width="1.5"/>
    <text x="15" y="25" fill="#d8b4fe" font-size="12" font-weight="700">3B. POST-SELECTION SEALED AUDIT</text>
    <text x="15" y="47" fill="#f8fafc" font-size="11.5">Opened strictly AFTER models are frozen:</text>
    <text x="15" y="70" fill="#e2e8f0" font-size="11">• Study Cohort ARI: <tspan fill="#38bdf8" font-weight="700">0.299</tspan> · NMI: <tspan fill="#38bdf8" font-weight="700">0.429</tspan></text>
    <text x="15" y="90" fill="#e2e8f0" font-size="11">• Holdout Cohort ARI: <tspan fill="#38bdf8" font-weight="700">0.301</tspan> · NMI: <tspan fill="#38bdf8" font-weight="700">0.435</tspan></text>
    <text x="15" y="112" fill="#c084fc" font-size="10.5" font-weight="600">Evaluates natural alignment without leakage.</text>
  </g>
</svg>'''

(OUT_DIR / "pipeline-architecture.svg").write_text(build_pipeline_svg())
(OUT_DIR / "feature-engineering.svg").write_text(build_features_svg())
(OUT_DIR / "pca-variance-scree.svg").write_text(build_scree_svg())
(OUT_DIR / "label-quarantine.svg").write_text(build_quarantine_svg())
print("Generated 4 SVG diagrams successfully in docs/diagrams/")
