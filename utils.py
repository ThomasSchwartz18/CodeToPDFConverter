import os
import zipfile
import fitz  # PyMuPDF
import textwrap
from docx import Document  # For handling Word documents
from config import UPLOAD_DIR, IMAGE_EXTENSIONS, TEXT_EXTENSIONS


def generate_code_pdf(file_paths, output_pdf_path):
    """
    Generates a PDF from the provided file paths.
    Supports text files, Word documents (.docx), and embeds PDF files as attachments.
    """
    doc = fitz.open()
    page_width, page_height = 612, 792
    margin = 10
    font_size = 10
    line_height = 12
    max_chars_per_line = 90

    for file_path in file_paths:
        file_name = os.path.basename(file_path)
        # Skip any files in a .venv directory
        if ".venv" in file_path.split(os.sep):
            continue
        # Skip files that start with ".__"
        if file_name.startswith(".__"):
            continue

        file_extension = os.path.splitext(file_name)[1].lower()
        if file_extension not in TEXT_EXTENSIONS and file_extension not in IMAGE_EXTENSIONS:
            continue

        # Extract relative path (only the part after the uploads directory)
        relative_path = file_path
        upload_index = file_path.find("uploads")
        if upload_index != -1:
            relative_path = file_path[upload_index + len("uploads") + 1:]  # Trim path up to 'uploads/'

        # Create a new page for each file
        page = doc.new_page(width=page_width, height=page_height)
        y_position = margin

        # Insert file name and path
        page.insert_text((margin, y_position), f"File: {file_name}", fontsize=12, fontname="courier-bold")
        y_position += line_height * 2
        page.insert_text((margin, y_position), f"File Path: {relative_path}", fontsize=10, fontname="courier-bold")
        y_position += line_height * 2

        if file_extension in IMAGE_EXTENSIONS:
            # Handle image files
            y_position += line_height * 2
            page.insert_text((margin, y_position), "This file is an asset.", fontsize=10, fontname="courier")
        elif file_extension == ".pdf":
            try:
                # Open the input PDF file with PyMuPDF
                pdf_in = fitz.open(file_path)
                # Loop through each page in the input PDF
                for pdf_page in pdf_in:
                    # Extract text from the current page
                    text = pdf_page.get_text()
                    for line in text.splitlines():
                        wrapped_lines = textwrap.wrap(line, width=max_chars_per_line)
                        for wrapped_line in wrapped_lines:
                            # Create a new page if the current page is full
                            if y_position + line_height > page_height - margin:
                                page = doc.new_page(width=page_width, height=page_height)
                                y_position = margin
                            page.insert_text((margin, y_position), wrapped_line, fontsize=font_size, fontname="courier")
                            y_position += line_height
                    # Optionally add a little extra spacing between pages
                    y_position += line_height
                pdf_in.close()
                y_position += line_height * 2
            except Exception as e:
                print(f"Error processing PDF {file_path}: {e}")
                continue
        else:
            try:
                if file_extension == ".docx":
                    # Handle Word documents (.docx)
                    docx = Document(file_path)
                    content = "\n".join([para.text for para in docx.paragraphs])
                else:
                    # Handle other text files
                    with open(file_path, "r", encoding="utf-8") as file:
                        content = file.read()

                # Insert content into the PDF
                for line in content.splitlines():
                    wrapped_lines = textwrap.wrap(line, width=max_chars_per_line)
                    for wrapped_line in wrapped_lines:
                        if y_position + line_height > page_height - margin:
                            # Create a new page if the current one is full
                            page = doc.new_page(width=page_width, height=page_height)
                            y_position = margin
                        page.insert_text((margin, y_position), wrapped_line, fontsize=font_size, fontname="courier")
                        y_position += line_height
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue

    # Save the final PDF
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