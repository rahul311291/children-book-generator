"""
UI component for viewing job history and resuming failed/incomplete jobs
"""

import streamlit as st
import logging
from typing import Optional
from datetime import datetime
import base64
import io
from progress_tracking import ProgressTracker
from template_book_generator import init_supabase, create_template_book_pdf

logger = logging.getLogger(__name__)


def render_job_history():
    """Render the job history interface."""
    st.header("📚 Book Generation History")

    try:
        supabase = init_supabase()
        tracker = ProgressTracker(supabase)

        jobs = tracker.get_all_jobs(limit=50)

        if not jobs:
            st.info("No book generation history found. Generate your first book to see it here!")
            return

        st.markdown(f"**Found {len(jobs)} generation job(s)**")

        filter_status = st.selectbox(
            "Filter by status",
            ["All", "In Progress", "Completed", "Failed"],
            key="job_filter"
        )

        filtered_jobs = jobs
        if filter_status != "All":
            status_map = {
                "In Progress": "in_progress",
                "Completed": "completed",
                "Failed": "failed"
            }
            filtered_jobs = [j for j in jobs if j['status'] == status_map[filter_status]]

        st.markdown("---")

        for job in filtered_jobs:
            render_job_card(job, tracker)

    except Exception as e:
        logger.error(f"Error loading job history: {e}")
        st.error(f"Could not load job history: {e}")


def render_job_card(job: dict, tracker: ProgressTracker):
    """Render a single job card."""
    job_id = job['id']
    status = job['status']
    child_name = job['child_name']
    template_name = job['template_name']
    created_at = job['created_at']
    pages_completed = job['pages_completed']
    total_pages = job['total_pages']

    status_emoji = {
        'in_progress': '🔄',
        'completed': '✅',
        'failed': '❌',
        'paused': '⏸️'
    }

    status_color = {
        'in_progress': 'blue',
        'completed': 'green',
        'failed': 'red',
        'paused': 'orange'
    }

    with st.container():
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.markdown(f"### {status_emoji.get(status, '📖')} {template_name} - {child_name}")
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M')
            st.caption(f"Created: {created_date} | Job ID: `{job_id[:8]}...`")

        with col2:
            st.markdown(f"**Progress**")
            progress_pct = (pages_completed / total_pages * 100) if total_pages > 0 else 0
            st.progress(progress_pct / 100)
            st.caption(f"{pages_completed}/{total_pages} pages")

        with col3:
            st.markdown(f"**Status**")
            st.markdown(f":{status_color.get(status, 'gray')}[{status.upper().replace('_', ' ')}]")

        if status == 'failed' and job.get('error_message'):
            with st.expander("⚠️ Error Details"):
                st.error(f"**Error:** {job['error_message']}")
                if job.get('error_page'):
                    st.write(f"**Failed at page:** {job['error_page']}")

        col_actions1, col_actions2, col_actions3, col_actions4 = st.columns(4)

        with col_actions1:
            if st.button("📋 View Details", key=f"view_{job_id}", use_container_width=True):
                st.session_state.viewing_job_id = job_id

        with col_actions2:
            if status in ['in_progress', 'failed']:
                if st.button("▶️ Resume", key=f"resume_{job_id}", use_container_width=True):
                    resume_job(job_id, job)

        with col_actions3:
            if status == 'completed':
                if st.button("👁️ View & Download", key=f"view_book_{job_id}", use_container_width=True):
                    if st.session_state.get('viewing_full_book_id') == job_id:
                        st.session_state.viewing_full_book_id = None
                    else:
                        st.session_state.viewing_full_book_id = job_id

        with col_actions4:
            if st.button("🗑️ Delete", key=f"delete_{job_id}", use_container_width=True):
                if tracker.delete_job(job_id):
                    st.success("Job deleted!")
                    st.rerun()
                else:
                    st.error("Failed to delete job")

        if st.session_state.get('viewing_job_id') == job_id:
            render_job_details(job_id, tracker)

        if st.session_state.get('viewing_full_book_id') == job_id:
            render_full_book_preview(job_id, tracker, job)

        st.markdown("---")


def render_job_details(job_id: str, tracker: ProgressTracker):
    """Render detailed view of a job."""
    summary = tracker.get_job_summary(job_id)

    if not summary:
        st.error("Could not load job details")
        return

    with st.expander("📊 Detailed Progress", expanded=True):
        job = summary['job']
        pages = summary['pages']
        stats = summary['stats']

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Pages", stats['total'])
        with col2:
            st.metric("Completed", stats['completed'], delta=None)
        with col3:
            st.metric("Failed", stats['failed'], delta=None)
        with col4:
            st.metric("Pending", stats['pending'], delta=None)

        st.markdown("### Page-by-Page Status")

        for page in pages:
            page_num = page['page_number']
            status = page['status']
            profession = page['profession_title']

            status_icon = {
                'pending': '⏳',
                'generating': '🔄',
                'completed': '✅',
                'failed': '❌'
            }

            col_page1, col_page2, col_page3 = st.columns([1, 3, 1])

            with col_page1:
                st.write(f"**Page {page_num}**")

            with col_page2:
                st.write(f"{status_icon.get(status, '❓')} {profession}")

            with col_page3:
                st.write(f"`{status}`")

            if status == 'failed' and page.get('error_message'):
                st.caption(f"⚠️ Error: {page['error_message']}")

            if page.get('generation_attempts', 0) > 1:
                st.caption(f"🔄 Attempts: {page['generation_attempts']}")


def resume_job(job_id: str, job: dict):
    """Resume a job from where it left off."""
    st.session_state.resume_job_id = job_id
    st.session_state.template_book_data = {
        'template_id': job['template_id'],
        'template_name': job['template_name'],
        'child_name': job['child_name'],
        'gender': job['child_gender'],
        'age': job['child_age'],
        'photos': []
    }
    st.session_state.generate_template_book = True
    st.success(f"Resuming job {job_id[:8]}...")
    st.rerun()


def load_completed_book(job_id: str, tracker: ProgressTracker):
    """Load a completed book into the preview."""
    try:
        job = tracker.get_job(job_id)
        pages = tracker.get_job_pages(job_id)

        if not job or not pages:
            st.error("Could not load book")
            return

        generated_book = {
            'template_id': job['template_id'],
            'template_name': job['template_name'],
            'child_name': job['child_name'],
            'gender': job['child_gender'],
            'age': job['child_age'],
            'pages': [],
            'job_id': job_id
        }

        for page in pages:
            generated_book['pages'].append({
                'page_number': page['page_number'],
                'profession_title': page['profession_title'],
                'text': page['text'],
                'image_prompt': page['image_prompt'],
                'image_url': page.get('image_url'),
                'error': page.get('error_message')
            })

        st.session_state.template_generated_book = generated_book
        st.success("Book loaded! Switch to the Book Preview tab.")
        st.rerun()

    except Exception as e:
        logger.error(f"Error loading completed book: {e}")
        st.error(f"Failed to load book: {e}")


def render_full_book_preview(job_id: str, tracker: ProgressTracker, job: dict):
    """Render full book preview with download option directly in history."""
    try:
        pages = tracker.get_job_pages(job_id)

        if not pages:
            st.error("No pages found for this book")
            return

        with st.container():
            st.markdown("---")

            col_header1, col_header2 = st.columns([3, 1])
            with col_header1:
                st.markdown(f"### 📖 {job['template_name']} - {job['child_name']}")
            with col_header2:
                book_data = {
                    'template_id': job['template_id'],
                    'template_name': job['template_name'],
                    'child_name': job['child_name'],
                    'gender': job['child_gender'],
                    'age': job['child_age'],
                    'pages': []
                }

                for page in pages:
                    book_data['pages'].append({
                        'page_number': page['page_number'],
                        'profession_title': page['profession_title'],
                        'text': page['text'],
                        'image_prompt': page['image_prompt'],
                        'image_url': page.get('image_url'),
                        'error': page.get('error_message')
                    })

                if st.button("📥 Download PDF", key=f"download_pdf_{job_id}", type="primary", use_container_width=True):
                    with st.spinner("Creating PDF..."):
                        pdf_path = create_template_book_pdf(book_data)
                        if pdf_path:
                            with open(pdf_path, "rb") as pdf_file:
                                pdf_bytes = pdf_file.read()
                            st.download_button(
                                label="💾 Save PDF",
                                data=pdf_bytes,
                                file_name=f"{job['child_name']}_book_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                                key=f"save_pdf_{job_id}"
                            )
                            st.success("PDF ready!")

            st.markdown("---")

            completed_pages = [p for p in pages if p.get('image_url')]
            failed_pages = [p for p in pages if not p.get('image_url')]

            if failed_pages:
                st.warning(f"⚠️ {len(failed_pages)} pages have missing images")

            st.markdown(f"**Book Preview** ({len(completed_pages)}/{len(pages)} pages with images)")

            for page in pages:
                status_icon = "✅" if page.get('image_url') else "❌"

                with st.expander(f"{status_icon} Page {page['page_number']}: {page['profession_title']}", expanded=False):
                    col1, col2 = st.columns([1, 1])

                    with col1:
                        st.markdown("#### 🖼️ Image")
                        if page.get('image_url'):
                            try:
                                if page['image_url'].startswith('data:image'):
                                    image_data = page['image_url'].split(',')[1]
                                    image_bytes = base64.b64decode(image_data)
                                    st.image(image_bytes, use_container_width=True)
                                else:
                                    st.image(page['image_url'], use_container_width=True)
                            except Exception as e:
                                st.error(f"Failed to display image: {e}")
                        else:
                            st.warning("❌ Image not available")
                            if page.get('error_message'):
                                st.caption(f"Error: {page['error_message']}")

                    with col2:
                        st.markdown("#### 📝 Story Text")
                        st.markdown(f"*{page['text']}*")

            if st.button("🔄 Load to Editor", key=f"load_to_editor_{job_id}", use_container_width=True):
                load_completed_book(job_id, tracker)

    except Exception as e:
        logger.error(f"Error rendering full book preview: {e}")
        st.error(f"Could not load book preview: {e}")
