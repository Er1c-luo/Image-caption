from PIL import Image
import boto3
from io import BytesIO
import pymysql

# RDS 数据库配置（替换成你的真实值）
DB_HOST = "your-db-endpoint"
DB_USER = "your-db-user"
DB_PASSWORD = "your-db-password"
DB_NAME = "image_caption_db"

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # 跳过 thumbnails 文件夹
    if key.startswith("thumbnails/"):
        return {"status": "skipped"}

    # 下载原始图片
    response = s3.get_object(Bucket=bucket, Key=key)
    image_data = response['Body'].read()

    # 生成缩略图
    img = Image.open(BytesIO(image_data))
    img.thumbnail((128, 128))
    output = BytesIO()
    img.save(output, format="JPEG")
    output.seek(0)

    thumb_key = f"thumbnails/{key}"
    s3.upload_fileobj(output, bucket, thumb_key)

    # 将 thumbnail_key 写入数据库
    conn = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME)
    with conn.cursor() as cursor:
        cursor.execute("UPDATE captions SET thumbnail_key=%s WHERE image_key=%s", (thumb_key, key))
        conn.commit()
    conn.close()

    return {"status": "success", "thumbnail_key": thumb_key}
