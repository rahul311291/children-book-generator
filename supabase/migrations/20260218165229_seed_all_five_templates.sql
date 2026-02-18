/*
  # Seed All Five Default Templates
  
  ## New Templates
    1. When I Grow Up (24 pages) - Career exploration
    2. Snow White and the Kind-Hearted Child (10 pages) - Fairy tale
    3. Cricket Champion (10 pages) - Sports coaching
    4. Cinderella and the Brave Heart (10 pages) - Fairy tale
    5. Sports Day Champion (10 pages) - Sports variety
  
  ## Details
    - Each template includes name, description, total_pages, and cover_image
    - Template pages are seeded separately via the application
*/

-- Insert template 1: When I Grow Up
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a1111111-1111-1111-1111-111111111111',
  'When I Grow Up',
  'A 24-page personalized book featuring different professions {name} might pursue when they grow up - astronaut, doctor, teacher, and more!',
  24,
  'https://images.pexels.com/photos/8613089/pexels-photo-8613089.jpeg?auto=compress&cs=tinysrgb&w=800'
) ON CONFLICT (id) DO UPDATE SET
  description = EXCLUDED.description,
  total_pages = EXCLUDED.total_pages,
  cover_image = EXCLUDED.cover_image;

-- Insert template 2: Snow White
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a2222222-2222-2222-2222-222222222222',
  'Snow White and the Kind-Hearted Child',
  'A gentle Snow White retelling where {name} faces unkind sisters and a cruel stepmother, but finds courage, friends, and a kind prince.',
  10,
  'https://images.pexels.com/photos/5706019/pexels-photo-5706019.jpeg?auto=compress&cs=tinysrgb&w=800'
) ON CONFLICT (id) DO UPDATE SET
  description = EXCLUDED.description,
  total_pages = EXCLUDED.total_pages,
  cover_image = EXCLUDED.cover_image;

-- Insert template 3: Cricket Champion
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a3333333-3333-3333-3333-333333333333',
  'Cricket Champion – Mastering Every Shot',
  'A coaching-style book where {name} learns 10 classic cricket shots with clear posture and body-position tips.',
  10,
  'https://images.pexels.com/photos/8224459/pexels-photo-8224459.jpeg?auto=compress&cs=tinysrgb&w=800'
) ON CONFLICT (id) DO UPDATE SET
  description = EXCLUDED.description,
  total_pages = EXCLUDED.total_pages,
  cover_image = EXCLUDED.cover_image;

-- Insert template 4: Cinderella
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a4444444-4444-4444-4444-444444444444',
  'Cinderella and the Brave Heart',
  'A Cinderella retelling where {name} overcomes unkindness from stepfamily and finds confidence, magic, and a caring prince.',
  10,
  'https://images.pexels.com/photos/7148655/pexels-photo-7148655.jpeg?auto=compress&cs=tinysrgb&w=800'
) ON CONFLICT (id) DO UPDATE SET
  description = EXCLUDED.description,
  total_pages = EXCLUDED.total_pages,
  cover_image = EXCLUDED.cover_image;

-- Insert template 5: Sports Day Champion
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a5555555-5555-5555-5555-555555555555',
  'Sports Day Champion',
  '{name} discovers ten different sports on school sports day and imagines becoming a champion in each one.',
  10,
  'https://images.pexels.com/photos/9295860/pexels-photo-9295860.jpeg?auto=compress&cs=tinysrgb&w=800'
) ON CONFLICT (id) DO UPDATE SET
  description = EXCLUDED.description,
  total_pages = EXCLUDED.total_pages,
  cover_image = EXCLUDED.cover_image;
