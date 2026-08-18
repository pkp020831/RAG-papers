from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

OUT = Path("output/pdf")
OUT.mkdir(parents=True, exist_ok=True)

PAPERS = [
    {
        "file": "synthetic_001_edge_retrieval.pdf",
        "title": "Energy-Aware Retrieval on Heterogeneous Edge Devices",
        "authors": "Mina Park, Joonho Lee, Elena Rossi",
        "venue": "Proceedings of the Synthetic Systems Workshop, 2026",
        "keywords": "edge computing; retrieval; energy efficiency; vector search",
        "abstract": "We introduce a simulated scheduling method for approximate vector retrieval across battery-constrained edge devices. In a controlled synthetic benchmark, the method reduces modeled energy use while retaining competitive top-k recall. This document is a fictional paper created solely for software and database testing; all authors, results, and references are invented.",
        "sections": [
            ("1. Introduction", "Retrieval systems increasingly run near data sources. We study a fictional deployment in which a coordinator assigns queries to devices with different latency and battery profiles. The objective is to make test corpora contain plausible research language, structured headings, and searchable technical terms."),
            ("2. Method", "Our simulator scores each candidate device by estimated energy cost, cache affinity, and response-time budget. A simple threshold policy routes low-urgency requests toward inexpensive approximate indexes and reserves exact search for high-confidence cases."),
            ("3. Results", "Across 12 generated workloads, the synthetic policy achieved a mean recall@10 of 0.91 and a modeled energy reduction of 27 percent versus a latency-only baseline. These numbers are fabricated and must not be cited as experimental evidence."),
            ("4. Conclusion", "The paper provides realistic metadata and prose for ingestion tests, ranking experiments, and semantic search evaluation."),
        ],
    },
    {
        "file": "synthetic_002_tmd_growth.pdf",
        "title": "Seeded Growth Windows for Monolayer Molybdenum Disulfide",
        "authors": "Ara Kim, Daniel M. Cole, Sora Choi",
        "venue": "Journal of Fictional Two-Dimensional Materials, 2025",
        "keywords": "MoS2; monolayer; CVD; two-dimensional materials; nucleation",
        "abstract": "This fictional study describes a synthetic chemical-vapor-deposition data set for monolayer molybdenum disulfide. It is designed to resemble materials-science literature for testing document parsing and retrieval. No experiment was performed and all values are simulated.",
        "sections": [
            ("1. Background", "Transition-metal dichalcogenides are commonly used as examples in two-dimensional materials research. We construct a plausible narrative around seed density, sulfur flux, and substrate temperature without claiming any real observation."),
            ("2. Synthetic Experimental Design", "Virtual sapphire substrates were assigned seed densities from 0.2 to 1.0 arbitrary units. The simulated reactor sweep combined temperatures between 680 and 760 degrees C with three sulfur-flow settings."),
            ("3. Simulated Observations", "The generated records show a broad optimum near intermediate seed density, where triangular domains reach a median synthetic width of 42 micrometers. Raman peak positions and photoluminescence intensities are placeholders used to exercise numeric extraction."),
            ("4. Data Availability", "All reported measurements are fictional. This PDF is an artificial test artifact, not a scientific source."),
        ],
    },
    {
        "file": "synthetic_003_clinical_timeline.pdf",
        "title": "Temporal Summarization of Longitudinal Clinical Notes Using Structured Prompts",
        "authors": "Hana Seo, Priya Natarajan, Lucas Weber",
        "venue": "Synthetic Health Informatics Review, 2026",
        "keywords": "clinical NLP; timeline summarization; prompts; safety evaluation",
        "abstract": "We present a fabricated evaluation of prompt-guided timeline summarization over de-identified-like synthetic clinical notes. The purpose is to provide a health-domain document with realistic headings and caveats for retrieval-system tests. It contains no patient data and no clinical guidance.",
        "sections": [
            ("1. Objective", "Longitudinal records include repeated events, uncertainty, and conflicting statements. Our fictional task asks a language model to group generated note fragments into dated episodes while preserving source uncertainty."),
            ("2. Evaluation Protocol", "We generated 240 mock patient timelines from templates. Reviewers in the simulation scored chronology, omission rate, and uncertainty retention. The protocol is not approved research and does not involve humans."),
            ("3. Findings", "The synthetic prompt achieved a chronology score of 0.86 and preserved explicit uncertainty in 88 percent of generated cases. Error examples included incorrect medication start dates and merged encounters, illustrating test cases for evaluation tooling."),
            ("4. Limitations", "These fabricated outcomes cannot establish medical performance, safety, or usefulness. Any real clinical application requires domain validation and governance."),
        ],
    },
    {
        "file": "synthetic_004_flood_forecasting.pdf",
        "title": "Graph-Based Flood Nowcasting from Sparse Urban Sensors",
        "authors": "Noah Bennett, Yejin Han, Camila Duarte",
        "venue": "International Conference on Imaginary Climate Analytics, 2024",
        "keywords": "flood forecasting; graph neural networks; urban sensing; nowcasting",
        "abstract": "This is a fabricated machine-learning paper about forecasting street-level flood depth from sparse urban sensors. It offers an environmental-science vocabulary profile for testing citation extraction, filtering, and vector retrieval. Maps, locations, and performance figures are entirely invented.",
        "sections": [
            ("1. Problem Setting", "Fast precipitation events can outpace manual reporting. We model a fictional city as a drainage graph whose nodes represent sensor sites and whose edges approximate runoff connectivity."),
            ("2. Model", "A temporal graph network consumes rainfall intensity, prior depth estimates, and node elevation features. A learned attention layer weights upstream observations during short prediction horizons."),
            ("3. Benchmark", "On 38 simulated storms, the method reports a fabricated mean absolute error of 6.4 centimeters at a 30-minute horizon. Baselines include persistence, linear interpolation, and a non-graph recurrent model."),
            ("4. Reproducibility Note", "The benchmark is synthetic. It intentionally includes method details and numerical results so a paper database can test facets, snippets, and result-oriented queries."),
        ],
    },
    {
        "file": "synthetic_005_robot_manipulation.pdf",
        "title": "Language-Conditioned Recovery Behaviors for Tabletop Robot Manipulation",
        "authors": "Taeho Lim, Sophie Martin, Omar Al-Karim",
        "venue": "Robotics Letters for Test Collections, 2026",
        "keywords": "robot manipulation; recovery policies; language conditioning; simulation",
        "abstract": "We describe a wholly synthetic robotics study in which a tabletop arm recovers after grasp and placement failures using language-conditioned recovery options. The document exists only to test a paper-search database and should not be interpreted as a report of real hardware results.",
        "sections": [
            ("1. Overview", "Robotic tasks fail for many reasons: an object may slip, a pose may be unreachable, or a scene may change. We generate a test corpus that associates these failures with concise recovery instructions and action labels."),
            ("2. Recovery Library", "The fictional library contains re-observe, retreat, regrasp, clear workspace, and request assistance behaviors. A text encoder maps generated operator instructions to recovery-policy embeddings."),
            ("3. Synthetic Evaluation", "In 500 simulated episodes, language conditioning selected the intended recovery in 82 percent of cases. The hardest category combined occlusion with object motion. All episode counts and scores are invented."),
            ("4. Conclusion", "The result is a compact, structured example of robotics research writing, suitable for PDFs, OCR, metadata indexing, and semantic search demos."),
        ],
    },
]

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="PaperTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=9))
styles.add(ParagraphStyle(name="Authors", parent=styles["Normal"], fontSize=10, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#334155"), spaceAfter=4))
styles.add(ParagraphStyle(name="Meta", parent=styles["Normal"], fontSize=8.5, leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#64748B"), spaceAfter=14))
styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=colors.HexColor("#123B5D"), spaceBefore=10, spaceAfter=5))
styles.add(ParagraphStyle(name="BodyJ", parent=styles["BodyText"], fontSize=10, leading=15, alignment=TA_JUSTIFY, spaceAfter=8))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#475569")))

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.line(20*mm, 15*mm, 190*mm, 15*mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(20*mm, 10*mm, "SYNTHETIC TEST PAPER - NOT FOR SCIENTIFIC USE")
    canvas.drawRightString(190*mm, 10*mm, f"Page {doc.page}")
    canvas.restoreState()

for p in PAPERS:
    doc = SimpleDocTemplate(str(OUT / p["file"]), pagesize=A4, rightMargin=20*mm, leftMargin=20*mm, topMargin=18*mm, bottomMargin=22*mm, title=p["title"], author=p["authors"])
    story = [
        Paragraph("SYNTHETIC PAPER COLLECTION", styles["Meta"]),
        Paragraph(p["title"], styles["PaperTitle"]),
        Paragraph(p["authors"], styles["Authors"]),
        Paragraph(p["venue"], styles["Meta"]),
    ]
    warning = Table([[Paragraph("<b>Test-data notice.</b> This is a generated fictional paper for database testing. It contains no real study, data, participants, or findings.", styles["Small"])]], colWidths=[170*mm])
    warning.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#FFF7ED")), ("BOX", (0,0), (-1,-1), 0.6, colors.HexColor("#FB923C")), ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7), ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6)]))
    story += [warning, Spacer(1, 10), Paragraph("Abstract", styles["Section"]), Paragraph(p["abstract"], styles["BodyJ"])]
    meta = [["Keywords", p["keywords"]], ["Document ID", p["file"].replace(".pdf", "").upper()], ["Status", "Synthetic test artifact"]]
    table = Table([[Paragraph(f"<b>{a}</b>", styles["Small"]), Paragraph(b, styles["Small"])] for a,b in meta], colWidths=[31*mm, 139*mm])
    table.setStyle(TableStyle([("BACKGROUND", (0,0), (0,-1), colors.HexColor("#E2E8F0")), ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#CBD5E1")), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6), ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5)]))
    story += [table, Spacer(1, 8)]
    for heading, body in p["sections"]:
        story += [Paragraph(heading, styles["Section"]), Paragraph(body, styles["BodyJ"])]
    story += [Paragraph("References", styles["Section"]), Paragraph("[1] Placeholder, A. (2026). Example citation generated for test parsing. <i>Synthetic Archive</i>, 1(1), 1-8.<br/>[2] Placeholder, B. (2025). Retrieval and indexing methods in fabricated corpora. <i>Test Data Journal</i>, 4(2), 12-19.", styles["BodyJ"])]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)

print(f"Created {len(PAPERS)} PDFs in {OUT}")
