from docx import Document


def load_docx(path: str) -> Document:
    return Document(path)


def iter_text_blocks(doc: Document):
    """Yield tuples (paragraph, text) for body, headers, footers, and table cells."""
    for paragraph in doc.paragraphs:
        yield paragraph, paragraph.text
    for section in doc.sections:
        header = section.header
        footer = section.footer
        if header is not None:
            for p in header.paragraphs:
                yield p, p.text
        if footer is not None:
            for p in footer.paragraphs:
                yield p, p.text
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for p in cell.paragraphs:
                    yield p, p.text
