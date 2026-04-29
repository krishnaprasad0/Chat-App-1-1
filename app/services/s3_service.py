import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import logging
from typing import Optional
import os
from cryptography.fernet import Fernet
import io

logger = logging.getLogger(__name__)

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.bucket_name = settings.S3_BUCKET_NAME
        self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    async def upload_file(
        self, 
        file_data: bytes, 
        file_name: str, 
        content_type: str,
        prefix: str = "media",
        encrypt: bool = True
    ) -> Optional[str]:
        """
        Uploads a file to S3. If encrypt is True, the file is encrypted before upload.
        Returns the public URL of the file.
        """
        try:
            if encrypt:
                # Encrypt the file data
                file_data = self.fernet.encrypt(file_data)
                file_name = f"enc_{file_name}"

            # Upload to S3 under the specified folder
            key = f"{prefix}/{file_name}"
            
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_data,
                ContentType=content_type
            )

            # Generate URL
            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            return url

        except ClientError as e:
            logger.error(f"S3 Upload Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected Upload Error: {e}")
            return None

    async def download_file(self, key: str, decrypt: bool = True) -> Optional[bytes]:
        """
        Downloads a file from S3 and decrypts it if requested.
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            file_data = response['Body'].read()

            if decrypt:
                file_data = self.fernet.decrypt(file_data)

            return file_data
        except ClientError as e:
            logger.error(f"S3 Download Error: {e}")
            return None

s3_service = S3Service()
