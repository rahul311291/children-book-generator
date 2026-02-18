/*
  # Seed Remaining Template Pages

  1. Inserts
    - Snow White pages (10 pages)
    - Cricket Champion pages (10 pages)
    - Cinderella pages (10 pages)
    - Sports Day pages (10 pages)
    
  2. Notes
    - Only inserts if pages don't already exist for each template
    - Uses predefined UUID values for templates
*/

DO $$
DECLARE
  v_snow_white_id uuid := 'a2222222-2222-2222-2222-222222222222';
  v_cricket_id uuid := 'a3333333-3333-3333-3333-333333333333';
  v_cinderella_id uuid := 'a4444444-4444-4444-4444-444444444444';
  v_sports_day_id uuid := 'a5555555-5555-5555-5555-555555555555';
  v_page_count integer;
BEGIN
  -- Snow White Template (10 pages)
  SELECT COUNT(*) INTO v_page_count FROM template_pages WHERE template_id = v_snow_white_id;
  IF v_page_count = 0 THEN
    INSERT INTO template_pages (id, template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
      (gen_random_uuid(), v_snow_white_id, 1, 'Once Upon a Time', 
       'Long ago, in a peaceful kingdom, there lived a kind child named {name}. {He_She} had two jealous sisters and a cruel stepmother who treated {him_her} badly, making {him_her} do all the chores while they rested and laughed.',
       'Watercolor illustration of a {age} year old {gender} child named {name} in simple clothes, carrying a heavy basket in a grand castle kitchen while two fancy-dressed sisters and a stern stepmother point and whisper, warm fairy-tale lighting, cozy storybook style.'),
      (gen_random_uuid(), v_snow_white_id, 2, 'A Heart of Kindness',
       'Even though {name}''s sisters were unkind, {he_she} stayed gentle and brave. Whenever they snapped at {him_her}, {name} took a deep breath and remembered that kindness is a special kind of magic no one can take away.',
       '{age} year old {gender} child {name} smiling softly while feeding birds at a castle window, two sisters frowning in the background, soft pastel colors, classic fairy-tale illustration, focus on {name}''s kind expression.'),
      (gen_random_uuid(), v_snow_white_id, 3, 'Into the Forest',
       'One day, the stepmother grew so jealous of {name}''s goodness that she ordered {him_her} to leave the castle. With tears in {his_her} eyes but courage in {his_her} heart, {name} walked into the deep green forest, not knowing what would happen next.',
       '{age} year old {gender} child {name} walking into a tall green forest with rays of sunlight shining through the trees, small animals peeking out curiously, storybook watercolor style, mood of sadness turning to quiet hope.'),
      (gen_random_uuid(), v_snow_white_id, 4, 'The Little Cottage',
       'After a long walk, {name} found a tiny, cozy cottage hidden among the trees. Inside, everything was messy and dusty. {He_She} decided to clean and tidy the little home, humming softly to feel less afraid.',
       'Small cottage interior in the forest, {age} year old {gender} child {name} sweeping the floor, washing dishes, and opening windows, warm golden light coming in, seven tiny chairs and beds, classic fairy-tale illustration.'),
      (gen_random_uuid(), v_snow_white_id, 5, 'New Friends',
       'When the owners of the cottage came home—seven kind dwarfs—they were surprised to find their house sparkling clean. They listened to {name}''s story and promised, ''You can stay with us. We will be your family and keep you safe.''',
       '{age} year old {gender} child {name} sitting at a small wooden table with seven friendly dwarfs, all smiling kindly, cozy candlelight, wooden cottage interior, storybook watercolor style.'),
      (gen_random_uuid(), v_snow_white_id, 6, 'The Poisoned Gift',
       'Far away, the stepmother learned that {name} was still alive and happy. Disguised as an old woman, she brought a beautiful red apple to the cottage. Trusting others, {name} took a bite—and everything suddenly turned dark.',
       'An old woman in a cloak handing a shiny red apple to {age} year old {gender} child {name} at the cottage door, subtle hint of danger in the shadows, rich colors, classic fairy-tale mood.'),
      (gen_random_uuid(), v_snow_white_id, 7, 'Asleep in Glass',
       'The dwarfs were heartbroken. They gently laid {name} in a clear glass coffin on a soft hill, surrounded by flowers. Though {name} seemed asleep, {his_her} gentle face still looked full of hope and kindness.',
       'Glass coffin on a flowery hill, {age} year old {gender} child {name} lying peacefully inside with folded hands, seven dwarfs weeping nearby, forest animals gathered around, tender fairy-tale scene.'),
      (gen_random_uuid(), v_snow_white_id, 8, 'The Prince Arrives',
       'One day, a kind prince passed through the forest and saw {name}. He listened to the dwarfs and felt deep respect for {name}''s brave heart. As the coffin was moved, the apple piece slipped from {name}''s throat, and {he_she} woke up with a gentle gasp.',
       'Gentle prince on horseback near the glass coffin, {age} year old {gender} child {name} beginning to wake, dwarfs looking surprised and hopeful, bright forest clearing, romantic but child-friendly style.'),
      (gen_random_uuid(), v_snow_white_id, 9, 'A New Beginning',
       '{name} thanked the dwarfs for their love and courage. The prince said, ''I admire your kindness and strength, {name}. Would you like to come to my castle, where people will treat you the way you deserve?''',
       '{age} year old {gender} child {name} standing beside the prince, holding hands with a dwarf in farewell, forest path leading to a bright castle in the distance, hopeful storybook illustration.'),
      (gen_random_uuid(), v_snow_white_id, 10, 'Happily Ever After',
       '{name} went to the prince''s castle, where {he_she} was finally treated with love and respect. {His_Her} unkind stepmother and sisters had to live with their choices, while {name}''s kindness shone brighter than ever. From that day on, {name} knew that being gentle and brave could change {his_her} story.',
       'Grand castle hall celebration, {age} year old {gender} child {name} dressed in royal clothes, smiling with the prince and new friends, warm golden light, joyful fairy-tale ending illustration.');
  END IF;

  -- Cricket Champion Template (10 pages)
  SELECT COUNT(*) INTO v_page_count FROM template_pages WHERE template_id = v_cricket_id;
  IF v_page_count = 0 THEN
    INSERT INTO template_pages (id, template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
      (gen_random_uuid(), v_cricket_id, 1, 'Forward Defensive',
       'Today, {name} is learning the forward defensive shot. {He_She} stands with feet shoulder-width apart, eyes on the ball, front foot stepping forward. The bat comes down straight, close to the pad, blocking the ball safely under {his_her} eyes.',
       '{age} year old {gender} child {name} in cricket whites, helmet on, playing a perfect forward defensive: front foot forward, bat straight and close to pad, head still over the ball, side-on stance on a sunny ground.'),
      (gen_random_uuid(), v_cricket_id, 2, 'Straight Drive',
       'Next, {name} practices the straight drive. {He_She} steps forward with the front foot, keeps {his_her} head still, and swings the bat straight down the line of the ball, sending it smoothly back past the bowler.',
       '{age} year old {gender} child {name} playing a straight drive, front knee bent, bat following through straight toward the bowler, head over the ball, front shoulder pointing down the pitch, clear coaching illustration.'),
      (gen_random_uuid(), v_cricket_id, 3, 'Cover Drive',
       'For the cover drive, {name} leans into the shot. {He_She} steps toward the off side with a bent front knee and drives the ball through the covers with a smooth arc, elbows high and head close to the line of the ball.',
       '{age} year old {gender} child {name} playing an elegant cover drive, front foot across to off side, bat following through high, ball flying through cover region, classic cricket coaching pose.'),
      (gen_random_uuid(), v_cricket_id, 4, 'On Drive',
       'The on drive helps {name} play toward the leg side. {He_She} steps slightly toward mid-on, keeps the bat close to the pad, and swings through the line of the ball with a straight face, guiding it past the bowler.',
       '{age} year old {gender} child {name} playing an on drive toward mid-on, front foot pointing slightly to leg side, bat straight, wrists firm, balanced stance, detailed lower-body and head position.'),
      (gen_random_uuid(), v_cricket_id, 5, 'Pull Shot',
       'For the pull shot, {name} waits for a short ball. {He_She} swivels on the back foot, keeps eyes level, and swings the bat horizontally. The front shoulder turns and {name} rolls {his_her} wrists to keep the ball down.',
       '{age} year old {gender} child {name} playing a pull shot off the back foot, body rotating, back foot anchored, front leg slightly lifted, bat horizontal, ball going toward mid-wicket, dynamic coaching-style pose.'),
      (gen_random_uuid(), v_cricket_id, 6, 'Cut Shot',
       'With the cut shot, {name} attacks a wide, short ball. {He_She} steps back and across, lets the ball come close, then slices it square through the off side with a firm, controlled bat, keeping {his_her} head still.',
       '{age} year old {gender} child {name} playing a square cut, back foot across toward off stump, body slightly open, bat cutting across the ball toward point, clear line of shoulders, arms, and bat.'),
      (gen_random_uuid(), v_cricket_id, 7, 'Sweep Shot',
       'Against spin, {name} kneels for the sweep shot. {He_She} gets low on one knee, stretches the front leg toward the pitch of the ball, and sweeps the bat in a smooth arc, keeping {his_her} head over the ball.',
       '{age} year old {gender} child {name} playing a classic sweep, front knee on the ground, back leg folded, bat sweeping low in front, head forward over the ball, spinner in the background.'),
      (gen_random_uuid(), v_cricket_id, 8, 'Lofted Drive',
       'When it is safe to hit in the air, {name} uses the lofted drive. {He_She} steps forward with a strong base and swings the bat upward through the line, lifting the ball over the infield while still watching carefully.',
       '{age} year old {gender} child {name} playing a lofted drive, front foot planted firmly, bat following through high above the shoulder, ball flying over extra cover, stable lower body, expressive coaching style.'),
      (gen_random_uuid(), v_cricket_id, 9, 'Back-Foot Defence',
       'For the back-foot defence, {name} moves back and across toward off stump. {He_She} lets the ball bounce, then meets it with a straight bat close to the body, using soft hands to drop the ball near {his_her} feet.',
       '{age} year old {gender} child {name} playing a back-foot defensive shot, back foot on the crease, front foot slightly forward, bat straight and close to pads, ball dropping near feet.'),
      (gen_random_uuid(), v_cricket_id, 10, 'Late Cut',
       'Finally, {name} learns the late cut. {He_She} waits for the ball to arrive, then opens the bat face at the last moment, guiding it softly past the slips toward third man with gentle hands and precise timing.',
       '{age} year old {gender} child {name} playing a late cut, bat angled with soft hands, body slightly open, ball running down to third man, wicket-keeper and slips in background.');
  END IF;

  -- Cinderella Template (10 pages)
  SELECT COUNT(*) INTO v_page_count FROM template_pages WHERE template_id = v_cinderella_id;
  IF v_page_count = 0 THEN
    INSERT INTO template_pages (id, template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
      (gen_random_uuid(), v_cinderella_id, 1, 'Life in the Kitchen',
       '{name} lived with a sharp-tongued stepmother and two lazy stepsisters. While they bossed {him_her} around, {name} swept floors, washed dishes, and cooked meals, keeping {his_her} gentle heart safe inside.',
       '{age} year old {gender} child {name} in simple clothes cleaning a big old kitchen, two fancy stepsisters and a strict stepmother ordering {him_her} around, warm but slightly sad fairy-tale style.'),
      (gen_random_uuid(), v_cinderella_id, 2, 'Dreams by the Fireplace',
       'At night, {name} sat by the fireplace, looking at the glowing embers and dreaming of a kinder life. {He_She} whispered wishes into the smoke, hoping that one day, someone would see {his_her} true worth.',
       '{age} year old {gender} child {name} sitting by a fireplace in a small corner, soft orange light on {his_her} face, old broom and bucket nearby, dreamy fairy-tale atmosphere.'),
      (gen_random_uuid(), v_cinderella_id, 3, 'Invitation to the Ball',
       'One day, a royal invitation arrived: everyone in the kingdom was invited to a grand ball at the palace. {name}''s stepmother dressed {his_her} sisters in fancy gowns, laughing as she told {name} that {he_she} was far too dirty and plain to go.',
       'Royal messenger delivering a scroll in a hallway, two excited stepsisters twirling in half-finished dresses, {age} year old {gender} child {name} holding a simple apron, looking hopeful, stern stepmother nearby.'),
      (gen_random_uuid(), v_cinderella_id, 4, 'The Fairy Godmother',
       'After everyone left, {name} cried in the garden. Suddenly, a warm light appeared, and a fairy godmother smiled at {him_her}. ''Your kindness shines brighter than any dress,'' she said. ''You shall go to the ball.''',
       'Magical fairy godmother with sparkling wand appearing before {age} year old {gender} child {name} in a garden, pumpkin and mice nearby, glowing soft blue and gold light, storybook style.'),
      (gen_random_uuid(), v_cinderella_id, 5, 'Magic Transformation',
       'With a flick of her wand, the fairy turned {name}''s rags into a shimmering outfit and glass shoes that fit perfectly. A pumpkin became a carriage, and the mice turned into horses. ''Be back by midnight,'' she warned gently.',
       '{age} year old {gender} child {name} spinning in a glowing magical dress or suit, glass slippers shining, pumpkin transforming into a carriage, mice into horses, sparkling fairy dust everywhere.'),
      (gen_random_uuid(), v_cinderella_id, 6, 'At the Ball',
       'At the palace, everyone stared in wonder at {name}. The prince noticed {his_her} gentle smile and brave eyes. He asked {name} to dance, and together they glided across the floor like they had always been meant to meet.',
       'Grand palace ballroom, {age} year old {gender} child {name} dancing with a kind prince, chandeliers and guests in the background, warm golden colors, elegant fairy-tale scene.'),
      (gen_random_uuid(), v_cinderella_id, 7, 'Midnight Escape',
       'Suddenly, the great clock began to strike twelve. Remembering the fairy''s warning, {name} thanked the prince and ran. On the palace steps, one glass shoe slipped off, but there was no time to turn back.',
       '{age} year old {gender} child {name} running down palace stairs at midnight, one glass slipper left behind, clock tower showing twelve, flowing dress or outfit, dramatic but child-friendly scene.'),
      (gen_random_uuid(), v_cinderella_id, 8, 'The Prince Searches',
       'The next day, the prince searched the kingdom with the glass shoe. He tried it on many people, but it never fit. He promised himself he would find the person whose kindness had touched his heart.',
       'Prince traveling in a carriage through villages, holding a glass slipper, trying it on different feet, people watching curiously, bright daytime fairy-tale illustration.'),
      (gen_random_uuid(), v_cinderella_id, 9, 'The Perfect Fit',
       'At last, the prince reached {name}''s home. The stepsisters tried to squeeze into the slipper, but it would not fit. When {name} gently tried it on, it slid perfectly over {his_her} foot, shining like it had always belonged there.',
       'Inside a modest room, prince kneeling to place glass slipper on {age} year old {gender} child {name}''s foot, stepsisters and stepmother shocked in the background, warm hopeful colors.'),
      (gen_random_uuid(), v_cinderella_id, 10, 'A Strong New Life',
       '{name} chose to leave the unkindness behind and start a new life at the palace. With the prince and new friends, {he_she} was finally treated with love and respect. {name} learned that {his_her} bravery and kindness were the strongest magic of all.',
       'Palace garden scene, {age} year old {gender} child {name} walking happily with the prince and new friends, flowers, fountains, and bright sky, peaceful fairy-tale ending.');
  END IF;

  -- Sports Day Template (10 pages)
  SELECT COUNT(*) INTO v_page_count FROM template_pages WHERE template_id = v_sports_day_id;
  IF v_page_count = 0 THEN
    INSERT INTO template_pages (id, template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
      (gen_random_uuid(), v_sports_day_id, 1, 'Sprinting Star',
       'On sports day, {name} lines up for the sprint race. {He_She} bends slightly forward, keeps arms loose, and focuses on the finish line. With each strong step, {name} feels faster and more confident.',
       '{age} year old {gender} child {name} sprinting on a school track, leaning slightly forward, arms pumping, knees lifting, cheering crowd and ''Sports Day'' banner in background.'),
      (gen_random_uuid(), v_sports_day_id, 2, 'Football Hero',
       'Next comes football. {name} keeps {his_her} head up, taps the ball with gentle touches, and uses quick steps to move past defenders. A strong, clean kick sends the ball spinning toward the goal.',
       '{age} year old {gender} child {name} dribbling a football on a green field, defenders nearby, legs in motion, focused eyes on the ball, school sports ground setting.'),
      (gen_random_uuid(), v_sports_day_id, 3, 'Basketball Shooter',
       'In basketball, {name} bends {his_her} knees, keeps elbows under the ball, and aims softly at the hoop. With a smooth push and flick of the wrists, the ball arcs through the air toward the net.',
       '{age} year old {gender} child {name} shooting a basketball, knees bent, arms extended, ball in mid-air heading to the hoop, indoor school gym, bright colors.'),
      (gen_random_uuid(), v_sports_day_id, 4, 'Tennis Ace',
       'With a tennis racket, {name} stands side-on, feet apart, eyes on the ball. {He_She} swings smoothly, striking the ball in front of the body and following through high, sending it neatly over the net.',
       '{age} year old {gender} child {name} playing tennis on a court, side-on stance, racket following through, ball crossing the net, sunny outdoor scene.'),
      (gen_random_uuid(), v_sports_day_id, 5, 'Swimming Dolphin',
       'In the pool, {name} reaches arms forward, kicks with straight legs, and keeps breathing calmly to the side. Each stroke feels smoother as {he_she} glides through the water like a fast, friendly dolphin.',
       '{age} year old {gender} child {name} swimming in a clean blue pool, freestyle stroke, face turning to breathe, lane lines visible, bright indoor lighting.'),
      (gen_random_uuid(), v_sports_day_id, 6, 'Gymnast on the Beam',
       'On the balance beam, {name} places one foot carefully in front of the other, arms stretched out wide. Slow, steady breaths help {him_her} stay calm as {he_she} takes graceful steps across.',
       '{age} year old {gender} child {name} balancing on a gymnastics beam, arms out for balance, focused face, coach and mats in the background, bright gym setting.'),
      (gen_random_uuid(), v_sports_day_id, 7, 'Badminton Flyer',
       'With a badminton racket, {name} watches the shuttle closely. {He_She} moves light on {his_her} feet, jumps for a high shot, and swings the racket with a quick snap to send the shuttle back over the net.',
       '{age} year old {gender} child {name} playing badminton indoors, jumping to hit a shuttlecock, racket arm stretched up, net and court lines visible.'),
      (gen_random_uuid(), v_sports_day_id, 8, 'Hockey Warrior',
       'In hockey, {name} bends knees, keeps the stick low, and uses quick pushes to guide the ball. Strong legs and sharp eyes help {him_her} move down the field like a true team warrior.',
       '{age} year old {gender} child {name} playing field hockey, slightly crouched, stick controlling the ball, teammates in background, school sports field.'),
      (gen_random_uuid(), v_sports_day_id, 9, 'Long Jump Flyer',
       'For long jump, {name} runs with powerful steps, then plants one foot on the board and swings arms forward. {He_She} lifts off the ground, flying through the air before landing softly in the sand.',
       '{age} year old {gender} child {name} mid-air in a long jump, knees up, arms forward, sand pit below, white takeoff board visible, outdoor track setting.'),
      (gen_random_uuid(), v_sports_day_id, 10, 'All-Round Champion',
       'At the end of sports day, {name} feels tired but proud. {He_She} has tried running, football, basketball, tennis, swimming, gymnastics, badminton, hockey, and long jump. With practice and heart, {name} knows {he_she} can become a champion in any sport {he_she} loves.',
       '{age} year old {gender} child {name} standing proudly with a small medal or ribbon, various sports equipment (football, racket, bat, ball) around, school field in background, bright celebratory children''s book style.');
  END IF;
END $$;