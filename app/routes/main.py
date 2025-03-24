import os
import secrets
import json
from flask import (
    Blueprint, render_template, request, send_file, 
    flash, session, current_app, jsonify
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from app.services.pdf_generator import PDFGenerator
from app.services.file_processor import FileProcessor
from app.services.github_service import GitHubService
from app.config.settings import Config

main_bp = Blueprint('main', __name__)
file_processor = FileProcessor()
github_service = GitHubService()

# Dictionary to track active conversions and their resources
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
        
        return render_template(
            "index.html", 
            pdf_url=pdf_url, 
            view_url=view_url, 
            section=section
        )

    # Handle POST request
    conversion_id = request.form.get('conversion_id', str(secrets.token_hex(8)))
    active_conversions[conversion_id] = {'status': 'processing'}

    try:
        # Clean up upload directory
        file_processor.cleanup_upload_dir()

        file_paths = []
        
        # Process GitHub repository if URL is provided
        github_url = request.form.get('github_url')
        if github_url:
            if not github_service.is_valid_github_url(github_url):
                raise ValueError("Invalid GitHub repository URL")
            
            try:
                repo_dir = github_service.clone_repository(github_url)
                for root, _, files in os.walk(repo_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_paths.append(file_path)
                # Store the repo information for cleanup later
                active_conversions[conversion_id]['github_repo'] = True
            except Exception as e:
                raise Exception(f"Failed to process GitHub repository: {str(e)}")
            
        # Process uploaded files
        uploaded_files = request.files.getlist("files")
        for file in uploaded_files:
            if file.filename:  # Only process if a file was actually selected
                filename = secure_filename(file.filename)
                file_path = os.path.join(Config.UPLOAD_DIR, filename)
                file.save(file_path)
                if filename.endswith(".zip"):
                    file_paths.extend(file_processor.process_zip(file_path))
                else:
                    file_paths.append(file_path)

        if not file_paths:
            raise ValueError("No files to process. Please provide either a GitHub repository URL or upload files.")

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
        
        # Store the PDF name for later cleanup
        active_conversions[conversion_id]['pdf_name'] = pdf_name

        # Check again if conversion was cancelled
        if active_conversions.get(conversion_id, {}).get('status') == 'cancelled':
            # Clean up generated files
            output_pdf_path = os.path.join(Config.UPLOAD_DIR, pdf_name)
            if os.path.exists(output_pdf_path):
                os.remove(output_pdf_path)
            if github_url:
                github_service.cleanup()
            return jsonify({'status': 'cancelled'})

        # Clean up conversion tracking
        active_conversions.pop(conversion_id, None)

        return jsonify({
            'status': 'success',
            'pdf_url': f"/download?pdf_name={pdf_name}&conversion_id={conversion_id}",
            'view_url': f"/view?pdf_name={pdf_name}&conversion_id={conversion_id}"
        })

    except Exception as e:
        # Clean up GitHub repository if it was used
        if 'github_url' in locals():
            github_service.cleanup()
        
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
    conversion_id = request.args.get("conversion_id")
    output_pdf_path = os.path.join(Config.UPLOAD_DIR, pdf_name)
    
    # Send the file
    response = send_file(output_pdf_path, as_attachment=True, download_name=pdf_name)
    
    # Clean up after sending the file
    @response.call_on_close
    def cleanup():
        # Clean up GitHub repository if it was used
        if conversion_id and conversion_id in active_conversions:
            if active_conversions[conversion_id].get('github_repo'):
                github_service.cleanup()
            # Remove the conversion tracking
            active_conversions.pop(conversion_id, None)
    
    return response

@main_bp.route("/view")
def view_pdf():
    pdf_name = request.args.get("pdf_name", "UnifyDoc.pdf")
    output_pdf_path = os.path.join(Config.UPLOAD_DIR, pdf_name)
    return send_file(output_pdf_path, as_attachment=False)

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