/*
  # Update Cinderella and Snow White templates to cartoon animated style

  1. Modified Tables
    - `templates`
      - Updated cover_image for Snow White template to fairy tale magic garden (Pexels #11890414)
      - Updated cover_image for Cinderella template to fairy tale castle (Pexels #17892641)
    - `template_pages`
      - Updated all image_prompt_template fields for Snow White (template a2222222) from watercolor style to cartoon animated cel-shaded style
      - Updated all image_prompt_template fields for Cinderella (template a4444444) from watercolor style to cartoon animated cel-shaded style

  2. Important Notes
    - No data is deleted or dropped
    - Only cover_image and image_prompt_template columns are updated
    - Both fairy tale templates now generate cartoon/animated style images matching classic animated storybook aesthetic
*/

-- Update Snow White cover image
UPDATE templates
SET cover_image = 'https://images.pexels.com/photos/11890414/pexels-photo-11890414.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE id = 'a2222222-2222-2222-2222-222222222222';

-- Update Cinderella cover image
UPDATE templates
SET cover_image = 'https://images.pexels.com/photos/17892641/pexels-photo-17892641.jpeg?auto=compress&cs=tinysrgb&w=800'
WHERE id = 'a4444444-4444-4444-4444-444444444444';

-- Update Snow White page 1 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} in simple patched clothes, carrying a heavy wicker basket through a grand stone castle kitchen. Two elaborately dressed sisters point and snicker while a stern stepmother watches from a throne-like chair. Warm candlelight, cobblestone floor, copper pots hanging on walls. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 1;

-- Update Snow White page 2 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} sitting on a stone castle windowsill, smiling softly while feeding colorful songbirds from {name}''s open palm. Morning sunlight streams through the arched window. Two sisters frown in the shadowy background. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 2;

-- Update Snow White page 3 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} walking along a winding path into a tall, ancient forest. Golden rays of sunlight filter through the canopy. A rabbit peeks from behind ferns, a bluebird perches on a branch overhead. The mood shifts from sadness to quiet hope. Rich greens, dappled light, bold outlines, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 3;

-- Update Snow White page 4 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a charming thatched-roof cottage nestled among tall forest trees with a mushroom-lined path leading to the door. Inside, a {age}-year-old {gender} child named {name} sweeps the wooden floor while sunlight pours through small round windows. Seven tiny chairs, seven tiny beds, cozy hearth. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 4;

-- Update Snow White page 5 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} sitting at a small round wooden table surrounded by seven cheerful cartoon dwarfs of different heights and personalities, all sharing a warm meal. Cozy candlelight, wooden beams overhead, a crackling fireplace. Everyone smiles kindly at {name}. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 5;

-- Update Snow White page 6 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a cloaked old woman with hidden eyes offers a single gleaming red apple to a {age}-year-old {gender} child named {name} at the cottage door. The apple glows ominously. Shadows creep at the edges while the cottage remains warm. Dramatic lighting, bold outlines, rich deep colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 6;

-- Update Snow White page 7 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a crystal glass coffin resting on a flower-covered hilltop under a canopy of blossoming trees. A {age}-year-old {gender} child named {name} lies peacefully inside with folded hands. Seven cartoon dwarfs weep nearby while forest animals -- deer, rabbits, birds -- gather in a circle. Tender, bittersweet mood, bold outlines, bright colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 7;

-- Update Snow White page 8 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a gentle young prince on a white horse arriving at the glass coffin on the hilltop. A {age}-year-old {gender} child named {name} begins to stir awake, eyes fluttering open. Cartoon dwarfs look up in astonished hope, golden sunlight breaking through clouds. Magical moment, bold outlines, bright hopeful colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 8;

-- Update Snow White page 9 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} standing between the kind prince and the seven cartoon dwarfs, holding a dwarf''s hand in farewell. A winding forest path leads to a sunlit white castle on a distant hill. Bold outlines, bright saturated colors, warm golden hour lighting, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 9;

-- Update Snow White page 10 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a grand castle courtyard celebration with banners and flowers. A {age}-year-old {gender} child named {name} in beautiful royal clothes stands at the center, surrounded by the prince, the seven cartoon dwarfs visiting, and new friends all smiling. Bright golden sunlight, joyful atmosphere, bold outlines, bright saturated colors, smooth shading, animated movie quality happily-ever-after ending, no text.'
WHERE template_id = 'a2222222-2222-2222-2222-222222222222' AND page_number = 10;

-- Update Cinderella page 1 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} in simple worn clothes, scrubbing a large wooden table in a grand old kitchen. Two overdressed stepsisters lounge on cushioned chairs pointing at {name}, while a stern stepmother supervises from the doorway. Warm but melancholy firelight, stone walls, hanging herbs. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 1;

-- Update Cinderella page 2 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} sitting curled up on a small stool beside a crackling fireplace, chin resting on knees, gazing into the dancing orange flames. Soft embers float upward like tiny stars. An old broom and bucket rest nearby. Warm amber glow, dreamy atmosphere, bold outlines, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 2;

-- Update Cinderella page 3 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a royal messenger in a plumed hat presenting a golden scroll at the door. Two excited stepsisters twirl in half-finished ball gowns. A {age}-year-old {gender} child named {name} stands in the background holding a simple apron, looking hopeful but sad. Stern stepmother blocks the way. Bold outlines, rich bright colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 3;

-- Update Cinderella page 4 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a glowing fairy godmother in a flowing silver gown, holding a sparkling wand, appearing in a moonlit garden before a {age}-year-old {gender} child named {name} who looks up in wonder. A pumpkin sits on the garden path, cartoon mice peek from behind flower pots. Magical blue and gold light radiates outward. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 4;

-- Update Cinderella page 5 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} spinning joyfully as rags transform into a magnificent glittering outfit with glass slippers that catch the moonlight. Behind {name}, a pumpkin morphs into a golden carriage, cartoon mice transform into elegant white horses. Sparkles and fairy dust fill the air. Bold outlines, bright saturated colors, smooth shading, animated movie quality, magical transformation scene, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 5;

-- Update Cinderella page 6 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a grand palace ballroom with crystal chandeliers, marble columns, and elegantly dressed cartoon guests. A {age}-year-old {gender} child named {name} in a magnificent outfit dances gracefully with a kind young prince at the center of the room. Golden candlelight reflects off the polished floor. Bold outlines, bright saturated colors, smooth shading, animated movie quality, enchanting atmosphere, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 6;

-- Update Cinderella page 7 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} running down wide marble palace stairs under a midnight sky full of stars. One sparkling glass slipper sits on a step behind. A large clock tower in the background shows midnight. Outfit beginning to shimmer and fade. Bold outlines, bright colors, smooth shading, animated movie quality, dramatic but child-friendly urgency, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 7;

-- Update Cinderella page 8 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a determined young cartoon prince traveling through a village in a horse-drawn carriage, holding up a single sparkling glass slipper on a velvet cushion. Cartoon villagers peer out from doorways and windows. Cobblestone streets, thatched-roof cottages, bright daytime scene. Bold outlines, bright saturated colors, smooth shading, animated movie quality, hopeful atmosphere, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 8;

-- Update Cinderella page 9 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: inside a modest room, the cartoon prince kneels to place the glass slipper on a {age}-year-old {gender} child named {name}''s foot. The slipper glows as it fits perfectly. Two cartoon stepsisters and the stepmother look shocked and dismayed in the background. Bold outlines, warm hopeful golden light, bright saturated colors, smooth shading, animated movie quality, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 9;

-- Update Cinderella page 10 image prompt
UPDATE template_pages
SET image_prompt_template = 'Cartoon animated children''s storybook illustration in vibrant cel-shaded style: a beautiful palace garden with fountains, rose bushes, and butterflies. A {age}-year-old {gender} child named {name} in elegant royal attire walks happily with the cartoon prince and new friends through the garden. Bright blue sky, warm sunshine, flowers in full bloom. Bold outlines, bright saturated colors, smooth shading, animated movie quality, joyful fairy-tale ending, no text.'
WHERE template_id = 'a4444444-4444-4444-4444-444444444444' AND page_number = 10;