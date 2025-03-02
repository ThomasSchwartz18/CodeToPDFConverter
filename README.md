# Code to PDF Converter

## Overview
The **Code to PDF Converter** is a simple web-based application that allows users to upload source code files (e.g., `.py`, `.html`, `.txt`, `.js`) or a ZIP folder containing multiple files and convert them into a structured PDF document. This tool ensures easy sharing, professional formatting, and enhanced readability.

## Features
- **Supports Multiple File Types**: Converts `.py`, `.txt`, `.html`, `.js`, `.css`, `.java`, `.cpp`, `.c`, `.json`, `.md` files to a formatted PDF.
- **ZIP File Support**: Upload a ZIP folder containing multiple code files.
- **Professional Formatting**: Maintains structure, syntax readability, and file organization in the generated PDF.
- **User-Friendly Interface**: Simple upload, process, and download functionality.
- **Web-Based Application**: Accessible from any browser.

## Installation

### Prerequisites
Ensure you have the following installed on your system:
- Python 3.x
- Flask
- PyMuPDF (`pip install pymupdf`)

### Setup Instructions
```sh
# Clone the repository
git clone https://github.com/your-repo/code-to-pdf.git
cd code-to-pdf
# Install required dependencies
pip install -r requirements.txt
# Run the application
python app.py
# Open a browser and navigate to:
echo "Server running at http://localhost:5000/"
