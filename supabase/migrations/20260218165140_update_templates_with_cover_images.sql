/*
  # Update Templates with Cover Images
  
  ## Changes
    - Update existing templates with cover image URLs
  
  ## Details
    - Sets cover images for all 5 default templates
    - Uses Pexels stock photos
*/

-- Update When I Grow Up template
UPDATE templates
SET cover_image = 'https://images.pexels.com/photos/8613089/pexels-photo-8613089.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE name = 'When I Grow Up'
AND (cover_image IS NULL OR cover_image = '');

-- Update Snow White template
UPDATE templates
SET cover_image = 'https://images.pexels.com/photos/5706019/pexels-photo-5706019.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE name = 'Snow White and the Kind-Hearted Child'
AND (cover_image IS NULL OR cover_image = '');

-- Update Cricket Champion template
UPDATE templates
SET cover_image = 'https://images.pexels.com/photos/8224459/pexels-photo-8224459.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE name = 'Cricket Champion – Mastering Every Shot'
AND (cover_image IS NULL OR cover_image = '');

-- Update Cinderella template
UPDATE templates
SET cover_image = 'https://images.pexels.com/photos/7148655/pexels-photo-7148655.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE name = 'Cinderella and the Brave Heart'
AND (cover_image IS NULL OR cover_image = '');

-- Update Sports Day template
UPDATE templates
SET cover_image = 'https://images.pexels.com/photos/9295860/pexels-photo-9295860.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE name = 'Sports Day Champion'
AND (cover_image IS NULL OR cover_image = '');
