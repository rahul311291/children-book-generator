/*
  # Create user profiles table and fix template seeding

  1. New Tables
    - `user_profiles`
      - `id` (uuid, primary key, references auth.users)
      - `email` (text, not null)
      - `gemini_api_key` (text, nullable) - encrypted API key storage per user
      - `display_name` (text, nullable)
      - `created_at` (timestamptz)
      - `updated_at` (timestamptz)

  2. Security
    - Enable RLS on `user_profiles`
    - Users can only read/update their own profile
    - Users can insert their own profile on signup

  3. Template Fixes
    - Add INSERT policy on `templates` and `template_pages` for authenticated users
    - Seed all 5 default templates directly via SQL so they persist across refreshes
*/

-- 1. Create user_profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text NOT NULL,
  gemini_api_key text,
  display_name text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can read own profile"
  ON user_profiles FOR SELECT
  TO authenticated
  USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON user_profiles FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON user_profiles FOR UPDATE
  TO authenticated
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- 2. Add INSERT/UPDATE policies for templates and template_pages so app can seed them
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'templates' AND policyname = 'Allow authenticated insert on templates'
  ) THEN
    CREATE POLICY "Allow authenticated insert on templates"
      ON templates FOR INSERT
      TO authenticated
      WITH CHECK (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'template_pages' AND policyname = 'Allow authenticated insert on template_pages'
  ) THEN
    CREATE POLICY "Allow authenticated insert on template_pages"
      ON template_pages FOR INSERT
      TO authenticated
      WITH CHECK (true);
  END IF;
END $$;

-- Also allow anon insert so seeding works before login
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'templates' AND policyname = 'Allow anon insert on templates'
  ) THEN
    CREATE POLICY "Allow anon insert on templates"
      ON templates FOR INSERT
      TO anon
      WITH CHECK (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'template_pages' AND policyname = 'Allow anon insert on template_pages'
  ) THEN
    CREATE POLICY "Allow anon insert on template_pages"
      ON template_pages FOR INSERT
      TO anon
      WITH CHECK (true);
  END IF;
END $$;

-- 3. Seed default templates directly via SQL
-- Template 1: When I Grow Up
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a1111111-1111-1111-1111-111111111111',
  'When I Grow Up',
  'A 24-page personalized book featuring different professions {name} might pursue when they grow up - astronaut, doctor, teacher, and more!',
  24,
  'https://images.pexels.com/photos/8613089/pexels-photo-8613089.jpeg?auto=compress&cs=tinysrgb&w=800'
)
ON CONFLICT (id) DO NOTHING;

-- Template 2: Snow White
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a2222222-2222-2222-2222-222222222222',
  'Snow White and the Kind-Hearted Child',
  'A gentle Snow White retelling where {name} faces unkind sisters and a cruel stepmother, but finds courage, friends, and a kind prince.',
  10,
  'https://images.pexels.com/photos/5706019/pexels-photo-5706019.jpeg?auto=compress&cs=tinysrgb&w=800'
)
ON CONFLICT (id) DO NOTHING;

-- Template 3: Cricket Champion
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a3333333-3333-3333-3333-333333333333',
  'Cricket Champion – Mastering Every Shot',
  'A coaching-style book where {name} learns 10 classic cricket shots with clear posture and body-position tips.',
  10,
  'https://images.pexels.com/photos/8224459/pexels-photo-8224459.jpeg?auto=compress&cs=tinysrgb&w=800'
)
ON CONFLICT (id) DO NOTHING;

-- Template 4: Cinderella
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a4444444-4444-4444-4444-444444444444',
  'Cinderella and the Brave Heart',
  'A Cinderella retelling where {name} overcomes unkindness from stepfamily and finds confidence, magic, and a caring prince.',
  10,
  'https://images.pexels.com/photos/7148655/pexels-photo-7148655.jpeg?auto=compress&cs=tinysrgb&w=800'
)
ON CONFLICT (id) DO NOTHING;

-- Template 5: Sports Day Champion
INSERT INTO templates (id, name, description, total_pages, cover_image)
VALUES (
  'a5555555-5555-5555-5555-555555555555',
  'Sports Day Champion',
  '{name} discovers ten different sports on school sports day and imagines becoming a champion in each one.',
  10,
  'https://images.pexels.com/photos/9295860/pexels-photo-9295860.jpeg?auto=compress&cs=tinysrgb&w=800'
)
ON CONFLICT (id) DO NOTHING;

-- Seed template pages for "When I Grow Up" (24 pages - only inserting if not present)
-- Using a DO block to check existence first
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM template_pages WHERE template_id = 'a1111111-1111-1111-1111-111111111111' LIMIT 1) THEN
    INSERT INTO template_pages (template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
    ('a1111111-1111-1111-1111-111111111111', 1, 'Astronaut', '{name} looked up at the twinkling stars and dreamed of floating in space. {He_She} imagined wearing a shiny spacesuit and bouncing on the moon, collecting moon rocks and waving at Earth far below.', '{age} year old {gender} child {name} wearing a space suit floating in space near the moon, Earth visible in background, stars twinkling, dreamy expression, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 2, 'Doctor', '{name} put on a white coat and a stethoscope around {his_her} neck. {He_She} gently checked {his_her} teddy bear''s heartbeat and said, "Don''t worry, I''ll make you feel better!"', '{age} year old {gender} child {name} in a white doctor coat with stethoscope, checking a teddy bear patient in a colorful clinic, warm lighting, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 3, 'Teacher', '{name} stood in front of a small blackboard, teaching {his_her} stuffed animals. "Today we will learn about colors!" {he_she} announced with a big smile, holding up bright flashcards.', '{age} year old {gender} child {name} standing at a small blackboard teaching stuffed animals sitting in tiny chairs, colorful classroom, chalk drawings, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 4, 'Chef', '{name} wore a tall white chef hat and stirred a big pot of soup. "A pinch of love and a dash of kindness," {he_she} said, tasting {his_her} delicious creation.', '{age} year old {gender} child {name} in a chef hat and apron stirring a colorful pot in a bright kitchen, vegetables and ingredients around, steam rising, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 5, 'Firefighter', 'Brave {name} slid down the fire pole and jumped into the big red fire truck. "Let''s go save the day!" {he_she} shouted, putting on {his_her} shiny helmet.', '{age} year old {gender} child {name} in firefighter gear sliding down a fire pole next to a shiny red fire truck, fire station background, heroic pose, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 6, 'Pilot', '{name} sat in the cockpit of a big airplane, pressing buttons and turning the wheel. "Prepare for takeoff!" {he_she} announced through the microphone as the plane zoomed into the sky.', '{age} year old {gender} child {name} sitting in airplane cockpit with headset, hands on controls, clouds visible through windshield, sunset sky, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 7, 'Scientist', '{name} peered through a microscope at tiny, glowing things. "I just discovered something amazing!" {he_she} exclaimed, writing notes in a special notebook.', '{age} year old {gender} child {name} in a lab coat looking through microscope, colorful test tubes and beakers around, bubbling experiments, bright lab, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 8, 'Artist', 'With a rainbow of paints, {name} created beautiful pictures on a big canvas. "Art is how I show the world what I feel inside," {he_she} smiled, brushing on bright colors.', '{age} year old {gender} child {name} painting on a large canvas with colorful paints, art studio with paintings on walls, splashes of color, creative atmosphere, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 9, 'Veterinarian', '{name} carefully bandaged a puppy''s paw. "There you go, little friend. You''ll be running again in no time!" The puppy licked {his_her} hand to say thank you.', '{age} year old {gender} child {name} in a vet coat gently treating a cute puppy on examination table, other animals waiting, bright veterinary clinic, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 10, 'Police Officer', '{name} wore a police badge and helped people cross the street safely. "Everyone matters in our town," {he_she} said proudly, waving at the grateful neighbors.', '{age} year old {gender} child {name} in police uniform helping people cross street, friendly neighborhood, traffic light, people waving, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 11, 'Musician', '{name} picked up a guitar and started to play. The beautiful music filled the room, and everyone began to smile and dance along.', '{age} year old {gender} child {name} playing guitar on a small stage, colorful spotlights, audience of stuffed animals and friends clapping, musical notes floating, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 12, 'Builder', 'With a hard hat and a toolbox, {name} built the tallest tower ever! "I can build anything I imagine," {he_she} said, hammering the last piece into place.', '{age} year old {gender} child {name} wearing hard hat building with blocks and tools, construction site with crane, colorful buildings, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 13, 'Dancer', '{name} twirled across the stage in a beautiful costume. Every step told a story, and the audience cheered as {he_she} took a graceful bow.', '{age} year old {gender} child {name} dancing gracefully on a stage with spotlights, flowing costume, audience silhouettes, sparkles and stars, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 14, 'Explorer', 'With a backpack and a compass, {name} set off into the jungle. {He_She} discovered a hidden waterfall and a family of colorful parrots!', '{age} year old {gender} child {name} with backpack and compass in lush jungle, discovering a waterfall with colorful parrots, adventure gear, tropical plants, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 15, 'Marine Biologist', '{name} dove deep into the ocean and swam with dolphins and sea turtles. "The ocean is full of wonderful secrets!" {he_she} said, bubbles floating around.', '{age} year old {gender} child {name} swimming underwater with dolphins and sea turtles, coral reef, colorful fish, sunlight filtering through water, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 16, 'Farmer', '{name} woke up early to feed the chickens and water the garden. "Growing food helps everyone," {he_she} said, picking a ripe red tomato.', '{age} year old {gender} child {name} in overalls on a farm, feeding chickens, watering garden, red barn in background, sunny day, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 17, 'Athlete', '{name} ran faster than the wind on the race track. Crossing the finish line, {he_she} threw {his_her} arms up high and shouted, "I did it!"', '{age} year old {gender} child {name} crossing finish line on race track, arms raised in victory, cheering crowd, medal, stadium background, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 18, 'Programmer', '{name} typed on a colorful keyboard, making a video game come to life. "I can create whole worlds with code!" {he_she} said excitedly.', '{age} year old {gender} child {name} typing on keyboard with colorful monitor showing a game world, robot companion, tech-filled room, holographic displays, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 19, 'Architect', '{name} carefully drew plans for an amazing treehouse. "I want it to have a slide, a bridge, and a lookout tower!" {he_she} explained.', '{age} year old {gender} child {name} drawing blueprints at a desk, model treehouse on table, architectural tools, creative workspace, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 20, 'Journalist', '{name} held a microphone and reported the news. "Breaking story: a butterfly garden has appeared in the park!" {he_she} announced enthusiastically.', '{age} year old {gender} child {name} holding microphone reporting news in a park with butterfly garden, camera crew, butterflies flying, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 21, 'Superhero', '{name} put on a cape and mask. With super speed and super kindness, {he_she} helped everyone in town, from rescuing kittens to cheering up friends.', '{age} year old {gender} child {name} in a superhero cape and mask, flying through a colorful city, helping people below, dynamic pose, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 22, 'Inventor', 'In {his_her} workshop, {name} built a robot friend. "This robot can help people carry heavy things!" {he_she} said, pressing the start button.', '{age} year old {gender} child {name} in workshop with tools and gadgets, activating a friendly robot, gears and inventions around, warm lighting, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 23, 'President', '{name} stood at a podium, speaking to a crowd. "When I grow up, I want to make the world a better place for everyone!" the crowd cheered loudly.', '{age} year old {gender} child {name} at a podium speaking to a crowd, flags and banners, confetti, inspiring scene, Pixar style 3D illustration'),
    ('a1111111-1111-1111-1111-111111111111', 24, 'Dreamer', '{name} lay on the soft grass, looking at the clouds. "I can be anything I want to be," {he_she} whispered. And with a heart full of dreams, {name} smiled because the future was bright and full of amazing possibilities.', '{age} year old {gender} child {name} lying on green grass looking at clouds shaped like different professions, sunset sky, peaceful field, dreamy atmosphere, Pixar style 3D illustration');
  END IF;
END $$;

-- Seed Snow White pages
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM template_pages WHERE template_id = 'a2222222-2222-2222-2222-222222222222' LIMIT 1) THEN
    INSERT INTO template_pages (template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
    ('a2222222-2222-2222-2222-222222222222', 1, 'Once Upon a Time', 'Long ago, in a peaceful kingdom, there lived a kind child named {name}. {He_She} had two jealous sisters and a cruel stepmother who treated {him_her} badly, making {him_her} do all the chores while they rested and laughed.', 'Watercolor illustration of a {age} year old {gender} child named {name} in simple clothes, carrying a heavy basket in a grand castle kitchen while two fancy-dressed sisters and a stern stepmother point and whisper, warm fairy-tale lighting, cozy storybook style.'),
    ('a2222222-2222-2222-2222-222222222222', 2, 'A Heart of Kindness', 'Even though {name}''s sisters were unkind, {he_she} stayed gentle and brave. Whenever they snapped at {him_her}, {name} took a deep breath and remembered that kindness is a special kind of magic no one can take away.', '{age} year old {gender} child {name} smiling softly while feeding birds at a castle window, two sisters frowning in the background, soft pastel colors, classic fairy-tale illustration, focus on {name}''s kind expression.'),
    ('a2222222-2222-2222-2222-222222222222', 3, 'Into the Forest', 'One day, the stepmother grew so jealous of {name}''s goodness that she ordered {him_her} to leave the castle. With tears in {his_her} eyes but courage in {his_her} heart, {name} walked into the deep green forest, not knowing what would happen next.', '{age} year old {gender} child {name} walking into a tall green forest with rays of sunlight shining through the trees, small animals peeking out curiously, storybook watercolor style, mood of sadness turning to quiet hope.'),
    ('a2222222-2222-2222-2222-222222222222', 4, 'The Little Cottage', 'After a long walk, {name} found a tiny, cozy cottage hidden among the trees. Inside, everything was messy and dusty. {He_She} decided to clean and tidy the little home, humming softly to feel less afraid.', 'Small cottage interior in the forest, {age} year old {gender} child {name} sweeping the floor, washing dishes, and opening windows, warm golden light coming in, seven tiny chairs and beds, classic fairy-tale illustration.'),
    ('a2222222-2222-2222-2222-222222222222', 5, 'New Friends', 'When the owners of the cottage came home—seven kind dwarfs—they were surprised to find their house sparkling clean. They listened to {name}''s story and promised, ''You can stay with us. We will be your family and keep you safe.''', '{age} year old {gender} child {name} sitting at a small wooden table with seven friendly dwarfs, all smiling kindly, cozy candlelight, wooden cottage interior, storybook watercolor style.'),
    ('a2222222-2222-2222-2222-222222222222', 6, 'The Poisoned Gift', 'Far away, the stepmother learned that {name} was still alive and happy. Disguised as an old woman, she brought a beautiful red apple to the cottage. Trusting others, {name} took a bite—and everything suddenly turned dark.', 'An old woman in a cloak handing a shiny red apple to {age} year old {gender} child {name} at the cottage door, subtle hint of danger in the shadows, rich colors, classic fairy-tale mood.'),
    ('a2222222-2222-2222-2222-222222222222', 7, 'Asleep in Glass', 'The dwarfs were heartbroken. They gently laid {name} in a clear glass coffin on a soft hill, surrounded by flowers. Though {name} seemed asleep, {his_her} gentle face still looked full of hope and kindness.', 'Glass coffin on a flowery hill, {age} year old {gender} child {name} lying peacefully inside with folded hands, seven dwarfs weeping nearby, forest animals gathered around, tender fairy-tale scene.'),
    ('a2222222-2222-2222-2222-222222222222', 8, 'The Prince Arrives', 'One day, a kind prince passed through the forest and saw {name}. He listened to the dwarfs and felt deep respect for {name}''s brave heart. As the coffin was moved, the apple piece slipped from {name}''s throat, and {he_she} woke up with a gentle gasp.', 'Gentle prince on horseback near the glass coffin, {age} year old {gender} child {name} beginning to wake, dwarfs looking surprised and hopeful, bright forest clearing, romantic but child-friendly style.'),
    ('a2222222-2222-2222-2222-222222222222', 9, 'A New Beginning', '{name} thanked the dwarfs for their love and courage. The prince said, ''I admire your kindness and strength, {name}. Would you like to come to my castle, where people will treat you the way you deserve?''', '{age} year old {gender} child {name} standing beside the prince, holding hands with a dwarf in farewell, forest path leading to a bright castle in the distance, hopeful storybook illustration.'),
    ('a2222222-2222-2222-2222-222222222222', 10, 'Happily Ever After', '{name} went to the prince''s castle, where {he_she} was finally treated with love and respect. {His_Her} unkind stepmother and sisters had to live with their choices, while {name}''s kindness shone brighter than ever. From that day on, {name} knew that being gentle and brave could change {his_her} story.', 'Grand castle hall celebration, {age} year old {gender} child {name} dressed in royal clothes, smiling with the prince and new friends, warm golden light, joyful fairy-tale ending illustration.');
  END IF;
END $$;

-- Seed Cricket Champion pages
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM template_pages WHERE template_id = 'a3333333-3333-3333-3333-333333333333' LIMIT 1) THEN
    INSERT INTO template_pages (template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
    ('a3333333-3333-3333-3333-333333333333', 1, 'Forward Defensive', 'Today, {name} is learning the forward defensive shot. {He_She} stands with feet shoulder-width apart, eyes on the ball, front foot stepping forward. The bat comes down straight, close to the pad, blocking the ball safely under {his_her} eyes.', '{age} year old {gender} child {name} in cricket whites, helmet on, playing a perfect forward defensive: front foot forward, bat straight and close to pad, head still over the ball, side-on stance on a sunny ground.'),
    ('a3333333-3333-3333-3333-333333333333', 2, 'Straight Drive', 'Next, {name} practices the straight drive. {He_She} steps forward with the front foot, keeps {his_her} head still, and swings the bat straight down the line of the ball, sending it smoothly back past the bowler.', '{age} year old {gender} child {name} playing a straight drive, front knee bent, bat following through straight toward the bowler, head over the ball, front shoulder pointing down the pitch, clear coaching illustration.'),
    ('a3333333-3333-3333-3333-333333333333', 3, 'Cover Drive', 'For the cover drive, {name} leans into the shot. {He_She} steps toward the off side with a bent front knee and drives the ball through the covers with a smooth arc, elbows high and head close to the line of the ball.', '{age} year old {gender} child {name} playing an elegant cover drive, front foot across to off side, bat following through high, ball flying through cover region, classic cricket coaching pose.'),
    ('a3333333-3333-3333-3333-333333333333', 4, 'On Drive', 'The on drive helps {name} play toward the leg side. {He_She} steps slightly toward mid-on, keeps the bat close to the pad, and swings through the line of the ball with a straight face, guiding it past the bowler.', '{age} year old {gender} child {name} playing an on drive toward mid-on, front foot pointing slightly to leg side, bat straight, wrists firm, balanced stance, detailed lower-body and head position.'),
    ('a3333333-3333-3333-3333-333333333333', 5, 'Pull Shot', 'For the pull shot, {name} waits for a short ball. {He_She} swivels on the back foot, keeps eyes level, and swings the bat horizontally. The front shoulder turns and {name} rolls {his_her} wrists to keep the ball down.', '{age} year old {gender} child {name} playing a pull shot off the back foot, body rotating, back foot anchored, front leg slightly lifted, bat horizontal, ball going toward mid-wicket, dynamic coaching-style pose.'),
    ('a3333333-3333-3333-3333-333333333333', 6, 'Cut Shot', 'With the cut shot, {name} attacks a wide, short ball. {He_She} steps back and across, lets the ball come close, then slices it square through the off side with a firm, controlled bat, keeping {his_her} head still.', '{age} year old {gender} child {name} playing a square cut, back foot across toward off stump, body slightly open, bat cutting across the ball toward point, clear line of shoulders, arms, and bat.'),
    ('a3333333-3333-3333-3333-333333333333', 7, 'Sweep Shot', 'Against spin, {name} kneels for the sweep shot. {He_She} gets low on one knee, stretches the front leg toward the pitch of the ball, and sweeps the bat in a smooth arc, keeping {his_her} head over the ball.', '{age} year old {gender} child {name} playing a classic sweep, front knee on the ground, back leg folded, bat sweeping low in front, head forward over the ball, spinner in the background.'),
    ('a3333333-3333-3333-3333-333333333333', 8, 'Lofted Drive', 'When it is safe to hit in the air, {name} uses the lofted drive. {He_She} steps forward with a strong base and swings the bat upward through the line, lifting the ball over the infield while still watching carefully.', '{age} year old {gender} child {name} playing a lofted drive, front foot planted firmly, bat following through high above the shoulder, ball flying over extra cover, stable lower body, expressive coaching style.'),
    ('a3333333-3333-3333-3333-333333333333', 9, 'Back-Foot Defence', 'For the back-foot defence, {name} moves back and across toward off stump. {He_She} lets the ball bounce, then meets it with a straight bat close to the body, using soft hands to drop the ball near {his_her} feet.', '{age} year old {gender} child {name} playing a back-foot defensive shot, back foot on the crease, front foot slightly forward, bat straight and close to pads, ball dropping near feet.'),
    ('a3333333-3333-3333-3333-333333333333', 10, 'Late Cut', 'Finally, {name} learns the late cut. {He_She} waits for the ball to arrive, then opens the bat face at the last moment, guiding it softly past the slips toward third man with gentle hands and precise timing.', '{age} year old {gender} child {name} playing a late cut, bat angled with soft hands, body slightly open, ball running down to third man, wicket-keeper and slips in background.');
  END IF;
END $$;

-- Seed Cinderella pages
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM template_pages WHERE template_id = 'a4444444-4444-4444-4444-444444444444' LIMIT 1) THEN
    INSERT INTO template_pages (template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
    ('a4444444-4444-4444-4444-444444444444', 1, 'Life in the Kitchen', '{name} lived with a sharp-tongued stepmother and two lazy stepsisters. While they bossed {him_her} around, {name} swept floors, washed dishes, and cooked meals, keeping {his_her} gentle heart safe inside.', '{age} year old {gender} child {name} in simple clothes cleaning a big old kitchen, two fancy stepsisters and a strict stepmother ordering {him_her} around, warm but slightly sad fairy-tale style.'),
    ('a4444444-4444-4444-4444-444444444444', 2, 'Dreams by the Fireplace', 'At night, {name} sat by the fireplace, looking at the glowing embers and dreaming of a kinder life. {He_She} whispered wishes into the smoke, hoping that one day, someone would see {his_her} true worth.', '{age} year old {gender} child {name} sitting by a fireplace in a small corner, soft orange light on {his_her} face, old broom and bucket nearby, dreamy fairy-tale atmosphere.'),
    ('a4444444-4444-4444-4444-444444444444', 3, 'Invitation to the Ball', 'One day, a royal invitation arrived: everyone in the kingdom was invited to a grand ball at the palace. {name}''s stepmother dressed {his_her} sisters in fancy gowns, laughing as she told {name} that {he_she} was far too dirty and plain to go.', 'Royal messenger delivering a scroll in a hallway, two excited stepsisters twirling in half-finished dresses, {age} year old {gender} child {name} holding a simple apron, looking hopeful, stern stepmother nearby.'),
    ('a4444444-4444-4444-4444-444444444444', 4, 'The Fairy Godmother', 'After everyone left, {name} cried in the garden. Suddenly, a warm light appeared, and a fairy godmother smiled at {him_her}. ''Your kindness shines brighter than any dress,'' she said. ''You shall go to the ball.''', 'Magical fairy godmother with sparkling wand appearing before {age} year old {gender} child {name} in a garden, pumpkin and mice nearby, glowing soft blue and gold light, storybook style.'),
    ('a4444444-4444-4444-4444-444444444444', 5, 'Magic Transformation', 'With a flick of her wand, the fairy turned {name}''s rags into a shimmering outfit and glass shoes that fit perfectly. A pumpkin became a carriage, and the mice turned into horses. ''Be back by midnight,'' she warned gently.', '{age} year old {gender} child {name} spinning in a glowing magical dress or suit, glass slippers shining, pumpkin transforming into a carriage, mice into horses, sparkling fairy dust everywhere.'),
    ('a4444444-4444-4444-4444-444444444444', 6, 'At the Ball', 'At the palace, everyone stared in wonder at {name}. The prince noticed {his_her} gentle smile and brave eyes. He asked {name} to dance, and together they glided across the floor like they had always been meant to meet.', 'Grand palace ballroom, {age} year old {gender} child {name} dancing with a kind prince, chandeliers and guests in the background, warm golden colors, elegant fairy-tale scene.'),
    ('a4444444-4444-4444-4444-444444444444', 7, 'Midnight Escape', 'Suddenly, the great clock began to strike twelve. Remembering the fairy''s warning, {name} thanked the prince and ran. On the palace steps, one glass shoe slipped off, but there was no time to turn back.', '{age} year old {gender} child {name} running down palace stairs at midnight, one glass slipper left behind, clock tower showing twelve, flowing dress or outfit, dramatic but child-friendly scene.'),
    ('a4444444-4444-4444-4444-444444444444', 8, 'The Prince Searches', 'The next day, the prince searched the kingdom with the glass shoe. He tried it on many people, but it never fit. He promised himself he would find the person whose kindness had touched his heart.', 'Prince traveling in a carriage through villages, holding a glass slipper, trying it on different feet, people watching curiously, bright daytime fairy-tale illustration.'),
    ('a4444444-4444-4444-4444-444444444444', 9, 'The Perfect Fit', 'At last, the prince reached {name}''s home. The stepsisters tried to squeeze into the slipper, but it would not fit. When {name} gently tried it on, it slid perfectly over {his_her} foot, shining like it had always belonged there.', 'Inside a modest room, prince kneeling to place glass slipper on {age} year old {gender} child {name}''s foot, stepsisters and stepmother shocked in the background, warm hopeful colors.'),
    ('a4444444-4444-4444-4444-444444444444', 10, 'A Strong New Life', '{name} chose to leave the unkindness behind and start a new life at the palace. With the prince and new friends, {he_she} was finally treated with love and respect. {name} learned that {his_her} bravery and kindness were the strongest magic of all.', 'Palace garden scene, {age} year old {gender} child {name} walking happily with the prince and new friends, flowers, fountains, and bright sky, peaceful fairy-tale ending.');
  END IF;
END $$;

-- Seed Sports Day Champion pages
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM template_pages WHERE template_id = 'a5555555-5555-5555-5555-555555555555' LIMIT 1) THEN
    INSERT INTO template_pages (template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
    ('a5555555-5555-5555-5555-555555555555', 1, 'Sprinting Star', 'On sports day, {name} lines up for the sprint race. {He_She} bends slightly forward, keeps arms loose, and focuses on the finish line. With each strong step, {name} feels faster and more confident.', '{age} year old {gender} child {name} sprinting on a school track, leaning slightly forward, arms pumping, knees lifting, cheering crowd and Sports Day banner in background.'),
    ('a5555555-5555-5555-5555-555555555555', 2, 'Football Hero', 'Next comes football. {name} keeps {his_her} head up, taps the ball with gentle touches, and uses quick steps to move past defenders. A strong, clean kick sends the ball spinning toward the goal.', '{age} year old {gender} child {name} dribbling a football on a green field, defenders nearby, legs in motion, focused eyes on the ball, school sports ground setting.'),
    ('a5555555-5555-5555-5555-555555555555', 3, 'Basketball Shooter', 'In basketball, {name} bends {his_her} knees, keeps elbows under the ball, and aims softly at the hoop. With a smooth push and flick of the wrists, the ball arcs through the air toward the net.', '{age} year old {gender} child {name} shooting a basketball, knees bent, arms extended, ball in mid-air heading to the hoop, indoor school gym, bright colors.'),
    ('a5555555-5555-5555-5555-555555555555', 4, 'Tennis Ace', 'With a tennis racket, {name} stands side-on, feet apart, eyes on the ball. {He_She} swings smoothly, striking the ball in front of the body and following through high, sending it neatly over the net.', '{age} year old {gender} child {name} playing tennis on a court, side-on stance, racket following through, ball crossing the net, sunny outdoor scene.'),
    ('a5555555-5555-5555-5555-555555555555', 5, 'Swimming Dolphin', 'In the pool, {name} reaches arms forward, kicks with straight legs, and keeps breathing calmly to the side. Each stroke feels smoother as {he_she} glides through the water like a fast, friendly dolphin.', '{age} year old {gender} child {name} swimming in a clean blue pool, freestyle stroke, face turning to breathe, lane lines visible, bright indoor lighting.'),
    ('a5555555-5555-5555-5555-555555555555', 6, 'Gymnast on the Beam', 'On the balance beam, {name} places one foot carefully in front of the other, arms stretched out wide. Slow, steady breaths help {him_her} stay calm as {he_she} takes graceful steps across.', '{age} year old {gender} child {name} balancing on a gymnastics beam, arms out for balance, focused face, coach and mats in the background, bright gym setting.'),
    ('a5555555-5555-5555-5555-555555555555', 7, 'Badminton Flyer', 'With a badminton racket, {name} watches the shuttle closely. {He_She} moves light on {his_her} feet, jumps for a high shot, and swings the racket with a quick snap to send the shuttle back over the net.', '{age} year old {gender} child {name} playing badminton indoors, jumping to hit a shuttlecock, racket arm stretched up, net and court lines visible.'),
    ('a5555555-5555-5555-5555-555555555555', 8, 'Hockey Warrior', 'In hockey, {name} bends knees, keeps the stick low, and uses quick pushes to guide the ball. Strong legs and sharp eyes help {him_her} move down the field like a true team warrior.', '{age} year old {gender} child {name} playing field hockey, slightly crouched, stick controlling the ball, teammates in background, school sports field.'),
    ('a5555555-5555-5555-5555-555555555555', 9, 'Long Jump Flyer', 'For long jump, {name} runs with powerful steps, then plants one foot on the board and swings arms forward. {He_She} lifts off the ground, flying through the air before landing softly in the sand.', '{age} year old {gender} child {name} mid-air in a long jump, knees up, arms forward, sand pit below, white takeoff board visible, outdoor track setting.'),
    ('a5555555-5555-5555-5555-555555555555', 10, 'All-Round Champion', 'At the end of sports day, {name} feels tired but proud. {He_She} has tried running, football, basketball, tennis, swimming, gymnastics, badminton, hockey, and long jump. With practice and heart, {name} knows {he_she} can become a champion in any sport {he_she} loves.', '{age} year old {gender} child {name} standing proudly with a small medal or ribbon, various sports equipment (football, racket, bat, ball) around, school field in background, bright celebratory children''s book style.');
  END IF;
END $$;
