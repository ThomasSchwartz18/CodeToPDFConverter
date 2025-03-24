import os
import secrets
import json
from flask import (
    Blueprint, render_template, request, send_file, 
    flash, session, current_app, jsonify, redirect, url_for
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

# Dictionary to track active conversions
active_conversions = {}

@main_bp.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    flash("File is too large. Maximum upload size is 200MB.")
    return jsonify({
        'status': 'error',
        'message': 'File is too large. Maximum upload size is 200MB.'
    }), 413

@main_bp.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        section = request.args.get('section', 'upload-section')
        pdf_url = request.args.get('pdf_url')
        view_url = request.args.get('view_url')
        current_count = counter_service.get_count()
        
        return render_template(
            "index.html", 
            pdf_url=pdf_url, 
            view_url=view_url, 
            section=section,
            converted_pdf_count=current_count
        )

    # Handle POST request
    conversion_id = request.form.get('conversion_id', str(secrets.token_hex(8)))
    active_conversions[conversion_id] = {'status': 'processing'}

    try:
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

        # Check if conversion was cancelled
        if active_conversions.get(conversion_id, {}).get('status') == 'cancelled':
            return jsonify({'status': 'cancelled'})

        # Process settings
        settings = {
            'margin': int(request.form.get("margin", 10)),
            'header_note': request.form.get("header_note", ""),
            'footer_note': request.form.get("footer_note", ""),
            'orientation': request.form.get("orientation", "portrait"),
            'page_size': request.form.get("page_size", "letter"),
            'show_file_info': bool(request.form.get("show_file_info")),
            'pdf_name': request.form.get("pdf_name", "UnifyDoc.pdf")
        }

        # Generate PDF
        pdf_name = generate_pdf_with_settings(settings, file_paths, conversion_id)
        
        # Check again if conversion was cancelled
        if active_conversions.get(conversion_id, {}).get('status') == 'cancelled':
            # Clean up generated files
            output_pdf_path = os.path.join(Config.UPLOAD_DIR, pdf_name)
            if os.path.exists(output_pdf_path):
                os.remove(output_pdf_path)
            return jsonify({'status': 'cancelled'})

        # Increment counter on success
        counter_service.increment()

        # Clean up conversion tracking
        active_conversions.pop(conversion_id, None)

        return jsonify({
            'status': 'success',
            'pdf_url': f"/download?pdf_name={pdf_name}",
            'view_url': f"/view?pdf_name={pdf_name}"
        })

    except Exception as e:
        active_conversions.pop(conversion_id, None)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@main_bp.route("/cancel_conversion", methods=["POST"])
def cancel_conversion():
    """Handle conversion cancellation requests."""
    conversion_id = request.headers.get('X-Conversion-ID')
    if conversion_id and conversion_id in active_conversions:
        active_conversions[conversion_id]['status'] = 'cancelled'
        return jsonify({'status': 'success', 'message': 'Conversion cancelled'})
    return jsonify({'status': 'error', 'message': 'Conversion not found'}), 404

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

@main_bp.route("/confirm", methods=["GET", "POST"])
def confirm():
    if request.method == "POST":
        # Process uploaded files
        uploaded_files = request.files.getlist("files")
        file_tree = {"files": [], "folders": []}
        for file in uploaded_files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(Config.UPLOAD_DIR, filename)
            file.save(file_path)
            if filename.endswith(".zip"):
                # Process the zip file and get its extracted file paths
                extracted_files = file_processor.process_zip(file_path)
                # Get the zip folder name (without .zip)
                zip_folder_name = os.path.splitext(filename)[0]
                for extracted_file in extracted_files:
                    # Skip any file or folder whose basename starts with "._"
                    if os.path.basename(extracted_file).startswith("._"):
                        continue
                    relative_path = os.path.relpath(extracted_file, Config.UPLOAD_DIR)
                    parts = relative_path.split(os.sep)
                    # Skip system folders like __MACOSX or any part starting with "._"
                    if parts[0] == "__MACOSX" or parts[0].startswith("._"):
                        continue
                    # Remove redundant top-level folder if it matches the zip file name
                    if parts[0] == zip_folder_name:
                        parts = parts[1:]
                        if not parts:
                            continue
                    # Build file tree structure
                    if len(parts) == 1:
                        file_tree["files"].append({
                            "name": parts[0],
                            "full_path": extracted_file
                        })
                    else:
                        current_folder = file_tree
                        for part in parts[:-1]:
                            if part == "__MACOSX" or part.startswith("._"):
                                continue
                            folder_found = None
                            for folder in current_folder.get("folders", []):
                                if folder["name"] == part:
                                    folder_found = folder
                                    break
                            if folder_found is None:
                                new_folder = {"name": part, "files": [], "folders": []}
                                current_folder.setdefault("folders", []).append(new_folder)
                                current_folder = new_folder
                            else:
                                current_folder = folder_found
                        current_folder.setdefault("files", []).append({
                            "name": parts[-1],
                            "full_path": extracted_file,
                            "indent": len(parts) * 20
                        })
            else:
                file_tree["files"].append({
                    "name": filename,
                    "full_path": file_path
                })
        return render_template("confirm.html", file_tree=file_tree)
    return redirect(url_for('main.index'))

@main_bp.route("/generate", methods=["POST"])
def generate():
    try:
        # Get selected files from confirmation page
        selected_files = request.form.getlist("files")
        
        # Generate PDF with selected files
        settings = {
            'margin': int(request.form.get("margin", 10)),
            'header_note': request.form.get("header_note", ""),
            'footer_note': request.form.get("footer_note", ""),
            'orientation': request.form.get("orientation", "portrait"),
            'page_size': request.form.get("page_size", "letter"),
            'show_file_info': bool(request.form.get("show_file_info")),
            'pdf_name': request.form.get("pdf_name", "UnifyDoc.pdf")
        }
        
        pdf_name = generate_pdf_with_settings(settings, selected_files, None)
        
        # Increment counter on success
        counter_service.increment()
        
        return redirect(f"/?pdf_url=/download?pdf_name={pdf_name}&view_url=/view?pdf_name={pdf_name}")
        
    except Exception as e:
        flash(str(e))
        return redirect(url_for('main.index'))

def generate_pdf_with_settings(settings, file_paths, conversion_id):
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
    
    # Check for cancellation before starting generation
    if active_conversions.get(conversion_id, {}).get('status') == 'cancelled':
        return None
        
    generator.generate(file_paths, output_pdf_path)
    return pdf_name 