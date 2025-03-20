from flask import Flask, render_template, request, send_file, flash, session
from werkzeug.exceptions import RequestEntityTooLarge
import os, secrets, shutil, json
from werkzeug.utils import secure_filename
from config import UPLOAD_DIR
from utils import generate_code_pdf, process_zip, build_file_tree
from config import UPLOAD_DIR, TEXT_EXTENSIONS, IMAGE_EXTENSIONS

app = Flask(__name__)

# Set maximum file upload size to 200MB (200 * 1024 * 1024 bytes)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

app.secret_key = secrets.token_hex(16)
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    flash("File is too large. Maximum upload size is 200MB.")
    return render_template("index.html", pdf_url=None, view_url=None), 413

@app.route("/", methods=["GET", "POST"])
def index():
    section = request.args.get('section', 'upload-section')
    if request.method == "POST":
        # Clear the UPLOAD_DIR before processing new uploads
        for filename in os.listdir(UPLOAD_DIR):
            file_path = os.path.join(UPLOAD_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')

        uploaded_files = request.files.getlist("files")
        file_paths = []
        for file in uploaded_files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(UPLOAD_DIR, filename)
            file.save(file_path)
            if filename.endswith(".zip"):
                file_paths.extend(process_zip(file_path))
            else:
                file_paths.append(file_path)

        # Immediately build and cache the file tree once per upload
        file_tree = build_file_tree(file_paths, UPLOAD_DIR)

        # Generate and store tokenized session data
        upload_token = secrets.token_hex(8)
        json_file_path = os.path.join(UPLOAD_DIR, f"{upload_token}.json")
        with open(json_file_path, "w") as f:
            json.dump({"file_paths": file_paths, "file_tree": file_tree}, f)
        session['upload_token'] = upload_token

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

        # If the user has opted to skip the confirmation step, generate PDF immediately.
        if request.form.get("skip_confirmation"):
            page_size_option = settings.get("page_size", "letter")
            page_width, page_height = {"letter": (612, 792), "a4": (595, 842), "legal": (612, 1008)}.get(page_size_option, (612, 792))

            if settings.get("orientation") == "landscape":
                page_width, page_height = page_height, page_width

            pdf_name_input = settings.get("pdf_name", "").strip()
            if not pdf_name_input or pdf_name_input == "UnifyDoc.pdf":
                pdf_name = f"UnifyDoc-{secrets.token_hex(8)}.pdf"
            else:
                pdf_name = secure_filename(pdf_name_input)

            output_pdf_path = os.path.join(UPLOAD_DIR, pdf_name)

            generate_code_pdf(
                file_paths,
                output_pdf_path,
                margin=settings.get("margin", 10),
                header_note=settings.get("header_note", ""),
                footer_note=settings.get("footer_note", ""),
                orientation=settings.get("orientation", "portrait"),
                page_size=(page_width, page_height),
                show_file_info=settings.get("show_file_info", False)
            )

            session.pop('upload_token', None)
            if os.path.exists(json_file_path):
                os.remove(json_file_path)

            return render_template("index.html",
                                   pdf_url=f"/download?pdf_name={pdf_name}",
                                   view_url=f"/view?pdf_name={pdf_name}",
                                   section=section)

        return render_template("confirm.html", file_tree=file_tree, settings=settings, section=section)

    return render_template("index.html", pdf_url=None, view_url=None, section=section)

@app.route("/generate", methods=["POST"])
def generate_pdf():
    # Retrieve the list of file paths selected by the user from the form.
    selected_files = request.form.getlist("files")
    settings = session.get('settings', {})

    # Determine page size
    page_size_option = settings.get("page_size", "letter")
    if page_size_option == "letter":
        page_width, page_height = 612, 792
    elif page_size_option == "a4":
        page_width, page_height = 595, 842
    elif page_size_option == "legal":
        page_width, page_height = 612, 1008
    else:
        page_width, page_height = 612, 792

    if settings.get("orientation") == "landscape":
        page_width, page_height = page_height, page_width

    # Use the PDF name from the session settings rather than a field in the confirmation form.
    pdf_name_input = settings.get("pdf_name", "").strip()
    if not pdf_name_input or pdf_name_input == "UnifyDoc.pdf":
        pdf_name = f"UnifyDoc-{secrets.token_hex(8)}.pdf"
    else:
        pdf_name = secure_filename(pdf_name_input)
    output_pdf_path = os.path.join(UPLOAD_DIR, pdf_name)

    generate_code_pdf(
        selected_files,
        output_pdf_path,
        margin=settings.get("margin", 10),
        header_note=settings.get("header_note", ""),
        footer_note=settings.get("footer_note", ""),
        orientation=settings.get("orientation", "portrait"),
        page_size=(page_width, page_height),
        show_file_info=settings.get("show_file_info", False)
    )
    # Cleanup the temporary JSON file after generation.
    upload_token = session.pop('upload_token', None)
    if upload_token:
        json_file_path = os.path.join(UPLOAD_DIR, f"{upload_token}.json")
        if os.path.exists(json_file_path):
            os.remove(json_file_path)
    return render_template("index.html",
                           pdf_url=f"/download?pdf_name={pdf_name}",
                           view_url=f"/view?pdf_name={pdf_name}",
                           section="upload-section")

@app.route("/download")
def download_pdf():
    pdf_name = request.args.get("pdf_name", "UnifyDoc.pdf")
    output_pdf_path = os.path.join(UPLOAD_DIR, pdf_name)
    return send_file(output_pdf_path, as_attachment=True, download_name=pdf_name)

@app.route("/view")
def view_pdf():
    pdf_name = request.args.get("pdf_name", "UnifyDoc.pdf")
    output_pdf_path = os.path.join(UPLOAD_DIR, pdf_name)
    return send_file(output_pdf_path, as_attachment=False)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
