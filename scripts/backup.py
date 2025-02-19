#!/usr/bin/env python
import os
import subprocess
import logging
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        self.backup_dir = Path("/app/backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        self.max_local_backups = int(os.getenv("MAX_LOCAL_BACKUPS", "5"))
        
        # AWS S3 configuration
        self.s3_bucket = os.getenv("BACKUP_S3_BUCKET")
        self.aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        
        # Database configuration
        self.db_host = 'db'
        self.db_user = 'postgres'
        self.db_name = 'civic_tracker'
        self.db_password = os.getenv("POSTGRES_PASSWORD")
        
    def create_database_backup(self):
        """Create a backup of the PostgreSQL database"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"db_backup_{timestamp}.sql"
        
        cmd = [
            "pg_dump",
            "-h", self.db_host,
            "-U", self.db_user,
            "-d", self.db_name,
            "-f", str(backup_file)
        ]
        
        try:
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.db_password
            
            subprocess.run(cmd, check=True, env=env)
            logger.info(f"Database backup created: {backup_file}")
            return backup_file
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create database backup: {str(e)}")
            raise

    def upload_to_s3(self, file_path):
        """Upload backup file to S3"""
        if not all([self.s3_bucket, self.aws_access_key, self.aws_secret_key]):
            logger.warning("AWS credentials not found. S3 backup disabled.")
            return False
            
        try:
            s3 = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key
            )
            
            file_name = file_path.name
            s3.upload_file(str(file_path), self.s3_bucket, f"backups/{file_name}")
            logger.info(f"Backup uploaded to S3: {self.s3_bucket}/backups/{file_name}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            return False

    def cleanup_old_backups(self):
        """Remove old local backups keeping only the most recent ones"""
        try:
            backups = sorted(
                [f for f in self.backup_dir.glob("db_backup_*")],
                reverse=True
            )
            
            for old_backup in backups[self.max_local_backups:]:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {str(e)}")

    def run_backup(self):
        """Run the complete backup process"""
        try:
            # Create database backup
            backup_file = self.create_database_backup()
            
            # Upload to S3 if configured
            self.upload_to_s3(backup_file)
            
            # Cleanup old backups
            self.cleanup_old_backups()
            
            logger.info("Backup process completed successfully")
        except Exception as e:
            logger.error(f"Backup process failed: {str(e)}")
            raise

if __name__ == "__main__":
    backup_manager = BackupManager()
    backup_manager.run_backup()
