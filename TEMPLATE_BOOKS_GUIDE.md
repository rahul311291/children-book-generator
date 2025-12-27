# Template Books Feature Guide

## Overview

The Template Books feature allows you to create personalized books using pre-designed templates. The first template available is **"When {name} Grows Up"**, which features 24 pages showcasing different professions your child might pursue.

## How It Works

### 1. Select Book Mode

When you open the app, you'll see two options:
- **Custom Story**: Create a completely custom story (original feature)
- **Template Book**: Use a pre-designed template (new feature)

### 2. Choose a Template

Currently available template:
- **When {name} Grows Up**: A 24-page book featuring inspiring professions

### 3. Personalize Your Book

Fill in the required information:
- **Child's Name**: Will appear throughout the book
- **Gender**: Boy, Girl, or Non-binary (affects pronouns in the story)
- **Age**: Child's age (2-16 years)
- **3 Photos**: Upload 3 clear photos of the child's face

### 4. Preview and Generate

- Click "Generate My Personalized Book"
- Review the 24 profession pages with personalized text
- Each page features a different profession with rhyming text
- Navigate through pages using the page selector

### 5. Generate Images (Coming Soon)

Once satisfied with the text, you can generate AI images showing the child in each profession.

## The 24 Professions

Your child's personalized book will feature these inspiring careers:

1. **ASTRONAUT** - Exploring space among the stars
2. **DOCTOR** - Helping people feel better
3. **TEACHER** - Sharing knowledge and wisdom
4. **FIREFIGHTER** - Brave hero saving lives
5. **CHEF** - Creating delicious meals
6. **PILOT** - Flying high in the sky
7. **VETERINARIAN** - Caring for animals
8. **ARMY OFFICER** - Leading with honor
9. **WILDLIFE CONSERVATIONIST** - Protecting nature
10. **MARTIAL ARTIST** - Mastering discipline
11. **DETECTIVE** - Solving mysteries
12. **MAGICIAN** - Creating wonder and magic
13. **ARTIST** - Painting and creating
14. **MUSICIAN** - Making beautiful music
15. **SCIENTIST** - Discovering new things
16. **ENGINEER** - Building and designing
17. **ATHLETE** - Competing and winning
18. **MARINE BIOLOGIST** - Exploring the ocean
19. **FASHION DESIGNER** - Creating stylish clothes
20. **ARCHITECT** - Designing buildings
21. **PHOTOGRAPHER** - Capturing moments
22. **BUSINESS LEADER** - Leading companies
23. **WRITER** - Creating stories
24. **DREAMER** - The final inspirational page

## Example Text

Here's how the personalization works (for a child named Emma):

**Original Template:**
```
When {name} grows up,
{he_she} just might be,
an astronaut floating free.
```

**Personalized Result:**
```
When Emma grows up,
she just might be,
an astronaut floating free.
```

## Database Structure

The template system uses three main tables:

1. **templates**: Stores template definitions
2. **template_pages**: Stores the 24 profession pages with text and image prompts
3. **user_template_books**: Stores generated books for users

## Technical Details

- Templates are stored in Supabase database
- Text personalization uses pronoun replacement system
- Image generation uses AI prompts customized for each profession
- Photos will be used to create consistent character appearance

## Future Enhancements

- More template options (birthday books, learning books, etc.)
- Custom template editor
- Ability to reorder or skip professions
- Enhanced image generation with photo-based AI models
- PDF export with template books

## Files Added

- `template_data.py`: Contains the 24-profession template data
- `template_book_generator.py`: Handles template book UI and generation
- `seed_template_data.py`: Script to populate database with template

## How to Add More Templates

1. Create template data in `template_data.py`
2. Run the seed script to add to database
3. The template will automatically appear in the app

## Support

For issues or questions about template books, check the application logs or reach out to support.
