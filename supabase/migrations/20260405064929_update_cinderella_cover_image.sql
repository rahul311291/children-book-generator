/*
  # Update Cinderella cover image

  1. Modified Tables
    - `templates`
      - Updated cover_image for Cinderella template to a fairy-tale princess photo (Pexels #19845247)

  2. Important Notes
    - No data is deleted or dropped
    - Only the cover_image column is updated for one template
*/

UPDATE templates
SET cover_image = 'https://images.pexels.com/photos/19845247/pexels-photo-19845247.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE id = 'a4444444-4444-4444-4444-444444444444';