from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
import os
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from db import create_user, get_user_by_username
from config import UPLOAD_DIR
from utils import generate_code_pdf, process_zip

# Create the Flask application
app = Flask(__name__)

# Generate a secure random secret key using the secrets module
app.secret_key = secrets.token_hex(16)  # Generates a 32-character hexadecimal string

# Ensure the upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def index():
    section = request.args.get('section', 'upload-section')
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
        return render_template("index.html", pdf_url="/download", view_url="/view", section=section)
    return render_template("index.html", pdf_url=None, view_url=None, section=section)

@app.route("/download")
def download_pdf():
    output_pdf_path = os.path.join(UPLOAD_DIR, "code_collection.pdf")
    return send_file(output_pdf_path, as_attachment=True, download_name="code_collection.pdf")

@app.route("/view")
def view_pdf():
    output_pdf_path = os.path.join(UPLOAD_DIR, "code_collection.pdf")
    return send_file(output_pdf_path, as_attachment=False)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        if create_user(username, hashed_password):
            flash("Registration successful! Please log in.")
            return redirect(url_for('login'))
        else:
            flash("Username already exists!")
            return redirect(url_for('register'))

    return render_template("index.html", section='register-section')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]  # Store user ID in session
            flash("Login successful!")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password!")
            return redirect(url_for('login'))

    return render_template("index.html", section='login-section')

@app.route("/logout")
def logout():
    session.pop('user_id', None)  # Remove user ID from session
    flash("You have been logged out.")
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)