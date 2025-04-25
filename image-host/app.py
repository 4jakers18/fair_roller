from flask import Flask, request, redirect, send_from_directory, render_template_string
from pathlib import Path
import mimetypes, os

app = Flask(__name__)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

HTML = """
<!doctype html>
<title>Fair Roller Cam</title>
<h1>Last upload</h1>
{% if image %}
  <img src="{{ url_for('uploaded_file', filename=image) }}" style="max-width:480px;"><br>
{% else %}
  <p><em>No image yet.</em></p>
{% endif %}
<hr>
<h2>Upload new image</h2>
<form method="post" enctype="multipart/form-data" action="/upload">
  <input type="file" name="file" accept="image/*" required>
  <button type="submit">Upload</button>
</form>
"""

def latest_image():
    pics = sorted(UPLOAD_DIR.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    return pics[0].name if pics else None

@app.route("/")
def index():
    return render_template_string(HTML, image=latest_image())

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("file")
    if not file:
        return redirect("/")
    if not file.mimetype.startswith("image/"):
        return "Only images, please.", 400
    ext = mimetypes.guess_extension(file.mimetype) or ".jpg"
    fname = f"cam_{int(Path().stat().st_mtime_ns)}{ext}"
    file.save(UPLOAD_DIR / fname)
    return redirect("/")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, cache_timeout=0)
