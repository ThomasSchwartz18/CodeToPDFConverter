from flask import Flask, render_template, request, send_file, flash
from werkzeug.exceptions import RequestEntityTooLarge
import os
import secrets
import shutil  # For clearing the upload directory
from werkzeug.utils import secure_filename
from config import UPLOAD_DIR
from utils import generate_code_pdf, process_zip

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
                
        try:
            margin = int(request.form.get("margin", 10))
        except ValueError:
            margin = 10
        header_note = request.form.get("header_note", "")
        footer_note = request.form.get("footer_note", "")
        orientation = request.form.get("orientation", "portrait")
        page_size_option = request.form.get("page_size", "letter")
        if page_size_option == "letter":
            page_width, page_height = 612, 792
        elif page_size_option == "a4":
            page_width, page_height = 595, 842
        elif page_size_option == "legal":
            page_width, page_height = 612, 1008
        else:
            page_width, page_height = 612, 792
        if orientation == "landscape":
            page_width, page_height = page_height, page_width

        show_file_info = True if request.form.get("show_file_info") else False

        # Generate a unique PDF file name if the preset is used.
        pdf_name_input = request.form.get("pdf_name", "").strip()
        if not pdf_name_input or pdf_name_input == "UnifyDoc.pdf":
            pdf_name = f"UnifyDoc-{secrets.token_hex(8)}.pdf"
        else:
            pdf_name = secure_filename(pdf_name_input)

        output_pdf_path = os.path.join(UPLOAD_DIR, pdf_name)
        generate_code_pdf(
            file_paths,
            output_pdf_path,
            margin=margin,
            header_note=header_note,
            footer_note=footer_note,
            orientation=orientation,
            page_size=(page_width, page_height),
            show_file_info=show_file_info
        )
        return render_template("index.html", 
                               pdf_url=f"/download?pdf_name={pdf_name}",
                               view_url=f"/view?pdf_name={pdf_name}",
                               section=section)
    return render_template("index.html", pdf_url=None, view_url=None, section=section)

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
