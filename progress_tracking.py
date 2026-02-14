"""
Progress tracking module for book generation
Handles saving/loading job state to enable resume functionality
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from supabase import Client

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Manages progress tracking for book generation jobs."""

    def __init__(self, supabase_client: Client):
        self.supabase = supabase_client

    def create_job(self, template_id: str, template_name: str, child_name: str,
                   child_age: int, child_gender: str, total_pages: int) -> Optional[str]:
        """Create a new book generation job and return job ID."""
        try:
            result = self.supabase.table("book_generation_jobs").insert({
                "template_id": template_id,
                "template_name": template_name,
                "child_name": child_name,
                "child_age": child_age,
                "child_gender": child_gender,
                "status": "in_progress",
                "total_pages": total_pages,
                "pages_completed": 0,
                "current_page": 0
            }).execute()

            if result.data:
                job_id = result.data[0]['id']
                logger.info(f"Created new job: {job_id}")
                return job_id
            return None
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            return None

    def create_page_records(self, job_id: str, pages: List[Dict]) -> bool:
        """Create page records for all pages in the book."""
        try:
            page_records = []
            for page in pages:
                page_records.append({
                    "job_id": job_id,
                    "page_number": page.get('page_number', 0),
                    "profession_title": page.get('profession_title', ''),
                    "text": page.get('text', ''),
                    "image_prompt": page.get('image_prompt', ''),
                    "status": "pending"
                })

            self.supabase.table("book_generation_pages").insert(page_records).execute()
            logger.info(f"Created {len(page_records)} page records for job {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating page records: {e}")
            return False

    def update_page_status(self, job_id: str, page_number: int, status: str,
                          image_url: Optional[str] = None, error_message: Optional[str] = None) -> bool:
        """Update the status of a specific page."""
        try:
            update_data = {
                "status": status,
                "generation_attempts": self._increment_attempts(job_id, page_number)
            }

            if image_url:
                update_data["image_url"] = image_url

            if error_message:
                update_data["error_message"] = error_message

            if status == "completed":
                update_data["completed_at"] = datetime.now().isoformat()

            self.supabase.table("book_generation_pages").update(update_data).eq(
                "job_id", job_id
            ).eq("page_number", page_number).execute()

            return True
        except Exception as e:
            logger.error(f"Error updating page status: {e}")
            return False

    def _increment_attempts(self, job_id: str, page_number: int) -> int:
        """Get current attempt count and increment it."""
        try:
            result = self.supabase.table("book_generation_pages").select(
                "generation_attempts"
            ).eq("job_id", job_id).eq("page_number", page_number).maybeSingle().execute()

            if result.data:
                return result.data.get('generation_attempts', 0) + 1
            return 1
        except Exception:
            return 1

    def update_job_progress(self, job_id: str, current_page: int,
                           pages_completed: int, status: str = "in_progress") -> bool:
        """Update job progress."""
        try:
            update_data = {
                "current_page": current_page,
                "pages_completed": pages_completed,
                "status": status
            }

            if status == "completed":
                update_data["completed_at"] = datetime.now().isoformat()

            self.supabase.table("book_generation_jobs").update(update_data).eq(
                "id", job_id
            ).execute()

            return True
        except Exception as e:
            logger.error(f"Error updating job progress: {e}")
            return False

    def mark_job_failed(self, job_id: str, error_message: str, error_page: Optional[int] = None) -> bool:
        """Mark a job as failed with error details."""
        try:
            update_data = {
                "status": "failed",
                "error_message": error_message
            }

            if error_page:
                update_data["error_page"] = error_page

            self.supabase.table("book_generation_jobs").update(update_data).eq(
                "id", job_id
            ).execute()

            logger.error(f"Job {job_id} marked as failed: {error_message}")
            return True
        except Exception as e:
            logger.error(f"Error marking job as failed: {e}")
            return False

    def get_job(self, job_id: str) -> Optional[Dict]:
        """Get job details."""
        try:
            result = self.supabase.table("book_generation_jobs").select("*").eq(
                "id", job_id
            ).maybeSingle().execute()

            return result.data
        except Exception as e:
            logger.error(f"Error fetching job: {e}")
            return None

    def get_job_pages(self, job_id: str) -> List[Dict]:
        """Get all pages for a job, ordered by page number."""
        try:
            result = self.supabase.table("book_generation_pages").select("*").eq(
                "job_id", job_id
            ).order("page_number").execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching job pages: {e}")
            return []

    def get_incomplete_pages(self, job_id: str) -> List[Dict]:
        """Get pages that haven't been completed yet."""
        try:
            result = self.supabase.table("book_generation_pages").select("*").eq(
                "job_id", job_id
            ).neq("status", "completed").order("page_number").execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching incomplete pages: {e}")
            return []

    def get_all_jobs(self, limit: int = 50) -> List[Dict]:
        """Get all jobs, most recent first."""
        try:
            result = self.supabase.table("book_generation_jobs").select("*").order(
                "created_at", desc=True
            ).limit(limit).execute()

            return result.data or []
        except Exception as e:
            logger.error(f"Error fetching jobs: {e}")
            return []

    def get_job_summary(self, job_id: str) -> Optional[Dict]:
        """Get comprehensive job summary with page details."""
        try:
            job = self.get_job(job_id)
            if not job:
                return None

            pages = self.get_job_pages(job_id)

            completed_pages = [p for p in pages if p['status'] == 'completed']
            failed_pages = [p for p in pages if p['status'] == 'failed']
            pending_pages = [p for p in pages if p['status'] == 'pending']

            return {
                "job": job,
                "pages": pages,
                "stats": {
                    "total": len(pages),
                    "completed": len(completed_pages),
                    "failed": len(failed_pages),
                    "pending": len(pending_pages)
                }
            }
        except Exception as e:
            logger.error(f"Error fetching job summary: {e}")
            return None

    def delete_job(self, job_id: str) -> bool:
        """Delete a job and all its pages (cascade delete)."""
        try:
            self.supabase.table("book_generation_jobs").delete().eq("id", job_id).execute()
            logger.info(f"Deleted job: {job_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting job: {e}")
            return False
