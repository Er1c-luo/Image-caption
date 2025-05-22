import json
import boto3
import pymysql
import base64
import google.generativeai as genai

# Gemini API 配置
genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel(model_name="gemini-2.0-pro-exp-02-05")

# RDS 数据库配置（替换成你的真实值）
DB_HOST = "your-db-endpoint"
DB_USER = "your-db-user"
DB_PASSWORD = "your-db-password"
DB_NAME = "image_caption_db"

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    
    # 获取 S3 信息
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # 跳过 thumbnails 文件夹
    if key.startswith("thumbnails/"):
        return {"status": "skipped"}

    # 下载图片数据
    response = s3.get_object(Bucket=bucket, Key=key)
    image_data = response['Body'].read()

    # 使用 Gemini 生成 caption
    encoded_image = base64.b64encode(image_data).decode("utf-8")
    caption = model.generate_content(
        [{"mime_type": "image/jpeg", "data": encoded_image}, "Caption this image."]
    ).text

    # 将 caption 写入数据库
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    with conn.cursor() as cursor:
        cursor.execute("UPDATE captions SET caption=%s WHERE image_key=%s", (caption, key))
        conn.commit()
    conn.close()

    return {"status": "success", "caption": caption}
