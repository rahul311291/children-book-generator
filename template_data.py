"""
Template data for 'When {name} Grows Up' book
Contains 24 professions with text and image prompts
"""

WHEN_I_GROW_UP_TEMPLATE = {
    "name": "When {name} Grows Up",
    "description": "A 24-page personalized book featuring different professions the child might pursue when they grow up",
    "total_pages": 24,
    "pages": [
        {
            "page_number": 1,
            "profession_title": "ASTRONAUT",
            "text_template": """When {name} grows up,
{he_she} just might be,
an astronaut floating free.
Among the stars and planets bright,
exploring space both day and night!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} dressed as an astronaut in a white spacesuit with helmet, floating in space surrounded by colorful planets, stars, and galaxies, dreamy cosmic background, children's book art style, inspiring and adventurous mood"
        },
        {
            "page_number": 2,
            "profession_title": "DOCTOR",
            "text_template": """Perhaps {name} will wear a white coat,
with a stethoscope around {his_her} throat.
Helping people feel better each day,
making all the sickness go away!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a white doctor's coat and stethoscope, standing in a cheerful hospital room, holding a medical chart, warm and caring expression, children's book art style, soft colors, compassionate and professional mood"
        },
        {
            "page_number": 3,
            "profession_title": "TEACHER",
            "text_template": """Maybe {name} will teach and guide,
with wisdom, patience, and pride.
Sharing knowledge every day,
helping students find their way!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} as a teacher standing in front of a colorful classroom with a chalkboard, books, and happy students, holding a book or pointer, kind and enthusiastic expression, children's book art style, bright educational setting"
        },
        {
            "page_number": 4,
            "profession_title": "FIREFIGHTER",
            "text_template": """When {name} grows up brave and strong,
{he_she} might fight fires all day long.
With a helmet and a hose so bright,
saving people day and night!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing firefighter gear with helmet and protective coat, holding a fire hose, standing in front of a fire truck, brave and heroic expression, children's book art style, action-packed scene with warm colors"
        },
        {
            "page_number": 5,
            "profession_title": "CHEF",
            "text_template": """Perhaps {name} will cook and bake,
delicious meals and birthday cake.
With a chef's hat upon {his_her} head,
making food that's perfectly spread!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a white chef's hat and apron in a professional kitchen, surrounded by fresh ingredients, pots, and pans, mixing or cooking something delicious, joyful expression, children's book art style, warm kitchen atmosphere"
        },
        {
            "page_number": 6,
            "profession_title": "PILOT",
            "text_template": """Maybe {name} will soar and fly,
high above in the bright blue sky.
Piloting planes from here to there,
traveling everywhere with care!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} in a pilot's uniform with cap and wings badge, sitting in an airplane cockpit with controls and dials, confident smile, view of clouds through windows, children's book art style, adventurous aviation scene"
        },
        {
            "page_number": 7,
            "profession_title": "VETERINARIAN",
            "text_template": """When {name} grows up with gentle care,
{he_she} might help animals everywhere.
A vet who heals with loving touch,
making sure they don't hurt much!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a veterinarian coat, gently examining a cute puppy or kitten in a veterinary clinic, surrounded by animal toys and medical tools, caring and gentle expression, children's book art style, soft warm colors"
        },
        {
            "page_number": 8,
            "profession_title": "ARMY OFFICER",
            "text_template": """Maybe one day, {name} will guide a team,
with discipline and a noble dream.
{he_she_cap}'ll serve with honor, lead with grace,
a hero in every time and place.""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing army officer uniform with cap, standing proudly with hands behind back, military backdrop with subtle camouflage colors, determined and noble expression, children's book art style, respectful and dignified tone"
        },
        {
            "page_number": 9,
            "profession_title": "WILDLIFE CONSERVATIONIST",
            "text_template": """Perhaps {name} will protect wild lands,
helping animals with gentle hands.
{he_she_cap}'ll plant new trees and guard each stream,
keeping Earth safe like in a dream.""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} in outdoor conservation gear with hat, holding a cute wild animal (sloth, baby panda, or bird), standing in a lush forest setting, caring and protective expression, children's book art style, natural green tones and wildlife elements"
        },
        {
            "page_number": 10,
            "profession_title": "MARTIAL ARTIST",
            "text_template": """Perhaps {name} will master Karate,
disciplined and wise.
Mastering each move
with sharp, focused eyes.
With every punch, with every block,
{he_she}'ll grow in power and never stop.""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a white karate gi with black belt, in a powerful martial arts stance with fists positioned, dojo background, focused and determined expression, children's book art style, dynamic action pose with subtle motion effects"
        },
        {
            "page_number": 11,
            "profession_title": "DETECTIVE",
            "text_template": """Perhaps {name} will wear a long dark coat,
look around carefully and study a note.
No mystery too big or clue too small,
{he_she}'ll be the best detective of all!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a detective's trench coat and hat, holding a magnifying glass and examining clues, mysterious urban backdrop with vintage detective aesthetic, clever and observant expression, children's book art style, muted detective colors with warm highlights"
        },
        {
            "page_number": 12,
            "profession_title": "MAGICIAN",
            "text_template": """When {name} grows up,
{he_she} just might be,
a wizard of great mystery.
Pulling rabbits, cards that fly,
with a wand held proudly to the sky!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a magician's hat and cape with stars, holding a magic wand with sparkles and magical effects, rabbit and playing cards floating around, stage with mystical atmosphere, excited and mysterious expression, children's book art style, deep blues and magical purple tones with golden sparkles"
        },
        {
            "page_number": 13,
            "profession_title": "ARTIST",
            "text_template": """Maybe {name} will paint and draw,
creating art that all will adore.
With brushes, colors bright and true,
making masterpieces just for you!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a paint-splattered apron, holding a palette and paintbrush, standing in front of an easel with a colorful painting, art studio setting with canvases and art supplies, creative and inspired expression, children's book art style, vibrant artistic colors"
        },
        {
            "page_number": 14,
            "profession_title": "MUSICIAN",
            "text_template": """When {name} grows up with music in heart,
{he_she} might play each note like art.
With instruments and melodies sweet,
making rhythms and dancing beats!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} playing a musical instrument (guitar, piano, or violin), surrounded by musical notes floating in the air, concert or music room setting, joyful and passionate expression, children's book art style, harmonious warm colors"
        },
        {
            "page_number": 15,
            "profession_title": "SCIENTIST",
            "text_template": """Perhaps {name} will discover and explore,
finding answers and so much more.
With test tubes, microscopes in sight,
unlocking secrets day and night!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a white lab coat and safety goggles, conducting a colorful chemistry experiment in a laboratory, beakers and scientific equipment around, curious and intelligent expression, children's book art style, scientific blue and green tones with bubbling reactions"
        },
        {
            "page_number": 16,
            "profession_title": "ENGINEER",
            "text_template": """Maybe {name} will build and design,
bridges, buildings so divine.
With blueprints, tools, and creative mind,
making structures of every kind!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing a hard hat and holding blueprints or drafting tools, standing at a construction site with building structures in background, confident and innovative expression, children's book art style, architectural scene with construction equipment"
        },
        {
            "page_number": 17,
            "profession_title": "ATHLETE",
            "text_template": """When {name} grows up strong and fast,
{he_she} might be an athlete unsurpassed.
Running, jumping, playing the game,
winning medals and sporting fame!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} in athletic sportswear, in dynamic running or jumping pose on a track or sports field, medal around neck, stadium background, energetic and triumphant expression, children's book art style, active sports scene with bright athletic colors"
        },
        {
            "page_number": 18,
            "profession_title": "MARINE BIOLOGIST",
            "text_template": """Perhaps {name} will dive deep in the sea,
studying fish and coral with glee.
With ocean creatures big and small,
protecting the underwater world for all!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} in scuba diving gear with mask and snorkel, swimming underwater surrounded by colorful fish, coral reefs, dolphins, and sea turtles, underwater scene, fascinated and adventurous expression, children's book art style, oceanic blues and vibrant marine life"
        },
        {
            "page_number": 19,
            "profession_title": "FASHION DESIGNER",
            "text_template": """Maybe {name} will create and sew,
fashion styles that steal the show.
With fabrics, patterns, colors bright,
designing clothes that fit just right!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} in a stylish outfit, standing at a designer's table with fabric swatches, sketches, and a dress form, fashion studio setting with creative atmosphere, confident and artistic expression, children's book art style, fashionable colors and elegant design elements"
        },
        {
            "page_number": 20,
            "profession_title": "ARCHITECT",
            "text_template": """When {name} grows up with vision clear,
{he_she} might design buildings far and near.
Drawing plans for homes and towers tall,
creating beautiful spaces for all!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} wearing professional attire, working at a drafting table with architectural models and blueprints, modern buildings in background, thoughtful and creative expression, children's book art style, architectural scene with geometric elements"
        },
        {
            "page_number": 21,
            "profession_title": "PHOTOGRAPHER",
            "text_template": """Perhaps {name} will capture moments dear,
through a camera lens so clear.
Snapping pictures far and wide,
preserving memories with pride!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} holding a professional camera up to eye level, various beautiful scenes in background (nature, people, events), photography studio or outdoor setting, focused and artistic expression, children's book art style, photographic elements with warm natural lighting"
        },
        {
            "page_number": 22,
            "profession_title": "BUSINESS LEADER",
            "text_template": """Maybe {name} will lead with might,
making decisions wise and right.
Running companies big and small,
inspiring teams and giving their all!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} in professional business attire at a desk with laptop, charts, and office setting, confident leadership pose, modern office background, determined and professional expression, children's book art style, business environment with warm corporate colors"
        },
        {
            "page_number": 23,
            "profession_title": "WRITER",
            "text_template": """When {name} grows up with words to share,
{he_she} might write stories everywhere.
Books and poems, tales untold,
adventures new and legends old!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} sitting at a cozy writing desk with books, papers, and a pen or typewriter, surrounded by floating story characters and imaginative elements, library or study setting, thoughtful and creative expression, children's book art style, warm literary atmosphere"
        },
        {
            "page_number": 24,
            "profession_title": "DREAMER",
            "text_template": """But whatever {name} may choose to be,
{he_she}'ll do it wonderfully!
With dreams so big and heart so true,
the whole world waits for all you'll do!""",
            "image_prompt_template": "Watercolor illustration of a {age} year old {gender} child named {name} standing confidently with arms spread wide, surrounded by floating symbols of all the professions (stethoscope, paint brush, camera, rocket, books, etc.), dreamy starry sky background, hopeful and inspired expression, children's book art style, magical and inspiring scene with rainbow of colors"
        }
    ]
}


def get_pronoun(gender: str, pronoun_type: str) -> str:
    """Get appropriate pronouns based on gender."""
    gender_lower = gender.lower()

    pronouns = {
        "boy": {
            "he_she": "he",
            "he_she_cap": "He",
            "his_her": "his",
            "his_her_cap": "His",
            "him_her": "him"
        },
        "girl": {
            "he_she": "she",
            "he_she_cap": "She",
            "his_her": "her",
            "his_her_cap": "Her",
            "him_her": "her"
        },
        "male": {
            "he_she": "he",
            "he_she_cap": "He",
            "his_her": "his",
            "his_her_cap": "His",
            "him_her": "him"
        },
        "female": {
            "he_she": "she",
            "he_she_cap": "She",
            "his_her": "her",
            "his_her_cap": "Her",
            "him_her": "her"
        }
    }

    # Default to they/them for non-binary or unspecified
    default_pronouns = {
        "he_she": "they",
        "he_she_cap": "They",
        "his_her": "their",
        "his_her_cap": "Their",
        "him_her": "them"
    }

    return pronouns.get(gender_lower, default_pronouns).get(pronoun_type, default_pronouns[pronoun_type])


def personalize_template_text(text_template: str, child_name: str, gender: str, age: int) -> str:
    """Replace placeholders in template text with actual values."""
    personalized = text_template.replace("{name}", child_name)
    personalized = personalized.replace("{age}", str(age))

    # Replace pronouns
    personalized = personalized.replace("{he_she}", get_pronoun(gender, "he_she"))
    personalized = personalized.replace("{he_she_cap}", get_pronoun(gender, "he_she_cap"))
    personalized = personalized.replace("{his_her}", get_pronoun(gender, "his_her"))
    personalized = personalized.replace("{his_her_cap}", get_pronoun(gender, "his_her_cap"))
    personalized = personalized.replace("{him_her}", get_pronoun(gender, "him_her"))

    return personalized


def personalize_template_image_prompt(prompt_template: str, child_name: str, gender: str, age: int, photo_description: str = "") -> str:
    """Replace placeholders in image prompt with actual values."""
    personalized = prompt_template.replace("{name}", child_name)
    personalized = personalized.replace("{age}", str(age))
    personalized = personalized.replace("{gender}", gender.lower())

    # Add photo description if provided
    if photo_description:
        personalized = f"{personalized}. The child should look like: {photo_description}"

    return personalized
