# 🎨 PDF Processing - Visual Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        1. UPLOAD & VALIDATION                           │
│  User uploads PDF → FastAPI endpoint → Save to data/uploads/           │
│  Create Document record in DB (status: "pending")                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     2. PDF EXTRACTION (PARALLEL)                        │
│                                                                         │
│  ThreadPoolExecutor (auto workers)                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       ┌──────────┐         │
│  │ Thread 1 │  │ Thread 2 │  │ Thread 3 │  ...  │ Thread N │         │
│  │  Page 1  │  │  Page 2  │  │  Page 3  │       │  Page N  │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       └────┬─────┘         │
│       │             │             │                    │                │
│       ▼             ▼             ▼                    ▼                │
│  pymupdf4llm    pymupdf4llm   pymupdf4llm        pymupdf4llm           │
│  - Extract text - Extract text - Extract text    - Extract text        │
│  - Save images  - Save images  - Save images     - Save images         │
│       │             │             │                    │                │
│       ▼             ▼             ▼                    ▼                │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │  Output:                                                │           │
│  │  pages[] = ["Page 1 text", "Page 2 text", ...]        │           │
│  │  image_metadata = {                                     │           │
│  │    1: [],  # No images                                  │           │
│  │    5: [{filename: "page_5_image_0.png", ...}],         │           │
│  │    10: [{...}, {...}]  # 2 images                       │           │
│  │  }                                                      │           │
│  └─────────────────────────────────────────────────────────┘           │
│                                                                         │
│  Images saved to: data/output/{timestamp}/images/                     │
│  Format: page_{N}_image_{I}.png                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         3. TOC PARSING                                  │
│                                                                         │
│  Take first 10 pages → Send to AI → Parse Table of Contents           │
│                                                                         │
│  Input:  "1. Введение ... стр. 1"                                     │
│          "2. Требования ... стр. 10"                                   │
│          "2.1 Общие ... стр. 10"                                       │
│          "3. Технические ... стр. 33"                                  │
│                                                                         │
│  Output: [                                                             │
│    {number: "1", title: "Введение", page_start: 1},                   │
│    {number: "2", title: "Требования", page_start: 10},                │
│    {number: "2.1", title: "Общие", page_start: 10},                   │
│    {number: "3", title: "Технические", page_start: 33}                │
│  ]                                                                     │
│                                                                         │
│  Fallback: If TOC parsing fails → create automatic sections (~20pp)   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               4. REQUIREMENTS EXTRACTION (BY SECTIONS)                  │
│                                                                         │
│  FOR EACH SECTION:                                                     │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐    │
│  │ Section 2: "Требования" (pages 10-32)                         │    │
│  │                                                                 │    │
│  │ Step 1: TEXT PROCESSING                                        │    │
│  │ ┌─────────────────────────────────────────────────────────┐   │    │
│  │ │ Combine pages 10-32 text                                │   │    │
│  │ │ Send to AI: extract_requirements()                      │   │    │
│  │ │ ↓                                                        │   │    │
│  │ │ AI returns: [                                           │   │    │
│  │ │   {id: "REQ-2-001", text: "...", type: "...", ...},    │   │    │
│  │ │   {id: "REQ-2-002", text: "...", type: "...", ...},    │   │    │
│  │ │   ...                                                    │   │    │
│  │ │ ]                                                        │   │    │
│  │ └─────────────────────────────────────────────────────────┘   │    │
│  │                                                                 │    │
│  │ Step 2: IMAGE PROCESSING                                       │    │
│  │ ┌─────────────────────────────────────────────────────────┐   │    │
│  │ │ Find images in pages 10-32                              │   │    │
│  │ │ image_metadata[10] = [img_0.png, img_1.png]            │   │    │
│  │ │ image_metadata[12] = [img_0.png]                        │   │    │
│  │ │ image_metadata[31] = [img_0.png, img_1.png, img_2.png] │   │    │
│  │ │                                                          │   │    │
│  │ │ FOR EACH IMAGE (6 images total):                        │   │    │
│  │ │   ┌──────────────────────────────────────────────┐     │   │    │
│  │ │   │ page_10_image_0.png                          │     │   │    │
│  │ │   │ ├─ Encode to Base64                          │     │   │    │
│  │ │   │ ├─ Create multimodal message:                │     │   │    │
│  │ │   │ │  {                                          │     │   │    │
│  │ │   │ │    role: "user",                            │     │   │    │
│  │ │   │ │    content: [                               │     │   │    │
│  │ │   │ │      {type: "text", text: "Раздел 2..."},  │     │   │    │
│  │ │   │ │      {type: "image_url", image_url: {...}} │     │   │    │
│  │ │   │ │    ]                                        │     │   │    │
│  │ │   │ │  }                                          │     │   │    │
│  │ │   │ └─ Send to AI → Get requirements            │     │   │    │
│  │ │   └──────────────────────────────────────────────┘     │   │    │
│  │ │   (Same for img_1, img_2, ... img_6)                   │   │    │
│  │ └─────────────────────────────────────────────────────────┘   │    │
│  │                                                                 │    │
│  │ Step 3: COMBINE & SAVE                                         │    │
│  │ all_requirements = text_reqs + image_reqs                      │    │
│  │ Save to DB: Section, Requirements                              │    │
│  └───────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  REPEAT FOR ALL SECTIONS (5 sections total)                           │
│                                                                         │
│  Total AI requests:                                                    │
│  - Text: 5 requests (one per section)                                 │
│  - Images: 219 requests (one per image)                               │
│  = 224 requests total                                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      5. METRICS CALCULATION                             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │ Find pages with requirements:                                   │  │
│  │                                                                  │  │
│  │ pages_with_requirements = set()                                 │  │
│  │ for section in sections:                                        │  │
│  │   for req in section.requirements:                              │  │
│  │     pages_with_requirements.add(req.page_number)                │  │
│  │                                                                  │  │
│  │ Result: {10, 11, 12, 31, 32, 33, ...} = 23 pages                │  │
│  │                                                                  │  │
│  │ Calculate skipped:                                              │  │
│  │ all_pages = {1, 2, 3, ..., 225}                                 │  │
│  │ skipped = all_pages - pages_with_requirements                   │  │
│  │ Result: [1, 2, 3, 4, 5, ...] = 202 pages                        │  │
│  │                                                                  │  │
│  │ Metrics:                                                         │  │
│  │ ├─ total_pages: 225                                             │  │
│  │ ├─ processed_pages: 23  (with requirements)                     │  │
│  │ ├─ skipped_pages: [1,2,3,4,5,...]  (without requirements)      │  │
│  │ ├─ coverage_percent: 10.2%                                      │  │
│  │ ├─ requirements_count: 662                                      │  │
│  │ └─ requirements_by_type: {...}                                  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Save to DB: coverage_metrics table                                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      6. GENERATE REPORTS                                │
│                                                                         │
│  ├─ JSON registry: data/output/{timestamp}/registry.json              │
│  │  └─ Contains: sections[], requirements[], metadata                 │
│  │                                                                     │
│  └─ Word document (optional): data/output/{timestamp}/result.docx     │
│     └─ Formatted document with all requirements                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        7. UPDATE DB STATUS                              │
│                                                                         │
│  Document status: "pending" → "processing" → "completed"              │
│                                                                         │
│  Final DB state:                                                       │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ documents                                                       │   │
│  │   id: 1                                                         │   │
│  │   filename: "ЗТ УПН 04.pdf"                                     │   │
│  │   status: "completed"                                           │   │
│  │   total_pages: 225                                              │   │
│  │                                                                  │   │
│  │ sections (5 rows)                                               │   │
│  │   └─ section_number, title, page_start, page_end               │   │
│  │                                                                  │   │
│  │ requirements (662 rows)                                         │   │
│  │   └─ text, type, priority, page_number, source_type            │   │
│  │      (source_type: "text" or "image")                           │   │
│  │                                                                  │   │
│  │ coverage_metrics (1 row)                                        │   │
│  │   total_pages: 225                                              │   │
│  │   processed_pages: 23                                           │   │
│  │   skipped_pages: [1,2,3,...]                                    │   │
│  │   coverage_percent: 10.2                                        │   │
│  │   requirements_count: 662                                       │   │
│  └────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Points Visualization

### Image Processing Flow

```
PDF Page 10
    │
    ├─ Text: "Насосы должны обеспечивать..."
    │  └─ Sent to AI as part of Section 2 text
    │
    └─ Images: 2 images detected
       │
       ├─ Image 0: Technical drawing
       │  ├─ Saved as: page_10_image_0.png
       │  ├─ Encoded to Base64
       │  ├─ Sent to AI (separate request)
       │  └─ AI returns: [REQ-2-IMG-001, REQ-2-IMG-002, ...]
       │
       └─ Image 1: Table with specifications
          ├─ Saved as: page_10_image_1.png
          ├─ Encoded to Base64
          ├─ Sent to AI (separate request)
          └─ AI returns: [REQ-2-IMG-003, REQ-2-IMG-004, ...]
```

### Section Processing Timeline

```
Section 2 (pages 10-32, 23 pages total)
│
├─ [00:00] Start processing section
│
├─ [00:01] Combine 23 pages of text
│  └─ Send to AI (1 request, ~50K tokens)
│
├─ [00:15] AI response received
│  └─ 145 text-based requirements extracted
│
├─ [00:16] Find images in pages 10-32
│  └─ Found 6 images
│
├─ [00:17] Process image 1/6 (page_10_image_0.png)
│  └─ AI response: 2 requirements
│
├─ [00:20] Process image 2/6 (page_10_image_1.png)
│  └─ AI response: 3 requirements
│
├─ [00:23] Process image 3/6 (page_12_image_0.png)
│  └─ AI response: 1 requirement
│
├─ [00:26] Process image 4/6 (page_31_image_0.png)
│  └─ AI response: 5 requirements
│
├─ [00:29] Process image 5/6 (page_31_image_1.png)
│  └─ AI response: 2 requirements
│
├─ [00:32] Process image 6/6 (page_31_image_2.png)
│  └─ AI response: 4 requirements
│
└─ [00:33] Section complete
   ├─ Text requirements: 145
   ├─ Image requirements: 17
   └─ Total: 162 requirements

Section processing time: ~33 seconds
Total AI requests: 7 (1 text + 6 images)
```

### Coverage Calculation

```
Document: 225 pages
│
├─ Pages WITH requirements (processed):
│  10, 11, 12, 31, 32, 33, 34, 35, 36, 37, 40, 41, 42, 43,
│  50, 51, 52, 150, 151, 152, 153, 154, 155
│  = 23 pages (10.2%)
│
└─ Pages WITHOUT requirements (skipped):
   1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 14, 15, ..., 224, 225
   = 202 pages (89.8%)
   │
   ├─ Title pages (1-5)
   ├─ Table of contents (6-9)
   ├─ Empty pages (various)
   ├─ Appendices with only images/tables (180-220)
   └─ References (221-225)
```
