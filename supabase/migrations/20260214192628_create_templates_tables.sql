/*
  # Create Templates Tables and Populate Data

  ## New Tables
  
  ### `templates`
  - `id` (text, primary key) - Unique identifier for the template
  - `name` (text) - Display name of the template (e.g., "When {name} Grows Up")
  - `description` (text) - Description of what the template is about
  - `total_pages` (integer) - Number of pages in this template
  - `created_at` (timestamptz) - When the template was created
  - `updated_at` (timestamptz) - When the template was last updated

  ### `template_pages`
  - `id` (uuid, primary key) - Unique identifier for the page
  - `template_id` (text, foreign key) - References templates table
  - `page_number` (integer) - Page number in the book (1-based)
  - `profession_title` (text) - Title of the profession on this page
  - `text_template` (text) - Template text with placeholders like {name}, {he_she}
  - `image_prompt_template` (text) - Image generation prompt with placeholders
  - `created_at` (timestamptz) - When the page was created

  ## Security
  - Enable RLS on both tables
  - Allow public read access (templates are public content)

  ## Initial Data
  - Populates the "When {name} Grows Up" template with 24 profession pages
*/

-- Create templates table
CREATE TABLE IF NOT EXISTS templates (
  id text PRIMARY KEY,
  name text NOT NULL,
  description text NOT NULL,
  total_pages integer NOT NULL DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

-- Create template_pages table
CREATE TABLE IF NOT EXISTS template_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_id text NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
  page_number integer NOT NULL,
  profession_title text NOT NULL DEFAULT '',
  text_template text NOT NULL DEFAULT '',
  image_prompt_template text NOT NULL DEFAULT '',
  created_at timestamptz DEFAULT now(),
  UNIQUE(template_id, page_number)
);

-- Enable RLS
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE template_pages ENABLE ROW LEVEL SECURITY;

-- Allow public read access to templates (they are public content)
CREATE POLICY "Anyone can read templates"
  ON templates
  FOR SELECT
  TO anon, authenticated
  USING (true);

CREATE POLICY "Anyone can read template pages"
  ON template_pages
  FOR SELECT
  TO anon, authenticated
  USING (true);

-- Insert the "When I Grow Up" template
INSERT INTO templates (id, name, description, total_pages)
VALUES (
  'when_i_grow_up',
  'When {name} Grows Up',
  'A 24-page personalized book featuring different professions the child might pursue when they grow up',
  24
)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  total_pages = EXCLUDED.total_pages,
  updated_at = now();

-- Insert all 24 pages for the template
INSERT INTO template_pages (template_id, page_number, profession_title, text_template, image_prompt_template)
VALUES 
  ('when_i_grow_up', 1, 'ASTRONAUT', 
   E'When {name} grows up,\n{he_she} just might be,\nan astronaut floating free.\nAmong the stars and planets bright,\nexploring space both day and night!',
   'Watercolor illustration of a {age} year old {gender} child named {name} dressed as an astronaut in a white spacesuit with helmet, floating in space surrounded by colorful planets, stars, and galaxies, dreamy cosmic background, children''s book art style, inspiring and adventurous mood'),
  
  ('when_i_grow_up', 2, 'DOCTOR',
   E'Perhaps {name} will wear a white coat,\nwith a stethoscope around {his_her} throat.\nHelping people feel better each day,\nmaking all the sickness go away!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a white doctor''s coat and stethoscope, standing in a cheerful hospital room, holding a medical chart, warm and caring expression, children''s book art style, soft colors, compassionate and professional mood'),
  
  ('when_i_grow_up', 3, 'TEACHER',
   E'Maybe {name} will teach and guide,\nwith wisdom, patience, and pride.\nSharing knowledge every day,\nhelping students find their way!',
   'Watercolor illustration of a {age} year old {gender} child named {name} as a teacher standing in front of a colorful classroom with a chalkboard, books, and happy students, holding a book or pointer, kind and enthusiastic expression, children''s book art style, bright educational setting'),
  
  ('when_i_grow_up', 4, 'FIREFIGHTER',
   E'When {name} grows up brave and strong,\n{he_she} might fight fires all day long.\nWith a helmet and a hose so bright,\nsaving people day and night!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing firefighter gear with helmet and protective coat, holding a fire hose, standing in front of a fire truck, brave and heroic expression, children''s book art style, action-packed scene with warm colors'),
  
  ('when_i_grow_up', 5, 'CHEF',
   E'Perhaps {name} will cook and bake,\ndelicious meals and birthday cake.\nWith a chef''s hat upon {his_her} head,\nmaking food that''s perfectly spread!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a white chef''s hat and apron in a professional kitchen, surrounded by fresh ingredients, pots, and pans, mixing or cooking something delicious, joyful expression, children''s book art style, warm kitchen atmosphere'),
  
  ('when_i_grow_up', 6, 'PILOT',
   E'Maybe {name} will soar and fly,\nhigh above in the bright blue sky.\nPiloting planes from here to there,\ntraveling everywhere with care!',
   'Watercolor illustration of a {age} year old {gender} child named {name} in a pilot''s uniform with cap and wings badge, sitting in an airplane cockpit with controls and dials, confident smile, view of clouds through windows, children''s book art style, adventurous aviation scene'),
  
  ('when_i_grow_up', 7, 'VETERINARIAN',
   E'When {name} grows up with gentle care,\n{he_she} might help animals everywhere.\nA vet who heals with loving touch,\nmaking sure they don''t hurt much!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a veterinarian coat, gently examining a cute puppy or kitten in a veterinary clinic, surrounded by animal toys and medical tools, caring and gentle expression, children''s book art style, soft warm colors'),
  
  ('when_i_grow_up', 8, 'ARTIST',
   E'Perhaps {name} will paint and draw,\ncreating art that fills with awe.\nWith brushes, colors, and a creative mind,\nmaking beauty of every kind!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a paint-splattered apron, standing at an easel with paintbrushes and palette, surrounded by colorful artwork and paint supplies, focused and creative expression, children''s book art style, vibrant artistic studio'),
  
  ('when_i_grow_up', 9, 'SCIENTIST',
   E'Maybe {name} will discover and explore,\nfinding answers and learning more.\nWith a lab coat and test tubes in hand,\nmaking breakthroughs across the land!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a white lab coat and safety goggles, standing in a science laboratory with beakers, test tubes, microscope, and colorful chemical reactions, excited and curious expression, children''s book art style, bright educational science setting'),
  
  ('when_i_grow_up', 10, 'MUSICIAN',
   E'When {name} grows up making sweet sound,\n{he_she} might play music all around.\nWith an instrument and a melody true,\nbringing joy to me and you!',
   'Watercolor illustration of a {age} year old {gender} child named {name} playing a musical instrument (guitar, piano, or violin), standing on a stage with musical notes floating around, spotlight shining, joyful and passionate expression, children''s book art style, warm concert atmosphere'),
  
  ('when_i_grow_up', 11, 'ATHLETE',
   E'Perhaps {name} will run and play,\nbecoming an athlete one day.\nWith sports and games and championship pride,\ninspiring others far and wide!',
   'Watercolor illustration of a {age} year old {gender} child named {name} in athletic sportswear, playing a sport (soccer, basketball, or running), in a stadium or field setting, determined and energetic expression, children''s book art style, dynamic action pose with bright sports equipment'),
  
  ('when_i_grow_up', 12, 'ENGINEER',
   E'Maybe {name} will build and design,\ncreating structures that will shine.\nWith blueprints, tools, and clever plans,\nbuilding bridges across the lands!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a hard hat and safety vest, holding blueprints, standing near building blocks or construction models, thoughtful and innovative expression, children''s book art style, construction site with cranes and buildings in background'),
  
  ('when_i_grow_up', 13, 'DENTIST',
   E'When {name} grows up caring for smiles,\n{he_she} might clean teeth all the while.\nA dentist who makes everything right,\nkeeping every tooth healthy and bright!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing dentist scrubs and mask around neck, holding dental tools, standing in a bright dental office with dental chair and tooth models, friendly and reassuring expression, children''s book art style, clean medical environment'),
  
  ('when_i_grow_up', 14, 'FARMER',
   E'Perhaps {name} will grow and tend,\nfields of crops from end to end.\nA farmer with a barn and land,\ngrowing food with gentle hands!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing overalls and straw hat, standing in a farm field with crops, barn and animals in background, holding farming tools or vegetables, content and hardworking expression, children''s book art style, sunny rural farm scene'),
  
  ('when_i_grow_up', 15, 'CONSTRUCTION WORKER',
   E'Maybe {name} will hammer and nail,\nbuilding structures without fail.\nWith tools and teamwork every day,\nmaking buildings that are here to stay!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a hard hat, safety vest, and work boots, holding a hammer or tools, standing at a construction site with building materials and equipment, strong and capable expression, children''s book art style, active construction scene'),
  
  ('when_i_grow_up', 16, 'LIBRARIAN',
   E'When {name} grows up loving books,\n{he_she} might organize library nooks.\nHelping people find stories to read,\nsharing knowledge for every need!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing professional attire, standing in a cozy library surrounded by colorful bookshelves, holding books, warm and welcoming expression, children''s book art style, inviting library atmosphere with reading chairs'),
  
  ('when_i_grow_up', 17, 'PHOTOGRAPHER',
   E'Perhaps {name} will capture the light,\ntaking pictures day and night.\nWith a camera and artistic eye,\npreserving moments as they fly by!',
   'Watercolor illustration of a {age} year old {gender} child named {name} holding a professional camera with strap around neck, taking photos in a scenic location, focused and artistic expression, children''s book art style, outdoor scene with beautiful lighting'),
  
  ('when_i_grow_up', 18, 'ZOO KEEPER',
   E'Maybe {name} will care for creatures great,\nelephants, lions, and apes who wait.\nA zookeeper with animals to feed,\ngiving them everything they need!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing zoo keeper uniform with khaki clothes, feeding or caring for friendly zoo animals (elephant, giraffe, or monkey), standing in a zoo setting with enclosures, caring and gentle expression, children''s book art style, colorful animal habitat'),
  
  ('when_i_grow_up', 19, 'DANCER',
   E'When {name} grows up graceful and light,\n{he_she} might dance both day and night.\nOn stages big with movements true,\ninspiring audiences through and through!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a dance costume (ballet tutu or contemporary dance outfit), performing a graceful dance pose on a stage with curtains and lights, elegant and expressive, children''s book art style, theatrical performance setting'),
  
  ('when_i_grow_up', 20, 'MAIL CARRIER',
   E'Perhaps {name} will deliver mail,\nthrough sunshine, wind, and even hail.\nBringing letters, cards, and packages too,\nconnecting people just like glue!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a mail carrier uniform with postal hat and bag full of letters, delivering mail on a friendly neighborhood street with mailboxes, cheerful and reliable expression, children''s book art style, sunny suburban scene'),
  
  ('when_i_grow_up', 21, 'MARINE BIOLOGIST',
   E'Maybe {name} will study the sea,\nlearning about life swimming free.\nWith dolphins, whales, and fish so bright,\nprotecting oceans day and night!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing diving gear or wetsuit, observing ocean life underwater or on a research boat, surrounded by colorful fish, coral, and sea creatures, curious and adventurous expression, children''s book art style, vibrant underwater scene'),
  
  ('when_i_grow_up', 22, 'PARK RANGER',
   E'When {name} grows up protecting trees,\n{he_she} might guard forests with expertise.\nA ranger keeping nature safe and sound,\nhelping wildlife all around!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing park ranger uniform with hat and badge, standing in a beautiful forest with trees and wildlife, holding binoculars or field guide, protective and caring expression, children''s book art style, lush natural outdoor setting'),
  
  ('when_i_grow_up', 23, 'BAKER',
   E'Perhaps {name} will knead and bake,\nbread and cookies, pies and cake.\nWith flour, sugar, and ovens warm,\ncreating treats in every form!',
   'Watercolor illustration of a {age} year old {gender} child named {name} wearing a baker''s apron and hat, standing in a cozy bakery with display cases of fresh bread, pastries, and cakes, holding a tray of baked goods, happy and proud expression, children''s book art style, warm bakery with delicious treats'),
  
  ('when_i_grow_up', 24, 'THE FUTURE',
   E'Whatever {name} chooses to be,\nwe''ll support {him_her} completely.\nThe future''s bright, the world''s so wide,\nwe''ll be here, right by {his_her} side!',
   'Watercolor illustration of a {age} year old {gender} child named {name} standing confidently on a path that leads to a bright, hopeful horizon with multiple career symbols floating around (stethoscope, paintbrush, stars, books, etc.), optimistic and inspired expression, children''s book art style, dreamy sunrise background with endless possibilities')
ON CONFLICT (template_id, page_number) DO UPDATE SET
  profession_title = EXCLUDED.profession_title,
  text_template = EXCLUDED.text_template,
  image_prompt_template = EXCLUDED.image_prompt_template;
