import os
import secrets
import json
import uuid
from flask import (
    Blueprint, render_template, request, send_file,
    flash, session, current_app, jsonify, redirect, abort
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
    # Always generate conversion_id securely on server-side
    conversion_id = uuid.uuid4().hex  # Generates a unique, secure 32-char hex id
    session['conversion_id'] = conversion_id  # Securely store in Flask session
    active_conversions[conversion_id] = {'status': 'processing'}
    try:
        # Get isolated upload directory for this conversion
        upload_dir = file_processor.get_upload_dir(conversion_id)
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
                file_path = os.path.join(upload_dir, filename)
                file.save(file_path)
                if filename.endswith(".zip"):
                    file_paths.extend(file_processor.process_zip(file_path, conversion_id))
                else:
                    file_paths.append(file_path)
                    
        if not file_paths:
            raise ValueError("No files to process. Please provide either a GitHub repository URL or upload files.")
        
        # Check if conversion was cancelled
        if active_conversions.get(conversion_id, {}).get('status') == 'cancelled':
            file_processor.cleanup_conversion_files(conversion_id)
            session.pop('conversion_id', None)  # Clear session on cancellation
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
        
        # If "Skip file confirmation" is unchecked, skip PDF generation and redirect to confirmation
        if not request.form.get('skip_confirmation'):
            active_conversions[conversion_id]['settings'] = settings
            active_conversions[conversion_id]['file_paths'] = file_paths
            return jsonify({
                'status': 'confirm_required',
                'redirect_url': f"/confirm?conversion_id={conversion_id}"
            })
        
        # Otherwise, proceed immediately with PDF generation
        pdf_name = generate_pdf_with_settings(settings, file_paths, conversion_id)
        active_conversions[conversion_id]['pdf_name'] = pdf_name
        
        # Check again if conversion was cancelled
        if active_conversions.get(conversion_id, {}).get('status') == 'cancelled':
            output_pdf_path = os.path.join(Config.UPLOAD_DIR, conversion_id, pdf_name)
            if os.path.exists(output_pdf_path):
                os.remove(output_pdf_path)
            if github_url:
                github_service.cleanup()
            file_processor.cleanup_conversion_files(conversion_id)
            session.pop('conversion_id', None)  # Clear session on cancellation
            return jsonify({'status': 'cancelled'})
        
        # Don't clear session here - wait until after download/view
        active_conversions.pop(conversion_id, None)
        return jsonify({
            'status': 'success',
            'pdf_url': f"/download?pdf_name={pdf_name}",
            'view_url': f"/view?pdf_name={pdf_name}"
        })
    except Exception as e:
        if 'github_url' in locals():
            github_service.cleanup()
        file_processor.cleanup_conversion_files(conversion_id)
        active_conversions.pop(conversion_id, None)
        session.pop('conversion_id', None)  # Clear session on error
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@main_bp.route("/confirm", methods=["GET"])
def confirm_files():
    conversion_id = session.get('conversion_id')
    if not conversion_id:
        flash("Session expired or invalid.", "error")
        return redirect("/")
    conversion = active_conversions.get(conversion_id)
    if not conversion:
        flash("Session expired or invalid.", "error")
        return redirect("/")
    file_paths = conversion.get('file_paths', [])
    file_tree = file_processor.build_file_tree(file_paths, Config.UPLOAD_DIR)
    return render_template("confirm.html", file_tree=file_tree, conversion_id=conversion_id)

@main_bp.route("/generate", methods=["POST"])
def generate_pdf_confirmed():
    """
    This route is triggered from the confirmation page (confirm.html).
    It receives the user's file selection and generates the PDF using
    the settings stored earlier.
    """
    conversion_id = session.get('conversion_id')
    if not conversion_id or conversion_id not in active_conversions:
        abort(403)  # Forbidden access if conversion_id is invalid or missing

    settings = active_conversions[conversion_id].get('settings')
    if not settings:
        return jsonify({'status': 'error', 'message': 'Missing conversion settings.'}), 400

    selected_files = request.form.getlist("files")
    if not selected_files:
        return jsonify({'status': 'error', 'message': 'No files selected for PDF generation.'}), 400

    try:
        pdf_name = generate_pdf_with_settings(settings, selected_files, conversion_id)
        active_conversions[conversion_id]['pdf_name'] = pdf_name
        # Don't clear session here - wait until after download/view
        active_conversions.pop(conversion_id, None)
        return jsonify({
            'status': 'success',
            'pdf_url': f"/download?pdf_name={pdf_name}",
            'view_url': f"/view?pdf_name={pdf_name}"
        })
    except Exception as e:
        file_processor.cleanup_conversion_files(conversion_id)
        active_conversions.pop(conversion_id, None)
        session.pop('conversion_id', None)  # Clear session on error
        return jsonify({'status': 'error', 'message': str(e)}), 500

@main_bp.route("/cancel_conversion", methods=["POST"])
def cancel_conversion():
    conversion_id = session.get('conversion_id')
    if conversion_id and conversion_id in active_conversions:
        active_conversions[conversion_id]['status'] = 'cancelled'
        file_processor.cleanup_conversion_files(conversion_id)
        session.pop('conversion_id', None)  # Clear session after cancellation
        return jsonify({'status': 'success', 'message': 'Conversion cancelled'})
    return jsonify({'status': 'error', 'message': 'Conversion not found'}), 404

@main_bp.route("/download")
def download_pdf():
    pdf_name = request.args.get("pdf_name", "UnifyDoc.pdf")
    conversion_id = session.get('conversion_id')
    if not conversion_id:
        abort(403)  # Forbidden access if no conversion_id in session

    output_pdf_path = os.path.join(Config.UPLOAD_DIR, conversion_id, pdf_name)
    print(f"Trying to serve file from: {output_pdf_path}")  # Debug log
    
    if not os.path.exists(output_pdf_path):
        print(f"File not found at: {output_pdf_path}")  # Debug log
        abort(404)  # File not found

    response = send_file(output_pdf_path, as_attachment=True, download_name=pdf_name)
    
    @response.call_on_close
    def cleanup():
        if conversion_id:
            if active_conversions.get(conversion_id, {}).get('github_repo'):
                github_service.cleanup()
            file_processor.cleanup_conversion_files(conversion_id)
            active_conversions.pop(conversion_id, None)
            session.pop('conversion_id', None)  # Only clear session here, after download
    return response

@main_bp.route("/view")
def view_pdf():
    pdf_name = request.args.get("pdf_name", "UnifyDoc.pdf")
    conversion_id = session.get('conversion_id')
    if not conversion_id:
        abort(403)  # Forbidden access if no conversion_id in session

    output_pdf_path = os.path.join(Config.UPLOAD_DIR, conversion_id, pdf_name)
    print(f"Trying to serve file from: {output_pdf_path}")  # Debug log
    
    if not os.path.exists(output_pdf_path):
        print(f"File not found at: {output_pdf_path}")  # Debug log
        abort(404)  # File not found

    # Do NOT cleanup session here, as user might still download afterward
    return send_file(output_pdf_path, as_attachment=False)

def generate_pdf_with_settings(settings, file_paths, conversion_id):
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
    
    output_pdf_path = os.path.join(Config.UPLOAD_DIR, conversion_id, pdf_name)
    print(f"Generating PDF at: {output_pdf_path}")  # Debug log
    
    generator = PDFGenerator(
        margin=settings.get("margin", 10),
        header_note=settings.get("header_note", ""),
        footer_note=settings.get("footer_note", ""),
        orientation=settings.get("orientation", "portrait"),
        page_size=page_size,
        show_file_info=settings.get("show_file_info", False)
    )
    if active_conversions.get(conversion_id, {}).get('status') == 'cancelled':
        return None
    generator.generate(file_paths, output_pdf_path)
    # Set proper file permissions for Heroku
    os.chmod(output_pdf_path, 0o644)
    return pdf_name
