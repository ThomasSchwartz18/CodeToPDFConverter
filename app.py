from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
import os
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
# Account creation is temporarily removed to make the application free for users.
# from db import create_user, get_user_by_username, get_user_by_id
from config import UPLOAD_DIR
from utils import generate_code_pdf, process_zip
from dotenv import load_dotenv
import re

EMAIL_REGEX = r'^[\w\.-]+@[\w\.-]+\.\w+$'

# check if password meets the requirements.
import re

def validate_password(password):
    """Check that password meets the requirements."""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[^a-zA-Z0-9]', password):
        return False, "Password must contain at least one special character."
    return True, ""


# Create the Flask application
app = Flask(__name__)

load_dotenv()  # Load environment variables from .env file

DATABASE_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}
# print(DATABASE_CONFIG)
# print("DB_HOST from .env:", os.getenv('DB_HOST'))

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
        # Loop through all uploaded files
        for file in uploaded_files:
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            file.save(file_path)
            if file.filename.endswith(".zip"):
                file_paths.extend(process_zip(file_path))  # Extract ZIP
            else:
                file_paths.append(file_path)
############# UNCOMMENT TO FORCE USERS TO LOGIN/SUBSCRIBE TO PROCESS ZIP FILES ###################################################

            # if file.filename.endswith(".zip"):
                # # Ensure user is logged in
                # if 'user_id' not in session:
                #     flash("You must be logged in to upload ZIP folders!")
                #     return render_template("index.html", pdf_url=None, view_url=None, section='upload-section')
                # # If logged in, check subscription status
                # user = get_user_by_id(session['user_id'])
                # # Assuming the subscription column is at index 3 (adjust if needed)
                # if not user[3]:
                #     flash("You must be subscribed to upload ZIP folders!")
                #     return render_template("index.html", pdf_url=None, view_url=None, section='upload-section')
                # If checks pass, save the file and process the ZIP
                
            # --- New PDF Settings ---
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
            page_width, page_height = 612, 792  # fallback default

        if orientation == "landscape":
            page_width, page_height = page_height, page_width

        output_pdf_path = os.path.join(UPLOAD_DIR, "code_collection.pdf")
        generate_code_pdf(
            file_paths, 
            output_pdf_path, 
            margin=margin,
            header_note=header_note,
            footer_note=footer_note,
            orientation=orientation,
            page_size=(page_width, page_height)
        )
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

# LOGIN/ REGISTER SECTION - Uncomment when account registrations are active again.
# @app.route("/register", methods=["GET", "POST"])
# def register():
#     if request.method == "POST":
#         username = request.form['username']
#         password = request.form['password']
#         confirm_password = request.form['confirm_password']
#         # Validate that the username is a valid email address.
#         if not re.match(EMAIL_REGEX, username):
#             flash("Must be a valid email address!")
#             return render_template("index.html", section='register-section')
#         if password != confirm_password:
#             flash("Passwords do not match!")
#             return render_template("index.html", section='register-section')
#         # Check password requirements
#         valid, message = validate_password(password)
#         if not valid:
#             flash(message)
#             return render_template("index.html", section='register-section')
#         # Check if email is already associated with an account.
#         if get_user_by_username(username):
#             flash("Email is already associated with an account!")
#             return render_template("index.html", section='register-section')
#         hashed_password = generate_password_hash(password)
#         if create_user(username, hashed_password):
#             flash("Registration successful! Please log in.")
#             return redirect(url_for('login'))
#         else:
#             flash("An error occurred during registration!")
#             return render_template("index.html", section='register-section')
#     return render_template("index.html", section='register-section')

# @app.route("/login", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         username = request.form['username']
#         password = request.form['password']
#         user = get_user_by_username(username)
#         if user and check_password_hash(user[2], password):
#             session['user_id'] = user[0]  # Store user ID in session
#             flash("Login successful!")
#             return redirect(url_for('index'))
#         else:
#             flash("Username or Password is incorrect!")
#             return render_template("index.html", section='login-section')
#     return render_template("index.html", section='login-section')

# @app.route("/logout")
# def logout():
#     session.pop('user_id', None)  # Remove user ID from session
#     flash("You have been logged out.")
#     return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True, port=5000)
