import boto3
import pymysql
import base64
import os
import google.generativeai as genai

# 环境变量读取
DB_HOST = os.environ['DB_HOST']
DB_NAME = os.environ['DB_NAME']
DB_USER = os.environ['DB_USER']
DB_PASSWORD = os.environ['DB_PASSWORD']
S3_BUCKET = os.environ['S3_BUCKET']
GOOGLE_API_KEY = os.environ['GOOGLE_API_KEY']

# Gemini 初始化
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-pro-exp-02-05")

def generate_caption(image_bytes):
    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        response = model.generate_content(
            [
                {"mime_type": "image/jpeg", "data": encoded},
                "Generate a short caption for this image"
            ]
        )
        return response.text or "[Empty]"
    except Exception as e:
        print(f"Gemini error: {e}")
        return "[Caption failed]"

def lambda_handler(event, context):
    print("Event:", event)

    s3 = boto3.client('s3')
    record = event['Records'][0]
    key = record['s3']['object']['key']

    try:
        # 下载图片
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        image_bytes = response['Body'].read()

        # 生成 caption
        caption = generate_caption(image_bytes)
        print(f"Generated caption: {caption}")

        # 写入数据库
        conn = pymysql.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connect_timeout=10
        )
        cursor = conn.cursor()
        sql = "UPDATE captions SET caption = %s WHERE image_key = %s"
        cursor.execute(sql, (caption, key))
        conn.commit()
        conn.close()

        return {
            'statusCode': 200,
            'body': f'Successfully captioned {key}'
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': f'Failed to process {key}'
        }
