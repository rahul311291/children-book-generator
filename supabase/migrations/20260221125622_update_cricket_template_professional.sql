/*
  # Update Cricket Champion Template - Professional Coaching Level

  1. Updates
    - All text templates: Detailed technical coaching instructions with specific body positions
    - All image prompts: Professional photorealistic cricket stadium backgrounds
    - Add annotation overlays showing key body positions with arrows and labels
    
  2. Changes
    - Text includes: Front foot position, back foot position, hand grip, bat angle, body weight distribution, contact point
    - Images: Photorealistic professional cricket stadium, coaching diagram overlays with arrows and labels
    - Each shot described with precise technical detail suitable for cricket coaching
*/

DO $$
DECLARE
  v_cricket_id uuid := 'a3333333-3333-3333-3333-333333333333';
BEGIN
  -- Delete existing pages for Cricket Champion template
  DELETE FROM template_pages WHERE template_id = v_cricket_id;

  -- Insert updated Cricket Champion pages with professional coaching detail
  INSERT INTO template_pages (id, template_id, page_number, profession_title, text_template, image_prompt_template) VALUES
    (gen_random_uuid(), v_cricket_id, 1, 'Forward Defensive',
     'THE FORWARD DEFENSIVE SHOT' || E'\n\n' ||
     'Today {name} masters the forward defensive - cricket''s most important shot.' || E'\n\n' ||
     'STANCE: Feet shoulder-width apart, knees slightly bent, weight evenly balanced.' || E'\n' ||
     'FRONT FOOT: Step forward with front foot toward the pitch of the ball, knee bent, toe pointing to bowler.' || E'\n' ||
     'BACK FOOT: Stays grounded, provides balance and support.' || E'\n' ||
     'HANDS: Top hand (left for right-hander) guides, bottom hand supports. Grip relaxed but firm.' || E'\n' ||
     'BAT: Comes down straight from high to low, blade angled slightly forward, close to front pad.' || E'\n' ||
     'HEAD: Still, eyes level, watching ball onto bat.' || E'\n' ||
     'CONTACT: Ball hits bat under the eyes, bat meets ball with soft hands.' || E'\n' ||
     'FOLLOW-THROUGH: Minimal - bat stays close to pad, no big swing.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} in full cricket whites and helmet, playing perfect forward defensive shot in a packed professional cricket stadium with crowds. IMPORTANT: Add coaching annotation overlays with WHITE ARROWS and WHITE TEXT LABELS showing: 1) Arrow pointing to front foot with label "FRONT FOOT: Step toward pitch, knee bent", 2) Arrow to bat with label "BAT: Straight down, close to pad", 3) Arrow to head with label "HEAD: Still, eyes on ball", 4) Arrow to back foot with label "BACK FOOT: Grounded for balance". Professional sports photography quality, bright daylight stadium lighting, green pitch, clear coaching diagram style with technical annotations.'),

    (gen_random_uuid(), v_cricket_id, 2, 'Straight Drive',
     'THE STRAIGHT DRIVE' || E'\n\n' ||
     '{name} learns cricket''s most elegant attacking shot - the straight drive.' || E'\n\n' ||
     'STANCE: Balanced, knees flexed, ready to move forward.' || E'\n' ||
     'FRONT FOOT: Big stride toward the pitch, front knee bent at 90 degrees, leg forming strong base.' || E'\n' ||
     'BACK FOOT: Pivots on toes, heel slightly raised.' || E'\n' ||
     'HANDS: Top hand dominant, pulling bat through the line of ball.' || E'\n' ||
     'BAT: High backlift, swing down in straight arc following ball''s line.' || E'\n' ||
     'HEAD: Over front knee, eyes locked on contact point.' || E'\n' ||
     'CONTACT: Hit ball at full extension, under the eyes, bat face straight.' || E'\n' ||
     'FOLLOW-THROUGH: Bat continues straight toward bowler, high finish with bat near shoulder, front shoulder pointing down pitch.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} in cricket whites executing perfect straight drive in professional cricket stadium with crowds and sight screens. IMPORTANT: Add coaching annotation overlays with WHITE ARROWS and WHITE TEXT LABELS: 1) Arrow to front foot "FRONT KNEE: Bent 90°, strong base", 2) Arrow to bat swing path showing curved arrow "BAT PATH: Straight line down to ball", 3) Arrow to head "HEAD: Over front knee", 4) Arrow to contact point "CONTACT: Full extension, under eyes", 5) Arrow to follow-through "FOLLOW-THROUGH: High finish toward bowler". Stadium lighting, green pitch, professional sports photography, technical coaching overlay.'),

    (gen_random_uuid(), v_cricket_id, 3, 'Cover Drive',
     'THE COVER DRIVE' || E'\n\n' ||
     'The cover drive - cricket''s most beautiful shot. {name} practices the technique.' || E'\n\n' ||
     'STANCE: Side-on, balanced weight distribution.' || E'\n' ||
     'FRONT FOOT: Step toward off side at 45-degree angle, front knee bent, getting close to pitch of ball.' || E'\n' ||
     'BACK FOOT: Pivots on toes for hip rotation.' || E'\n' ||
     'HANDS: High backlift, top hand controls swing, wrists stay firm through contact.' || E'\n' ||
     'BAT: Swings in arc from high to low, face angled toward cover region.' || E'\n' ||
     'HEAD: Stays still over ball, chin points toward cover.' || E'\n' ||
     'CONTACT: Hit ball just in front of front pad, full face of bat, at full arm extension.' || E'\n' ||
     'FOLLOW-THROUGH: Bat flows through toward cover, high finish near left ear, elbows high, front shoulder dips.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} playing elegant cover drive in international cricket stadium with crowds. IMPORTANT: Add detailed coaching annotation overlays with WHITE ARROWS and LABELS: 1) Arrow showing 45° angle of front foot step "FRONT FOOT: 45° toward off side", 2) Arrow to bat angle "BAT FACE: Angled toward cover", 3) Arrow to contact point with circle "CONTACT ZONE: In front of pad, full extension", 4) Arrow to head position "HEAD: Still, chin to cover", 5) Curved arrow showing bat swing path from backlift to follow-through, 6) Arrow to follow-through "HIGH FINISH: Near left ear". Professional cricket photography, stadium background, bright lighting, coaching diagram style.'),

    (gen_random_uuid(), v_cricket_id, 4, 'On Drive',
     'THE ON DRIVE' || E'\n\n' ||
     '{name} masters playing straight balls to the leg side with the on drive.' || E'\n\n' ||
     'STANCE: Slightly closed, ready for leg-side play.' || E'\n' ||
     'FRONT FOOT: Move toward mid-on, front knee bent, getting to pitch of ball.' || E'\n' ||
     'BACK FOOT: Stays back and across toward off stump for balance.' || E'\n' ||
     'HANDS: Tight grip, top hand pulls bat through, keeping face closed.' || E'\n' ||
     'BAT: High backlift, swing straight down the line, bat face slightly closed toward leg side.' || E'\n' ||
     'HEAD: Still position, eyes watching ball onto middle of bat.' || E'\n' ||
     'CONTACT: Meet ball with full bat face, slightly in front of front pad, wrists turn bat face toward mid-on.' || E'\n' ||
     'FOLLOW-THROUGH: Bat continues toward mid-on/mid-wicket, finishing high near right shoulder.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} executing on drive in packed cricket stadium. IMPORTANT: Add technical coaching overlays with WHITE ARROWS and LABELS: 1) Arrow to front foot "FRONT FOOT: Toward mid-on, knee bent", 2) Arrow to wrists "WRISTS: Turn bat face to leg", 3) Arrow showing bat face angle "BAT FACE: Slightly closed", 4) Circle at contact point "CONTACT: In front of pad", 5) Arrow to head "HEAD: Still, eyes on ball", 6) Curved arrow showing swing path toward mid-on. Professional stadium background with crowds, bright lighting, green pitch, technical coaching style.'),

    (gen_random_uuid(), v_cricket_id, 5, 'Pull Shot',
     'THE PULL SHOT' || E'\n\n' ||
     'Against short bowling, {name} plays the aggressive pull shot.' || E'\n\n' ||
     'STANCE: Slightly open, weight on balls of feet, ready to rock back.' || E'\n' ||
     'BACK FOOT: Move back and across toward off stump, weight transfers to back foot.' || E'\n' ||
     'FRONT FOOT: Lifts slightly off ground or toes stay light, allowing hip rotation.' || E'\n' ||
     'HANDS: Quick hands bring bat back, then swing horizontal across body.' || E'\n' ||
     'BAT: Horizontal swing at chest/shoulder height, bat parallel to ground.' || E'\n' ||
     'HEAD: Eyes level with bounce of ball, watching it closely.' || E'\n' ||
     'CONTACT: Hit ball in front of body, between waist and chest height, rolling wrists over ball.' || E'\n' ||
     'FOLLOW-THROUGH: Complete rotation, bat finishes near left shoulder, front shoulder pulls down and around.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} playing powerful pull shot in professional cricket stadium with crowds. IMPORTANT: Add detailed technical overlays with WHITE ARROWS and LABELS: 1) Arrow to back foot "BACK FOOT: Back & across, weight here", 2) Arrow showing body rotation with curved arrow "HIP ROTATION: Turn into shot", 3) Arrow to bat showing horizontal line "BAT: Horizontal swing", 4) Circle showing contact zone "CONTACT: Chest-shoulder height", 5) Arrow to wrists "WRISTS: Roll over ball", 6) Arrow to eyes "EYES: Level with bounce", 7) Dotted line showing ball trajectory to mid-wicket. Stadium background, action photography, coaching annotations.'),

    (gen_random_uuid(), v_cricket_id, 6, 'Cut Shot',
     'THE SQUARE CUT' || E'\n\n' ||
     'When the ball is short and wide, {name} uses the cut shot to pierce the off side.' || E'\n\n' ||
     'STANCE: Balanced, ready to move back.' || E'\n' ||
     'BACK FOOT: Move back and across toward off stump, creating room.' || E'\n' ||
     'FRONT FOOT: Stays light or lifts slightly, allowing free swing.' || E'\n' ||
     'HANDS: Bat taken back high near shoulder, then cut down and across ball.' || E'\n' ||
     'BAT: Comes from high to low, chopping motion, blade cuts across line of ball.' || E'\n' ||
     'HEAD: Stays still and over the ball, watching closely.' || E'\n' ||
     'CONTACT: Hit ball when it''s beside body, at arm''s length, with controlled chop.' || E'\n' ||
     'FOLLOW-THROUGH: Bat continues toward point region, controlled finish, head stays still throughout.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} executing square cut in international cricket stadium. IMPORTANT: Add professional coaching overlays with WHITE ARROWS and LABELS: 1) Arrow to back foot "BACK FOOT: Back & across for room", 2) Arrow showing bat path from high to low "BAT PATH: High to low, cutting motion", 3) Circle at contact point "CONTACT: Beside body, arm''s length", 4) Arrow to head "HEAD: Still over ball", 5) Arrow showing body opening "BODY: Slightly open stance", 6) Dotted line showing ball going square to point. Stadium setting, professional photography, technical coaching style.'),

    (gen_random_uuid(), v_cricket_id, 7, 'Sweep Shot',
     'THE SWEEP SHOT' || E'\n\n' ||
     'Against spin bowling, {name} learns the sweep to score on the leg side.' || E'\n\n' ||
     'STANCE: Slightly open toward leg side.' || E'\n' ||
     'FRONT LEG: Bends down on front knee until it touches ground, front foot points toward pitch of ball.' || E'\n' ||
     'BACK LEG: Folds under, back knee on or near ground for low center of gravity.' || E'\n' ||
     'HANDS: Bat brought across body horizontally, top hand controls direction.' || E'\n' ||
     'BAT: Horizontal swing low to ground, keeping bat face square, sweeping across line.' || E'\n' ||
     'HEAD: Gets down low, eyes watch ball from release to contact, head over ball.' || E'\n' ||
     'CONTACT: Hit ball when it pitches in line with body, in front of stumps, with horizontal bat.' || E'\n' ||
     'FOLLOW-THROUGH: Bat continues sweeping motion toward square leg, staying low throughout shot.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} playing sweep shot against spinner in cricket stadium. IMPORTANT: Add technical coaching overlays with WHITE ARROWS and LABELS: 1) Arrow to front knee "FRONT KNEE: On ground", 2) Arrow to back leg "BACK LEG: Folded under", 3) Horizontal arrow showing bat path "BAT: Horizontal sweep", 4) Arrow to head "HEAD: Low, over ball", 5) Circle at pitch point "CONTACT: When ball pitches here", 6) Arrow to bat angle "BAT FACE: Square to ball", 7) Dotted line showing ball to square leg. Spinner visible in background, stadium setting, coaching diagram style.'),

    (gen_random_uuid(), v_cricket_id, 8, 'Lofted Drive',
     'THE LOFTED DRIVE' || E'\n\n' ||
     'To clear the infield, {name} plays the powerful lofted drive.' || E'\n\n' ||
     'STANCE: Strong base, knees flexed, weight centered.' || E'\n' ||
     'FRONT FOOT: Big stride to pitch of ball, front knee bent 90 degrees for solid base.' || E'\n' ||
     'BACK FOOT: Firmly planted, transfers power through shot.' || E'\n' ||
     'HANDS: Full swing, bottom hand provides power, top hand guides.' || E'\n' ||
     'BAT: Complete swing from high backlift, bat face lofts through ball, following upward arc.' || E'\n' ||
     'HEAD: Stays still until contact, then can follow ball flight.' || E'\n' ||
     'CONTACT: Hit ball at full extension under eyes, bat face angled up 15-30 degrees.' || E'\n' ||
     'FOLLOW-THROUGH: Full, high finish, bat ends up over shoulder, weight transfers completely onto front foot.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} playing lofted drive in cricket stadium with ball in air. IMPORTANT: Add detailed overlays with WHITE ARROWS and LABELS: 1) Arrow to front foot "FRONT FOOT: To pitch, knee 90°", 2) Curved arrow showing bat swing "SWING: Full arc, high to high", 3) Arrow to bat angle at contact "BAT FACE: Angled up 15-30°", 4) Arrow to contact point "CONTACT: Full extension", 5) Arrow to follow-through "FOLLOW-THROUGH: High over shoulder", 6) Dotted arc showing ball flight over infield, 7) Arrow showing weight transfer to front. Stadium background, ball visible in air, professional coaching style.'),

    (gen_random_uuid(), v_cricket_id, 9, 'Back-Foot Defence',
     'THE BACK-FOOT DEFENCE' || E'\n\n' ||
     'For short rising balls, {name} uses the back-foot defence to stay safe.' || E'\n\n' ||
     'STANCE: Slightly open, ready to move back quickly.' || E'\n' ||
     'BACK FOOT: Move straight back toward stumps, weight fully on back foot.' || E'\n' ||
     'FRONT FOOT: Lifts and moves slightly forward for balance, toe pointing down pitch.' || E'\n' ||
     'HANDS: Bat held high initially, then brought down straight with soft hands.' || E'\n' ||
     'BAT: Comes down late and close to body, blade vertical or slightly angled forward.' || E'\n' ||
     'HEAD: Moves back with body but stays over ball, eyes watch ball onto bat.' || E'\n' ||
     'CONTACT: Meet ball right under eyes with soft hands, close to body, letting ball come to bat.' || E'\n' ||
     'FOLLOW-THROUGH: Minimal - just enough to drop ball safely near feet, bat stays close to pads.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} playing back-foot defence in professional cricket stadium. IMPORTANT: Add coaching overlays with WHITE ARROWS and LABELS: 1) Arrow to back foot "BACK FOOT: Straight back to stumps", 2) Arrow to weight distribution "WEIGHT: On back foot", 3) Arrow to hands "HANDS: Soft grip", 4) Arrow to bat position "BAT: Late, close to body", 5) Circle at contact "CONTACT: Under eyes", 6) Arrow to head "HEAD: Back but over ball", 7) Dotted line showing ball dropping near feet. Fast bowler in background, stadium setting, technical coaching diagram.'),

    (gen_random_uuid(), v_cricket_id, 10, 'Late Cut',
     'THE LATE CUT' || E'\n\n' ||
     'The late cut requires perfect timing. {name} practices this delicate shot.' || E'\n\n' ||
     'STANCE: Slightly open, ready to move back and create room.' || E'\n' ||
     'BACK FOOT: Move back and across, creating space between body and ball.' || E'\n' ||
     'FRONT FOOT: Stays light, allowing free arm movement.' || E'\n' ||
     'HANDS: Hold bat with soft hands, waiting for ball to come close.' || E'\n' ||
     'BAT: Opens bat face at last moment, blade angled toward third man, using ball''s pace.' || E'\n' ||
     'HEAD: Stays still right next to line of ball, eyes watch ball onto edge of bat.' || E'\n' ||
     'CONTACT: Play ball very late, almost beside or behind body, gentle touch with open face.' || E'\n' ||
     'FOLLOW-THROUGH: Minimal, controlled finish, letting ball glide off bat face with soft hands toward third man.',
     'Professional cricket coaching diagram: Photorealistic {age} year old {gender} child {name} playing late cut in cricket stadium with wicketkeeper and slips visible. IMPORTANT: Add technical overlays with WHITE ARROWS and LABELS: 1) Arrow to back foot "BACK FOOT: Back & across for space", 2) Arrow to bat angle "BAT FACE: Opens late", 3) Arrow to hands "HANDS: Soft, gentle touch", 4) Circle showing late contact point "CONTACT: Late, beside body", 5) Arrow to head "HEAD: Still, beside ball line", 6) Dotted line showing ball going fine to third man, 7) Arrow showing timing "TIMING: Wait for ball". Wicketkeeper and slip fielders visible, stadium setting, professional coaching diagram style.');
END $$;