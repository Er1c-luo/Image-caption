"""
COMP5349 Assignment: Image Captioning App using Gemini API and AWS Services

IMPORTANT:
Before running this application, ensure that you update the following configurations:
1. Replace the GEMINI API key (`GOOGLE_API_KEY`) with your own key from Google AI Studio.
2. Replace the AWS S3 bucket name (`S3_BUCKET`) with your own S3 bucket.
3. Update the RDS MySQL database credentials (`DB_HOST`, `DB_USER`, `DB_PASSWORD`).
4. Ensure all necessary dependencies are installed by running the provided setup script.

Failure to update these values will result in authentication errors or failure to access cloud services.
"""

# To use on an AWS Linux instance
# #!/bin/bash
# sudo yum install python3-pip -y
# pip install flask
# pip install mysql-connector-python
# pip install -q -U google-generativeai
# pip install boto3 werkzeug
# sudo yum install -y mariadb105

import boto3  # AWS S3 SDK
import mysql.connector  # MySQL database connector
from flask import Flask, request, render_template # Web framework
from werkzeug.utils import secure_filename  # Secure filename handling
import base64  # Encoding image data for API processing
from io import BytesIO  # Handling in-memory file objects
import os


# Flask app setup
app = Flask(__name__)

# AWS S3 Configuration
S3_BUCKET = "myiamgebucket"
S3_REGION = "us-east-1"
# AWS S3 Configuration, REPLACE with your S3 bucket
DB_HOST = "captioning-db.cnwyqwsus01i.us-east-1.rds.amazonaws.com"
DB_NAME = "image_caption_db"
DB_USER = "admin"
DB_PASSWORD = "labpassword"

# Allowed file types
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def get_s3_client():
    return boto3.client("s3", region_name=S3_REGION)

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD
        )
    except mysql.connector.Error as err:
        print("Error connecting to DB:", err)
        return None

@app.route("/")
def upload_form():
    return render_template("index.html")

@app.route("/upload", methods=["GET", "POST"])
def upload_image():
    if request.method == "POST":
        if "file" not in request.files:
            return render_template("upload.html", error="No file part")

        file = request.files["file"]
        if file.filename == "":
            return render_template("upload.html", error="No selected file")

        if not allowed_file(file.filename):
            return render_template("upload.html", error="Invalid file type")

        filename = secure_filename(file.filename)
        file_data = file.read()

        # Upload to S3
        try:
            s3 = get_s3_client()
            s3.upload_fileobj(BytesIO(file_data), S3_BUCKET, filename)
        except Exception as e:
            print("S3 Upload Error:", e)
            return render_template("upload.html", error=f"S3 Error: {str(e)}")

        # Insert metadata to DB, caption left empty (to be filled by Lambda)
        try:
            conn = get_db_connection()
            if conn is None:
                raise Exception("Database connection failed")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO captions (image_key, caption) VALUES (%s, %s)",
                (filename, "")
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print("DB Insert Error:", e)
            return render_template("upload.html", error=f"DB Error: {str(e)}")

        image_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{filename}"
        return render_template("upload.html", file_url=image_url)

    return render_template("upload.html")

@app.route("/gallery")
def gallery():
    try:
        conn = get_db_connection()
        if conn is None:
            raise Exception("Database connection failed")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT image_key, caption FROM captions ORDER BY uploaded_at DESC")
        rows = cursor.fetchall()
        conn.close()

        images = []
        for row in rows:
            image_url = get_s3_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": row["image_key"]},
                ExpiresIn=3600,
            )
            thumbnail_key = f"thumbnails/{row['image_key']}"
            thumbnail_url = get_s3_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": thumbnail_key},
                ExpiresIn=3600,
            )
            images.append({
                "image_url": image_url,
                "thumbnail_url": thumbnail_url,
                "caption": row["caption"] or "[Pending annotation...]"
            })

        return render_template("gallery.html", images=images)

    except Exception as e:
        print("Gallery Load Error:", e)
        return render_template("gallery.html", error=f"Gallery Error: {str(e)}")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
