from flask import Flask, render_template, request
import os
import uuid
import hashlib
from datetime import datetime

app = Flask(__name__)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
LOG_FILE = os.path.join(BASE_DIR, 'upload_logs.txt')

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Config
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB

# Check allowed file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Generate hash
def generate_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

# Save logs
def log_upload(filename, filehash):
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now()}|{filename}|{filehash}\n")

# Read logs
def read_logs():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            for line in f:
                parts = [p.strip() for p in line.strip().split('|')]
                if len(parts) == 3:
                    logs.append({
                        'time': parts[0],
                        'file': parts[1],
                        'hash': parts[2]
                    })
    return logs

# Upload route
@app.route('/', methods=['GET', 'POST'])
def upload():
    message = ""

    if request.method == 'POST':
        file = request.files.get('file')

        if not file or file.filename == '':
            message = "⚠️ No file selected"

        elif allowed_file(file.filename):

            # safer filename
            original_name = file.filename.replace(" ", "_")
            safe_name = str(uuid.uuid4()) + "_" + original_name

            path = os.path.join(app.config['UPLOAD_FOLDER'], safe_name)
            file.save(path)

            # hash
            file_hash = generate_hash(path)

            # size + type
            size_kb = round(os.path.getsize(path) / 1024, 2)
            ext = original_name.split('.')[-1]

            log_upload(safe_name, file_hash)

            message = f"✅ Uploaded | Type: {ext.upper()} | Size: {size_kb} KB | Hash: {file_hash}"

        else:
            message = "❌ Blocked: Unsafe file type detected"

    return render_template('index.html', message=message)

# Logs route
@app.route('/logs')
def logs():
    return render_template('logs.html', logs=read_logs())

# Verify route
@app.route('/verify', methods=['GET', 'POST'])
def verify():
    result = ""
    new_hash = ""

    if request.method == 'POST':
        file = request.files.get('file')

        if file:
            temp_path = os.path.join(UPLOAD_FOLDER, "temp_" + file.filename)
            file.save(temp_path)

            new_hash = generate_hash(temp_path)
            os.remove(temp_path)

            logs = read_logs()
            match = next((log for log in logs if log['hash'] == new_hash), None)

            if match:
                result = f"✅ File is original (not tampered)"
            else:
                result = f"❌ File may be tampered or unknown"

    return render_template('verify.html', result=result, new_hash=new_hash)

if __name__ == '__main__':
    app.run(debug=True)