"""
Filesystem abstraction to use either the local file system or S3 compatible storage system like MinIO.
"""
from abc import ABC, abstractmethod
from typing import BinaryIO, List, Optional, Union
from pathlib import Path
import os
import shutil
import glob
import io
import tempfile
from contextlib import contextmanager


class FileSystemBackend(ABC):
    """Abstract base class for filesystem operations."""

    @abstractmethod
    def write_file(self, path: str, content: Union[bytes, BinaryIO], content_type: Optional[str] = None) -> None:
        """
        Write content to a file.

        Args:
            path: The file path
            content: Either bytes or a file-like object to write
            content_type: Optional MIME type for the file
        """
        pass

    @abstractmethod
    def read_file(self, path: str) -> bytes:
        """
        Read entire file content as bytes.

        Args:
            path: The file path

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    def read_file_stream(self, path: str) -> BinaryIO:
        """
        Open a file for streaming/reading.

        Args:
            path: The file path

        Returns:
            File-like object for reading
        """
        pass

    @abstractmethod
    def delete_file(self, path: str) -> None:
        """
        Delete a file.

        Args:
            path: The file path
        """
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
            path: The file path

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def makedirs(self, path: str, exist_ok: bool = True) -> None:
        """
        Create directories (including parent directories).

        Args:
            path: The directory path
            exist_ok: If True, don't raise error if directory exists
        """
        pass

    @abstractmethod
    def list_files(self, pattern: str) -> List[str]:
        """
        List files matching a glob pattern.

        Args:
            pattern: Glob pattern (e.g., "*.pdf", "dir/*.marked.*.pdf")

        Returns:
            List of matching file paths
        """
        pass

    @abstractmethod
    def get_file_path(self, *parts: str) -> str:
        """
        Join path components into a complete path.

        Args:
            parts: Path components to join

        Returns:
            Complete file path
        """
        pass

    @abstractmethod
    def get_base_path(self) -> str:
        """
        Get the base storage path.

        Returns:
            Base storage path
        """
        pass

    @abstractmethod
    def rename(self, src: str, dst: str) -> None:
        """
        Rename/move a file.

        Args:
            src: Source file path
            dst: Destination file path
        """
        pass

    @abstractmethod
    def get_local_path(self, path: str) -> str:
        """
        Get a local filesystem path for the file.
        For local storage, returns the path directly.
        For S3, downloads to temp directory and returns the temp path.

        Args:
            path: The file path in storage

        Returns:
            Local filesystem path to the file
        """
        pass

    @abstractmethod
    def sync_to_storage(self, local_path: str, storage_path: str) -> None:
        """
        Sync a local file to storage.
        For local storage, this is a no-op if paths are the same.
        For S3, uploads the local file to S3.

        Args:
            local_path: Path to the local file
            storage_path: Path in storage where file should be saved
        """
        pass

    @contextmanager
    def with_local_file(self, path: str, mode: str = "r"):
        """
        Context manager for working with a local copy of a file.
        Automatically handles download (for S3) and cleanup.

        Args:
            path: The file path in storage
            mode: File access mode ("r" for read-only, "rw" for read-write)

        Yields:
            Local filesystem path to the file

        Example:
            with fs.with_local_file("path/to/file.pdf", "rw") as local_path:
                # Work with local_path
                subprocess.run(["pdftotext", local_path, output_path])
            # File is automatically synced back to storage if mode is "rw"
        """
        local_path = self.get_local_path(path)
        try:
            yield local_path
            # If mode includes write, sync back to storage
            if "w" in mode:
                self.sync_to_storage(local_path, path)
        finally:
            # Cleanup is handled by the implementation
            pass


class LocalFileSystem(FileSystemBackend):
    """Local filesystem implementation."""

    def __init__(self, base_path: str):
        """
        Initialize local filesystem backend.

        Args:
            base_path: Base directory for file storage
        """
        self.base_path = base_path
        # Ensure base path exists
        os.makedirs(base_path, exist_ok=True)
        self.temp_dir = None  # Local storage doesn't need a separate temp dir

    def write_file(self, path: str, content: Union[bytes, BinaryIO], content_type: Optional[str] = None) -> None:
        """Write content to a file."""
        # Ensure directory exists
        dir_path = os.path.dirname(path)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)

        with open(path, 'wb') as f:
            if isinstance(content, bytes):
                f.write(content)
            else:
                # It's a file-like object
                shutil.copyfileobj(content, f)

    def read_file(self, path: str) -> bytes:
        """Read entire file content as bytes."""
        with open(path, 'rb') as f:
            return f.read()

    def read_file_stream(self, path: str) -> BinaryIO:
        """Open a file for streaming/reading."""
        return open(path, 'rb')

    def delete_file(self, path: str) -> None:
        """Delete a file."""
        if os.path.exists(path):
            os.remove(path)

    def exists(self, path: str) -> bool:
        """Check if a file exists."""
        return os.path.exists(path)

    def makedirs(self, path: str, exist_ok: bool = True) -> None:
        """Create directories (including parent directories)."""
        os.makedirs(path, exist_ok=exist_ok)

    def list_files(self, pattern: str) -> List[str]:
        """List files matching a glob pattern."""
        return glob.glob(pattern)

    def get_file_path(self, *parts: str) -> str:
        """Join path components into a complete path."""
        return os.path.join(*parts)

    def get_base_path(self) -> str:
        """Get the base storage path."""
        return self.base_path

    def rename(self, src: str, dst: str) -> None:
        """Rename/move a file."""
        os.rename(src, dst)

    def get_local_path(self, path: str) -> str:
        """Return the path directly (already local)."""
        return path

    def sync_to_storage(self, local_path: str, storage_path: str) -> None:
        """No-op for local storage if paths are the same, otherwise copy."""
        if local_path != storage_path:
            shutil.copy2(local_path, storage_path)


class S3FileSystem(FileSystemBackend):
    """S3-compatible storage implementation (works with MinIO, AWS S3, etc.)."""

    def __init__(self, endpoint_url: str, bucket_name: str, access_key: str,
                 secret_key: str, region: Optional[str] = None, base_prefix: str = "",
                 temp_dir: Optional[str] = None):
        """
        Initialize S3 filesystem backend.

        Args:
            endpoint_url: S3 endpoint URL (e.g., "https://s3.amazonaws.com" or MinIO URL)
            bucket_name: S3 bucket name
            access_key: AWS access key ID
            secret_key: AWS secret access key
            region: AWS region (optional)
            base_prefix: Base prefix/folder within the bucket (optional)
            temp_dir: Local temp directory for file operations (optional, creates if not provided)
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 storage. Install it with: pip install boto3"
            )

        self.bucket_name = bucket_name
        self.base_prefix = base_prefix.rstrip('/') if base_prefix else ""
        self.ClientError = ClientError

        # Setup temp directory for local file operations
        if temp_dir:
            self.temp_dir = temp_dir
            os.makedirs(temp_dir, exist_ok=True)
        else:
            # Create a persistent temp directory
            self.temp_dir = os.path.join(tempfile.gettempdir(), "s3_file_cache")
            os.makedirs(self.temp_dir, exist_ok=True)

        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )

        # Verify bucket exists or create it
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                # Bucket doesn't exist, create it
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                raise

    def _get_s3_key(self, path: str) -> str:
        """
        Convert a file path to an S3 key.

        Args:
            path: File path

        Returns:
            S3 object key
        """
        # Normalize path separators and remove leading/trailing slashes
        normalized = path.replace('\\', '/').strip('/')

        if self.base_prefix:
            return f"{self.base_prefix}/{normalized}"
        return normalized

    def write_file(self, path: str, content: Union[bytes, BinaryIO], content_type: Optional[str] = None) -> None:
        """Write content to S3."""
        key = self._get_s3_key(path)
        extra_args = {}

        if content_type:
            extra_args['ContentType'] = content_type

        if isinstance(content, bytes):
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                **extra_args
            )
        else:
            # It's a file-like object
            self.s3_client.upload_fileobj(
                content,
                self.bucket_name,
                key,
                ExtraArgs=extra_args if extra_args else None
            )

    def read_file(self, path: str) -> bytes:
        """Read entire file content from S3."""
        key = self._get_s3_key(path)
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body'].read()

    def read_file_stream(self, path: str) -> BinaryIO:
        """Get a streaming object from S3."""
        key = self._get_s3_key(path)
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        # Return the streaming body wrapped to ensure compatibility
        return response['Body']

    def delete_file(self, path: str) -> None:
        """Delete a file from S3."""
        key = self._get_s3_key(path)
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
        except self.ClientError:
            # Silently ignore if file doesn't exist (matching local behavior)
            pass

    def exists(self, path: str) -> bool:
        """Check if a file exists in S3."""
        key = self._get_s3_key(path)
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.ClientError:
            return False

    def makedirs(self, path: str, exist_ok: bool = True) -> None:
        """
        No-op for S3 (directories don't need to be created).
        Included for API compatibility.
        """
        pass

    def list_files(self, pattern: str) -> List[str]:
        """
        List files matching a pattern in S3.
        Note: This implements basic glob-like matching but is less flexible than filesystem glob.
        """
        import fnmatch

        # Convert pattern to S3 prefix
        # Extract the directory part and the filename pattern
        pattern = pattern.replace('\\', '/')
        if '/' in pattern:
            prefix_parts = pattern.split('/')
            # Find where wildcards start
            prefix_end = 0
            for i, part in enumerate(prefix_parts):
                if '*' in part or '?' in part or '[' in part:
                    break
                prefix_end = i + 1

            if prefix_end > 0:
                prefix = '/'.join(prefix_parts[:prefix_end])
            else:
                prefix = ""
        else:
            prefix = ""

        s3_prefix = self._get_s3_key(prefix) if prefix else self.base_prefix

        # List objects with the prefix
        matching_files = []
        paginator = self.s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=s3_prefix):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                # Remove base prefix to get relative path
                if self.base_prefix and key.startswith(self.base_prefix + '/'):
                    relative_path = key[len(self.base_prefix) + 1:]
                else:
                    relative_path = key

                # Match against pattern
                if fnmatch.fnmatch(relative_path, pattern.replace('\\', '/')):
                    # Reconstruct full path similar to local filesystem
                    if self.base_prefix:
                        full_path = os.path.join(self.base_prefix, relative_path)
                    else:
                        full_path = relative_path
                    matching_files.append(full_path)

        return matching_files

    def get_file_path(self, *parts: str) -> str:
        """Join path components into a complete path."""
        # For S3, we still use local path joining, then convert to S3 key when needed
        return os.path.join(*parts)

    def get_base_path(self) -> str:
        """Get the base storage path."""
        if self.base_prefix:
            return self.base_prefix
        return ""

    def rename(self, src: str, dst: str) -> None:
        """Rename/move a file in S3 (copy + delete)."""
        src_key = self._get_s3_key(src)
        dst_key = self._get_s3_key(dst)

        # Copy object to new location
        self.s3_client.copy_object(
            Bucket=self.bucket_name,
            CopySource={'Bucket': self.bucket_name, 'Key': src_key},
            Key=dst_key
        )

        # Delete original
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=src_key)

    def get_local_path(self, path: str) -> str:
        """Download file from S3 to temp directory and return local path."""
        # Create a local path that mirrors the S3 structure
        key = self._get_s3_key(path)
        # Use a hash or sanitized version to avoid path issues
        local_path = os.path.join(self.temp_dir, path.replace('/', '_'))

        # Ensure directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        # Download file if it doesn't exist locally or if S3 version is newer
        try:
            self.s3_client.download_file(self.bucket_name, key, local_path)
        except self.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise FileNotFoundError(f"File not found in S3: {path}")
            raise

        return local_path

    def sync_to_storage(self, local_path: str, storage_path: str) -> None:
        """Upload local file to S3."""
        key = self._get_s3_key(storage_path)
        self.s3_client.upload_file(local_path, self.bucket_name, key)


# Global filesystem instance
_filesystem: Optional[FileSystemBackend] = None


def init_filesystem(
    backend_type: str = "local",
    base_path: Optional[str] = None,
    s3_endpoint: Optional[str] = None,
    s3_bucket: Optional[str] = None,
    s3_access_key: Optional[str] = None,
    s3_secret_key: Optional[str] = None,
    s3_region: Optional[str] = None,
    s3_prefix: Optional[str] = None,
    temp_dir: Optional[str] = None
) -> FileSystemBackend:
    """
    Initialize the filesystem backend based on configuration.

    Args:
        backend_type: "local" or "s3"
        base_path: Base path for local filesystem
        s3_endpoint: S3 endpoint URL
        s3_bucket: S3 bucket name
        s3_access_key: S3 access key
        s3_secret_key: S3 secret key
        s3_region: S3 region (optional)
        s3_prefix: Base prefix within S3 bucket (optional)
        temp_dir: Local temp directory for S3 file operations (optional)

    Returns:
        Initialized filesystem backend
    """
    global _filesystem

    if backend_type.lower() == "local":
        if not base_path:
            raise ValueError("base_path is required for local filesystem")
        _filesystem = LocalFileSystem(base_path)
    elif backend_type.lower() == "s3":
        if not all([s3_endpoint, s3_bucket, s3_access_key, s3_secret_key]):
            raise ValueError(
                "s3_endpoint, s3_bucket, s3_access_key, and s3_secret_key "
                "are required for S3 filesystem"
            )
        _filesystem = S3FileSystem(
            endpoint_url=s3_endpoint,
            bucket_name=s3_bucket,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
            region=s3_region,
            base_prefix=s3_prefix or "",
            temp_dir=temp_dir
        )
    else:
        raise ValueError(f"Unknown backend type: {backend_type}")

    return _filesystem


def get_filesystem() -> FileSystemBackend:
    """
    Get the initialized filesystem backend.

    Returns:
        The filesystem backend instance

    Raises:
        RuntimeError: If filesystem has not been initialized
    """
    if _filesystem is None:
        raise RuntimeError(
            "Filesystem not initialized. Call init_filesystem() first."
        )
    return _filesystem


def init_filesystem_from_env() -> FileSystemBackend:
    """
    Initialize filesystem from environment variables.

    Expected environment variables:
    - STORAGE_BACKEND: "local" or "s3" (default: "local")
    - DOCUMENT_STORAGE: Base path for local storage (required for local)
    - S3_ENDPOINT: S3 endpoint URL (required for s3)
    - S3_BUCKET: S3 bucket name (required for s3)
    - S3_ACCESS_KEY: S3 access key (required for s3)
    - S3_SECRET_KEY: S3 secret key (required for s3)
    - S3_REGION: S3 region (optional)
    - S3_PREFIX: Base prefix within S3 bucket (optional)
    - TEMP_DIR: Local temp directory for S3 file operations (optional)

    Returns:
        Initialized filesystem backend
    """
    backend_type = os.environ.get('STORAGE_BACKEND', 'local')

    return init_filesystem(
        backend_type=backend_type,
        base_path=os.environ.get('DOCUMENT_STORAGE'),
        s3_endpoint=os.environ.get('S3_ENDPOINT'),
        s3_bucket=os.environ.get('S3_BUCKET'),
        s3_access_key=os.environ.get('S3_ACCESS_KEY'),
        s3_secret_key=os.environ.get('S3_SECRET_KEY'),
        s3_region=os.environ.get('S3_REGION'),
        s3_prefix=os.environ.get('S3_PREFIX'),
        temp_dir=os.environ.get('TEMP_DIR')
    )