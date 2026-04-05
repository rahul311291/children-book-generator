"""
Template-based book generator for predefined book templates
Handles "When I Grow Up" and other template-based personalized books
"""

import streamlit as st
import streamlit.components.v1
import os
import base64
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
from template_data import personalize_template_text, personalize_template_image_prompt, WHEN_I_GROW_UP_TEMPLATE
from PIL import Image
import io
import logging
import requests
import json
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER

logger = logging.getLogger(__name__)

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()


# Built-in default templates we seed into Supabase if missing
# Include the existing "When I Grow Up" template plus 4 new ones = 5 total templates
DEFAULT_TEMPLATES: List[Dict] = [
    {
        "id": "a1111111-1111-1111-1111-111111111111",
        "name": "When I Grow Up",
        "description": "A 24-page personalized book featuring different professions {name} might pursue when they grow up - astronaut, doctor, teacher, and more!",
        "cover_image": "https://images.pexels.com/photos/5560536/pexels-photo-5560536.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 24,
        "pages": [
            {
                "page_number": page["page_number"],
                "profession_title": page["profession_title"],
                "text_template": page["text_template"],
                "image_prompt_template": page["image_prompt_template"],
            }
            for page in WHEN_I_GROW_UP_TEMPLATE["pages"]
        ],
    },
    {
        "id": "a2222222-2222-2222-2222-222222222222",
        "name": "Snow White and the Kind-Hearted Child",
        "description": "A gentle Snow White retelling where {name} faces unkind sisters and a cruel stepmother, but finds courage, friends, and a kind prince.",
        "cover_image": "https://images.pexels.com/photos/8501420/pexels-photo-8501420.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Once Upon a Time",
                "text_template": (
                    "Long ago, in a peaceful kingdom surrounded by mountains and meadows, "
                    "there lived a kind child named {name}. {He_She} had two jealous sisters and a cruel stepmother "
                    "who made {him_her} do all the chores while they wore fine dresses and laughed."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} in simple "
                    "patched clothes, carrying a heavy wicker basket through a grand stone castle kitchen. Two elaborately "
                    "dressed sisters point and snicker while a stern stepmother watches from a throne-like chair. Warm "
                    "candlelight, cobblestone floor, copper pots hanging on walls. Classic storybook style, no text."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "A Heart of Kindness",
                "text_template": (
                    "Even though {name}'s sisters were unkind, {he_she} stayed gentle and brave. "
                    "Whenever they snapped at {him_her}, {name} took a deep breath and remembered that kindness "
                    "is a special kind of magic no one can take away."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} sitting "
                    "on a stone castle windowsill, smiling softly while feeding colorful songbirds from {name}'s open palm. "
                    "Morning sunlight streams through the arched window. Two sisters frown in the shadowy background. "
                    "Soft pastel colors, gentle atmosphere, classic storybook style, no text."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Into the Forest",
                "text_template": (
                    "One day, the stepmother grew so jealous of {name}'s goodness that she ordered {him_her} "
                    "to leave the castle. With tears in {his_her} eyes but courage in {his_her} heart, "
                    "{name} walked into the deep green forest, not knowing what would happen next."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} walking "
                    "along a winding path into a tall, ancient forest. Golden rays of sunlight filter through the canopy. "
                    "A rabbit peeks from behind ferns, a bluebird perches on a branch overhead. The mood shifts from "
                    "sadness to quiet hope. Rich greens, dappled light, classic storybook style, no text."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "The Little Cottage",
                "text_template": (
                    "After a long walk, {name} found a tiny, cozy cottage hidden among the trees. "
                    "Inside, everything was messy and dusty. {He_She} decided to clean and tidy the little home, "
                    "humming softly to feel less afraid."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a charming thatched-roof cottage nestled among tall "
                    "forest trees with a mushroom-lined path leading to the door. Inside, a {age}-year-old {gender} child "
                    "named {name} sweeps the wooden floor while sunlight pours through small round windows. Seven tiny "
                    "chairs, seven tiny beds, cozy hearth. Warm golden tones, classic storybook style, no text."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "New Friends",
                "text_template": (
                    "When the owners of the cottage came home -- seven kind dwarfs -- they were surprised to find their house "
                    "sparkling clean. They listened to {name}'s story and promised, 'You can stay with us. "
                    "We will be your family and keep you safe.'"
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} sitting at "
                    "a small round wooden table surrounded by seven cheerful dwarfs of different heights and personalities, "
                    "all sharing a warm meal. Cozy candlelight, wooden beams overhead, a crackling fireplace. Everyone smiles "
                    "kindly at {name}. Warm amber tones, classic storybook style, no text."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "The Poisoned Gift",
                "text_template": (
                    "Far away, the stepmother learned that {name} was still alive and happy. Disguised as an old woman, "
                    "she brought a beautiful red apple to the cottage. Trusting others, {name} took a bite -- and everything "
                    "suddenly turned dark."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a cloaked old woman with hidden eyes offers a single "
                    "gleaming red apple to a {age}-year-old {gender} child named {name} at the cottage door. The apple "
                    "glows ominously. Shadows creep at the edges while the cottage remains warm. Subtle tension, "
                    "rich deep colors, classic storybook style, no text."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "Asleep in Glass",
                "text_template": (
                    "The dwarfs were heartbroken. They gently laid {name} in a clear glass coffin on a soft hill, "
                    "surrounded by flowers. Though {name} seemed asleep, {his_her} gentle face still looked full of "
                    "hope and kindness."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a crystal glass coffin resting on a flower-covered "
                    "hilltop under a canopy of blossoming trees. A {age}-year-old {gender} child named {name} lies "
                    "peacefully inside with folded hands. Seven dwarfs weep nearby while forest animals -- deer, rabbits, "
                    "birds -- gather in a circle. Tender, bittersweet mood, soft light, classic storybook style, no text."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "The Prince Arrives",
                "text_template": (
                    "One day, a kind prince passed through the forest and saw {name}. He listened to the dwarfs and felt "
                    "deep respect for {name}'s brave heart. As the coffin was moved, the apple piece slipped from "
                    "{name}'s throat, and {he_she} woke up with a gentle gasp."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a gentle young prince on a white horse arriving at the "
                    "glass coffin on the hilltop. A {age}-year-old {gender} child named {name} begins to stir awake, "
                    "eyes fluttering open. Dwarfs look up in astonished hope, golden sunlight breaking through clouds. "
                    "Magical moment, bright hopeful colors, classic storybook style, no text."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "A New Beginning",
                "text_template": (
                    "{name} thanked the dwarfs for their love and courage. The prince said, 'I admire your kindness and strength, "
                    "{name}. Would you like to come to my castle, where people will treat you the way you deserve?'"
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} standing "
                    "between the kind prince and the seven dwarfs, holding a dwarf's hand in farewell. A winding forest "
                    "path leads to a sunlit white castle on a distant hill. Warm hopeful atmosphere, golden hour lighting, "
                    "classic storybook style, no text."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "Happily Ever After",
                "text_template": (
                    "{name} went to the prince's castle, where {he_she} was finally treated with love and respect. "
                    "{His_Her} unkind stepmother and sisters had to live with their choices, while {name}'s kindness shone "
                    "brighter than ever. From that day on, {name} knew that being gentle and brave could change {his_her} story."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a grand castle courtyard celebration with banners and "
                    "flowers. A {age}-year-old {gender} child named {name} in beautiful royal clothes stands at the center, "
                    "surrounded by the prince, the seven dwarfs visiting, and new friends all smiling. Warm golden "
                    "sunlight, joyful atmosphere, classic storybook happily-ever-after ending, no text."
                ),
            },
        ],
    },
    {
        "id": "a3333333-3333-3333-3333-333333333333",
        "name": "Cricket Champion - Mastering Every Shot",
        "description": "A coaching-style book where {name} learns 10 classic cricket shots with clear posture and body-position tips.",
        "cover_image": "https://images.pexels.com/photos/3718433/pexels-photo-3718433.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Forward Defensive",
                "text_template": (
                    "Today, {name} is learning the forward defensive shot. {He_She} stands with feet shoulder-width apart, "
                    "eyes locked on the ball, front foot stepping forward. The bat comes down straight, close to the pad, "
                    "blocking the ball safely under {his_her} steady gaze."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} in crisp white "
                    "cricket gear and blue helmet, executing a textbook forward defensive shot on a sunlit cricket ground. "
                    "Front foot planted forward, bat perfectly straight next to the front pad, head still and eyes watching "
                    "the ball. Green pitch, white crease lines, clear blue sky. Clean coaching-diagram style, no text."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Straight Drive",
                "text_template": (
                    "Next, {name} practices the straight drive. {He_She} steps forward with the front foot, keeps {his_her} head still, "
                    "and swings the bat straight down the line of the ball, sending it smoothly back past the bowler."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} in cricket whites "
                    "and helmet, executing a beautiful straight drive. Front knee bent, bat following through in a full arc "
                    "toward the sightscreen, head perfectly over the ball. The ball races along the green pitch toward the "
                    "boundary. Sunny cricket ground, clear coaching illustration, no text."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Cover Drive",
                "text_template": (
                    "For the cover drive, {name} leans into the shot. {He_She} steps toward the off side with a bent front knee "
                    "and drives the ball through the covers with a smooth arc, elbows high and head close to the line of the ball."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} playing an elegant "
                    "cover drive, front foot reaching toward off side, bat sweeping through in a graceful high arc. The ball "
                    "flies through the cover region between fielders. Beautiful side-on stance, arms extended. Lush green "
                    "cricket field, classic coaching pose, no text."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "On Drive",
                "text_template": (
                    "The on drive helps {name} play toward the leg side. {He_She} steps slightly toward mid-on, keeps the bat close "
                    "to the pad, and swings through the line of the ball with a straight face, guiding it past the bowler."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} in cricket gear "
                    "playing a controlled on drive. Front foot angled toward mid-on, bat face straight, wrists firm. Ball "
                    "glides past the bowler on the leg side. Balanced stance with weight transferred forward. Clean green "
                    "pitch, coaching-style illustration, no text."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "Pull Shot",
                "text_template": (
                    "For the pull shot, {name} waits for a short ball. {He_She} swivels on the back foot, keeps eyes level, "
                    "and swings the bat horizontally. The front shoulder turns and {name} rolls {his_her} wrists to keep the ball down."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} in cricket whites "
                    "and helmet, executing a powerful pull shot. Body rotating on the back foot, bat swinging horizontally, "
                    "front leg lifting slightly. The ball rockets toward mid-wicket. Dynamic action pose with motion energy. "
                    "Sunny cricket ground, coaching-style illustration, no text."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "Cut Shot",
                "text_template": (
                    "With the cut shot, {name} attacks a wide, short ball. {He_She} steps back and across, lets the ball come close, "
                    "then slices it square through the off side with a firm, controlled bat, keeping {his_her} head still."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} executing a crisp "
                    "square cut shot. Back foot planted across toward off stump, body opening slightly, bat slicing "
                    "horizontally through the ball toward the point boundary. Head perfectly still. Cricket field with "
                    "fielders in background, coaching-style illustration, no text."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "Sweep Shot",
                "text_template": (
                    "Against spin, {name} kneels for the sweep shot. {He_She} gets low on one knee, stretches the front leg toward "
                    "the pitch of the ball, and sweeps the bat in a smooth arc, keeping {his_her} head over the ball."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} in cricket whites "
                    "playing a classic sweep shot against a spin bowler. Front knee down on the pitch, back leg folded, "
                    "bat sweeping in a low arc in front of the body. Head leaning forward over the ball. Spinner visible "
                    "in the background. Clean coaching-style illustration, no text."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "Lofted Drive",
                "text_template": (
                    "When it is safe to hit in the air, {name} uses the lofted drive. {He_She} steps forward with a strong base "
                    "and swings the bat upward through the line, lifting the ball over the infield while still watching carefully."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} playing a confident "
                    "lofted drive. Front foot firmly planted, bat following through high above the shoulder, ball soaring "
                    "over the infield toward the boundary. Stable lower body, eyes following the ball. Blue sky, green "
                    "outfield, coaching-style illustration, no text."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "Back-Foot Defence",
                "text_template": (
                    "For the back-foot defence, {name} moves back and across toward off stump. {He_She} lets the ball bounce, "
                    "then meets it with a straight bat close to the body, using soft hands to drop the ball near {his_her} feet."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} in cricket gear "
                    "playing a solid back-foot defensive shot. Back foot planted on the crease line, bat straight and close "
                    "to the pads, ball dropping gently near the feet. Composed posture, soft hands. Cricket pitch with "
                    "stumps visible, coaching-style illustration, no text."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "Late Cut",
                "text_template": (
                    "Finally, {name} learns the late cut. {He_She} waits for the ball to arrive, then opens the bat face at the "
                    "last moment, guiding it softly past the slips toward third man with gentle hands and precise timing."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} executing a delicate "
                    "late cut shot. Bat angled with soft wrists, body slightly open, ball guided past the slip fielders "
                    "toward third man. Wicket-keeper reaching behind, slips watching. Precise timing captured in a still "
                    "moment. Cricket ground setting, coaching-style illustration, no text."
                ),
            },
        ],
    },
    {
        "id": "a4444444-4444-4444-4444-444444444444",
        "name": "Cinderella and the Brave Heart",
        "description": "A Cinderella retelling where {name} overcomes unkindness from stepfamily and finds confidence, magic, and a caring prince.",
        "cover_image": "https://images.pexels.com/photos/5560517/pexels-photo-5560517.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Life in the Kitchen",
                "text_template": (
                    "{name} lived with a sharp-tongued stepmother and two lazy stepsisters. While they bossed {him_her} around, "
                    "{name} swept floors, washed dishes, and cooked meals, keeping {his_her} gentle heart safe inside."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} in simple "
                    "worn clothes, scrubbing a large wooden table in a grand old kitchen. Two overdressed stepsisters "
                    "lounge on cushioned chairs pointing at {name}, while a stern stepmother supervises from the doorway. "
                    "Warm but melancholy firelight, stone walls, hanging herbs. Classic storybook style, no text."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Dreams by the Fireplace",
                "text_template": (
                    "At night, {name} sat by the fireplace, looking at the glowing embers and dreaming of a kinder life. "
                    "{He_She} whispered wishes into the smoke, hoping that one day, someone would see {his_her} true worth."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} sitting "
                    "curled up on a small stool beside a crackling fireplace, chin resting on knees, gazing into the "
                    "dancing orange flames. Soft embers float upward like tiny stars. An old broom and bucket rest nearby. "
                    "Warm amber glow, dreamy peaceful atmosphere, classic storybook style, no text."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Invitation to the Ball",
                "text_template": (
                    "One day, a royal invitation arrived: everyone in the kingdom was invited to a grand ball at the palace. "
                    "{name}'s stepmother dressed {his_her} sisters in fancy gowns, laughing as she told {name} that "
                    "{he_she} was far too dirty and plain to go."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a royal messenger in a plumed hat presenting a golden "
                    "scroll at the door. Two excited stepsisters twirl in half-finished ball gowns. A {age}-year-old "
                    "{gender} child named {name} stands in the background holding a simple apron, looking hopeful "
                    "but sad. Stern stepmother blocks the way. Rich colors, classic storybook style, no text."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "The Fairy Godmother",
                "text_template": (
                    "After everyone left, {name} cried in the garden. Suddenly, a warm light appeared, and a fairy godmother "
                    "smiled at {him_her}. 'Your kindness shines brighter than any dress,' she said. 'You shall go to the ball.'"
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a glowing fairy godmother in a flowing silver gown, "
                    "holding a sparkling wand, appearing in a moonlit garden before a {age}-year-old {gender} child "
                    "named {name} who looks up in wonder. A pumpkin sits on the garden path, mice peek from behind "
                    "flower pots. Magical blue and gold light radiates outward. Classic storybook style, no text."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "Magic Transformation",
                "text_template": (
                    "With a flick of her wand, the fairy turned {name}'s rags into a shimmering outfit and glass shoes that fit perfectly. "
                    "A pumpkin became a carriage, and the mice turned into horses. 'Be back by midnight,' she warned gently."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} spinning "
                    "joyfully as rags transform into a magnificent glittering outfit with glass slippers that catch the "
                    "moonlight. Behind {name}, a pumpkin morphs into a golden carriage, mice transform into elegant white "
                    "horses. Sparkles and fairy dust fill the air. Magical transformation scene, classic storybook style, no text."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "At the Ball",
                "text_template": (
                    "At the palace, everyone stared in wonder at {name}. The prince noticed {his_her} gentle smile and brave eyes. "
                    "He asked {name} to dance, and together they glided across the floor like they had always been meant to meet."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a grand palace ballroom with crystal chandeliers, marble "
                    "columns, and elegantly dressed guests. A {age}-year-old {gender} child named {name} in a magnificent "
                    "outfit dances gracefully with a kind young prince at the center of the room. Golden candlelight "
                    "reflects off the polished floor. Enchanting atmosphere, classic storybook style, no text."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "Midnight Escape",
                "text_template": (
                    "Suddenly, the great clock began to strike twelve. Remembering the fairy's warning, {name} thanked the prince and ran. "
                    "On the palace steps, one glass shoe slipped off, but there was no time to turn back."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a {age}-year-old {gender} child named {name} running "
                    "down wide marble palace stairs under a midnight sky full of stars. One sparkling glass slipper sits "
                    "on a step behind. A large clock tower in the background shows midnight. Outfit beginning to shimmer "
                    "and fade. Dramatic but child-friendly urgency, classic storybook style, no text."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "The Prince Searches",
                "text_template": (
                    "The next day, the prince searched the kingdom with the glass shoe. He tried it on many people, but it never fit. "
                    "He promised himself he would find the person whose kindness had touched his heart."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a determined young prince traveling through a village "
                    "in a horse-drawn carriage, holding up a single sparkling glass slipper on a velvet cushion. "
                    "Villagers peer out from doorways and windows. Cobblestone streets, thatched-roof cottages, bright "
                    "daytime scene. Hopeful atmosphere, classic storybook style, no text."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "The Perfect Fit",
                "text_template": (
                    "At last, the prince reached {name}'s home. The stepsisters tried to squeeze into the slipper, but it would not fit. "
                    "When {name} gently tried it on, it slid perfectly over {his_her} foot, shining like it had always belonged there."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: inside a modest room, the prince kneels to place the "
                    "glass slipper on a {age}-year-old {gender} child named {name}'s foot. The slipper glows as it fits "
                    "perfectly. Two stepsisters and the stepmother look shocked and dismayed in the background. Warm "
                    "hopeful golden light fills the room, classic storybook style, no text."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "A Strong New Life",
                "text_template": (
                    "{name} chose to leave the unkindness behind and start a new life at the palace. "
                    "With the prince and new friends, {he_she} was finally treated with love and respect. "
                    "{name} learned that {his_her} bravery and kindness were the strongest magic of all."
                ),
                "image_prompt_template": (
                    "Detailed watercolor fairy-tale illustration: a beautiful palace garden with fountains, rose bushes, "
                    "and butterflies. A {age}-year-old {gender} child named {name} in elegant royal attire walks happily "
                    "with the prince and new friends through the garden. Bright blue sky, warm sunshine, flowers in "
                    "full bloom. Peaceful, joyful fairy-tale ending, classic storybook style, no text."
                ),
            },
        ],
    },
    {
        "id": "a5555555-5555-5555-5555-555555555555",
        "name": "Sports Day Champion",
        "description": "{name} discovers ten different sports on school sports day and imagines becoming a champion in each one.",
        "cover_image": "https://images.pexels.com/photos/8035133/pexels-photo-8035133.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Sprinting Star",
                "text_template": (
                    "On sports day, {name} lines up for the sprint race. {He_She} bends slightly forward, keeps arms loose, "
                    "and focuses on the finish line. With each strong step, {name} feels faster and more confident."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a determined {age}-year-old {gender} child named {name} in "
                    "bright athletic clothes and running shoes, sprinting on a red school track. Arms pumping, knees "
                    "lifting high, hair flowing. A cheering crowd of parents and students behind a colorful 'Sports Day' "
                    "banner. Bright sunny day, dynamic motion, no text."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Football Hero",
                "text_template": (
                    "Next comes football. {name} keeps {his_her} head up, taps the ball with gentle touches, "
                    "and uses quick steps to move past defenders. A strong, clean kick sends the ball spinning toward the goal."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: an agile {age}-year-old {gender} child named {name} dribbling "
                    "a black-and-white football past two defenders on a lush green school field. Eyes focused on the ball, "
                    "legs in dynamic motion. White goalposts visible ahead, teammates cheering from the sideline. Bright "
                    "energetic atmosphere, no text."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Basketball Shooter",
                "text_template": (
                    "In basketball, {name} bends {his_her} knees, keeps elbows under the ball, and aims softly at the hoop. "
                    "With a smooth push and flick of the wrists, the ball arcs through the air toward the net."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a focused {age}-year-old {gender} child named {name} in a "
                    "basketball jersey, shooting a basketball toward an orange hoop. Knees bent, arms fully extended, "
                    "the ball at the peak of its arc. Indoor school gymnasium with polished wooden floor, colorful "
                    "bleachers, bright overhead lights, no text."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "Tennis Ace",
                "text_template": (
                    "With a tennis racket, {name} stands side-on, feet apart, eyes on the ball. {He_She} swings smoothly, "
                    "striking the ball in front of the body and following through high, sending it neatly over the net."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: an athletic {age}-year-old {gender} child named {name} on a "
                    "green tennis court, hitting a forehand with perfect form. Side-on stance, racket following through "
                    "high, tennis ball crossing the white net. Sunny outdoor court with green trees in the background. "
                    "Clean sporty atmosphere, no text."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "Swimming Dolphin",
                "text_template": (
                    "In the pool, {name} reaches arms forward, kicks with straight legs, and keeps breathing calmly to the side. "
                    "Each stroke feels smoother as {he_she} glides through the water like a fast, friendly dolphin."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a streamlined {age}-year-old {gender} child named {name} in a "
                    "swim cap and goggles, gliding through crystal-clear blue pool water in a freestyle stroke. Face "
                    "turning to the side to breathe, water splashing gently. Lane lines and pool tiles visible. Bright "
                    "indoor pool lighting, refreshing atmosphere, no text."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "Gymnast on the Beam",
                "text_template": (
                    "On the balance beam, {name} places one foot carefully in front of the other, arms stretched out wide. "
                    "Slow, steady breaths help {him_her} stay calm as {he_she} takes graceful steps across."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a graceful {age}-year-old {gender} child named {name} in a "
                    "gymnastics leotard, walking along a balance beam with arms extended for balance. Focused determined "
                    "expression. Safety mats below, a supportive coach watching nearby. Bright gym with colorful "
                    "equipment in background, no text."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "Badminton Flyer",
                "text_template": (
                    "With a badminton racket, {name} watches the shuttle closely. {He_She} moves light on {his_her} feet, "
                    "jumps for a high shot, and swings the racket with a quick snap to send the shuttle back over the net."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a nimble {age}-year-old {gender} child named {name} leaping "
                    "to smash a badminton shuttlecock, racket arm stretched high overhead. Indoor court with a white "
                    "net, court lines on the floor, and a competitor on the other side. Athletic jump captured mid-air. "
                    "Bright indoor lighting, dynamic action, no text."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "Hockey Warrior",
                "text_template": (
                    "In hockey, {name} bends knees, keeps the stick low, and uses quick pushes to guide the ball. "
                    "Strong legs and sharp eyes help {him_her} move down the field like a true team warrior."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} in a hockey "
                    "uniform with shin guards, crouching low and dribbling a ball with a hockey stick on a green turf "
                    "field. Teammates run alongside in matching jerseys. School field with goal cage visible. "
                    "Determined teamwork atmosphere, no text."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "Long Jump Flyer",
                "text_template": (
                    "For long jump, {name} runs with powerful steps, then plants one foot on the board and swings arms forward. "
                    "{He_She} lifts off the ground, flying through the air before landing softly in the sand."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a {age}-year-old {gender} child named {name} captured mid-flight "
                    "in a long jump, legs tucked forward, arms reaching ahead. A sand pit stretches below, a white "
                    "takeoff board visible behind. Outdoor school track with spectators clapping. Sense of weightless "
                    "flight and freedom, no text."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "All-Round Champion",
                "text_template": (
                    "At the end of sports day, {name} feels tired but proud. {He_She} has tried running, football, basketball, "
                    "tennis, swimming, gymnastics, badminton, hockey, and long jump. With practice and heart, "
                    "{name} knows {he_she} can become a champion in any sport {he_she} loves."
                ),
                "image_prompt_template": (
                    "Detailed children's book illustration: a proud {age}-year-old {gender} child named {name} standing "
                    "on a winners' podium wearing a shiny gold medal on a ribbon, arms raised in celebration. Scattered "
                    "around the podium are a football, tennis racket, basketball, hockey stick, swim goggles, and "
                    "badminton shuttlecock. Friends and family cheer, colorful confetti falls. Triumphant celebratory "
                    "mood, bright storybook style, no text."
                ),
            },
        ],
    },
]


def init_supabase() -> Client:
    """Initialize Supabase client."""
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_SUPABASE_ANON_KEY")

    if not supabase_url:
        supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_key:
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

    if not supabase_url or not supabase_key:
        try:
            supabase_url = st.secrets.get("VITE_SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
            supabase_key = st.secrets.get("VITE_SUPABASE_ANON_KEY") or st.secrets.get("SUPABASE_ANON_KEY")
        except Exception:
            pass

    if not supabase_url or not supabase_key:
        error_msg = f"Supabase credentials not found. URL: {'found' if supabase_url else 'missing'}, Key: {'found' if supabase_key else 'missing'}"
        logger.error(error_msg)
        raise Exception(error_msg)

    return create_client(supabase_url, supabase_key)


def seed_default_templates_if_missing(supabase: Client, show_errors_in_ui: bool = False) -> None:
    """Ensure our built-in templates exist in Supabase without overwriting user content."""
    try:
        logger.info(f"Seeding {len(DEFAULT_TEMPLATES)} default templates into Supabase...")
        seeded_count = 0
        errors = []
        
        for idx, tmpl in enumerate(DEFAULT_TEMPLATES):
            name = tmpl["name"]
            try:
                logger.info(f"Processing template {idx+1}/{len(DEFAULT_TEMPLATES)}: '{name}'")
                
                # Find or create template row by name
                existing = supabase.table("templates").select("id").eq("name", name).execute()
                if existing.data:
                    template_id = existing.data[0]["id"]
                    logger.info(f"Template '{name}' already exists (ID: {template_id})")
                else:
                    logger.info(f"Creating new template '{name}'...")
                    try:
                        # Generate UUID for id if Supabase table requires it (some tables don't auto-generate)
                        insert_data = {
                            "id": str(uuid.uuid4()),  # Generate UUID for the id column
                            "name": name,
                            "description": tmpl.get("description", ""),
                            "total_pages": tmpl.get("total_pages", len(tmpl.get("pages", []))),
                            "cover_image": tmpl.get("cover_image", ""),
                        }
                        # If template already has an id, use it instead
                        if "id" in tmpl and tmpl["id"]:
                            insert_data["id"] = tmpl["id"]
                        
                        insert_resp = supabase.table("templates").insert(insert_data).execute()
                        if not insert_resp.data:
                            error_msg = f"Failed to insert template '{name}' - no data returned from Supabase"
                            logger.error(error_msg)
                            errors.append(error_msg)
                            if show_errors_in_ui:
                                st.error(error_msg)
                            continue
                        template_id = insert_resp.data[0]["id"]
                        logger.info(f"✅ Created new template '{name}' (ID: {template_id})")
                        if show_errors_in_ui:
                            st.success(f"✅ Created template: {name}")
                        seeded_count += 1
                    except Exception as insert_error:
                        error_msg = f"Failed to insert template '{name}': {str(insert_error)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        if show_errors_in_ui:
                            st.error(error_msg)
                        import traceback
                        logger.error(traceback.format_exc())
                        continue

                # Only insert pages if none exist yet for this template_id
                pages_existing = supabase.table("template_pages").select("id").eq("template_id", template_id).limit(1).execute()
                if pages_existing.data:
                    logger.info(f"Template '{name}' already has pages, skipping page insertion")
                    continue

                # Prepare pages payload
                pages_payload = []
                for page in tmpl.get("pages", []):
                    page_data = {
                        "id": str(uuid.uuid4()),  # Generate UUID for each page id
                        "template_id": template_id,
                        "page_number": page["page_number"],
                        "profession_title": page["profession_title"],
                        "text_template": page["text_template"],
                        "image_prompt_template": page["image_prompt_template"],
                    }
                    # If page already has an id, use it instead
                    if "id" in page and page["id"]:
                        page_data["id"] = page["id"]
                    pages_payload.append(page_data)
                
                if pages_payload:
                    logger.info(f"Inserting {len(pages_payload)} pages for template '{name}'...")
                    try:
                        page_insert = supabase.table("template_pages").insert(pages_payload).execute()
                        if page_insert.data:
                            logger.info(f"✅ Inserted {len(pages_payload)} pages for template '{name}'")
                            if show_errors_in_ui:
                                st.success(f"✅ Inserted {len(pages_payload)} pages for {name}")
                        else:
                            error_msg = f"Failed to insert pages for template '{name}' - no data returned"
                            logger.error(error_msg)
                            errors.append(error_msg)
                            if show_errors_in_ui:
                                st.error(error_msg)
                    except Exception as page_error:
                        error_msg = f"Failed to insert pages for template '{name}': {str(page_error)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        if show_errors_in_ui:
                            st.error(error_msg)
                        import traceback
                        logger.error(traceback.format_exc())
                else:
                    logger.warning(f"No pages to insert for template '{name}'")
                    
            except Exception as e:
                error_msg = f"Error seeding template '{name}': {str(e)}"
                logger.error(error_msg)
                import traceback
                logger.error(traceback.format_exc())
                errors.append(error_msg)
        
        logger.info(f"Template seeding complete. Created {seeded_count} new templates out of {len(DEFAULT_TEMPLATES)}.")
        if errors:
            logger.error(f"Encountered {len(errors)} errors during seeding:")
            for err in errors:
                logger.error(f"  - {err}")
                
    except Exception as e:
        error_msg = f"Critical error in seed_default_templates_if_missing: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        raise  # Re-raise to surface the error


def get_available_templates() -> List[Dict]:
    """Fetch all available templates from database (seeded via SQL migration)."""
    try:
        supabase = init_supabase()
        response = supabase.table("templates").select("*").execute()
        templates = response.data or []
        logger.info(f"Retrieved {len(templates)} templates from Supabase")
        return templates
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
        import traceback
        logger.error(traceback.format_exc())
        st.error(f"Failed to load templates: {e}")
        return []


def get_template_pages(template_id: str) -> List[Dict]:
    """Fetch all pages for a specific template."""
    try:
        supabase = init_supabase()
        response = supabase.table("template_pages").select("*").eq("template_id", template_id).order("page_number").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching template pages: {e}")
        st.error(f"Failed to load template pages: {e}")
        return []


def render_template_book_form():
    """Render the form for template book creation."""
    st.header("📖 Create Your Personalized Template Book")

    # Check if user wants to start fresh (no template selected yet but has generated book)
    if st.session_state.get("template_generated_book") and not st.session_state.get("selected_template_id"):
        # User navigated back to template selection, clear generated book
        for key in list(st.session_state.keys()):
            if key in ("template_generated_book", "template_book_data", "generate_template_book") or key.startswith("template_page_text_") or key == "regenerate_template_page_idx":
                del st.session_state[key]

    templates = get_available_templates()

    # Debug section to help troubleshoot
    with st.expander("🔧 Debug: Template Status", expanded=False):
        st.write(f"**Templates found:** {len(templates)}")
        if templates:
            for t in templates:
                st.write(f"- {t.get('name', 'Unknown')} (ID: {t.get('id', 'N/A')}, Pages: {t.get('total_pages', 'N/A')})")
        else:
            st.error("No templates found! Check Supabase connection and seeding logs.")
        st.caption("Expected: 5 templates (When I Grow Up, Snow White, Cricket, Cinderella, Sports Day)")
        
        # Manual seed button
        st.markdown("---")
        if st.button("🔄 Force Reseed Templates", help="Manually trigger template seeding into Supabase", type="primary"):
            try:
                supabase = init_supabase()
                with st.spinner("Seeding templates into Supabase..."):
                    seed_default_templates_if_missing(supabase, show_errors_in_ui=True)
                st.success("✅ Seeding complete! Check the messages above for details.")
                st.info("💡 Refresh the page or check Supabase Dashboard to see the templates.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Seeding failed: {str(e)}")
                import traceback
                with st.expander("Full Error Details"):
                    st.code(traceback.format_exc())
                st.warning("💡 Common issues: Check Supabase RLS policies, API keys, and table permissions.")

    if not templates:
        st.warning("No templates available. Please contact support.")
        st.info("💡 Check the Debug section above for details. You may need to manually seed templates in Supabase.")
        return

    st.markdown("### Choose a template")
    st.caption(f"Select from {len(templates)} available templates below:")

    # Template cards grid - use 3 columns for better layout
    if "selected_template_id" not in st.session_state:
        st.session_state.selected_template_id = None
        st.session_state.selected_template_name = None

    # Display templates in a grid (3 columns, wraps to next row)
    num_cols = 3
    for row_start in range(0, len(templates), num_cols):
        cols = st.columns(num_cols)
        for col_idx, col in enumerate(cols):
            idx = row_start + col_idx
            if idx < len(templates):
                tmpl = templates[idx]
                with col:
                    # Card-like container with border
                    st.markdown(
                        f"""
                        <div style="
                            border: 2px solid #e0e0e0;
                            border-radius: 10px;
                            padding: 15px;
                            margin-bottom: 15px;
                            background-color: {'#f0f8ff' if st.session_state.selected_template_id == tmpl.get('id') else '#ffffff'};
                        ">
                        """,
                        unsafe_allow_html=True,
                    )

                    # Display cover image if available
                    cover_img = tmpl.get("cover_image", "")
                    if cover_img:
                        st.image(cover_img, use_container_width=True)

                    st.markdown(f"#### {tmpl.get('name', 'Template')}")
                    desc = tmpl.get("description", "")
                    # Truncate long descriptions
                    if len(desc) > 100:
                        desc = desc[:97] + "..."
                    st.caption(desc)
                    total_pages = tmpl.get("total_pages") or tmpl.get("page_count") or 0
                    if total_pages:
                        st.markdown(f"📄 **{total_pages} pages**")
                    if st.button(
                        "✨ Use This Template",
                        key=f"use_template_{tmpl.get('id')}",
                        use_container_width=True,
                        type="primary" if st.session_state.selected_template_id == tmpl.get("id") else "secondary",
                    ):
                        st.session_state.selected_template_id = tmpl.get("id")
                        st.session_state.selected_template_name = tmpl.get("name")
                        st.session_state.scroll_to_details = True
                        st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

    if not st.session_state.selected_template_id:
        st.info("👆 Select a template above to continue creating your personalized book.")
        return

    selected_template_id = st.session_state.selected_template_id
    selected_template_name = st.session_state.selected_template_name
    template_info = next((t for t in templates if t["id"] == selected_template_id), None)

    if template_info:
        st.markdown("---")
        st.info(f"📚 **{template_info['name']}** – {template_info.get('description', '')}")
        st.caption(f"This template includes {template_info.get('total_pages', 'multiple')} pages")

    # Auto-scroll to details section when template is selected
    if st.session_state.get("scroll_to_details"):
        st.session_state.scroll_to_details = False
        st.markdown('<div id="details-section"></div>', unsafe_allow_html=True)
        st.components.v1.html(
            """
            <script>
                setTimeout(function() {
                    const element = window.parent.document.getElementById('details-section');
                    if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }, 100);
            </script>
            """,
            height=0
        )

    st.markdown("---")
    st.markdown("### Personalize your book")

    col1, col2 = st.columns(2)

    with col1:
        child_name = st.text_input(
            "Child's Name *",
            placeholder="e.g., Emma, Jack, Alex",
            help="The child's name that will appear throughout the book"
        )

        gender = st.selectbox(
            "Gender *",
            options=["Boy", "Girl", "Neutral"],
            help="This affects pronouns used in the story (he/she/they)"
        )

    with col2:
        age = st.number_input(
            "Child's Age *",
            min_value=1,
            max_value=12,
            value=5,
            help="The child's age helps personalize the imagery"
        )

    st.markdown("### Upload Photos (Optional)")
    st.caption("Upload 1-3 photos of the child to personalize select pages")

    photo_cols = st.columns(3)

    photos = []
    for i, col in enumerate(photo_cols):
        with col:
            uploaded_file = st.file_uploader(
                f"Photo {i + 1}",
                type=['png', 'jpg', 'jpeg'],
                key=f"template_photo_{i}"
            )
            if uploaded_file:
                photos.append(uploaded_file)
                st.image(uploaded_file, caption=f"Photo {i + 1}", use_container_width=True)

    st.markdown("---")

    if st.button("✨ Generate Template Book", type="primary", use_container_width=True):
        if not child_name:
            st.error("⚠️ Please enter the child's name")
            return

        with st.spinner("Creating your personalized book..."):
            st.session_state.template_book_data = {
                'template_id': selected_template_id,
                'template_name': selected_template_name,
                'child_name': child_name,
                'gender': gender,
                'age': age,
                'photos': photos
            }
            st.session_state.generate_template_book = True
            st.rerun()


def generate_template_book(api_key: str, book_data: Dict):
    """Generate a complete template book with AI-generated images."""
    try:
        template_id = book_data['template_id']
        child_name = book_data['child_name']
        gender = book_data['gender']
        age = book_data['age']
        photos = book_data.get('photos', [])

        pages = get_template_pages(template_id)

        if not pages:
            st.error("No pages found for this template")
            return

        reference_image_base64 = None
        if photos:
            reference_image_base64 = convert_uploaded_file_to_base64(photos[0])

        generated_book = {
            'template_id': template_id,
            'template_name': book_data['template_name'],
            'child_name': child_name,
            'gender': gender,
            'age': age,
            'reference_image_base64': reference_image_base64,  # for regenerate image in preview
            'pages': []
        }

        progress_bar = st.progress(0)
        status_text = st.empty()

        total_pages = len(pages)

        for idx, page in enumerate(pages):
            status_text.text(f"Generating page {idx + 1} of {total_pages}: {page['profession_title']}")

            personalized_text = personalize_template_text(
                page['text_template'],
                child_name,
                gender
            )

            personalized_image_prompt = personalize_template_image_prompt(
                page['image_prompt_template'],
                child_name,
                gender,
                age
            )

            image_url = generate_page_image(
                api_key,
                personalized_image_prompt,
                reference_image_base64
            )

            generated_book['pages'].append({
                'page_number': page['page_number'],
                'profession_title': page['profession_title'],
                'text': personalized_text,
                'image_prompt': personalized_image_prompt,
                'image_url': image_url
            })

            progress_bar.progress((idx + 1) / total_pages)

        status_text.text("✅ Book generation complete!")

        st.session_state.template_generated_book = generated_book

    except Exception as e:
        logger.error(f"Error generating template book: {e}")
        st.error(f"Failed to generate book: {e}")


def _template_page_image_to_pil(page: Dict) -> Optional[Image.Image]:
    """Convert template page image_url (data URL or URL) to PIL Image, or None if missing/failed."""
    url = page.get("image_url")
    if not url:
        return None
    try:
        if url.startswith("data:image"):
            # data:image/png;base64,...
            b64 = url.split(",", 1)[-1]
            raw = base64.b64decode(b64)
            return Image.open(io.BytesIO(raw)).convert("RGB")
        return None
    except Exception as e:
        logger.warning(f"Could not decode template page image: {e}")
        return None


def create_template_pdf(book_data: Dict, output_path_or_buffer):
    """Create PDF from template book (same layout as main create_pdf: 8.5x8.5, dedication, image+text per page).

    Special handling for Cricket template: separate pages for image and text with themed background.
    """
    page_width = 8.5 * inch
    page_height = 8.5 * inch
    c = canvas.Canvas(output_path_or_buffer, pagesize=(page_width, page_height))
    styles = getSampleStyleSheet()
    text_style = ParagraphStyle(
        "CustomText",
        parent=styles["BodyText"],
        fontSize=18,
        textColor="black",
        alignment=TA_CENTER,
        leading=24,
    )
    child_name = book_data.get("child_name", "Child")
    pages = book_data.get("pages", [])
    template_id = book_data.get("template_id", "")

    # Check if this is the Cricket template
    is_cricket_template = template_id == "a3333333-3333-3333-3333-333333333333"

    # Dedication page
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(page_width / 2, page_height / 2 + 50, "This book belongs to")
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(page_width / 2, page_height / 2 - 20, child_name)
    c.showPage()

    for page in pages:
        img_pil = _template_page_image_to_pil(page)
        if img_pil is None:
            img_pil = Image.new("RGB", (512, 512), color=(220, 220, 220))

        if is_cricket_template:
            # Cricket template: separate pages for image and text

            # PAGE 1: Full-page image
            content_width = page_width * 0.95
            content_height = page_height * 0.95
            margin = page_width * 0.025

            img_width, img_height = img_pil.size
            aspect_ratio = img_width / img_height

            if aspect_ratio > 1:
                display_width = content_width
                display_height = display_width / aspect_ratio
                if display_height > content_height:
                    display_height = content_height
                    display_width = display_height * aspect_ratio
            else:
                display_height = content_height
                display_width = display_height * aspect_ratio
                if display_width > content_width:
                    display_width = content_width
                    display_height = display_width / aspect_ratio

            image_x_offset = (page_width - display_width) / 2
            image_y_offset = (page_height - display_height) / 2

            img_resized = img_pil.resize((int(display_width), int(display_height)), Image.Resampling.LANCZOS)
            img_io = io.BytesIO()
            img_resized.save(img_io, format="PNG")
            img_io.seek(0)
            c.drawImage(ImageReader(img_io), image_x_offset, image_y_offset, width=display_width, height=display_height, preserveAspectRatio=True)
            c.showPage()

            # PAGE 2: Text with cricket-themed background
            from reportlab.lib.colors import HexColor
            bg_color = HexColor("#E8F5E9")
            c.setFillColor(bg_color)
            c.rect(0, 0, page_width, page_height, fill=True, stroke=False)

            text = page.get("text", "")
            text_width = page_width * 0.85
            text_x_offset = (page_width - text_width) / 2

            base_font_size = 22
            min_font_size = 16
            leading_multiplier = 1.5

            text_style_cricket = ParagraphStyle(
                "CricketText",
                parent=styles["BodyText"],
                fontSize=base_font_size,
                textColor="black",
                alignment=TA_CENTER,
                leading=base_font_size * leading_multiplier,
                spaceAfter=20,
                spaceBefore=20,
            )

            para = Paragraph(text, text_style_cricket)
            available_height = page_height * 0.8
            para_width, para_height = para.wrap(text_width, available_height)

            if para_height > available_height:
                base_font_size = max(min_font_size, base_font_size * 0.85)
                text_style_cricket = ParagraphStyle(
                    "CricketText",
                    parent=styles["BodyText"],
                    fontSize=base_font_size,
                    textColor="black",
                    alignment=TA_CENTER,
                    leading=base_font_size * leading_multiplier,
                )
                para = Paragraph(text, text_style_cricket)
                para_width, para_height = para.wrap(text_width, available_height)

            text_y = (page_height - para_height) / 2
            para.drawOn(c, text_x_offset, text_y)
            c.showPage()

        else:
            # Standard layout: image + text on same page
            top_margin = page_height * 0.05
            image_area_height = page_height * 0.85
            text_area_height = page_height * 0.10
            content_width = page_width - 40
            image_y_start = page_height - top_margin - image_area_height
            image_available_height = image_area_height
            img_width, img_height = img_pil.size
            aspect_ratio = img_width / img_height
            if aspect_ratio > 1:
                display_width = content_width
                display_height = display_width / aspect_ratio
                if display_height > image_available_height:
                    display_height = image_available_height
                    display_width = display_height * aspect_ratio
            else:
                display_height = image_available_height
                display_width = display_height * aspect_ratio
                if display_width > content_width:
                    display_width = content_width
                    display_height = display_width / aspect_ratio
            image_x_offset = (page_width - display_width) / 2
            image_y_offset = image_y_start + (image_available_height - display_height) / 2
            img_resized = img_pil.resize((int(display_width), int(display_height)), Image.Resampling.LANCZOS)
            img_io = io.BytesIO()
            img_resized.save(img_io, format="PNG")
            img_io.seek(0)
            c.drawImage(ImageReader(img_io), image_x_offset, image_y_offset, width=display_width, height=display_height, preserveAspectRatio=True)
            text = page.get("text", "")
            text_width = display_width * 0.95
            text_x_offset = image_x_offset + (display_width - text_width) / 2
            base_font_size = 18
            min_font_size = 12
            char_per_line_estimate = max(1, int(text_width / (base_font_size * 0.6)))
            estimated_lines = max(1, len(text) / char_per_line_estimate)
            font_size = max(min_font_size, base_font_size - (estimated_lines - 3) * 1.5) if estimated_lines > 3 else base_font_size
            dynamic_style = ParagraphStyle("DynamicText", parent=text_style, fontSize=font_size, textColor="black", alignment=TA_CENTER, leading=font_size * 1.3)
            para = Paragraph(text, dynamic_style)
            para_height = para.wrap(text_width, text_area_height)[1]
            if para_height > text_area_height * 0.95:
                font_size = max(min_font_size, font_size * 0.85)
                dynamic_style = ParagraphStyle("DynamicText", parent=text_style, fontSize=font_size, textColor="black", alignment=TA_CENTER, leading=font_size * 1.3)
                para = Paragraph(text, dynamic_style)
                para_height = para.wrap(text_width, text_area_height)[1]
            text_y = (text_area_height - para_height) / 2
            para.drawOn(c, text_x_offset, text_y)
            c.showPage()
    c.save()


def convert_uploaded_file_to_base64(uploaded_file) -> str:
    """Convert Streamlit uploaded file to base64 string."""
    try:
        bytes_data = uploaded_file.getvalue()
        return base64.b64encode(bytes_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error converting file to base64: {e}")
        return None


def generate_page_image(api_key: str, prompt: str, reference_image_base64: Optional[str] = None) -> Optional[str]:
    """Generate a single image using Gemini API with optional reference image."""
    try:
        # Use the correct Gemini image generation endpoint
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

        headers = {
            "Content-Type": "application/json"
        }

        # Add no-text guardrail to prompt
        no_text_instruction = "CRITICAL: NO TEXT in this image. No words, letters, numbers, speech bubbles, captions, signs, or labels. Pure illustration only."
        style_modifiers = "Watercolor illustration style, soft edges, gentle colors, children's book art, high quality"
        
        enhanced_prompt = f"{no_text_instruction}. {prompt}. {style_modifiers}. {no_text_instruction}"

        # Build the payload - with or without reference image
        if reference_image_base64:
            # Include reference image for face matching
            payload = {
                "contents": [{
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": reference_image_base64
                            }
                        },
                        {
                            "text": f"{enhanced_prompt}. Make the child look exactly like the person in the reference photo - same facial features, skin tone, and hair."
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "topK": 32,
                    "topP": 1,
                    "imageConfig": {
                        "aspectRatio": "1:1",
                        "imageSize": "2K"
                    }
                }
            }
        else:
            # No reference image
            payload = {
                "contents": [{
                    "parts": [{
                        "text": enhanced_prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.4,
                    "topK": 32,
                    "topP": 1,
                    "imageConfig": {
                        "aspectRatio": "1:1",
                        "imageSize": "2K"
                    }
                }
            }

        params = {"key": api_key}

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            params=params,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            
            # Extract image from Gemini response format
            if "candidates" in result and len(result["candidates"]) > 0:
                parts = result["candidates"][0].get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        image_data = part["inlineData"]["data"]
                        return f"data:image/png;base64,{image_data}"

        logger.warning(f"Image generation failed with status {response.status_code}: {response.text[:500] if response.text else 'No error message'}")
        return None

    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None


def display_template_book_preview(book_data: Dict, api_key: Optional[str] = None):
    """Display the generated template book for preview with edit, regenerate, and download."""
    # Handle single-page image regeneration (must run before rendering so updated image shows)
    if api_key and st.session_state.get("regenerate_template_page_idx") is not None:
        idx = st.session_state.regenerate_template_page_idx
        st.session_state.regenerate_template_page_idx = None
        pages = book_data.get("pages", [])
        if 0 <= idx < len(pages):
            page = pages[idx]
            ref_b64 = book_data.get("reference_image_base64")
            new_url = generate_page_image(api_key, page.get("image_prompt", ""), ref_b64)
            if new_url:
                book_data["pages"][idx]["image_url"] = new_url
            else:
                st.error(f"Failed to regenerate image for page {idx + 1}. Please try again.")

    st.success(f"✨ Your personalized book for **{book_data['child_name']}** is ready!")

    st.markdown("---")
    st.markdown("### 📖 Book Preview (edit text or regenerate any image)")

    for idx, page in enumerate(book_data["pages"]):
        with st.container():
            st.markdown(f"#### Page {page['page_number']}: {page['profession_title']}")

            col1, col2 = st.columns([1, 1])

            with col1:
                if page.get("image_url"):
                    try:
                        if page["image_url"].startswith("data:image"):
                            image_data = page["image_url"].split(",", 1)[1]
                            image_bytes = base64.b64decode(image_data)
                            st.image(image_bytes, use_container_width=True)
                        else:
                            st.image(page["image_url"], use_container_width=True)
                    except Exception as e:
                        st.error(f"Failed to display image: {e}")
                else:
                    st.info("Image generation in progress or failed")
                # Regenerate image for this page
                if api_key and st.button("🔄 Regenerate this image", key=f"regen_tpl_img_{idx}", use_container_width=True):
                    st.session_state.regenerate_template_page_idx = idx
                    st.rerun()

            with col2:
                st.markdown("**Story text (editable):**")
                # Editable text: sync widget value back to book_data so PDF/JSON use latest
                key_edit = f"template_page_text_{idx}"
                if key_edit not in st.session_state:
                    st.session_state[key_edit] = page.get("text", "")
                current_text = st.text_area(
                    "Edit page text",
                    value=st.session_state[key_edit],
                    height=120,
                    key=f"template_text_area_{idx}",
                    label_visibility="collapsed",
                )
                st.session_state[key_edit] = current_text
                book_data["pages"][idx]["text"] = current_text

            st.markdown("---")

    # Prominent download section at the end
    st.markdown("---")
    st.markdown("### 📥 Download your book")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        buf = io.BytesIO()
        create_template_pdf(book_data, buf)
        pdf_bytes = buf.getvalue()
        st.download_button(
            label="📥 Download PDF",
            data=pdf_bytes,
            file_name=f"book-template-{ts}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
            key="template_download_pdf",
        )
    except Exception as e:
        logger.exception("Template PDF download failed")
        st.error(f"Download failed: {e}")

    col_json, col_another = st.columns(2)
    with col_json:
        try:
            json_str = json.dumps(book_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="📥 Download JSON",
                data=json_str,
                file_name=f"book-template-{ts}.json",
                mime="application/json",
                type="secondary",
                use_container_width=True,
                key="template_download_json",
            )
        except Exception as e:
            st.error(f"JSON download failed: {e}")
    with col_another:
        if st.button("🔄 Create Another Book", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key in ("template_generated_book", "template_book_data", "generate_template_book") or key.startswith("template_page_text_") or key == "regenerate_template_page_idx":
                    del st.session_state[key]
            st.rerun()
