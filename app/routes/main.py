import os
import secrets
from flask import (
    Blueprint, render_template, request, send_file, 
    flash, session, current_app
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from app.services.pdf_generator import PDFGenerator
from app.services.file_processor import FileProcessor
from app.services.counter_service import CounterService
from app.config.settings import Config

main_bp = Blueprint('main', __name__)
counter_service = CounterService()
file_processor = FileProcessor()

@main_bp.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    flash("File is too large. Maximum upload size is 200MB.")
    return render_template("index.html", pdf_url=None, view_url=None), 413

@main_bp.route("/", methods=["GET", "POST"])
def index():
    section = request.args.get('section', 'upload-section')
    current_count = counter_service.get_count()

    if request.method == "POST":
        # Clean up upload directory
        file_processor.cleanup_upload_dir()

        # Process uploaded files
        uploaded_files = request.files.getlist("files")
        file_paths = []
        for file in uploaded_files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(Config.UPLOAD_DIR, filename)
            file.save(file_path)
            if filename.endswith(".zip"):
                file_paths.extend(file_processor.process_zip(file_path))
            else:
                file_paths.append(file_path)

        # Build and cache file tree
        file_tree = file_processor.build_file_tree(file_paths, Config.UPLOAD_DIR)

        # Store session data
        upload_token = secrets.token_hex(8)
        json_file_path = os.path.join(Config.UPLOAD_DIR, f"{upload_token}.json")
        with open(json_file_path, "w") as f:
            import json
            json.dump({"file_paths": file_paths, "file_tree": file_tree}, f)
        session['upload_token'] = upload_token

        # Process settings
        settings = {}
        try:
            settings['margin'] = int(request.form.get("margin", 10))
        except ValueError:
            settings['margin'] = 10
        settings['header_note'] = request.form.get("header_note", "")
        settings['footer_note'] = request.form.get("footer_note", "")
        settings['orientation'] = request.form.get("orientation", "portrait")
        settings['page_size'] = request.form.get("page_size", "letter")
        settings['show_file_info'] = bool(request.form.get("show_file_info"))
        settings['pdf_name'] = request.form.get("pdf_name", "UnifyDoc.pdf")
        session['settings'] = settings

        # Handle immediate PDF generation if skip confirmation
        if request.form.get("skip_confirmation"):
            return generate_pdf_immediately(settings, file_paths, section)

        return render_template(
            "confirm.html", 
            file_tree=file_tree, 
            settings=settings, 
            section=section,
            converted_pdf_count=current_count
        )

    return render_template(
        "index.html", 
        pdf_url=None, 
        view_url=None, 
        section=section,
        converted_pdf_count=current_count
    )

@main_bp.route("/generate", methods=["POST"])
def generate():
    selected_files = request.form.getlist("files")
    settings = session.get('settings', {})
    
    # Generate PDF
    pdf_name = generate_pdf_with_settings(settings, selected_files)
    
    # Increment counter
    counter_service.increment()
    
    # Cleanup session data
    upload_token = session.pop('upload_token', None)
    if upload_token:
        json_file_path = os.path.join(Config.UPLOAD_DIR, f"{upload_token}.json")
        if os.path.exists(json_file_path):
            os.remove(json_file_path)
            
    return render_template(
        "index.html",
        pdf_url=f"/download?pdf_name={pdf_name}",
        view_url=f"/view?pdf_name={pdf_name}",
        section="upload-section"
    )

@main_bp.route("/download")
def download_pdf():
    pdf_name = request.args.get("pdf_name", "UnifyDoc.pdf")
    output_pdf_path = os.path.join(Config.UPLOAD_DIR, pdf_name)
    return send_file(output_pdf_path, as_attachment=True, download_name=pdf_name)

@main_bp.route("/view")
def view_pdf():
    pdf_name = request.args.get("pdf_name", "UnifyDoc.pdf")
    output_pdf_path = os.path.join(Config.UPLOAD_DIR, pdf_name)
    return send_file(output_pdf_path, as_attachment=False)

def generate_pdf_immediately(settings, file_paths, section):
    """Helper function to generate PDF without confirmation step."""
    pdf_name = generate_pdf_with_settings(settings, file_paths)
    counter_service.increment()
    
    return render_template(
        "index.html",
        pdf_url=f"/download?pdf_name={pdf_name}",
        view_url=f"/view?pdf_name={pdf_name}",
        section=section
    )

def generate_pdf_with_settings(settings, file_paths):
    """Helper function to generate PDF with given settings."""
    page_size_option = settings.get("page_size", "letter")
    page_sizes = {
        "letter": (612, 792),
        "a4": (595, 842),
        "legal": (612, 1008)
    }
    page_size = page_sizes.get(page_size_option, (612, 792))
    
    if settings.get("orientation") == "landscape":
        page_size = (page_size[1], page_size[0])
    
    pdf_name_input = settings.get("pdf_name", "").strip()
    if not pdf_name_input or pdf_name_input == "UnifyDoc.pdf":
        pdf_name = f"UnifyDoc-{secrets.token_hex(8)}.pdf"
    else:
        pdf_name = secure_filename(pdf_name_input)
    
    output_pdf_path = os.path.join(Config.UPLOAD_DIR, pdf_name)
    
    generator = PDFGenerator(
        margin=settings.get("margin", 10),
        header_note=settings.get("header_note", ""),
        footer_note=settings.get("footer_note", ""),
        orientation=settings.get("orientation", "portrait"),
        page_size=page_size,
        show_file_info=settings.get("show_file_info", False)
    )
    
    generator.generate(file_paths, output_pdf_path)
    return pdf_name 