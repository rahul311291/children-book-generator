# Job Tracking and Resume System

The Children's Book Generator now includes automatic progress tracking and resume functionality for template book generation. This ensures you never lose progress if something goes wrong during book creation.

## Features

### Automatic Progress Saving
- Every generated image is saved automatically to the database
- Progress is tracked page-by-page in real-time
- Each job gets a unique ID for easy reference
- All personalized text and image prompts are preserved

### Job History View
- Access via the "Job History" option in the Book Mode selector
- See all your previous book generation attempts
- Filter by status: In Progress, Completed, or Failed
- View detailed progress for each job

### Resume Capability
- Resume any incomplete or failed job from where it left off
- Already-generated images are loaded instantly
- Only missing pages are regenerated
- Saves time and API costs

### Error Tracking
- Detailed error messages for failed generations
- See exactly which page failed and why
- Track generation attempts per page
- Easy debugging with page-level error details

## How It Works

### During Generation
1. A job record is created when you start generating a template book
2. Page records are created for all pages in the template
3. As each page is generated:
   - Image is saved to the database (base64 encoded)
   - Page status is updated to "completed"
   - Job progress counter is incremented
4. If an error occurs:
   - Error message is saved with the specific page
   - Job is marked as "failed" with error details
   - All successfully generated pages are preserved

### Viewing History
1. Switch to "Job History" mode in the sidebar
2. Browse all your generation jobs
3. Click "View Details" to see page-by-page progress
4. See completion percentage and error details

### Resuming a Job
1. Find the incomplete or failed job in Job History
2. Click the "Resume" button
3. The system will:
   - Load all previously generated pages
   - Identify which pages need to be generated
   - Continue from where it left off
4. You'll see a mix of "Loading saved page" and "Generating page" messages

### Loading Completed Books
1. Find a completed job in Job History
2. Click "Load Book" to view it in the preview
3. You can then download the PDF or regenerate specific pages

## Database Schema

### book_generation_jobs
Stores overall job information:
- Job ID, template details, child information
- Status (in_progress, completed, failed)
- Progress counters (total pages, completed pages, current page)
- Error information
- Timestamps

### book_generation_pages
Stores individual page data:
- Page number and profession title
- Personalized text and image prompt
- Generated image (base64)
- Page status and error messages
- Generation attempt count

## Benefits

### Never Lose Work
- If generation fails midway, all completed pages are saved
- Network issues, API rate limits, or crashes won't erase your progress

### Save Time
- Resume exactly where you left off
- Don't regenerate pages that already succeeded

### Save Money
- Avoid re-running successful API calls
- Only pay for images that actually need to be generated

### Easy Debugging
- See exactly what went wrong
- Track which pages consistently fail
- Monitor generation attempts per page

### Historical Reference
- Keep a record of all your created books
- Quickly recreate or modify previous books
- Compare different versions

## Usage Tips

1. **Check Job ID**: When generating a book, note the Job ID displayed. You can reference it later in Job History.

2. **Review Errors**: If a job fails, check the error details before resuming to understand what went wrong.

3. **Delete Old Jobs**: Clean up completed or unwanted jobs using the Delete button to keep your history manageable.

4. **Resume Promptly**: If a job fails due to rate limits, wait a few minutes then resume rather than starting fresh.

5. **Load Completed Books**: Use the "Load Book" button to quickly access previously generated books without regenerating.

## Technical Details

### Storage
- All data is stored in Supabase PostgreSQL database
- Images are stored as base64-encoded strings
- Row Level Security (RLS) is enabled for data protection

### Error Handling
- Page-level error tracking
- Job-level error tracking with failed page reference
- Automatic retry counting per page

### Performance
- Completed pages load instantly (no API calls)
- Only incomplete pages trigger new image generation
- Efficient database queries with indexes

## Troubleshooting

**Q: My job shows "failed" but some pages generated successfully. What happened?**
A: The job failed partway through, but all completed pages are saved. Use the Resume button to continue from where it failed.

**Q: Can I resume a job from a different session?**
A: Yes! Jobs are saved in the database and persist across sessions. Just find it in Job History and click Resume.

**Q: What happens if I resume a completed job?**
A: The system will load all pages instantly without regenerating anything. Use this to quickly reload a book.

**Q: How long are jobs kept in history?**
A: Jobs are kept indefinitely unless you manually delete them. Use the Delete button to clean up old jobs.

**Q: Can I edit a resumed job?**
A: Currently, you can only resume with the same parameters. To make changes, start a new book generation.
