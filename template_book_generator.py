"""
Template-based book generator for predefined book templates
Handles "When I Grow Up" and other template-based personalized books
"""

import streamlit as st
import os
import base64
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
from template_data import personalize_template_text, personalize_template_image_prompt
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
DEFAULT_TEMPLATES: List[Dict] = [
    {
        "name": "Snow White and the Kind-Hearted Child",
        "description": "A gentle Snow White retelling where {name} faces unkind sisters and a cruel stepmother, but finds courage, friends, and a kind prince.",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Once Upon a Time",
                "text_template": (
                    "Long ago, in a peaceful kingdom, there lived a kind child named {name}. "
                    "{He_She} had two jealous sisters and a cruel stepmother who treated {him_her} badly, "
                    "making {him_her} do all the chores while they rested and laughed."
                ),
                "image_prompt_template": (
                    "Watercolor illustration of a {age} year old {gender} child named {name} in simple clothes, "
                    "carrying a heavy basket in a grand castle kitchen while two fancy-dressed sisters and a stern stepmother "
                    "point and whisper, warm fairy-tale lighting, cozy storybook style."
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
                    "{age} year old {gender} child {name} smiling softly while feeding birds at a castle window, "
                    "two sisters frowning in the background, soft pastel colors, classic fairy-tale illustration, "
                    "focus on {name}'s kind expression."
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
                    "{age} year old {gender} child {name} walking into a tall green forest with rays of sunlight "
                    "shining through the trees, small animals peeking out curiously, storybook watercolor style, "
                    "mood of sadness turning to quiet hope."
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
                    "Small cottage interior in the forest, {age} year old {gender} child {name} sweeping the floor, "
                    "washing dishes, and opening windows, warm golden light coming in, seven tiny chairs and beds, "
                    "classic fairy-tale illustration."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "New Friends",
                "text_template": (
                    "When the owners of the cottage came home—seven kind dwarfs—they were surprised to find their house "
                    "sparkling clean. They listened to {name}'s story and promised, 'You can stay with us. "
                    "We will be your family and keep you safe.'"
                ),
                "image_prompt_template": (
                    "{age} year old {gender} child {name} sitting at a small wooden table with seven friendly dwarfs, "
                    "all smiling kindly, cozy candlelight, wooden cottage interior, storybook watercolor style."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "The Poisoned Gift",
                "text_template": (
                    "Far away, the stepmother learned that {name} was still alive and happy. Disguised as an old woman, "
                    "she brought a beautiful red apple to the cottage. Trusting others, {name} took a bite—and everything "
                    "suddenly turned dark."
                ),
                "image_prompt_template": (
                    "An old woman in a cloak handing a shiny red apple to {age} year old {gender} child {name} "
                    "at the cottage door, subtle hint of danger in the shadows, rich colors, classic fairy-tale mood."
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
                    "Glass coffin on a flowery hill, {age} year old {gender} child {name} lying peacefully inside "
                    "with folded hands, seven dwarfs weeping nearby, forest animals gathered around, tender fairy-tale scene."
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
                    "Gentle prince on horseback near the glass coffin, {age} year old {gender} child {name} beginning to wake, "
                    "dwarfs looking surprised and hopeful, bright forest clearing, romantic but child-friendly style."
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
                    "{age} year old {gender} child {name} standing beside the prince, holding hands with a dwarf in farewell, "
                    "forest path leading to a bright castle in the distance, hopeful storybook illustration."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "Happily Ever After",
                "text_template": (
                    "{name} went to the prince’s castle, where {he_she} was finally treated with love and respect. "
                    "{His_Her} unkind stepmother and sisters had to live with their choices, while {name}'s kindness shone "
                    "brighter than ever. From that day on, {name} knew that being gentle and brave could change {his_her} story."
                ),
                "image_prompt_template": (
                    "Grand castle hall celebration, {age} year old {gender} child {name} dressed in royal clothes, "
                    "smiling with the prince and new friends, warm golden light, joyful fairy-tale ending illustration."
                ),
            },
        ],
    },
    {
        "name": "Cricket Champion – Mastering Every Shot",
        "description": "A coaching-style book where {name} learns 10 classic cricket shots with clear posture and body-position tips.",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Forward Defensive",
                "text_template": (
                    "Today, {name} is learning the forward defensive shot. {He_She} stands with feet shoulder-width apart, "
                    "eyes on the ball, front foot stepping forward. The bat comes down straight, close to the pad, "
                    "blocking the ball safely under {his_her} eyes."
                ),
                "image_prompt_template": (
                    "{age} year old {gender} child {name} in cricket whites, helmet on, playing a perfect forward defensive: "
                    "front foot forward, bat straight and close to pad, head still over the ball, side-on stance on a sunny ground."
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
                    "{age} year old {gender} child {name} playing a straight drive, front knee bent, bat following through straight "
                    "toward the bowler, head over the ball, front shoulder pointing down the pitch, clear coaching illustration."
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
                    "{age} year old {gender} child {name} playing an elegant cover drive, front foot across to off side, "
                    "bat following through high, ball flying through cover region, classic cricket coaching pose."
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
                    "{age} year old {gender} child {name} playing an on drive toward mid-on, front foot pointing slightly to leg side, "
                    "bat straight, wrists firm, balanced stance, detailed lower-body and head position."
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
                    "{age} year old {gender} child {name} playing a pull shot off the back foot, body rotating, back foot anchored, "
                    "front leg slightly lifted, bat horizontal, ball going toward mid-wicket, dynamic coaching-style pose."
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
                    "{age} year old {gender} child {name} playing a square cut, back foot across toward off stump, body slightly open, "
                    "bat cutting across the ball toward point, clear line of shoulders, arms, and bat."
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
                    "{age} year old {gender} child {name} playing a classic sweep, front knee on the ground, back leg folded, "
                    "bat sweeping low in front, head forward over the ball, spinner in the background."
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
                    "{age} year old {gender} child {name} playing a lofted drive, front foot planted firmly, bat following through high "
                    "above the shoulder, ball flying over extra cover, stable lower body, expressive coaching style."
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
                    "{age} year old {gender} child {name} playing a back-foot defensive shot, back foot on the crease, "
                    "front foot slightly forward, bat straight and close to pads, ball dropping near feet."
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
                    "{age} year old {gender} child {name} playing a late cut, bat angled with soft hands, body slightly open, "
                    "ball running down to third man, wicket-keeper and slips in background."
                ),
            },
        ],
    },
    {
        "name": "Cinderella and the Brave Heart",
        "description": "A Cinderella retelling where {name} overcomes unkindness from stepfamily and finds confidence, magic, and a caring prince.",
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
                    "{age} year old {gender} child {name} in simple clothes cleaning a big old kitchen, "
                    "two fancy stepsisters and a strict stepmother ordering {him_her} around, warm but slightly sad fairy-tale style."
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
                    "{age} year old {gender} child {name} sitting by a fireplace in a small corner, "
                    "soft orange light on {his_her} face, old broom and bucket nearby, dreamy fairy-tale atmosphere."
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
                    "Royal messenger delivering a scroll in a hallway, two excited stepsisters twirling in half-finished dresses, "
                    "{age} year old {gender} child {name} holding a simple apron, looking hopeful, stern stepmother nearby."
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
                    "Magical fairy godmother with sparkling wand appearing before {age} year old {gender} child {name} in a garden, "
                    "pumpkin and mice nearby, glowing soft blue and gold light, storybook style."
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
                    "{age} year old {gender} child {name} spinning in a glowing magical dress or suit, glass slippers shining, "
                    "pumpkin transforming into a carriage, mice into horses, sparkling fairy dust everywhere."
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
                    "Grand palace ballroom, {age} year old {gender} child {name} dancing with a kind prince, chandeliers and guests "
                    "in the background, warm golden colors, elegant fairy-tale scene."
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
                    "{age} year old {gender} child {name} running down palace stairs at midnight, one glass slipper left behind, "
                    "clock tower showing twelve, flowing dress or outfit, dramatic but child-friendly scene."
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
                    "Prince traveling in a carriage through villages, holding a glass slipper, trying it on different feet, "
                    "people watching curiously, bright daytime fairy-tale illustration."
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
                    "Inside a modest room, prince kneeling to place glass slipper on {age} year old {gender} child {name}'s foot, "
                    "stepsisters and stepmother shocked in the background, warm hopeful colors."
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
                    "Palace garden scene, {age} year old {gender} child {name} walking happily with the prince and new friends, "
                    "flowers, fountains, and bright sky, peaceful fairy-tale ending."
                ),
            },
        ],
    },
    {
        "name": "Sports Day Champion",
        "description": "{name} discovers ten different sports on school sports day and imagines becoming a champion in each one.",
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
                    "{age} year old {gender} child {name} sprinting on a school track, leaning slightly forward, "
                    "arms pumping, knees lifting, cheering crowd and 'Sports Day' banner in background."
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
                    "{age} year old {gender} child {name} dribbling a football on a green field, defenders nearby, "
                    "legs in motion, focused eyes on the ball, school sports ground setting."
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
                    "{age} year old {gender} child {name} shooting a basketball, knees bent, arms extended, "
                    "ball in mid-air heading to the hoop, indoor school gym, bright colors."
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
                    "{age} year old {gender} child {name} playing tennis on a court, side-on stance, racket following through, "
                    "ball crossing the net, sunny outdoor scene."
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
                    "{age} year old {gender} child {name} swimming in a clean blue pool, freestyle stroke, "
                    "face turning to breathe, lane lines visible, bright indoor lighting."
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
                    "{age} year old {gender} child {name} balancing on a gymnastics beam, arms out for balance, "
                    "focused face, coach and mats in the background, bright gym setting."
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
                    "{age} year old {gender} child {name} playing badminton indoors, jumping to hit a shuttlecock, "
                    "racket arm stretched up, net and court lines visible."
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
                    "{age} year old {gender} child {name} playing field hockey, slightly crouched, stick controlling the ball, "
                    "teammates in background, school sports field."
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
                    "{age} year old {gender} child {name} mid-air in a long jump, knees up, arms forward, "
                    "sand pit below, white takeoff board visible, outdoor track setting."
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
                    "{age} year old {gender} child {name} standing proudly with a small medal or ribbon, "
                    "various sports equipment (football, racket, bat, ball) around, school field in background, "
                    "bright celebratory children’s book style."
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


def seed_default_templates_if_missing(supabase: Client) -> None:
    """Ensure our built-in templates exist in Supabase without overwriting user content."""
    try:
        for tmpl in DEFAULT_TEMPLATES:
            name = tmpl["name"]
            # Find or create template row by name
            existing = supabase.table("templates").select("id").eq("name", name).execute()
            if existing.data:
                template_id = existing.data[0]["id"]
            else:
                insert_resp = supabase.table("templates").insert(
                    {
                        "name": name,
                        "description": tmpl.get("description", ""),
                        "total_pages": tmpl.get("total_pages", len(tmpl.get("pages", []))),
                    }
                ).execute()
                if not insert_resp.data:
                    continue
                template_id = insert_resp.data[0]["id"]

            # Only insert pages if none exist yet for this template_id
            pages_existing = supabase.table("template_pages").select("id").eq("template_id", template_id).limit(1).execute()
            if pages_existing.data:
                continue

            pages_payload = []
            for page in tmpl.get("pages", []):
                pages_payload.append(
                    {
                        "template_id": template_id,
                        "page_number": page["page_number"],
                        "profession_title": page["profession_title"],
                        "text_template": page["text_template"],
                        "image_prompt_template": page["image_prompt_template"],
                    }
                )
            if pages_payload:
                supabase.table("template_pages").insert(pages_payload).execute()
    except Exception as e:
        logger.error(f"Error seeding default templates: {e}")


def get_available_templates() -> List[Dict]:
    """Fetch all available templates from database."""
    try:
        supabase = init_supabase()
        # Seed built-in templates if they are missing (idempotent; skips if already present)
        seed_default_templates_if_missing(supabase)
        response = supabase.table("templates").select("*").execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching templates: {e}")
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

    templates = get_available_templates()

    if not templates:
        st.warning("No templates available. Please contact support.")
        return

    st.markdown("### Choose a template")

    # Template cards grid for easier selection
    if "selected_template_id" not in st.session_state:
        st.session_state.selected_template_id = None
        st.session_state.selected_template_name = None

    cols = st.columns(2)
    for idx, tmpl in enumerate(templates):
        with cols[idx % 2]:
            st.subheader(tmpl.get("name", "Template"))
            st.caption(tmpl.get("description", ""))
            total_pages = tmpl.get("total_pages") or tmpl.get("page_count") or len(tmpl.get("pages", []))
            if total_pages:
                st.markdown(f"_Approx. {total_pages} pages_")
            if st.button("Use this template", key=f"use_template_{tmpl.get('id')}", use_container_width=True):
                st.session_state.selected_template_id = tmpl.get("id")
                st.session_state.selected_template_name = tmpl.get("name")

    if not st.session_state.selected_template_id:
        st.info("Select a template above to continue.")
        return

    selected_template_id = st.session_state.selected_template_id
    template_info = next((t for t in templates if t["id"] == selected_template_id), None)

    if template_info:
        st.markdown("---")
        st.info(f"📚 **{template_info['name']}** – {template_info.get('description', '')}")
        st.caption(f"This template includes {template_info.get('total_pages', 'multiple')} pages")

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
    """Create PDF from template book (same layout as main create_pdf: 8.5x8.5, dedication, image+text per page)."""
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
