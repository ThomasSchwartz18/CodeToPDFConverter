import os
import zipfile
import fitz  # PyMuPDF
import textwrap
from docx import Document  # For handling Word documents
from config import UPLOAD_DIR, IMAGE_EXTENSIONS, TEXT_EXTENSIONS

def insert_page_header(page, y_position, header_note, file_name, relative_path, line_height, margin, show_file_info):
    """Helper to insert header note and file info; returns updated y_position."""
    if header_note:
        page.insert_text((margin, y_position), header_note, fontsize=12, fontname="courier-bold")
        y_position += line_height * 2
    if show_file_info:
        page.insert_text((margin, y_position), f"File: {file_name}", fontsize=12, fontname="courier-bold")
        y_position += line_height * 2
        page.insert_text((margin, y_position), f"File Path: {relative_path}", fontsize=10, fontname="courier-bold")
        y_position += line_height * 2
    return y_position

def generate_code_pdf(file_paths, output_pdf_path, margin=10, header_note="",
                      footer_note="", orientation="portrait", page_size=(612,792),
                      show_file_info=True):
    """
    Generates a PDF from the provided file paths.
    Supports text files, Word documents (.docx), PDFs, and image files.
    
    New parameters:
      - margin: space (in points) around the content (default: 10)
      - header_note: optional header text to include on each page
      - footer_note: optional footer text to include on each page
      - orientation: 'portrait' or 'landscape' (used in app.py to set page_size)
      - page_size: tuple (width, height) defining the page dimensions
    """
    page_width, page_height = page_size
    font_size = 10
    line_height = 12
    max_chars_per_line = 90
    reserved_space = margin + (line_height * 2 if footer_note else 0)
    
    doc = fitz.open()

    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        # Skip files in .venv or with specific problematic prefixes.
        if ".venv" in file_path.split(os.sep) or file_name.startswith(".__") or file_name.startswith("._"):
            continue

        file_extension = os.path.splitext(file_name)[1].lower()
        if file_extension not in TEXT_EXTENSIONS and file_extension not in IMAGE_EXTENSIONS and file_extension != ".pdf":
            continue

        # Compute a relative path (using os.path.relpath if possible)
        if UPLOAD_DIR in file_path:
            relative_path = os.path.relpath(file_path, UPLOAD_DIR)
        else:
            relative_path = file_path

        # Process PDF files without adding extra blank pages.
        if file_extension == ".pdf":
            try:
                pdf_in = fitz.open(file_path)
                for pdf_page in pdf_in:
                    new_page = doc.new_page(width=page_width, height=page_height)
                    new_page.show_pdf_page(new_page.rect, pdf_in, pdf_page.number)
                pdf_in.close()
            except Exception as e:
                print(f"Error processing PDF {file_path}: {e}")
            continue

        # Create a new page for non-PDF files.
        page = doc.new_page(width=page_width, height=page_height)
        y_position = margin

        # Insert header and file info once.
        y_position = insert_page_header(page, y_position, header_note, file_name, relative_path, line_height, margin, show_file_info)

        if file_extension in IMAGE_EXTENSIONS:
            try:
                if y_position + 200 > page_height - margin:
                    page = doc.new_page(width=page_width, height=page_height)
                    y_position = margin
                # Calculate image dimensions and center it.
                img_width = (page_width - 2 * margin) * 0.5
                img_height = img_width * 0.75
                img_x0 = (page_width - img_width) / 2
                img_y0 = y_position
                img_rect = fitz.Rect(img_x0, img_y0, img_x0 + img_width, img_y0 + img_height)
                page.insert_image(img_rect, filename=file_path)
                y_position += img_height + 20
            except Exception as e:
                print(f"Error processing image {file_path}: {e}")
        else:
            try:
                if file_extension == ".docx":
                    docx_document = Document(file_path)
                    content = "\n".join(para.text for para in docx_document.paragraphs)
                else:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                for line in content.splitlines():
                    wrapped_lines = textwrap.wrap(line, width=max_chars_per_line)
                    for wrapped_line in wrapped_lines:
                        if y_position + line_height > page_height - reserved_space:
                            if footer_note:
                                page.insert_text((margin, page_height - margin - line_height),
                                                 footer_note, fontsize=10, fontname="courier-oblique")
                            # Start a new page and reinsert header info.
                            page = doc.new_page(width=page_width, height=page_height)
                            y_position = margin
                            y_position = insert_page_header(page, y_position, header_note, file_name, relative_path, line_height, margin, show_file_info)
                        page.insert_text((margin, y_position), wrapped_line, fontsize=font_size, fontname="courier")
                        y_position += line_height
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

        # Append footer note at the end of the file's content.
        if footer_note:
            if y_position + line_height <= page_height - margin:
                page.insert_text((margin, page_height - margin - line_height),
                                 footer_note, fontsize=10, fontname="courier-oblique")
            else:
                page = doc.new_page(width=page_width, height=page_height)
                page.insert_text((margin, page_height - margin - line_height),
                                 footer_note, fontsize=10, fontname="courier-oblique")

    doc.save(output_pdf_path)
    doc.close()

def is_safe_path(basedir, path, follow_symlinks=True):
    # Resolve the absolute path and compare it with the base directory.
    if follow_symlinks:
        return os.path.realpath(path).startswith(os.path.realpath(basedir))
    return os.path.abspath(path).startswith(os.path.abspath(basedir))

def process_zip(zip_path):
    """
    Extracts files from a ZIP folder and returns a list of file paths, ensuring no directory traversal.
    """
    extracted_folder = os.path.join(UPLOAD_DIR, os.path.basename(zip_path).replace(".zip", ""))
    os.makedirs(extracted_folder, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_path = os.path.join(extracted_folder, member.filename)
            if not is_safe_path(extracted_folder, member_path):
                print(f"Skipped unsafe file path: {member.filename}")
                continue
            zip_ref.extract(member, extracted_folder)
    return sorted([
        os.path.join(root, file)
        for root, _, files in os.walk(extracted_folder)
        for file in files
    ])
