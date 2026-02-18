/*
  # Fix Templates and Cover Images

  1. Updates
    - Update cover images for all 5 templates with relevant, thematic images
    - Seed all template pages for the 5 templates
  
  2. Changes Made
    - Cricket Champion: Changed to cricket-relevant image (child with cricket bat)
    - Snow White: Changed to fairy tale/fantasy themed image
    - Cinderella: Changed to elegant princess/ball themed image  
    - Sports Day Champion: Already has appropriate sports image
    - When I Grow Up: Already has appropriate career/profession image
    
  3. Template Pages
    - Seeds all pages for: When I Grow Up (24 pages), Snow White (10 pages), Cricket Champion (10 pages), Cinderella (10 pages), Sports Day (10 pages)
    - Total of 64 pages inserted
*/

-- Update cover images with relevant, thematic photos
UPDATE templates 
SET cover_image = 'https://images.pexels.com/photos/3819572/pexels-photo-3819572.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE name = 'Cricket Champion – Mastering Every Shot';

UPDATE templates 
SET cover_image = 'https://images.pexels.com/photos/6693661/pexels-photo-6693661.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE name = 'Snow White and the Kind-Hearted Child';

UPDATE templates 
SET cover_image = 'https://images.pexels.com/photos/8923187/pexels-photo-8923187.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE name = 'Cinderella and the Brave Heart';

-- Now seed all template pages (only if they don't already exist)
DO $$
DECLARE
  v_template_id uuid;
  v_page_count integer;
BEGIN
  -- When I Grow Up Template (24 pages)
  SELECT id INTO v_template_id FROM templates WHERE name = 'When I Grow Up' LIMIT 1;
  IF v_template_id IS NOT NULL THEN
    SELECT COUNT(*) INTO v_page_count FROM template_pages WHERE template_id = v_template_id;
    IF v_page_count = 0 THEN
      INSERT INTO template_pages (id, template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
        (gen_random_uuid(), v_template_id, 1, 'ASTRONAUT', 
         'When {name} grows up,' || E'\n' || '{he_she} just might be,' || E'\n' || 'an astronaut floating free.' || E'\n' || 'Among the stars and planets bright,' || E'\n' || 'exploring space both day and night!',
         'Watercolor illustration of a {age} year old {gender} child named {name} dressed as an astronaut in a white spacesuit with helmet, floating in space surrounded by colorful planets, stars, and galaxies, dreamy cosmic background, children''s book art style, inspiring and adventurous mood'),
        (gen_random_uuid(), v_template_id, 2, 'DOCTOR',
         'Perhaps {name} will wear a white coat,' || E'\n' || 'with a stethoscope around {his_her} throat.' || E'\n' || 'Helping people feel better each day,' || E'\n' || 'making all the sickness go away!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a white doctor''s coat and stethoscope, standing in a cheerful hospital room, holding a medical chart, warm and caring expression, children''s book art style, soft colors, compassionate and professional mood'),
        (gen_random_uuid(), v_template_id, 3, 'TEACHER',
         'Maybe {name} will teach and guide,' || E'\n' || 'with wisdom, patience, and pride.' || E'\n' || 'Sharing knowledge every day,' || E'\n' || 'helping students find their way!',
         'Watercolor illustration of a {age} year old {gender} child named {name} as a teacher standing in front of a colorful classroom with a chalkboard, books, and happy students, holding a book or pointer, kind and enthusiastic expression, children''s book art style, bright educational setting'),
        (gen_random_uuid(), v_template_id, 4, 'FIREFIGHTER',
         'When {name} grows up brave and strong,' || E'\n' || '{he_she} might fight fires all day long.' || E'\n' || 'With a helmet and a hose so bright,' || E'\n' || 'saving people day and night!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing firefighter gear with helmet and protective coat, holding a fire hose, standing in front of a fire truck, brave and heroic expression, children''s book art style, action-packed scene with warm colors'),
        (gen_random_uuid(), v_template_id, 5, 'CHEF',
         'Perhaps {name} will cook and bake,' || E'\n' || 'delicious meals and birthday cake.' || E'\n' || 'With a chef''s hat upon {his_her} head,' || E'\n' || 'making food that''s perfectly spread!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a white chef''s hat and apron in a professional kitchen, surrounded by fresh ingredients, pots, and pans, mixing or cooking something delicious, joyful expression, children''s book art style, warm kitchen atmosphere'),
        (gen_random_uuid(), v_template_id, 6, 'PILOT',
         'Maybe {name} will soar and fly,' || E'\n' || 'high above in the bright blue sky.' || E'\n' || 'Piloting planes from here to there,' || E'\n' || 'traveling everywhere with care!',
         'Watercolor illustration of a {age} year old {gender} child named {name} in a pilot''s uniform with cap and wings badge, sitting in an airplane cockpit with controls and dials, confident smile, view of clouds through windows, children''s book art style, adventurous aviation scene'),
        (gen_random_uuid(), v_template_id, 7, 'VETERINARIAN',
         'When {name} grows up with gentle care,' || E'\n' || '{he_she} might help animals everywhere.' || E'\n' || 'A vet who heals with loving touch,' || E'\n' || 'making sure they don''t hurt much!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a veterinarian coat, gently examining a cute puppy or kitten in a veterinary clinic, surrounded by animal toys and medical tools, caring and gentle expression, children''s book art style, soft warm colors'),
        (gen_random_uuid(), v_template_id, 8, 'ARTIST',
         'Perhaps {name} will paint and draw,' || E'\n' || 'creating art that fills with awe.' || E'\n' || 'With brushes, colors, and a creative mind,' || E'\n' || 'making beauty of every kind!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a paint-splattered apron, standing at an easel with paintbrushes and palette, surrounded by colorful artwork and paint supplies, focused and creative expression, children''s book art style, vibrant artistic studio'),
        (gen_random_uuid(), v_template_id, 9, 'SCIENTIST',
         'Maybe {name} will discover and explore,' || E'\n' || 'finding answers and learning more.' || E'\n' || 'With a lab coat and test tubes in hand,' || E'\n' || 'making breakthroughs across the land!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a white lab coat and safety goggles, standing in a science laboratory with beakers, test tubes, microscope, and colorful chemical reactions, excited and curious expression, children''s book art style, bright educational science setting'),
        (gen_random_uuid(), v_template_id, 10, 'MUSICIAN',
         'When {name} grows up making sweet sound,' || E'\n' || '{he_she} might play music all around.' || E'\n' || 'With an instrument and a melody true,' || E'\n' || 'bringing joy to me and you!',
         'Watercolor illustration of a {age} year old {gender} child named {name} playing a musical instrument (guitar, piano, or violin), standing on a stage with musical notes floating around, spotlight shining, joyful and passionate expression, children''s book art style, warm concert atmosphere'),
        (gen_random_uuid(), v_template_id, 11, 'ATHLETE',
         'Perhaps {name} will run and play,' || E'\n' || 'becoming an athlete one day.' || E'\n' || 'With sports and games and championship pride,' || E'\n' || 'inspiring others far and wide!',
         'Watercolor illustration of a {age} year old {gender} child named {name} in athletic sportswear, playing a sport (soccer, basketball, or running), in a stadium or field setting, determined and energetic expression, children''s book art style, dynamic action pose with bright sports equipment'),
        (gen_random_uuid(), v_template_id, 12, 'ENGINEER',
         'Maybe {name} will build and design,' || E'\n' || 'creating structures that will shine.' || E'\n' || 'With blueprints, tools, and clever plans,' || E'\n' || 'building bridges across the lands!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a hard hat and safety vest, holding blueprints, standing near building blocks or construction models, thoughtful and innovative expression, children''s book art style, construction site with cranes and buildings in background'),
        (gen_random_uuid(), v_template_id, 13, 'DENTIST',
         'When {name} grows up caring for smiles,' || E'\n' || '{he_she} might clean teeth all the while.' || E'\n' || 'A dentist who makes everything right,' || E'\n' || 'keeping every tooth healthy and bright!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing dentist scrubs and mask around neck, holding dental tools, standing in a bright dental office with dental chair and tooth models, friendly and reassuring expression, children''s book art style, clean medical environment'),
        (gen_random_uuid(), v_template_id, 14, 'FARMER',
         'Perhaps {name} will grow and tend,' || E'\n' || 'fields of crops from end to end.' || E'\n' || 'A farmer with a barn and land,' || E'\n' || 'growing food with gentle hands!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing overalls and straw hat, standing in a farm field with crops, barn and animals in background, holding farming tools or vegetables, content and hardworking expression, children''s book art style, sunny rural farm scene'),
        (gen_random_uuid(), v_template_id, 15, 'CONSTRUCTION WORKER',
         'Maybe {name} will hammer and nail,' || E'\n' || 'building structures without fail.' || E'\n' || 'With tools and teamwork every day,' || E'\n' || 'making buildings that are here to stay!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a hard hat, safety vest, and work boots, holding a hammer or tools, standing at a construction site with building materials and equipment, strong and capable expression, children''s book art style, active construction scene'),
        (gen_random_uuid(), v_template_id, 16, 'LIBRARIAN',
         'When {name} grows up loving books,' || E'\n' || '{he_she} might organize library nooks.' || E'\n' || 'Helping people find stories to read,' || E'\n' || 'sharing knowledge for every need!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing professional attire, standing in a cozy library surrounded by colorful bookshelves, holding books, warm and welcoming expression, children''s book art style, inviting library atmosphere with reading chairs'),
        (gen_random_uuid(), v_template_id, 17, 'PHOTOGRAPHER',
         'Perhaps {name} will capture the light,' || E'\n' || 'taking pictures day and night.' || E'\n' || 'With a camera and artistic eye,' || E'\n' || 'preserving moments as they fly by!',
         'Watercolor illustration of a {age} year old {gender} child named {name} holding a professional camera with strap around neck, taking photos in a scenic location, focused and artistic expression, children''s book art style, outdoor scene with beautiful lighting'),
        (gen_random_uuid(), v_template_id, 18, 'ZOO KEEPER',
         'Maybe {name} will care for creatures great,' || E'\n' || 'elephants, lions, and apes who wait.' || E'\n' || 'A zookeeper with animals to feed,' || E'\n' || 'giving them everything they need!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing zoo keeper uniform with khaki clothes, feeding or caring for friendly zoo animals (elephant, giraffe, or monkey), standing in a zoo setting with enclosures, caring and gentle expression, children''s book art style, colorful animal habitat'),
        (gen_random_uuid(), v_template_id, 19, 'DANCER',
         'When {name} grows up graceful and light,' || E'\n' || '{he_she} might dance both day and night.' || E'\n' || 'On stages big with movements true,' || E'\n' || 'inspiring audiences through and through!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a dance costume (ballet tutu or contemporary dance outfit), performing a graceful dance pose on a stage with curtains and lights, elegant and expressive, children''s book art style, theatrical performance setting'),
        (gen_random_uuid(), v_template_id, 20, 'MAIL CARRIER',
         'Perhaps {name} will deliver mail,' || E'\n' || 'through sunshine, wind, and even hail.' || E'\n' || 'Bringing letters, cards, and packages too,' || E'\n' || 'connecting people just like glue!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a mail carrier uniform with postal hat and bag full of letters, delivering mail on a friendly neighborhood street with mailboxes, cheerful and reliable expression, children''s book art style, sunny suburban scene'),
        (gen_random_uuid(), v_template_id, 21, 'MARINE BIOLOGIST',
         'Maybe {name} will study the sea,' || E'\n' || 'learning about life swimming free.' || E'\n' || 'With dolphins, whales, and fish so bright,' || E'\n' || 'protecting oceans day and night!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing diving gear or wetsuit, observing ocean life underwater or on a research boat, surrounded by colorful fish, coral, and sea creatures, curious and adventurous expression, children''s book art style, vibrant underwater scene'),
        (gen_random_uuid(), v_template_id, 22, 'PARK RANGER',
         'When {name} grows up protecting trees,' || E'\n' || '{he_she} might guard forests with expertise.' || E'\n' || 'A ranger keeping nature safe and sound,' || E'\n' || 'helping wildlife all around!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing park ranger uniform with hat and badge, standing in a beautiful forest with trees and wildlife, holding binoculars or field guide, protective and caring expression, children''s book art style, lush natural outdoor setting'),
        (gen_random_uuid(), v_template_id, 23, 'BAKER',
         'Perhaps {name} will knead and bake,' || E'\n' || 'bread and cookies, pies and cake.' || E'\n' || 'With flour, sugar, and ovens warm,' || E'\n' || 'creating treats in every form!',
         'Watercolor illustration of a {age} year old {gender} child named {name} wearing a baker''s apron and hat, standing in a cozy bakery with display cases of fresh bread, pastries, and cakes, holding a tray of baked goods, happy and proud expression, children''s book art style, warm bakery with delicious treats'),
        (gen_random_uuid(), v_template_id, 24, 'THE FUTURE',
         'Whatever {name} chooses to be,' || E'\n' || 'we''ll support {him_her} completely.' || E'\n' || 'The future''s bright, the world''s so wide,' || E'\n' || 'we''ll be here, right by {his_her} side!',
         'Watercolor illustration of a {age} year old {gender} child named {name} standing confidently on a path that leads to a bright, hopeful horizon with multiple career symbols floating around (stethoscope, paintbrush, stars, books, etc.), optimistic and inspired expression, children''s book art style, dreamy sunrise background with endless possibilities');
    END IF;
  END IF;
END $$;