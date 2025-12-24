#!/usr/bin/env python3
"""
Video Transfer Pipeline
Automated transfer pipeline for processed video content to various output formats and destinations
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import shutil
import zipfile
from urllib.parse import urlparse
import hashlib

# Import our processors
from video_extractor_enhanced import VideoContent
from notebooklm_processor import VideoNotebook
from videoprism_analyzer import VideoPrismAnalysis

# Cloud storage imports (optional)
try:
    import boto3
    from google.cloud import storage as gcs
    import dropbox
    HAS_CLOUD_DEPS = True
except ImportError:
    HAS_CLOUD_DEPS = False
    logging.warning("Cloud storage dependencies not available")

# Email and notification imports (optional)
try:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    import requests
    HAS_NOTIFICATION_DEPS = True
except ImportError:
    HAS_NOTIFICATION_DEPS = False
    logging.warning("Notification dependencies not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [Transfer] %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class TransferDestination:
    """Configuration for transfer destination"""
    destination_type: str  # local, s3, gcs, dropbox, email, webhook
    destination_path: str
    credentials: Dict[str, Any] = None
    options: Dict[str, Any] = None

@dataclass
class TransferPackage:
    """Package containing all processed content for transfer"""
    video_metadata: Dict[str, Any]
    video_content: Optional[VideoContent] = None
    notebook: Optional[VideoNotebook] = None
    analysis: Optional[VideoPrismAnalysis] = None
    files: List[str] = None  # List of file paths to transfer
    created_at: str = None

@dataclass
class TransferResult:
    """Result of transfer operation"""
    destination: TransferDestination
    success: bool
    transferred_files: List[str]
    destination_urls: List[str]
    error_message: Optional[str] = None
    transfer_time: float = 0.0

class VideoTransferPipeline:
    """
    Automated transfer pipeline for processed video content
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.temp_dir = Path("/tmp/video_transfer")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize cloud clients if available
        self.cloud_clients = {}
        if HAS_CLOUD_DEPS:
            self._initialize_cloud_clients()
        
        logger.info("Video Transfer Pipeline initialized")
    
    def _initialize_cloud_clients(self):
        """Initialize cloud storage clients"""
        try:
            # AWS S3
            if self.config.get('aws_access_key_id'):
                self.cloud_clients['s3'] = boto3.client(
                    's3',
                    aws_access_key_id=self.config.get('aws_access_key_id'),
                    aws_secret_access_key=self.config.get('aws_secret_access_key'),
                    region_name=self.config.get('aws_region', 'us-east-1')
                )
                logger.info("AWS S3 client initialized")
            
            # Google Cloud Storage
            if self.config.get('gcs_credentials_path'):
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = self.config.get('gcs_credentials_path')
                self.cloud_clients['gcs'] = gcs.Client()
                logger.info("Google Cloud Storage client initialized")
            
            # Dropbox
            if self.config.get('dropbox_access_token'):
                self.cloud_clients['dropbox'] = dropbox.Dropbox(
                    self.config.get('dropbox_access_token')
                )
                logger.info("Dropbox client initialized")
        
        except Exception as e:
            logger.warning(f"Failed to initialize some cloud clients: {e}")
    
    async def create_transfer_package(
        self,
        video_content: Optional[VideoContent] = None,
        notebook: Optional[VideoNotebook] = None,
        analysis: Optional[VideoPrismAnalysis] = None,
        include_raw_data: bool = True
    ) -> TransferPackage:
        """Create a comprehensive transfer package"""
        logger.info("Creating transfer package...")
        
        # Create unique package directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if video_content:
            video_id = video_content.metadata.video_id
        elif notebook:
            video_id = notebook.video_metadata.video_id
        elif analysis:
            video_id = analysis.video_metadata.video_id
        else:
            video_id = "unknown"
        
        package_dir = self.temp_dir / f"package_{video_id}_{timestamp}"
        package_dir.mkdir(exist_ok=True)
        
        files = []
        video_metadata = {}
        
        try:
            # Process video content
            if video_content:
                video_metadata = asdict(video_content.metadata)
                
                # Export transcript
                if video_content.transcript:
                    transcript_file = package_dir / "transcript.json"
                    transcript_data = [asdict(seg) for seg in video_content.transcript]
                    with open(transcript_file, 'w', encoding='utf-8') as f:
                        json.dump(transcript_data, f, indent=2, default=str)
                    files.append(str(transcript_file))
                
                # Export summary and analysis
                content_file = package_dir / "video_content.json"
                with open(content_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(video_content), f, indent=2, default=str)
                files.append(str(content_file))
            
            # Process notebook
            if notebook:
                if not video_metadata:
                    video_metadata = asdict(notebook.video_metadata)
                
                # Export notebook as markdown
                notebook_md = package_dir / "notebook.md"
                markdown_content = self._generate_notebook_markdown(notebook)
                with open(notebook_md, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                files.append(str(notebook_md))
                
                # Export notebook as JSON
                notebook_json = package_dir / "notebook.json"
                with open(notebook_json, 'w', encoding='utf-8') as f:
                    json.dump(asdict(notebook), f, indent=2, default=str)
                files.append(str(notebook_json))
                
                # Export insights separately
                insights_file = package_dir / "insights.txt"
                with open(insights_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Key Insights from {notebook.video_metadata.title}\n\n")
                    for i, insight in enumerate(notebook.key_insights, 1):
                        f.write(f"{i}. {insight}\n")
                    
                    f.write(f"\n# Discussion Questions\n\n")
                    for question in notebook.questions_raised:
                        f.write(f"- {question}\n")
                    
                    f.write(f"\n# Action Items\n\n")
                    for action in notebook.action_items:
                        f.write(f"{action}\n")
                files.append(str(insights_file))
            
            # Process analysis
            if analysis:
                if not video_metadata:
                    video_metadata = asdict(analysis.video_metadata)
                
                # Export analysis as JSON
                analysis_json = package_dir / "analysis.json"
                with open(analysis_json, 'w', encoding='utf-8') as f:
                    json.dump(asdict(analysis), f, indent=2, default=str)
                files.append(str(analysis_json))
                
                # Export analysis report
                report_file = package_dir / "analysis_report.md"
                report_content = self._generate_analysis_report(analysis)
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                files.append(str(report_file))
                
                # Export category and audience info
                category_file = package_dir / "categorization.txt"
                with open(category_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Content Categorization for {analysis.video_metadata.title}\n\n")
                    f.write(f"Primary Category: {analysis.content_category.primary_category}\n")
                    f.write(f"Subcategories: {', '.join(analysis.content_category.subcategories)}\n")
                    f.write(f"Target Audience: {analysis.audience_analysis.target_age_group}\n")
                    f.write(f"Education Level: {analysis.audience_analysis.education_level}\n")
                    f.write(f"Expertise Level: {analysis.audience_analysis.expertise_level}\n")
                    f.write(f"Accessibility Score: {analysis.audience_analysis.accessibility_score:.2f}\n")
                files.append(str(category_file))
            
            # Create package summary
            summary_file = package_dir / "package_summary.json"
            package_summary = {
                "created_at": datetime.now().isoformat(),
                "video_metadata": video_metadata,
                "included_components": {
                    "video_content": video_content is not None,
                    "notebook": notebook is not None,
                    "analysis": analysis is not None
                },
                "files": [Path(f).name for f in files],
                "package_size": sum(Path(f).stat().st_size for f in files if Path(f).exists())
            }
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(package_summary, f, indent=2)
            files.append(str(summary_file))
            
            # Create transfer package
            package = TransferPackage(
                video_metadata=video_metadata,
                video_content=video_content,
                notebook=notebook,
                analysis=analysis,
                files=files,
                created_at=datetime.now().isoformat()
            )
            
            logger.info(f"Transfer package created with {len(files)} files")
            return package
        
        except Exception as e:
            logger.error(f"Failed to create transfer package: {e}")
            # Clean up on failure
            if package_dir.exists():
                shutil.rmtree(package_dir)
            raise
    
    async def transfer_package(
        self,
        package: TransferPackage,
        destinations: List[TransferDestination],
        create_archive: bool = True
    ) -> List[TransferResult]:
        """Transfer package to multiple destinations"""
        logger.info(f"Transferring package to {len(destinations)} destinations...")
        
        results = []
        archive_path = None
        
        try:
            # Create archive if requested
            if create_archive and package.files:
                archive_path = await self._create_archive(package)
            
            # Transfer to each destination
            for destination in destinations:
                try:
                    start_time = datetime.now()
                    
                    if destination.destination_type == "local":
                        result = await self._transfer_to_local(package, destination, archive_path)
                    elif destination.destination_type == "s3":
                        result = await self._transfer_to_s3(package, destination, archive_path)
                    elif destination.destination_type == "gcs":
                        result = await self._transfer_to_gcs(package, destination, archive_path)
                    elif destination.destination_type == "dropbox":
                        result = await self._transfer_to_dropbox(package, destination, archive_path)
                    elif destination.destination_type == "email":
                        result = await self._transfer_via_email(package, destination, archive_path)
                    elif destination.destination_type == "webhook":
                        result = await self._transfer_via_webhook(package, destination, archive_path)
                    else:
                        result = TransferResult(
                            destination=destination,
                            success=False,
                            transferred_files=[],
                            destination_urls=[],
                            error_message=f"Unsupported destination type: {destination.destination_type}"
                        )
                    
                    result.transfer_time = (datetime.now() - start_time).total_seconds()
                    results.append(result)
                    
                    if result.success:
                        logger.info(f"Successfully transferred to {destination.destination_type}")
                    else:
                        logger.error(f"Failed to transfer to {destination.destination_type}: {result.error_message}")
                
                except Exception as e:
                    logger.error(f"Transfer to {destination.destination_type} failed: {e}")
                    results.append(TransferResult(
                        destination=destination,
                        success=False,
                        transferred_files=[],
                        destination_urls=[],
                        error_message=str(e)
                    ))
            
            return results
        
        finally:
            # Clean up archive
            if archive_path and Path(archive_path).exists():
                Path(archive_path).unlink()
    
    async def _create_archive(self, package: TransferPackage) -> str:
        """Create ZIP archive of package files"""
        if not package.files:
            return None
        
        # Generate archive name
        video_id = package.video_metadata.get('video_id', 'unknown')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"video_package_{video_id}_{timestamp}.zip"
        archive_path = self.temp_dir / archive_name
        
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in package.files:
                    if Path(file_path).exists():
                        # Add file with relative path
                        arcname = Path(file_path).name
                        zipf.write(file_path, arcname)
            
            logger.info(f"Created archive: {archive_path}")
            return str(archive_path)
        
        except Exception as e:
            logger.error(f"Failed to create archive: {e}")
            return None
    
    async def _transfer_to_local(
        self,
        package: TransferPackage,
        destination: TransferDestination,
        archive_path: Optional[str] = None
    ) -> TransferResult:
        """Transfer to local directory"""
        try:
            dest_path = Path(destination.destination_path)
            dest_path.mkdir(parents=True, exist_ok=True)
            
            transferred_files = []
            destination_urls = []
            
            # Transfer archive if available
            if archive_path and Path(archive_path).exists():
                dest_file = dest_path / Path(archive_path).name
                shutil.copy2(archive_path, dest_file)
                transferred_files.append(str(dest_file))
                destination_urls.append(f"file://{dest_file}")
            else:
                # Transfer individual files
                for file_path in package.files or []:
                    if Path(file_path).exists():
                        dest_file = dest_path / Path(file_path).name
                        shutil.copy2(file_path, dest_file)
                        transferred_files.append(str(dest_file))
                        destination_urls.append(f"file://{dest_file}")
            
            return TransferResult(
                destination=destination,
                success=True,
                transferred_files=transferred_files,
                destination_urls=destination_urls
            )
        
        except Exception as e:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message=str(e)
            )
    
    async def _transfer_to_s3(
        self,
        package: TransferPackage,
        destination: TransferDestination,
        archive_path: Optional[str] = None
    ) -> TransferResult:
        """Transfer to AWS S3"""
        if 's3' not in self.cloud_clients:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message="S3 client not initialized"
            )
        
        try:
            s3_client = self.cloud_clients['s3']
            bucket_name = destination.destination_path.split('/')[0]
            prefix = '/'.join(destination.destination_path.split('/')[1:]) if '/' in destination.destination_path else ''
            
            transferred_files = []
            destination_urls = []
            
            # Transfer archive if available
            if archive_path and Path(archive_path).exists():
                key = f"{prefix}/{Path(archive_path).name}" if prefix else Path(archive_path).name
                s3_client.upload_file(archive_path, bucket_name, key)
                transferred_files.append(key)
                destination_urls.append(f"s3://{bucket_name}/{key}")
            else:
                # Transfer individual files
                for file_path in package.files or []:
                    if Path(file_path).exists():
                        key = f"{prefix}/{Path(file_path).name}" if prefix else Path(file_path).name
                        s3_client.upload_file(file_path, bucket_name, key)
                        transferred_files.append(key)
                        destination_urls.append(f"s3://{bucket_name}/{key}")
            
            return TransferResult(
                destination=destination,
                success=True,
                transferred_files=transferred_files,
                destination_urls=destination_urls
            )
        
        except Exception as e:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message=str(e)
            )
    
    async def _transfer_to_gcs(
        self,
        package: TransferPackage,
        destination: TransferDestination,
        archive_path: Optional[str] = None
    ) -> TransferResult:
        """Transfer to Google Cloud Storage"""
        if 'gcs' not in self.cloud_clients:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message="GCS client not initialized"
            )
        
        try:
            gcs_client = self.cloud_clients['gcs']
            bucket_name = destination.destination_path.split('/')[0]
            prefix = '/'.join(destination.destination_path.split('/')[1:]) if '/' in destination.destination_path else ''
            
            bucket = gcs_client.bucket(bucket_name)
            transferred_files = []
            destination_urls = []
            
            # Transfer archive if available
            if archive_path and Path(archive_path).exists():
                blob_name = f"{prefix}/{Path(archive_path).name}" if prefix else Path(archive_path).name
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(archive_path)
                transferred_files.append(blob_name)
                destination_urls.append(f"gs://{bucket_name}/{blob_name}")
            else:
                # Transfer individual files
                for file_path in package.files or []:
                    if Path(file_path).exists():
                        blob_name = f"{prefix}/{Path(file_path).name}" if prefix else Path(file_path).name
                        blob = bucket.blob(blob_name)
                        blob.upload_from_filename(file_path)
                        transferred_files.append(blob_name)
                        destination_urls.append(f"gs://{bucket_name}/{blob_name}")
            
            return TransferResult(
                destination=destination,
                success=True,
                transferred_files=transferred_files,
                destination_urls=destination_urls
            )
        
        except Exception as e:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message=str(e)
            )
    
    async def _transfer_to_dropbox(
        self,
        package: TransferPackage,
        destination: TransferDestination,
        archive_path: Optional[str] = None
    ) -> TransferResult:
        """Transfer to Dropbox"""
        if 'dropbox' not in self.cloud_clients:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message="Dropbox client not initialized"
            )
        
        try:
            dbx = self.cloud_clients['dropbox']
            base_path = destination.destination_path
            
            transferred_files = []
            destination_urls = []
            
            # Transfer archive if available
            if archive_path and Path(archive_path).exists():
                dropbox_path = f"{base_path}/{Path(archive_path).name}"
                with open(archive_path, 'rb') as f:
                    dbx.files_upload(f.read(), dropbox_path)
                transferred_files.append(dropbox_path)
                destination_urls.append(f"dropbox:{dropbox_path}")
            else:
                # Transfer individual files
                for file_path in package.files or []:
                    if Path(file_path).exists():
                        dropbox_path = f"{base_path}/{Path(file_path).name}"
                        with open(file_path, 'rb') as f:
                            dbx.files_upload(f.read(), dropbox_path)
                        transferred_files.append(dropbox_path)
                        destination_urls.append(f"dropbox:{dropbox_path}")
            
            return TransferResult(
                destination=destination,
                success=True,
                transferred_files=transferred_files,
                destination_urls=destination_urls
            )
        
        except Exception as e:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message=str(e)
            )
    
    async def _transfer_via_email(
        self,
        package: TransferPackage,
        destination: TransferDestination,
        archive_path: Optional[str] = None
    ) -> TransferResult:
        """Transfer via email"""
        if not HAS_NOTIFICATION_DEPS:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message="Email dependencies not available"
            )
        
        try:
            # Email configuration
            smtp_server = destination.credentials.get('smtp_server', 'smtp.gmail.com')
            smtp_port = destination.credentials.get('smtp_port', 587)
            email_user = destination.credentials.get('email_user')
            email_password = destination.credentials.get('email_password')
            recipient = destination.destination_path
            
            if not all([email_user, email_password, recipient]):
                raise ValueError("Missing email credentials")
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = email_user
            msg['To'] = recipient
            msg['Subject'] = f"Video Processing Results - {package.video_metadata.get('title', 'Unknown')}"
            
            # Email body
            body = f"""
Video Processing Results

Video: {package.video_metadata.get('title', 'Unknown')}
Processed at: {package.created_at}

Included components:
- Video Content: {'Yes' if package.video_content else 'No'}
- Notebook: {'Yes' if package.notebook else 'No'}
- Analysis: {'Yes' if package.analysis else 'No'}

Files attached: {len(package.files or [])}
            """
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach archive or individual files
            if archive_path and Path(archive_path).exists():
                self._attach_file_to_email(msg, archive_path)
            else:
                for file_path in (package.files or [])[:5]:  # Limit to 5 files
                    if Path(file_path).exists():
                        self._attach_file_to_email(msg, file_path)
            
            # Send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(email_user, email_password)
            text = msg.as_string()
            server.sendmail(email_user, recipient, text)
            server.quit()
            
            return TransferResult(
                destination=destination,
                success=True,
                transferred_files=[archive_path] if archive_path else package.files or [],
                destination_urls=[f"mailto:{recipient}"]
            )
        
        except Exception as e:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message=str(e)
            )
    
    def _attach_file_to_email(self, msg: MIMEMultipart, file_path: str):
        """Attach file to email message"""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {Path(file_path).name}',
            )
            
            msg.attach(part)
        except Exception as e:
            logger.warning(f"Failed to attach file {file_path}: {e}")
    
    async def _transfer_via_webhook(
        self,
        package: TransferPackage,
        destination: TransferDestination,
        archive_path: Optional[str] = None
    ) -> TransferResult:
        """Transfer via webhook"""
        if not HAS_NOTIFICATION_DEPS:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message="Webhook dependencies not available"
            )
        
        try:
            webhook_url = destination.destination_path
            headers = destination.options.get('headers', {'Content-Type': 'application/json'})
            
            # Prepare payload
            payload = {
                'video_metadata': package.video_metadata,
                'created_at': package.created_at,
                'components': {
                    'video_content': package.video_content is not None,
                    'notebook': package.notebook is not None,
                    'analysis': package.analysis is not None
                },
                'files_count': len(package.files or [])
            }
            
            # Add summary data
            if package.notebook:
                payload['summary'] = {
                    'executive_summary': package.notebook.executive_summary,
                    'key_insights': package.notebook.key_insights[:3],  # First 3 insights
                    'questions_count': len(package.notebook.questions_raised),
                    'action_items_count': len(package.notebook.action_items)
                }
            
            if package.analysis:
                payload['analysis_summary'] = {
                    'primary_category': package.analysis.content_category.primary_category,
                    'target_audience': package.analysis.audience_analysis.target_age_group,
                    'complexity_scores': {
                        'visual': package.analysis.video_complexity.visual_complexity,
                        'content': package.analysis.video_complexity.content_complexity
                    }
                }
            
            # Send webhook
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            return TransferResult(
                destination=destination,
                success=True,
                transferred_files=[],
                destination_urls=[webhook_url],
                error_message=None
            )
        
        except Exception as e:
            return TransferResult(
                destination=destination,
                success=False,
                transferred_files=[],
                destination_urls=[],
                error_message=str(e)
            )
    
    def _generate_notebook_markdown(self, notebook: VideoNotebook) -> str:
        """Generate markdown content for notebook"""
        md = f"""# 📓 Video Notebook: {notebook.video_metadata.title}

## 📋 Executive Summary
{notebook.executive_summary}

## 🎯 Key Insights
"""
        
        for i, insight in enumerate(notebook.key_insights, 1):
            md += f"{i}. {insight}\n"
        
        md += f"""
## 🤔 Discussion Questions
"""
        
        for question in notebook.questions_raised:
            md += f"- {question}\n"
        
        md += f"""
## ✅ Action Items
"""
        
        for action in notebook.action_items:
            md += f"{action}\n"
        
        md += f"""
## 🗺️ Concept Map
"""
        
        for topic, concepts in notebook.concept_map.items():
            md += f"**{topic}**: {', '.join(concepts)}\n"
        
        md += f"""
---
*Generated on {notebook.processing_metadata['processed_at']}*
"""
        
        return md
    
    def _generate_analysis_report(self, analysis: VideoPrismAnalysis) -> str:
        """Generate analysis report in markdown"""
        md = f"""# 🎬 Video Analysis Report: {analysis.video_metadata.title}

## 📊 Content Categorization
- **Primary Category**: {analysis.content_category.primary_category}
- **Subcategories**: {', '.join(analysis.content_category.subcategories)}
- **Content Tags**: {', '.join(analysis.content_category.content_tags)}

## 🎯 Target Audience
- **Age Group**: {analysis.audience_analysis.target_age_group}
- **Education Level**: {analysis.audience_analysis.education_level}
- **Expertise Level**: {analysis.audience_analysis.expertise_level}
- **Accessibility Score**: {analysis.audience_analysis.accessibility_score:.2f}/1.0

## 📈 Complexity Analysis
- **Visual Complexity**: {analysis.video_complexity.visual_complexity:.2f}/1.0
- **Audio Complexity**: {analysis.video_complexity.audio_complexity:.2f}/1.0
- **Content Complexity**: {analysis.video_complexity.content_complexity:.2f}/1.0
- **Production Quality**: {analysis.video_complexity.production_quality:.2f}/1.0

## 🎨 Visual Analysis
Analyzed {len(analysis.visual_analysis)} frames from the video.

## ⭐ Key Moments ({len(analysis.key_moments)})
"""
        
        for moment in analysis.key_moments[:5]:  # Top 5 moments
            timestamp_str = f"{int(moment['timestamp']//60)}:{int(moment['timestamp']%60):02d}"
            md += f"- **[{timestamp_str}]** {moment['description']}\n"
        
        md += f"""
## 🏷️ Content Themes
{chr(10).join([f"- {theme}" for theme in analysis.content_themes])}

---
*Analysis completed on {analysis.analysis_metadata['analyzed_at']}*
"""
        
        return md
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            if self.temp_dir.exists():
                for item in self.temp_dir.iterdir():
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
            logger.info("Temporary files cleaned up")
        except Exception as e:
            logger.warning(f"Failed to clean up temp files: {e}")

# Convenience functions
async def transfer_video_processing_results(
    video_content: Optional[VideoContent] = None,
    notebook: Optional[VideoNotebook] = None,
    analysis: Optional[VideoPrismAnalysis] = None,
    destinations: List[TransferDestination] = None,
    config: Dict[str, Any] = None
) -> List[TransferResult]:
    """Convenience function to transfer video processing results"""
    
    if not destinations:
        # Default to local transfer
        destinations = [TransferDestination(
            destination_type="local",
            destination_path="./output"
        )]
    
    pipeline = VideoTransferPipeline(config)
    
    try:
        # Create package
        package = await pipeline.create_transfer_package(
            video_content=video_content,
            notebook=notebook,
            analysis=analysis
        )
        
        # Transfer to destinations
        results = await pipeline.transfer_package(package, destinations)
        
        return results
    
    finally:
        pipeline.cleanup_temp_files()

# Example usage
async def main():
    """Example usage of video transfer pipeline"""
    
    # Example destinations
    destinations = [
        TransferDestination(
            destination_type="local",
            destination_path="./output"
        ),
        # TransferDestination(
        #     destination_type="email",
        #     destination_path="user@example.com",
        #     credentials={
        #         'email_user': 'sender@gmail.com',
        #         'email_password': 'app_password',
        #         'smtp_server': 'smtp.gmail.com',
        #         'smtp_port': 587
        #     }
        # )
    ]
    
    # Example: Transfer mock results
    from video_extractor_enhanced import VideoMetadata
    
    mock_metadata = VideoMetadata(
        video_id="test123",
        title="Test Video",
        description="Test description",
        duration=300,
        upload_date="2024-01-01",
        uploader="Test Channel",
        view_count=1000,
        like_count=50,
        thumbnail_url="https://example.com/thumb.jpg"
    )
    
    # Create mock video content
    mock_video_content = VideoContent(
        metadata=mock_metadata,
        transcript=[],
        summary="This is a test video summary",
        key_points=["Point 1", "Point 2", "Point 3"],
        topics=["topic1", "topic2"]
    )
    
    # Transfer results
    results = await transfer_video_processing_results(
        video_content=mock_video_content,
        destinations=destinations
    )
    
    # Print results
    for result in results:
        if result.success:
            print(f"✓ Successfully transferred to {result.destination.destination_type}")
            print(f"  Files: {len(result.transferred_files)}")
            print(f"  Time: {result.transfer_time:.2f}s")
        else:
            print(f"❌ Failed to transfer to {result.destination.destination_type}")
            print(f"  Error: {result.error_message}")

if __name__ == "__main__":
    asyncio.run(main())