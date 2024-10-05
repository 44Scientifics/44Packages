import os
import boto3
from dotenv import load_dotenv

load_dotenv()


def upload_to_S3(file_object, bucket_name: str, file_name: str):
    s3 = boto3.client(
        service_name="s3",
        region_name=os.getenv("AWS_DEFAULT_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )

    s3.upload_fileobj(file_object, bucket_name, file_name)

    file_path_in_s3 = f"{file_name}"
    return file_path_in_s3


def read_file_from_s3(bucket_name, file_name):
    s3 = boto3.client(
        service_name="s3",
        region_name=os.getenv("AWS_DEFAULT_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    obj = s3.get_object(Bucket=bucket_name, Key=file_name)
    data = obj['Body'].read()
    return data


def delete_file_from_S3(bucket_name, file_name):
    s3 = boto3.client(
        service_name="s3",
        region_name=os.getenv("AWS_DEFAULT_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    obj = s3.get_object(Bucket=bucket_name, Key=file_name)
    obj.delete()
