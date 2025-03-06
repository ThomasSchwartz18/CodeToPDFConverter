import os
import zipfile
import fitz  # PyMuPDF
import textwrap
from docx import Document  # For handling Word documents
from config import UPLOAD_DIR, IMAGE_EXTENSIONS, TEXT_EXTENSIONS

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
    # Unpack page dimensions from page_size tuple
    page_width, page_height = page_size
    font_size = 10
    line_height = 12
    max_chars_per_line = 90

    doc = fitz.open()

    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        # Skip any files in a .venv directory or with specific patterns
        if ".venv" in file_path.split(os.sep) or file_name.startswith(".__") or file_name.startswith("._") or file_name == "paypal_code.txt":
            continue
        file_extension = os.path.splitext(file_name)[1].lower()
        # Allow PDFs along with text and images.
        if file_extension not in TEXT_EXTENSIONS and file_extension not in IMAGE_EXTENSIONS and file_extension != ".pdf":
            continue

        # Extract relative path (only the part after the uploads directory)
        relative_path = file_path
        upload_index = file_path.find("uploads")
        if upload_index != -1:
            relative_path = file_path[upload_index + len("uploads") + 1:]  # Trim path up to 'uploads/'

        # If the file is a PDF, process it without creating an extra blank page.
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
            continue  # Skip the rest of the loop for PDF files

        # Create a new page for non-PDF files
        page = doc.new_page(width=page_width, height=page_height)
        y_position = margin

        # Insert header note (if provided)
        if header_note:
            page.insert_text((margin, y_position), header_note, fontsize=12, fontname="courier-bold")
            y_position += line_height * 2
            
        # Only display file info if enabled
        if show_file_info:
            page.insert_text((margin, y_position), f"File: {file_name}",
                             fontsize=12, fontname="courier-bold")
            y_position += line_height * 2
            # Compute relative file path if needed
            relative_path = file_path
            upload_index = file_path.find("uploads")
            if upload_index != -1:
                relative_path = file_path[upload_index + len("uploads") + 1:]
            page.insert_text((margin, y_position), f"File Path: {relative_path}",
                             fontsize=10, fontname="courier-bold")
            y_position += line_height * 2

        if file_extension in IMAGE_EXTENSIONS:
            try:
                # Open a new page if needed
                if y_position + 200 > page_height - margin:  # Adjust for new page
                    page = doc.new_page(width=page_width, height=page_height)
                    y_position = margin

                # Define image size (Adjust width and height as needed)
                img_width = (page_width - 2 * margin) * 0.5  # 50% of page width
                img_height = img_width * 0.75  # Maintain aspect ratio

                # Center image horizontally
                img_x0 = (page_width - img_width) / 2
                img_y0 = y_position

                # Define image rectangle
                img_rect = fitz.Rect(img_x0, img_y0, img_x0 + img_width, img_y0 + img_height)

                # Insert image
                page.insert_image(img_rect, filename=file_path)

                # Move y_position down for next content
                y_position += img_height + 20  # Add spacing after image

            except Exception as e:
                print(f"Error processing image {file_path}: {e}")

        else:
            try:
                if file_extension == ".docx":
                    docx_document = Document(file_path)
                    content = "\n".join([para.text for para in docx_document.paragraphs])
                else:
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()
                for line in content.splitlines():
                    wrapped_lines = textwrap.wrap(line, width=max_chars_per_line)
                    for wrapped_line in wrapped_lines:
                        footer_space = margin + (line_height * 2 if footer_note else 0)
                        if y_position + line_height > page_height - footer_space:
                            if footer_note:
                                page.insert_text((margin, page_height - margin - line_height), footer_note, fontsize=10, fontname="courier-oblique")
                            page = doc.new_page(width=page_width, height=page_height)
                            y_position = margin
                            if header_note:
                                page.insert_text((margin, y_position), header_note, fontsize=12, fontname="courier-bold")
                                y_position += line_height * 2
                        page.insert_text((margin, y_position), wrapped_line, fontsize=font_size, fontname="courier")
                        y_position += line_height
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

        # At the end of the file, add the footer note if provided and if space allows
        if footer_note:
            if y_position + line_height <= page_height - margin:
                page.insert_text((margin, page_height - margin - line_height), footer_note, fontsize=10, fontname="courier-oblique")
            else:
                page = doc.new_page(width=page_width, height=page_height)
                page.insert_text((margin, page_height - margin - line_height), footer_note, fontsize=10, fontname="courier-oblique")

    doc.save(output_pdf_path)
    doc.close()

def process_zip(zip_path):
    """
    Extracts files from a ZIP folder and returns a list of file paths.
    """
    extracted_folder = os.path.join(UPLOAD_DIR, os.path.basename(zip_path).replace(".zip", ""))
    os.makedirs(extracted_folder, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extracted_folder)
    # Return a list of all extracted file paths
    return [os.path.join(root, file) for root, _, files in os.walk(extracted_folder) for file in files]
