import os
import zipfile
import fitz  # PyMuPDF
import textwrap
from config import UPLOAD_DIR, IMAGE_EXTENSIONS, TEXT_EXTENSIONS

def generate_code_pdf(file_paths, output_pdf_path):
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

        # Skip files that start with "._"
        if file_name.startswith("._"):
            continue

        file_extension = os.path.splitext(file_name)[1].lower()

        if file_extension not in TEXT_EXTENSIONS and file_extension not in IMAGE_EXTENSIONS:
            continue  

        # Extract relative path (only the part after the uploads directory)
        relative_path = file_path
        upload_index = file_path.find("uploads")
        if upload_index != -1:
            relative_path = file_path[upload_index + len("uploads") + 1:]  # Trim path up to 'uploads/'

        page = doc.new_page(width=page_width, height=page_height)
        y_position = margin

        page.insert_text((margin, y_position), f"File: {file_name}",
                         fontsize=12, fontname="courier-bold")
        y_position += line_height * 2
        
        page.insert_text((margin, y_position), f"File Path: {relative_path}", fontsize=10, fontname="courier-bold")
        y_position += line_height * 2

        if file_extension in IMAGE_EXTENSIONS:
            y_position += line_height * 2
            page.insert_text((margin, y_position), "This file is an asset.",
                             fontsize=10, fontname="courier")
        else:
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    code_content = file.readlines()
            except UnicodeDecodeError:
                try:
                    with open(file_path, "r", encoding="latin-1") as file:
                        code_content = file.readlines()
                except Exception:
                    continue  

            for line in code_content:
                wrapped_lines = textwrap.wrap(line.rstrip(), width=max_chars_per_line)
                for wrapped_line in wrapped_lines:
                    if y_position + line_height > page_height - margin:
                        page = doc.new_page(width=page_width, height=page_height)
                        y_position = margin
                    page.insert_text((margin, y_position), wrapped_line,
                                     fontsize=font_size, fontname="courier")
                    y_position += line_height

    doc.save(output_pdf_path)
    doc.close()

def process_zip(zip_path):
    extracted_folder = os.path.join(UPLOAD_DIR, os.path.basename(zip_path).replace(".zip", ""))
    os.makedirs(extracted_folder, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extracted_folder)

    return [os.path.join(root, file) for root, _, files in os.walk(extracted_folder) for file in files]
