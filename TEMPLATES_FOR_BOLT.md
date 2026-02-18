# Template Definitions for Bolt - All 5 Templates

This file contains the complete structure of all 5 templates that need to be seeded into Supabase.

## Template Structure

Each template has:
- `name`: Template name (string)
- `description`: Template description (string, can contain `{name}` placeholder)
- `total_pages`: Number of pages (integer)
- `pages`: Array of page objects, each with:
  - `page_number`: Page order (integer, 1-based)
  - `profession_title`: Page title/heading (string)
  - `text_template`: Story text with placeholders like `{name}`, `{he_she}`, `{his_her}`, etc. (string)
  - `image_prompt_template`: Image generation prompt with `{name}`, `{age}`, `{gender}` placeholders (string)

## All 5 Templates

### 1. "When I Grow Up" (24 pages)
- **Name**: `When I Grow Up`
- **Description**: `A 24-page personalized book featuring different professions {name} might pursue when they grow up - astronaut, doctor, teacher, and more!`
- **Total Pages**: 24
- **Pages**: Defined in `template_data.py` → `WHEN_I_GROW_UP_TEMPLATE` (imported and used)
- **Page Titles**: ASTRONAUT, DOCTOR, TEACHER, FIREFIGHTER, CHEF, PILOT, VETERINARIAN, ARTIST, SCIENTIST, MUSICIAN, ATHLETE, ENGINEER, DENTIST, FARMER, CONSTRUCTION WORKER, LIBRARIAN, PHOTOGRAPHER, ZOO KEEPER, DANCER, MAIL CARRIER, MARINE BIOLOGIST, PARK RANGER, BAKER, THE FUTURE

### 2. "Snow White and the Kind-Hearted Child" (10 pages)
- **Name**: `Snow White and the Kind-Hearted Child`
- **Description**: `A gentle Snow White retelling where {name} faces unkind sisters and a cruel stepmother, but finds courage, friends, and a kind prince.`
- **Total Pages**: 10
- **Page Titles**:
  1. Once Upon a Time
  2. A Heart of Kindness
  3. Into the Forest
  4. The Little Cottage
  5. New Friends
  6. The Poisoned Gift
  7. Asleep in Glass
  8. The Prince Arrives
  9. A New Beginning
  10. Happily Ever After

### 3. "Cricket Champion – Mastering Every Shot" (10 pages)
- **Name**: `Cricket Champion – Mastering Every Shot`
- **Description**: `A coaching-style book where {name} learns 10 classic cricket shots with clear posture and body-position tips.`
- **Total Pages**: 10
- **Page Titles**:
  1. Forward Defensive
  2. Straight Drive
  3. Cover Drive
  4. On Drive
  5. Pull Shot
  6. Cut Shot
  7. Sweep Shot
  8. Lofted Drive
  9. Back-Foot Defence
  10. Late Cut

### 4. "Cinderella and the Brave Heart" (10 pages)
- **Name**: `Cinderella and the Brave Heart`
- **Description**: `A Cinderella retelling where {name} overcomes unkindness from stepfamily and finds confidence, magic, and a caring prince.`
- **Total Pages**: 10
- **Page Titles**:
  1. Life in the Kitchen
  2. Dreams by the Fireplace
  3. Invitation to the Ball
  4. The Fairy Godmother
  5. Magic Transformation
  6. At the Ball
  7. Midnight Escape
  8. The Prince Searches
  9. The Perfect Fit
  10. A Strong New Life

### 5. "Sports Day Champion" (10 pages)
- **Name**: `Sports Day Champion`
- **Description**: `{name} discovers ten different sports on school sports day and imagines becoming a champion in each one.`
- **Total Pages**: 10
- **Page Titles**:
  1. Sprinting Star
  2. Football Hero
  3. Basketball Shooter
  4. Tennis Ace
  5. Swimming Dolphin
  6. Gymnast on the Beam
  7. Badminton Flyer
  8. Hockey Warrior
  9. Long Jump Flyer
  10. All-Round Champion

## Full Template Data Location

The complete template definitions with all text and image prompts are in:
- **File**: `template_book_generator.py`
- **Variable**: `DEFAULT_TEMPLATES` (starts around line 39)
- **Lines**: Approximately lines 39-580

## Database Schema Expected

### `templates` table:
- `id` (uuid, PRIMARY KEY, DEFAULT gen_random_uuid())
- `name` (text, NOT NULL)
- `description` (text)
- `total_pages` (integer)

### `template_pages` table:
- `id` (uuid, PRIMARY KEY, DEFAULT gen_random_uuid())
- `template_id` (uuid, NOT NULL, FOREIGN KEY → templates.id)
- `page_number` (integer, NOT NULL)
- `profession_title` (text)
- `text_template` (text)
- `image_prompt_template` (text)
- UNIQUE constraint on (template_id, page_number)

## For Bolt: What to Check

1. **Verify table schema** matches above structure
2. **Ensure `id` columns have `DEFAULT gen_random_uuid()`**
3. **Check RLS policies** allow INSERT and SELECT
4. **Verify all 5 templates** can be inserted with their pages

The Python code in `template_book_generator.py` will automatically seed these templates when the app runs, but it needs:
- Correct table schema (especially UUID defaults)
- RLS policies allowing inserts
- Proper foreign key relationships
