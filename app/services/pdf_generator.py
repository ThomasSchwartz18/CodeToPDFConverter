import os
import fitz
import textwrap
from docx import Document
from app.config.settings import Config

class PDFGenerator:
    def __init__(self, margin=None, header_note="", footer_note="", 
                 orientation="portrait", page_size=(612, 792), show_file_info=True):
        self.margin = margin or Config.DEFAULT_MARGIN
        self.header_note = header_note
        self.footer_note = footer_note
        self.page_size = page_size
        self.show_file_info = show_file_info
        self.font_size = Config.DEFAULT_FONT_SIZE
        self.line_height = Config.DEFAULT_LINE_HEIGHT
        self.max_chars_per_line = Config.MAX_CHARS_PER_LINE
        self.reserved_space = self.margin + (self.line_height * 2 if footer_note else 0)

    def _insert_page_header(self, page, y_position, file_name, relative_path):
        """Helper to insert header note and file info."""
        if self.header_note:
            page.insert_text((self.margin, y_position), self.header_note, 
                           fontsize=12, fontname="courier-bold")
            y_position += self.line_height * 2
            
        if self.show_file_info:
            page.insert_text((self.margin, y_position), f"File: {file_name}", 
                           fontsize=12, fontname="courier-bold")
            y_position += self.line_height * 2
            page.insert_text((self.margin, y_position), f"File Path: {relative_path}", 
                           fontsize=10, fontname="courier-bold")
            y_position += self.line_height * 2
            
        return y_position

    def generate(self, file_paths, output_pdf_path):
        """
        Generates a PDF from the provided file paths.
        Supports text files, Word documents (.docx), PDFs, and image files.
        """
        page_width, page_height = self.page_size
        doc = fitz.open()

        for file_path in file_paths:
            file_name = os.path.basename(file_path)
            # Skip system files and files in virtual environments
            if (file_name.startswith((".", "__")) or 
                ".venv" in file_path.split(os.sep)):
                continue

            file_extension = os.path.splitext(file_name)[1].lower()
            if (file_extension not in Config.TEXT_EXTENSIONS and 
                file_extension not in Config.IMAGE_EXTENSIONS):
                continue

            # Compute relative path
            relative_path = (os.path.relpath(file_path, Config.UPLOAD_DIR) 
                           if Config.UPLOAD_DIR in file_path else file_path)

            # Handle PDF files
            if file_extension == ".pdf":
                try:
                    with fitz.open(file_path) as pdf_in:
                        for pdf_page in pdf_in:
                            new_page = doc.new_page(width=page_width, height=page_height)
                            new_page.show_pdf_page(new_page.rect, pdf_in, pdf_page.number)
                except Exception as e:
                    print(f"Error processing PDF {file_path}: {e}")
                continue

            # Create new page for non-PDF files
            page = doc.new_page(width=page_width, height=page_height)
            y_position = self.margin

            # Insert header and file info
            y_position = self._insert_page_header(page, y_position, file_name, relative_path)

            # Handle images
            if file_extension in Config.IMAGE_EXTENSIONS:
                try:
                    if y_position + 200 > page_height - self.margin:
                        page = doc.new_page(width=page_width, height=page_height)
                        y_position = self.margin
                        
                    # Calculate image dimensions and center it
                    img_width = (page_width - 2 * self.margin) * 0.5
                    img_height = img_width * 0.75
                    img_x0 = (page_width - img_width) / 2
                    img_rect = fitz.Rect(img_x0, y_position, 
                                       img_x0 + img_width, y_position + img_height)
                    page.insert_image(img_rect, filename=file_path)
                    y_position += img_height + 20
                except Exception as e:
                    print(f"Error processing image {file_path}: {e}")

            # Handle text files
            else:
                try:
                    # Read content from docx or text file
                    if file_extension == ".docx":
                        docx_document = Document(file_path)
                        content = "\n".join(para.text for para in docx_document.paragraphs)
                    else:
                        with open(file_path, "r", encoding="utf-8") as file:
                            content = file.read()

                    # Process content line by line
                    for line in content.splitlines():
                        wrapped_lines = textwrap.wrap(line, width=self.max_chars_per_line)
                        for wrapped_line in wrapped_lines:
                            if y_position + self.line_height > page_height - self.reserved_space:
                                if self.footer_note:
                                    page.insert_text(
                                        (self.margin, page_height - self.margin - self.line_height),
                                        self.footer_note, fontsize=10, fontname="courier-oblique"
                                    )
                                # Start new page
                                page = doc.new_page(width=page_width, height=page_height)
                                y_position = self.margin
                                y_position = self._insert_page_header(page, y_position, 
                                                                    file_name, relative_path)
                                
                            page.insert_text((self.margin, y_position), wrapped_line, 
                                           fontsize=self.font_size, fontname="courier")
                            y_position += self.line_height

                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue

            # Add footer note at the end of file's content
            if self.footer_note:
                if y_position + self.line_height <= page_height - self.margin:
                    page.insert_text(
                        (self.margin, page_height - self.margin - self.line_height),
                        self.footer_note, fontsize=10, fontname="courier-oblique"
                    )
                else:
                    page = doc.new_page(width=page_width, height=page_height)
                    page.insert_text(
                        (self.margin, page_height - self.margin - self.line_height),
                        self.footer_note, fontsize=10, fontname="courier-oblique"
                    )

        doc.save(output_pdf_path)
        doc.close() 