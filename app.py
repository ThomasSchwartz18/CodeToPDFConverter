from flask import Flask, render_template, request, send_file
import os
from utils import generate_code_pdf, process_zip
from config import UPLOAD_DIR

app = Flask(__name__)
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_files = request.files.getlist("files")  # Accepts multiple files
        file_paths = []
        for file in uploaded_files:
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            file.save(file_path)
            if file.filename.endswith(".zip"):
                file_paths.extend(process_zip(file_path))  # Extract ZIP
            else:
                file_paths.append(file_path)
        
        output_pdf_path = os.path.join(UPLOAD_DIR, "code_collection.pdf")
        generate_code_pdf(file_paths, output_pdf_path)

        return render_template("index.html", pdf_url="/download", view_url="/view")
    
    return render_template("index.html", pdf_url=None, view_url=None)

@app.route("/download")
def download_pdf():
    output_pdf_path = os.path.join(UPLOAD_DIR, "code_collection.pdf")
    return send_file(output_pdf_path, as_attachment=True, download_name="code_collection.pdf")

@app.route("/view")
def view_pdf():
    output_pdf_path = os.path.join(UPLOAD_DIR, "code_collection.pdf")
    return send_file(output_pdf_path, as_attachment=False)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
