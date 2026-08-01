import pytest
from unittest.mock import MagicMock, patch
from io import BytesIO
from FortyFour.Utils.aws import upload_to_s3, read_file_from_s3, delete_file_from_s3


def test_upload_to_s3():
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        file_obj = BytesIO(b"test data")
        result = upload_to_s3(file_obj, "my-bucket", "test.txt", "us-east-1", "key", "secret")
        mock_s3.upload_fileobj.assert_called_once_with(file_obj, "my-bucket", "test.txt")
        assert result == "test.txt"


def test_read_file_from_s3():
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_s3.get_object.return_value = {"Body": MagicMock(read=MagicMock(return_value=b"hello"))}
        mock_client.return_value = mock_s3
        result = read_file_from_s3("my-bucket", "test.txt", "us-east-1", "key", "secret")
        mock_s3.get_object.assert_called_once_with(Bucket="my-bucket", Key="test.txt")
        assert result == b"hello"


def test_delete_file_from_s3():
    with patch("boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        delete_file_from_s3("my-bucket", "test.txt", "us-east-1", "key", "secret")
        mock_s3.delete_object.assert_called_once_with(Bucket="my-bucket", Key="test.txt")
