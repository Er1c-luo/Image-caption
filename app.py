import boto3
import mysql.connector
from flask import Flask, request, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from io import BytesIO
from os.path import basename

app = Flask(__name__)

S3_BUCKET = "myimage-bk"
S3_REGION = "us-east-1"
DB_HOST = "captioning-db.cgn20o9covfc.us-east-1.rds.amazonaws.com"
DB_NAME = "image_caption_db"
DB_USER = "admin"
DB_PASSWORD = "labpassword"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_s3_client():
    return boto3.client("s3", region_name=S3_REGION)

def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
    )

@app.route("/")
def upload_form():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_image():
    file = request.files.get("file")
    if not file or not allowed_file(file.filename):
        return render_template("upload.html", error="Invalid file")

    filename = secure_filename(basename(file.filename))
    file_data = file.read()
    upload_key = f"uploads/{filename}"

    try:
        s3 = get_s3_client()
        s3.upload_fileobj(BytesIO(file_data), S3_BUCKET, upload_key)
    except Exception as e:
        return render_template("upload.html", error=f"S3 Error: {str(e)}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO captions (image_key, caption, thumbnail_key) VALUES (%s, %s, %s)",
            (upload_key, "", None)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        return render_template("upload.html", error=f"DB Error: {str(e)}")

    return redirect(url_for("gallery"))

@app.route("/gallery")
def gallery():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT image_key, caption, thumbnail_key FROM captions;")
        rows = cursor.fetchall()
        conn.close()

        s3 = get_s3_client()
        images = []
        for row in rows:
            image_url = s3.generate_presigned_url("get_object", Params={"Bucket": S3_BUCKET, "Key": row["image_key"]}, ExpiresIn=3600)
            thumbnail_url = s3.generate_presigned_url("get_object", Params={"Bucket": S3_BUCKET, "Key": row["thumbnail_key"]}, ExpiresIn=3600) if row["thumbnail_key"] else None
            images.append({"image_url": image_url, "thumbnail_url": thumbnail_url, "caption": row["caption"] or "[Pending annotation...]"})

        return render_template("gallery.html", images=images)
    except Exception as e:
        return render_template("gallery.html", error=f"Gallery Error: {str(e)}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
    #app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

