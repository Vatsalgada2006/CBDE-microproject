import os
import mimetypes
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ExtractionService:
    def __init__(self):
        # Initialize any necessary resources
        pass

    def extract_text(self, file_path: str, content_type: str = None, filename: str = None) -> Tuple[str, str]:
        """
        Extract text from a file.
        Returns a tuple (extracted_text, status) where status is one of:
        'success', 'unsupported', 'failed'
        """
        if content_type is None and filename:
            content_type, _ = mimetypes.guess_type(filename)
            if content_type is None:
                content_type = 'application/octet-stream'

        try:
            if content_type == 'application/pdf' or (filename and filename.lower().endswith('.pdf')):
                return self._extract_pdf(file_path), 'success'
            elif content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' or \
                 (filename and filename.lower().endswith('.docx')):
                return self._extract_docx(file_path), 'success'
            elif content_type == 'text/plain' or (filename and filename.lower().endswith('.txt')):
                return self._extract_txt(file_path), 'success'
            elif content_type == 'application/vnd.openxmlformats-officedocument.presentationml.presentation' or \
                 (filename and filename.lower().endswith('.pptx')):
                return self._extract_pptx(file_path), 'success'
            elif content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or \
                 (filename and filename.lower().endswith('.xlsx')):
                return self._extract_xlsx(file_path), 'success'
            else:
                logger.warning(f"Unsupported content type: {content_type} for file {filename}")
                return '', 'unsupported'
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}")
            return '', 'failed'

    def _extract_pdf(self, file_path: str) -> str:
        import PyPDF2
        text = ""
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _extract_docx(self, file_path: str) -> str:
        import docx
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text

    def _extract_txt(self, file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()

    def _extract_pptx(self, file_path: str) -> str:
        import pptx
        presentation = pptx.Presentation(file_path)
        text = ""
        for slide in presentation.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text += shape.text + "\n"
        return text

    def _extract_xlsx(self, file_path: str) -> str:
        import openpyxl
        workbook = openpyxl.load_workbook(file_path)
        text = ""
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            for row in sheet.iter_rows(values_only=True):
                for cell in row:
                    if cell is not None:
                        text += str(cell) + " "
            text += "\n"
        return text