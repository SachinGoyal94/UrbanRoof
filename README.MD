
<div align="center">

<img src="img.png" width="180" alt="UrbanRoof Logo" />

# UrbanRoof — Professional AI Report Generator

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google%20Gemini-API-4285F4?style=for-the-badge&logo=google&logoColor=white)
![ReportLab](https://img.shields.io/badge/ReportLab-4.0+-FF6B6B?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Transform raw inspection documents into professional, client-ready Detailed Diagnostic Reports (DDRs) with Multi-Agent AI.**

[⚡ Quick Start](#-quick-start) • [🏗️ Architecture](#-architecture) • [📡 API](#-api-documentation) • [📁 Structure](#-project-structure)

</div>

---

## 📖 Overview

**UrbanRoof** is a production-ready AI system designed to automate the creation of complex building inspection reports. It orchestrates a team of **7 specialized AI agents** to read visual inspection reports and thermal imaging data, categorize simple and complex issues, diagnosis root causes, and generate a fully formatted PDF report that looks like it was written by a human expert.

### Key Capabilities
- **Multi-Modal Input:** Processes Text, Tables, and Images from multiple PDFs.
- **Intelligent Synthesis:** Merges visual observations with thermal anomalies.
- **Dynamic Formatting:** Auto-generates layouts, Tables of Contents, and side-by-side image comparisons.
- **Self-Correction:** Includes a QA Agent loop that rejects and fixes low-quality output before final delivery.

---

## ⚡ Features

| Feature | Description |
|---------|-------------|
| **🤖 7-Agent Pipeline** | Orchestrator, Inspection Analyst, Thermal Analyst, Root Cause, Recommendations, Synthesis, QA. |
| **📄 Professional PDF** | Branded header/footer, hexagonal cover page, auto-pagination, color-coded severity tables. |
| **🔍 Deep Discovery** | No hardcoded area names. The system "learns" the building structure from the uploaded report. |
| **🌡️ Thermal Fusion** | Automatically pairs visual photos with their corresponding thermal images based on context. |
| **🛡️ Robustness** | Handles missing data gracefully (`"Not Available"`) and explicit conflicts. |
| **🚀 Async API** | FastAPI backend with background job processing for long-running report generation (30-90s). |

---

## 📁 Project Structure

```bash
UrbanRoof/
├── 📄 requirements.txt           # Python dependencies
├── 🚀 main.py                    # FastAPI server entry point
├── 🔄 pipeline.py                # Main workflow orchestrator
├── 🔧 config.py                  # Environment configuration
├── 📄 DDR_System_Documentation.docx              # Project Documentation
│
├── 🤖 agents/                    # AI Agent Definitions
│   ├── orchestrator.py           # Plan & Area Discovery
│   ├── inspection_analyst.py     # Visual Finding Extractor
│   ├── thermal_analyst.py        # Thermal Image Interpreter
│   ├── root_cause_analyst.py     # Diagnosis Engine
│   ├── recommendations_agent.py  # Repair Solution Generator
│   ├── synthesis_agent.py        # Final Content Merger
│   └── qa_agent.py               # Quality Assurance Loop
│
├── 📦 extractors/                # Document Processing
│   ├── text_extractor.py         # PDF Text Parsing
│   └── image_extractor.py        # PDF -> Image Conversion
│
├── 🔀 merger/                    # Data Merging & Extraction
│   ├── thermal_extractor.py      # Thermal Metadata Parsing
│   ├── conflict_handler.py       # Visual vs Thermal conflict resolution
│   └── data_merger.py            # Data aggregation logic
│
├── 🛠️ generator/                 # LLM & Validation Utilities
│   ├── llm_client.py             # Gemini API Wrapper
│   ├── prompt_builder.py         # Prompt engineering helpers
│   └── ddr_validator.py          # Output validation logic
│
├── 📄 report/                    # Output Generation
│   └── pdf_assembler.py          # ReportLab PDF Engine
│
├── 📂 outputs/                   # Generated Reports (Artifacts)
└── 📂 temp_images/               # Intermediate Image Storage
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- [Poppler](https://github.com/oschwartz10612/poppler-windows/releases/) (for PDF processing)
- A [Google Gemini API Key](https://aistudio.google.com/)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/urbanroof.git
cd UrbanRoof

# Create virtual environment
python -m venv venv
# Activate:
#   Windows: .\venv\Scripts\activate
#   Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Edit `.env`:
```ini
GEMINI_KEY=AIzaSy...YourKeyHere...
MODEL_NAME=gemini-3.1-flash-lite-preview
```

### 4. Run the Server

```bash
python -m uvicorn main:app --reload
```
Review documentation at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📡 API Documentation

### Generate Report (Synchronous)
**POST** `/generate`
- Uploads files and waits for the process to complete.
- **Inputs:** `inspection_pdf`, `thermal_pdf`, `sample_ddr_pdf` (Reference style)

```bash
curl -X POST http://localhost:8000/generate \
  -H "accept: application/pdf" \
  -H "Content-Type: multipart/form-data" \
  -F "inspection_pdf=@./docs/Sample_Report.pdf" \
  -F "thermal_pdf=@./docs/Thermal_Images.pdf" \
  -F "sample_ddr_pdf=@./docs/Main_DDR.pdf" \
  --output report.pdf
```

### Generate Report (Asynchronous)
**POST** `/generate/async`
- Triggers a background job and returns a `job_id`.

**GET** `/status/{job_id}`
- Check progress (`queued` -> `processing` -> `done` / `failed`).

**GET** `/download/{job_id}`
- Download the final PDF.

---

## 🏗️ Architecture

The system uses a sequential multi-agent chain with a feedback loop:

1.  **Orchestrator:** Reads all docs, identifies "Areas" (e.g., "Kitchen", "Terrace"), and maps page numbers to these areas.
2.  **Extractors:** Converts PDF pages to images and extracts raw text.
3.  **Parallel Analysis:**
    *   *Inspection Agent* reads visual reports.
    *   *Thermal Agent* reads thermal reports.
4.  **Root Cause Agent:** Synthesizes findings from both sources to determine root cause and severity.
5.  **Recommendations Agent:** drafting repair scopes (materials + methods).
6.  **Synthesis Agent:** Drafts the narrative text for the report.
7.  **QA Agent:** Reviews the draft. If it fails (e.g., missing sections), it sends it back to Synthesis with correction instructions.
8.  **PDF Assembler:** Compiles text, images, and tables into the final PDF.

---



