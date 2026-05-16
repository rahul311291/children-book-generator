# ---------------------------------------------------------------------------
# Image prompt helper – all template pages use the Diffrun-style spread format:
#   • semi-realistic watercolor portrait
#   • white/minimal background with soft watercolor splash accents
#   • child positioned slightly off-centre so text can sit on the other side
# ---------------------------------------------------------------------------
_BASE = (
    "Semi-realistic watercolor portrait storybook illustration. "
    "White background with soft watercolor paint splashes at the corners. "
    "The child is the single hero subject, rendered with photographic facial accuracy "
    "(real face shape, skin tone, hair colour and texture). "
    "Child positioned slightly to the {side} of the frame, clear white space on the {opp} side for text. "
    "{details} "
    "Professional premium children's book illustration quality. No text, no watermarks."
)

def _p(side, details):
    opp = "right" if side == "left" else "left"
    return _BASE.format(side=side, opp=opp, details=details)

# Alternates L / R for visual variety
_L = "left"
_R = "right"


WHEN_I_GROW_UP_TEMPLATE = {
    "name": "When {name} Grows Up",
    "description": "A personalised book where your child stars as the hero exploring every career they might become",
    "total_pages": 28,
    "pages": [
        # ── Page 1 ──────────────────────────────────────────────────────────
        {
            "page_number": 1,
            "profession_title": "ASTRONAUT",
            "text_template": """\
When {name} grows up,
{he_she} just might be,
an astronaut floating free.
Among the stars and planets bright,
exploring space both day and night!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} wearing a gleaming white spacesuit with a round glass "
                "helmet, floating weightlessly. Colourful planets, swirling nebulae, and twinkling stars surround "
                "{name}. Earth glows blue below. Soft brush strokes, warm pastel palette."
            )),
        },
        # ── Page 2 ──────────────────────────────────────────────────────────
        {
            "page_number": 2,
            "profession_title": "DOCTOR",
            "text_template": """\
Perhaps {name} will wear a white coat,
with a stethoscope around {his_her} throat.
Healing people every single day,
making all the aches just fade away!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} in a crisp white doctor's coat with a silver stethoscope, "
                "smiling warmly and holding a clipboard. Soft pastel hospital background accents."
            )),
        },
        # ── Page 3 ──────────────────────────────────────────────────────────
        {
            "page_number": 3,
            "profession_title": "TEACHER",
            "text_template": """\
Maybe {name} will teach and guide,
with wisdom, patience, and pride.
Sharing knowledge every day,
helping students find their way!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} standing at a colourful classroom chalkboard with ABCs "
                "and numbers, holding an open storybook. Warm sunny lighting."
            )),
        },
        # ── Page 4 ──────────────────────────────────────────────────────────
        {
            "page_number": 4,
            "profession_title": "FIREFIGHTER",
            "text_template": """\
When {name} grows up brave and strong,
{he_she} might fight fires all day long.
With a helmet and a hose so bright,
saving people day and night!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} wearing a shiny red firefighter helmet and yellow turnout "
                "coat, standing proudly. A dalmatian sits beside {name}. Heroic warm mood."
            )),
        },
        # ── Page 5 ──────────────────────────────────────────────────────────
        {
            "page_number": 5,
            "profession_title": "CHEF",
            "text_template": """\
Maybe one day,
{name} would choose to cook.
As a renowned chef,
{he_she}'ll be in every recipe book!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} wearing a tall white chef's hat and apron, "
                "holding a beautiful decorated cake or a tray of golden pastries. Cosy warm kitchen accents."
            )),
        },
        # ── Page 6 ──────────────────────────────────────────────────────────
        {
            "page_number": 6,
            "profession_title": "PILOT",
            "text_template": """\
Maybe {name} will soar and fly,
high above the bright blue sky.
Piloting planes from here to there,
travelling everywhere with care!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} in a navy pilot's uniform with gold wings badge and cap, "
                "sitting in an airplane cockpit. Fluffy clouds visible through the windshield."
            )),
        },
        # ── Page 7 ──────────────────────────────────────────────────────────
        {
            "page_number": 7,
            "profession_title": "VETERINARIAN",
            "text_template": """\
When {name} grows up with gentle care,
{he_she} might help animals everywhere.
A vet who heals with loving touch,
making sure they don't hurt much!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} in a light blue vet coat, carefully examining a fluffy "
                "golden puppy with a tiny stethoscope. A kitten and bunny watch nearby."
            )),
        },
        # ── Page 8 ──────────────────────────────────────────────────────────
        {
            "page_number": 8,
            "profession_title": "ARTIST",
            "text_template": """\
Perhaps {name} will paint and draw,
creating art that fills with awe.
With brushes, colours, and a creative mind,
making beauty of every kind!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} in a paint-splattered smock, standing at a tall wooden "
                "easel, painting a vibrant rainbow landscape. Jars of brushes and colour splashes around."
            )),
        },
        # ── Page 9 ──────────────────────────────────────────────────────────
        {
            "page_number": 9,
            "profession_title": "SCIENTIST",
            "text_template": """\
Maybe {name} will discover and explore,
finding answers and learning more.
With a lab coat and test tubes in hand,
making breakthroughs across the land!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} wearing a white lab coat and big safety goggles, "
                "holding a bubbling green test tube. A microscope and colourful beakers fill the background."
            )),
        },
        # ── Page 10 ─────────────────────────────────────────────────────────
        {
            "page_number": 10,
            "profession_title": "MUSICIAN",
            "text_template": """\
When {name} grows up making sweet sound,
{he_she} might play music all around.
With an instrument and a melody true,
bringing joy to me and you!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} playing a shiny acoustic guitar, colourful musical "
                "notes floating and dancing in the air around {name}. Warm spotlight glow."
            )),
        },
        # ── Page 11 ─────────────────────────────────────────────────────────
        {
            "page_number": 11,
            "profession_title": "MARTIAL ARTIST",
            "text_template": """\
Perhaps {name} will master karate,
disciplined and wise and smarty.
With every punch and every block,
{he_she}'ll grow in power round the clock!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} in a crisp white karate gi with a black belt, "
                "performing a powerful dynamic kick pose. Focus and determination on {name}'s face. "
                "Soft dojo background accents."
            )),
        },
        # ── Page 12 ─────────────────────────────────────────────────────────
        {
            "page_number": 12,
            "profession_title": "ATHLETE",
            "text_template": """\
Perhaps {name} will run and play,
becoming an athlete one day.
With sports and games and champion pride,
inspiring others far and wide!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} in bright athletic sportswear, mid-stride on a running "
                "track, arms pumping. Dynamic action pose with motion lines. Triumphant mood."
            )),
        },
        # ── Page 13 ─────────────────────────────────────────────────────────
        {
            "page_number": 13,
            "profession_title": "RACER",
            "text_template": """\
When {name} grows up with speed and flair,
{he_she} might race through the open air.
In a helmet, suit, and blazing car,
zooming past each shining star!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} wearing a colourful racing helmet and fireproof racing "
                "suit, sitting in a sleek low Formula-style race car cockpit. Speed lines and blurred track in the "
                "background. Exciting high-energy mood."
            )),
        },
        # ── Page 14 ─────────────────────────────────────────────────────────
        {
            "page_number": 14,
            "profession_title": "DETECTIVE",
            "text_template": """\
Maybe {name} will solve each clue,
finding answers old and new.
With a magnifying glass in hand,
solving mysteries across the land!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} wearing a classic detective trench coat and cap, "
                "holding a large magnifying glass with a thoughtful expression. Mysterious soft-lit background "
                "with floating question marks and clue cards."
            )),
        },
        # ── Page 15 ─────────────────────────────────────────────────────────
        {
            "page_number": 15,
            "profession_title": "ENGINEER",
            "text_template": """\
Maybe {name} will build and design,
creating structures that will shine.
With blueprints, tools, and clever plans,
building bridges across the lands!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} wearing a bright yellow hard hat and orange safety vest, "
                "studying a large blueprint. A model bridge and tower of colourful blocks rise behind {name}."
            )),
        },
        # ── Page 16 ─────────────────────────────────────────────────────────
        {
            "page_number": 16,
            "profession_title": "SOFTWARE ENGINEER",
            "text_template": """\
Perhaps {name} will code and create,
building apps that others await.
With a keyboard, logic, and creative mind,
solving problems of every kind!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} sitting at a glowing laptop with colourful code lines "
                "on the screen, wearing a fun tech hoodie. Floating app icons and circuit patterns in the background. "
                "Modern innovative mood."
            )),
        },
        # ── Page 17 ─────────────────────────────────────────────────────────
        {
            "page_number": 17,
            "profession_title": "PRODUCT MANAGER",
            "text_template": """\
When {name} grows up leading the way,
{he_she} might shape new products every day.
With a vision, plan, and team so great,
turning ideas into something first-rate!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} standing at a colourful whiteboard covered in sticky "
                "notes and flowcharts, pointing to a roadmap diagram with a confident smile. "
                "A small diverse team of children in the background. Creative office mood."
            )),
        },
        # ── Page 18 ─────────────────────────────────────────────────────────
        {
            "page_number": 18,
            "profession_title": "AUTOMOTIVE ENGINEER",
            "text_template": """\
Maybe {name} will design the cars,
that carry people near and far.
With engines, wheels, and clever art,
{he_she}'ll build machines with a brilliant heart!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} wearing a sleek navy engineer's jacket, standing beside "
                "a shiny futuristic electric car with the hood open showing a clean engine. Blueprints and design "
                "sketches float around. Modern automotive workshop backdrop."
            )),
        },
        # ── Page 19 ─────────────────────────────────────────────────────────
        {
            "page_number": 19,
            "profession_title": "JUDGE",
            "text_template": """\
Perhaps {name} will uphold what's right,
keeping justice shining bright.
In robes and gavel, fair and true,
making sure that justice shines through!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} wearing a black judge's robe and a small powdered wig, "
                "seated at a grand wooden bench and holding a gavel with a wise dignified expression. "
                "Soft courtroom backdrop with scales-of-justice symbol."
            )),
        },
        # ── Page 20 ─────────────────────────────────────────────────────────
        {
            "page_number": 20,
            "profession_title": "FARMER",
            "text_template": """\
Perhaps {name} will grow and tend,
fields of crops from end to end.
A farmer with a barn and land,
growing food with gentle hands!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} wearing denim overalls and a wide straw hat, "
                "holding a basket of fresh vegetables. A red barn and rolling green hills in the soft background."
            )),
        },
        # ── Page 21 ─────────────────────────────────────────────────────────
        {
            "page_number": 21,
            "profession_title": "LIBRARIAN",
            "text_template": """\
When {name} grows up loving books,
{he_she} might organise library nooks.
Helping people find stories to read,
sharing knowledge for every need!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} seated in a cosy library corner surrounded by tall "
                "colourful bookshelves, reading aloud from a large open storybook. Soft golden lamp light."
            )),
        },
        # ── Page 22 ─────────────────────────────────────────────────────────
        {
            "page_number": 22,
            "profession_title": "ZOO KEEPER",
            "text_template": """\
Maybe {name} will care for creatures great,
elephants, lions, and apes who wait.
A zoo keeper with animals to feed,
giving them everything they need!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} in khaki zoo keeper uniform, gently feeding a tall "
                "giraffe that bends down. A baby elephant and colourful parrots watch nearby. Lush green zoo habitat."
            )),
        },
        # ── Page 23 ─────────────────────────────────────────────────────────
        {
            "page_number": 23,
            "profession_title": "DANCER",
            "text_template": """\
When {name} grows up graceful and light,
{he_she} might dance both day and night.
On stages big with movements true,
inspiring audiences through and through!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} in a sparkling dance outfit, performing an elegant "
                "mid-air leap. Soft warm stage lights and sparkle trails behind the movement."
            )),
        },
        # ── Page 24 ─────────────────────────────────────────────────────────
        {
            "page_number": 24,
            "profession_title": "MARINE BIOLOGIST",
            "text_template": """\
Maybe {name} will study the sea,
learning about life swimming free.
With dolphins, whales, and fish so bright,
protecting oceans day and night!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} in a blue wetsuit and snorkel mask, surrounded by a "
                "friendly dolphin, sea turtle, and colourful coral reef. Sunlight rays pierce through crystal water."
            )),
        },
        # ── Page 25 ─────────────────────────────────────────────────────────
        {
            "page_number": 25,
            "profession_title": "PHOTOGRAPHER",
            "text_template": """\
Perhaps {name} will capture the light,
taking pictures day and night.
With a camera and an artistic eye,
preserving moments as they fly by!""",
            "image_prompt_template": _p(_R, (
                "A {age}-year-old {gender} child named {name} holding a vintage camera up to one eye, capturing a "
                "butterfly on a sunflower. Framed photos float around showing mountains, animals, and sunsets."
            )),
        },
        # ── Page 26 ─────────────────────────────────────────────────────────
        {
            "page_number": 26,
            "profession_title": "CONSTRUCTION WORKER",
            "text_template": """\
Maybe {name} will hammer and nail,
building structures without fail.
With tools and teamwork every day,
making buildings that are here to stay!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} wearing a hard hat, safety vest, and sturdy boots, "
                "holding a hammer near wooden beams of a house frame. Bright sunny construction site mood."
            )),
        },
        # ── Page 27 ─────────────────────────────────────────────────────────
        {
            "page_number": 27,
            "profession_title": "MAIL CARRIER",
            "text_template": """\
Perhaps {name} will deliver mail,
through sunshine, wind, and even hail.
Bringing letters, cards, and packages too,
connecting people just like glue!""",
            "image_prompt_template": _p(_L, (
                "A {age}-year-old {gender} child named {name} in a blue postal uniform with a cap, carrying a leather "
                "mail bag full of colourful letters, walking along a sunny neighbourhood street."
            )),
        },
        # ── Page 28 — Closing ───────────────────────────────────────────────
        {
            "page_number": 28,
            "profession_title": "THE FUTURE",
            "text_template": """\
Whatever {name} chooses to be,
we'll support {him_her} completely.
The future's bright, the world's so wide,
we'll be here, right by {his_her} side!""",
            "image_prompt_template": (
                "Semi-realistic watercolor portrait storybook illustration. "
                "White background with soft rainbow watercolor splash accents. "
                "A {age}-year-old {gender} child named {name} stands on a hilltop at golden sunrise, "
                "looking toward a bright hopeful horizon. Floating around {name} are soft glowing symbols of "
                "different careers: stethoscope, paintbrush, rocket, laptop, racing helmet, chef hat, magnifying glass. "
                "Dreamy hopeful atmosphere, endless possibilities mood. No text, no watermarks."
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def personalize_template_text(text_template: str, child_name: str, gender: str) -> str:
    pronouns = get_pronouns(gender)
    return text_template.format(
        name=child_name,
        he_she=pronouns['he_she'],
        He_She=pronouns['He_She'],
        he_she_cap=pronouns['He_She'],
        his_her=pronouns['his_her'],
        His_Her=pronouns['His_Her'],
        him_her=pronouns['him_her'],
        Him_Her=pronouns['Him_Her'],
    )


def personalize_template_image_prompt(prompt_template: str, child_name: str, gender: str, age: int) -> str:
    gender_desc = get_gender_description(gender)
    return prompt_template.format(name=child_name, gender=gender_desc, age=age)


def get_pronouns(gender: str) -> dict:
    g = gender.lower()
    if g in ('boy', 'male'):
        return {'he_she': 'he', 'He_She': 'He', 'his_her': 'his',
                'His_Her': 'His', 'him_her': 'him', 'Him_Her': 'Him'}
    elif g in ('girl', 'female'):
        return {'he_she': 'she', 'He_She': 'She', 'his_her': 'her',
                'His_Her': 'Her', 'him_her': 'her', 'Him_Her': 'Her'}
    else:
        return {'he_she': 'they', 'He_She': 'They', 'his_her': 'their',
                'His_Her': 'Their', 'him_her': 'them', 'Him_Her': 'Them'}


def get_gender_description(gender: str) -> str:
    g = gender.lower()
    if g in ('boy', 'male'):
        return 'boy'
    elif g in ('girl', 'female'):
        return 'girl'
    return 'child'
