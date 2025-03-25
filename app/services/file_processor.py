import os
import zipfile
from app.config.settings import Config
from app.utils.security import is_safe_path

class FileProcessor:
    @staticmethod
    def get_upload_dir(conversion_id):
        upload_path = os.path.join(Config.UPLOAD_DIR, conversion_id)
        os.makedirs(upload_path, exist_ok=True)
        return upload_path

    @staticmethod
    def cleanup_conversion_files(conversion_id):
        path = os.path.join(Config.UPLOAD_DIR, conversion_id)
        if os.path.exists(path):
            import shutil
            shutil.rmtree(path, ignore_errors=True)

    @staticmethod
    def process_zip(zip_path, conversion_id):
        """
        Extracts files from a ZIP folder and returns a list of file paths.
        Ensures no directory traversal attacks are possible.
        """
        extracted_folder = os.path.join(
            FileProcessor.get_upload_dir(conversion_id),
            os.path.basename(zip_path).replace(".zip", "")
        )
        os.makedirs(extracted_folder, exist_ok=True)
        
        file_paths = []
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for member in zip_ref.infolist():
                member_path = os.path.join(extracted_folder, member.filename)
                if not is_safe_path(extracted_folder, member_path):
                    print(f"Skipped unsafe file path: {member.filename}")
                    continue
                zip_ref.extract(member, extracted_folder)
                
        # Return sorted list of extracted files
        return sorted([
            os.path.join(root, file)
            for root, _, files in os.walk(extracted_folder)
            for file in files
        ])

    @staticmethod
    def build_file_tree(file_paths, base_dir):
        """
        Builds a nested file tree structure with metadata for UI.
        """
        tree = {"folders": [], "files": []}
        
        for file in file_paths:
            if file.startswith('.') or '/.' in file or '__MACOSX' in file:
                continue
            
            file_extension = os.path.splitext(file)[1].lower()
            if (file_extension not in Config.TEXT_EXTENSIONS and 
                file_extension not in Config.IMAGE_EXTENSIONS):
                continue

            rel_path = os.path.relpath(file, base_dir)
            parts = rel_path.split(os.sep)
            current = tree

            # Process folders
            for depth, part in enumerate(parts[:-1]):
                folder_name = part + "/"
                folder = next((f for f in current.get('folders', []) 
                             if f['name'] == folder_name), None)
                if folder is None:
                    folder = {
                        "name": folder_name,
                        "folders": [],
                        "files": [],
                        "level": depth + 1,
                        "indent": (depth + 1) * 20
                    }
                    current['folders'].append(folder)
                current = folder

            # Add file
            current_level = len(parts)
            current["files"].append({
                "name": parts[-1],
                "full_path": file,
                "level": current_level,
                "indent": current_level * 20
            })

        return tree

    @staticmethod
    def cleanup_upload_dir():
        """
        Cleans up the upload directory by removing all files and subdirectories.
        """
        for filename in os.listdir(Config.UPLOAD_DIR):
            file_path = os.path.join(Config.UPLOAD_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}') 