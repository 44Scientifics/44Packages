from typing import BinaryIO

import boto3


def upload_to_s3(file_object: BinaryIO, bucket_name: str, file_name: str, region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> str:
    s3 = boto3.client(
        service_name="s3",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )

    s3.upload_fileobj(file_object, bucket_name, file_name)

    return file_name


def read_file_from_s3(bucket_name: str, file_name: str, region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> bytes:
    s3 = boto3.client(
        service_name="s3",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
    obj = s3.get_object(Bucket=bucket_name, Key=file_name)
    data = obj['Body'].read()
    return data


def delete_file_from_s3(bucket_name: str, file_name: str, region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> None:
    s3 = boto3.client(
        service_name="s3",
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key
    )
    s3.delete_object(Bucket=bucket_name, Key=file_name)
