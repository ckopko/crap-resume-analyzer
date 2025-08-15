import pypdf

def extract_text_from_pdf(file_obj):
    """
    Extracts text from an in-memory PDF file object.
    """
    try:
        pdf_reader = pypdf.PdfReader(file_obj)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return f"Error reading PDF file: {e}"