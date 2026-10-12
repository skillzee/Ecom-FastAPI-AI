# Everyday project pack

Poster, LLD and assistance prompt log updated from the repository on 12 October 2026.

- **Everyday-LLD.pdf**: 8-page current design with architecture, entity, authentication and cache diagrams, table definitions, API contracts, all seven agent tools, ownership rules and operational limits. The Markdown file is the editable source.
- **Everyday-Project-Prompt.pdf**: 2-page log of selected development assistance prompts, grouped and condensed by topic rather than presented as verbatim chat. The Markdown file is the editable source.
- **Everyday-Poster.pdf**: one-page A3 portrait poster for printing.
- **Everyday-Poster.png**: poster image for sharing (1984 x 2806 pixels).
- **Everyday-Books-Illustration.png**: new generated book artwork used on the updated poster; not actual inventory photography.
- **Everyday-Artwork-Prompt.txt**: exact prompt and generation method for the current book artwork.

The design documents current code, including book comparison, the shared five-minute in-memory source cache, chat product cards and owned order lookup through the agent. Checkout saves unpaid orders. Persistent chat, payments, inventory quantities and administrator protection for catalog writes are future work. Product seeding is automatic; policy-PDF ingestion is manual.

The earlier `Everyday-Presentation.pptx`/PDF, `Everyday-Poster-Editable.pptx` and `Everyday-Illustration.png` are retained as 11 October legacy assets. They describe the previous catalog and were not updated in this task. Use the current poster PDF/PNG, LLD and prompt log for this submission.

Editable documentation sources and `build_docs.py` live in `docs/project/`. The builder uses ReportLab, Pillow and PyMuPDF and the installed Arial, Georgia and Consolas fonts. Build and QA files live in the ignored `tmp/project-artifacts/` directory and are not part of the delivery pack.
