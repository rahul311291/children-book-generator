"""
Template-based book generator for predefined book templates
Handles "When I Grow Up" and other template-based personalized books
"""

import streamlit as st
import streamlit.components.v1
import os
import base64
import uuid
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from template_data import personalize_template_text, personalize_template_image_prompt, WHEN_I_GROW_UP_TEMPLATE
from PIL import Image
import io
import logging
import requests
import json
import time
import hashlib
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_CENTER

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def compress_image_for_storage(data_url: str, max_size: int = 768, quality: int = 75) -> str:
    """Resize and JPEG-compress a base64 data URL for compact Supabase storage."""
    if not data_url or not data_url.startswith("data:image"):
        return data_url
    try:
        b64 = data_url.split(",", 1)[1]
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality, optimize=True)
        compressed = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/jpeg;base64,{compressed}"
    except Exception as e:
        logger.warning(f"Image compression failed: {e}")
        return data_url


# ---------------------------------------------------------------------------
# Shared image pool helpers (generic template images, no reference photos)
# ---------------------------------------------------------------------------

def _age_to_group(age: int) -> str:
    """Map an age to a canonical age-group string used as pool key."""
    if age <= 4:
        return "2-4"
    elif age <= 6:
        return "4-6"
    elif age <= 8:
        return "6-8"
    else:
        return "8-12"


def _pool_hash(template_id: str, page_number: int, age_group: str, gender: str) -> str:
    key = f"{template_id}:{page_number}:{age_group}:{gender.lower()}"
    return hashlib.md5(key.encode()).hexdigest()


def get_shared_pool_image(template_id: str, page_number: int, age_group: str, gender: str) -> Optional[str]:
    """Return image_url from shared image pool on hit, or None on miss."""
    try:
        from mongo_client import image_pool_col
        ph = _pool_hash(template_id, page_number, age_group, gender)
        doc = image_pool_col().find_one({"prompt_hash": ph}, {"image_url": 1})
        if doc:
            logger.info(f"Shared pool HIT: template={template_id} page={page_number} age={age_group} gender={gender}")
            return doc["image_url"]
    except Exception as e:
        logger.warning(f"Shared pool lookup failed: {e}")
    return None


def get_any_pool_image_for_page(template_id: str, page_number: int) -> Optional[str]:
    """Return any available pool image for this template page regardless of age/gender."""
    try:
        from mongo_client import image_pool_col
        doc = image_pool_col().find_one(
            {"template_id": template_id, "page_number": page_number},
            {"image_url": 1},
        )
        if doc:
            return doc["image_url"]
    except Exception:
        pass
    return None


def save_to_shared_pool(template_id: str, page_number: int, age_group: str, gender: str, image_url: str) -> None:
    """Persist a generated image to the shared pool (silent no-op on duplicate or error)."""
    try:
        from mongo_client import image_pool_col
        ph = _pool_hash(template_id, page_number, age_group, gender)
        compressed = compress_image_for_storage(image_url)
        image_pool_col().insert_one({
            "_id": ph,
            "prompt_hash": ph,
            "template_id": template_id,
            "page_number": page_number,
            "age_group": age_group,
            "gender": gender.lower(),
            "image_url": compressed,
            "created_at": datetime.utcnow(),
        })
        logger.info(f"Saved to shared pool: hash={ph}")
    except Exception as e:
        logger.debug(f"Shared pool save skipped (likely duplicate): {e}")


# ---------------------------------------------------------------------------
# MongoDB book cache helpers
# ---------------------------------------------------------------------------

def get_cached_template_book(user_id: str, template_id: str, child_name: str, gender: str, age: int) -> Optional[Dict]:
    """Fetch a previously generated book from the MongoDB cache, or None if not found."""
    try:
        from mongo_client import book_cache_col
        doc = book_cache_col().find_one(
            {"user_id": user_id, "template_id": template_id,
             "child_name": child_name, "gender": gender, "age": age},
            {"book_data": 1}
        )
        if doc:
            logger.info(f"Cache hit for template {template_id}, child {child_name}")
            return doc["book_data"]
    except Exception as e:
        logger.warning(f"Could not query book cache: {e}")
    return None


def save_template_book_to_cache(user_id: str, template_id: str, child_name: str, gender: str, age: int, book_data: Dict) -> None:
    """Store a generated template book (with compressed images) in the MongoDB cache and book_history."""
    try:
        from mongo_client import book_cache_col, book_history_col
        book_to_store = json.loads(json.dumps(book_data))
        for page in book_to_store.get("pages", []):
            if page.get("image_url"):
                page["image_url"] = compress_image_for_storage(page["image_url"])
        book_to_store.pop("reference_image_base64", None)

        book_cache_col().update_one(
            {"user_id": user_id, "template_id": template_id,
             "child_name": child_name, "gender": gender, "age": age},
            {"$set": {"book_data": book_to_store, "updated_at": datetime.utcnow()},
             "$setOnInsert": {"created_at": datetime.utcnow()}},
            upsert=True,
        )

        # Also save to book_history for community gallery (only if all pages have images)
        pages = book_to_store.get("pages", [])
        all_have_images = all(p.get("image_url") for p in pages)
        if all_have_images and pages:
            images_list = [p["image_url"] for p in pages]
            title = book_to_store.get("template_name", f"{child_name}'s Storybook")
            book_history_col().update_one(
                {"user_id": user_id, "template_id": template_id, "child_name": child_name},
                {"$set": {
                    "child_name": child_name,
                    "images": images_list,
                    "story_data": {"title": title, "pages": [{"text": p.get("text", "")} for p in pages]},
                    "metadata": {"age": age, "gender": gender, "template_id": template_id},
                    "is_private": False,
                    "updated_at": datetime.utcnow(),
                }, "$setOnInsert": {"created_at": datetime.utcnow()}},
                upsert=True,
            )

        logger.info(f"Template book cached for user {user_id}, template {template_id}, child {child_name}")
    except Exception as e:
        logger.warning(f"Could not save book to cache: {e}")

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
        "cover_image": "https://images.pexels.com/photos/11890414/pexels-photo-11890414.jpeg?auto=compress&cs=tinysrgb&w=800",
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} in simple "
                    "patched clothes, carrying a heavy wicker basket through a grand stone castle kitchen. Two elaborately "
                    "dressed sisters point and snicker while a stern stepmother watches from a throne-like chair. Warm "
                    "candlelight, cobblestone floor, copper pots hanging on walls. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} sitting "
                    "on a stone castle windowsill, smiling softly while feeding colorful songbirds from {name}'s open palm. "
                    "Morning sunlight streams through the arched window. Two sisters frown in the shadowy background. "
                    "Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} walking "
                    "along a winding path into a tall, ancient forest. Golden rays of sunlight filter through the canopy. "
                    "A rabbit peeks from behind ferns, a bluebird perches on a branch overhead. The mood shifts from "
                    "sadness to quiet hope. Rich greens, dappled light, bold outlines, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a charming thatched-roof cottage nestled among tall "
                    "forest trees with a mushroom-lined path leading to the door. Inside, a {age}-year-old {gender} child "
                    "named {name} sweeps the wooden floor while sunlight pours through small round windows. Seven tiny "
                    "chairs, seven tiny beds, cozy hearth. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} sitting at "
                    "a small round wooden table surrounded by seven cheerful cartoon dwarfs of different heights and personalities, "
                    "all sharing a warm meal. Cozy candlelight, wooden beams overhead, a crackling fireplace. Everyone smiles "
                    "kindly at {name}. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a cloaked old woman with hidden eyes offers a single "
                    "gleaming red apple to a {age}-year-old {gender} child named {name} at the cottage door. The apple "
                    "glows ominously. Shadows creep at the edges while the cottage remains warm. Dramatic lighting, "
                    "bold outlines, rich deep colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a crystal glass coffin resting on a flower-covered "
                    "hilltop under a canopy of blossoming trees. A {age}-year-old {gender} child named {name} lies "
                    "peacefully inside with folded hands. Seven cartoon dwarfs weep nearby while forest animals -- deer, rabbits, "
                    "birds -- gather in a circle. Tender, bittersweet mood, bold outlines, bright colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a gentle young prince on a white horse arriving at the "
                    "glass coffin on the hilltop. A {age}-year-old {gender} child named {name} begins to stir awake, "
                    "eyes fluttering open. Cartoon dwarfs look up in astonished hope, golden sunlight breaking through clouds. "
                    "Magical moment, bold outlines, bright hopeful colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} standing "
                    "between the kind prince and the seven cartoon dwarfs, holding a dwarf's hand in farewell. A winding forest "
                    "path leads to a sunlit white castle on a distant hill. Bold outlines, bright saturated colors, warm golden hour lighting, "
                    "smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a grand castle courtyard celebration with banners and "
                    "flowers. A {age}-year-old {gender} child named {name} in beautiful royal clothes stands at the center, "
                    "surrounded by the prince, the seven cartoon dwarfs visiting, and new friends all smiling. Bright golden "
                    "sunlight, joyful atmosphere, bold outlines, bright saturated colors, smooth shading, animated movie quality happily-ever-after ending, no text."
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
        "cover_image": "https://images.pexels.com/photos/17892641/pexels-photo-17892641.jpeg?auto=compress&cs=tinysrgb&w=800",
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} in simple "
                    "worn clothes, scrubbing a large wooden table in a grand old kitchen. Two overdressed stepsisters "
                    "lounge on cushioned chairs pointing at {name}, while a stern stepmother supervises from the doorway. "
                    "Warm but melancholy firelight, stone walls, hanging herbs. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} sitting "
                    "curled up on a small stool beside a crackling fireplace, chin resting on knees, gazing into the "
                    "dancing orange flames. Soft embers float upward like tiny stars. An old broom and bucket rest nearby. "
                    "Warm amber glow, dreamy atmosphere, bold outlines, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a royal messenger in a plumed hat presenting a golden "
                    "scroll at the door. Two excited stepsisters twirl in half-finished ball gowns. A {age}-year-old "
                    "{gender} child named {name} stands in the background holding a simple apron, looking hopeful "
                    "but sad. Stern stepmother blocks the way. Bold outlines, rich bright colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a glowing fairy godmother in a flowing silver gown, "
                    "holding a sparkling wand, appearing in a moonlit garden before a {age}-year-old {gender} child "
                    "named {name} who looks up in wonder. A pumpkin sits on the garden path, cartoon mice peek from behind "
                    "flower pots. Magical blue and gold light radiates outward. Bold outlines, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} spinning "
                    "joyfully as rags transform into a magnificent glittering outfit with glass slippers that catch the "
                    "moonlight. Behind {name}, a pumpkin morphs into a golden carriage, cartoon mice transform into elegant white "
                    "horses. Sparkles and fairy dust fill the air. Bold outlines, bright saturated colors, smooth shading, animated movie quality, magical transformation scene, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a grand palace ballroom with crystal chandeliers, marble "
                    "columns, and elegantly dressed cartoon guests. A {age}-year-old {gender} child named {name} in a magnificent "
                    "outfit dances gracefully with a kind young prince at the center of the room. Golden candlelight "
                    "reflects off the polished floor. Bold outlines, bright saturated colors, smooth shading, animated movie quality, enchanting atmosphere, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a {age}-year-old {gender} child named {name} running "
                    "down wide marble palace stairs under a midnight sky full of stars. One sparkling glass slipper sits "
                    "on a step behind. A large clock tower in the background shows midnight. Outfit beginning to shimmer "
                    "and fade. Bold outlines, bright colors, smooth shading, animated movie quality, dramatic but child-friendly urgency, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a determined young cartoon prince traveling through a village "
                    "in a horse-drawn carriage, holding up a single sparkling glass slipper on a velvet cushion. "
                    "Cartoon villagers peer out from doorways and windows. Cobblestone streets, thatched-roof cottages, bright "
                    "daytime scene. Bold outlines, bright saturated colors, smooth shading, animated movie quality, hopeful atmosphere, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: inside a modest room, the cartoon prince kneels to place the "
                    "glass slipper on a {age}-year-old {gender} child named {name}'s foot. The slipper glows as it fits "
                    "perfectly. Two cartoon stepsisters and the stepmother look shocked and dismayed in the background. Bold outlines, "
                    "warm hopeful golden light, bright saturated colors, smooth shading, animated movie quality, no text."
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
                    "Cartoon animated children's storybook illustration in vibrant cel-shaded style: a beautiful palace garden with fountains, rose bushes, "
                    "and butterflies. A {age}-year-old {gender} child named {name} in elegant royal attire walks happily "
                    "with the cartoon prince and new friends through the garden. Bright blue sky, warm sunshine, flowers in "
                    "full bloom. Bold outlines, bright saturated colors, smooth shading, animated movie quality, joyful fairy-tale ending, no text."
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
    # ── Template 6: Space Adventure ──────────────────────────────────────────
    {
        "id": "a6666666-6666-6666-6666-666666666666",
        "name": "{name}'s Space Adventure",
        "description": "Blast off on an intergalactic journey! {name} explores the Moon, Mars, Saturn's rings, meets alien friends, and returns home a hero.",
        "cover_image": "https://images.pexels.com/photos/1169754/pexels-photo-1169754.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 12,
        "tags": ["Adventure", "Sci-Fi"],
        "age_range": "4 - 10",
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Launch Day",
                "text_template": (
                    "{name} straps in tight and counts to three,\n"
                    "{He_She} rockets off to find what{he_she} can see.\n"
                    "The engines roar, the Earth falls away,\n"
                    "{name}'s grand space adventure starts today!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} wearing a gleaming white astronaut suit with a clear helmet visor, "
                    "sitting inside a rocket cockpit, hand on launch controls, wide-eyed with excitement. "
                    "Flames and stars visible through the porthole. Soft brush strokes, warm pastel palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Walking on the Moon",
                "text_template": (
                    "{name} bounces lightly on the Moon so grey,\n"
                    "{He_She} floats with each and every step {he_she} takes today.\n"
                    "The craters shine beneath {his_her} boots so bright,\n"
                    "With Earth above and stars that fill the night!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in an astronaut suit bounding across the moon's grey cratered surface, "
                    "Earth glowing blue in the dark sky above. Footprints trail behind. Soft brush strokes, cool silver-blue palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Red Planet Mars",
                "text_template": (
                    "Next {name} lands on Mars so red and vast,\n"
                    "{He_She} plants a flag that flies against the blast.\n"
                    "Red dust swirls around {his_her} boots and toes,\n"
                    "{name} explores wherever {he_she} wants to go!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} in a white astronaut suit planting a small flag on the dusty red surface of Mars, "
                    "rust-red rocky landscape with pink sky and distant mountains. Soft brush strokes, warm terracotta palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "Jupiter's Storms",
                "text_template": (
                    "Jupiter looms large with swirling bands of cloud,\n"
                    "{name} watches storms that rumble fierce and loud.\n"
                    "{He_She} steers {his_her} ship through orange and cream,\n"
                    "It's more amazing than the grandest dream!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} piloting a small round spaceship past Jupiter, the giant striped planet filling the background with its Great Red Spot. "
                    "Orange and cream swirling cloud bands, sense of awe and wonder. Soft brush strokes, warm amber palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "Saturn's Rings",
                "text_template": (
                    "Saturn's rings glow gold like sparkly bands,\n"
                    "{name} reaches out as if to hold them in {his_her} hands.\n"
                    "{He_She} glides between the ice and dust and light,\n"
                    "Oh what a glittering, magnificent sight!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} in an astronaut suit floating beside Saturn, its golden rings sweeping across the scene, glittering ice particles catching the sunlight. "
                    "Magical sparkling atmosphere. Soft brush strokes, golden pastel palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "Alien Friends",
                "text_template": (
                    "{name} meets some aliens green and small,\n"
                    "{He_She} greets them kindly, sharing smiles with all.\n"
                    "They laugh and dance and teach {him_her} games to play,\n"
                    "New friends from galaxies so far away!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in an astronaut suit shaking hands with two small friendly green aliens with big eyes and wide smiles, on an alien planet with purple foliage and pink sky. "
                    "Warm, joyful and welcoming scene. Soft brush strokes, vibrant playful palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "Asteroid Belt",
                "text_template": (
                    "Through the asteroid belt {name} carefully weaves,\n"
                    "{He_She} dodges boulders tumbling past like leaves.\n"
                    "{His_Her} quick hands steer the ship with steady care,\n"
                    "{name} is the bravest pilot anywhere!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} focused and determined at the controls of a spaceship weaving through a field of tumbling grey asteroids, determined expression, starfield background. "
                    "Sense of action and bravery. Soft brush strokes, deep blue-charcoal palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "Black Hole (Safe!)",
                "text_template": (
                    "A swirling black hole glows with violet light,\n"
                    "{name} watches safely — what a curious sight!\n"
                    "{He_She} sketches notes and marvels at its spin,\n"
                    "How much the universe has tucked within!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in an astronaut suit floating at a safe distance, gazing with wonder at a swirling violet and gold black hole, a small notebook in hand, completely safe and curious. "
                    "Magical cosmic atmosphere. Soft brush strokes, deep violet and gold palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "Nebula Dreams",
                "text_template": (
                    "Pink and purple nebula clouds drift by,\n"
                    "Like cotton candy smeared across the sky.\n"
                    "{name} floats through colours soft and bright,\n"
                    "Wrapped in the universe's glowing light!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} floating freely in a spacesuit through a beautiful pink and purple nebula, soft glowing clouds of stardust surrounding {name}, serene dreamy expression. "
                    "Ethereal soft light, watercolor cloud washes. Soft brush strokes, rose and lavender palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "Space Station",
                "text_template": (
                    "The space station spins like a silver wheel,\n"
                    "{name} docks {his_her} ship with skilled, sure zeal.\n"
                    "{He_She} meets the crew and shares {his_her} tales with pride,\n"
                    "Of every wonder {he_she} has seen outside!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in an astronaut suit floating inside a bright space station, waving cheerfully to a diverse crew of adult astronauts, large circular portholes showing stars outside. "
                    "Warm welcoming community feeling. Soft brush strokes, clean white and silver palette with accent colours. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 11,
                "profession_title": "Return Home",
                "text_template": (
                    "{name} points the ship back home through starry space,\n"
                    "Earth grows bigger — blue and green with grace.\n"
                    "{He_She} smiles wide, {his_her} heart so full and warm,\n"
                    "Home is the best discovery of all!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} in a spacesuit sitting in the capsule window, gazing at a beautiful blue and green Earth growing larger ahead, warm smile of homecoming. "
                    "Soft emotional warmth, watercolor Earth tones. Soft brush strokes, blue-green palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 12,
                "profession_title": "Hero's Welcome",
                "text_template": (
                    "Back on Earth with stories grand to tell,\n"
                    "{name} shares each planet, moon, and wishing well.\n"
                    "{He_She} proves that every child can touch the stars,\n"
                    "From here to Saturn, Jupiter, and Mars!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in a spacesuit with helmet off, arms raised in triumph, surrounded by cheering family and friends holding welcome-home banners, confetti falling. "
                    "Joyful celebratory homecoming scene. Soft brush strokes, warm bright festive palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
        ],
    },
    # ── Template 7: World of Friends ─────────────────────────────────────────
    {
        "id": "a7777777-7777-7777-7777-777777777777",
        "name": "{name}'s World of Friends",
        "description": "A heartwarming journey where {name} travels the globe meeting friends from different cultures, learning about sharing, kindness, bravery, and gratitude.",
        "cover_image": "https://images.pexels.com/photos/296301/pexels-photo-296301.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 12,
        "tags": ["Friendship", "Emotions"],
        "age_range": "3 - 7",
        "pages": [
            {
                "page_number": 1,
                "profession_title": "The Big Wide World",
                "text_template": (
                    "{name} looks at a map with wondering eyes,\n"
                    "{He_She} sees every country under sunny skies.\n"
                    "So many places, so many friends to meet,\n"
                    "{name}'s world adventure can't be beat!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} sitting cross-legged on the floor, holding a big colourful world map open wide, eyes sparkling with curiosity and excitement. "
                    "Warm cosy home setting. Soft brush strokes, warm golden palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "A Friend from Japan",
                "text_template": (
                    "In Japan {name} meets Hana dressed in pink,\n"
                    "They fold paper cranes as quick as you can think.\n"
                    "{He_She} learns that sharing makes a friendship grow,\n"
                    "Like cherry blossoms dancing in the snow!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} sitting at a low Japanese table with a smiling Japanese girl friend, both folding origami paper cranes together, cherry blossom petals floating around them. "
                    "Soft pink and white palette, gentle joy. Soft brush strokes, pastel sakura palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Kindness in Kenya",
                "text_template": (
                    "On the Kenyan savanna wide and free,\n"
                    "{name} and Amara climb a baobab tree.\n"
                    "{He_She} shares {his_her} lunch and Amara shares {his_her} song,\n"
                    "Kindness makes them feel they both belong!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} sitting under a giant baobab tree on the African savanna sharing food with a smiling African boy friend, a giraffe visible in the golden distance. "
                    "Warm earthy tones, joyful sharing scene. Soft brush strokes, ochre and terracotta palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "Bravery in Brazil",
                "text_template": (
                    "In Brazil the rainforest hums and sings,\n"
                    "{name} and Lucas explore on colourful wings.\n"
                    "{He_She} feels a little scared but takes a step,\n"
                    "Being brave means trying — that's the best!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} stepping bravely across a hanging rope bridge in a lush Amazon rainforest, a cheerful Brazilian boy friend encouraging from the other side, colourful toucans and butterflies around them. "
                    "Lush tropical greens and bright parrots. Soft brush strokes, vibrant jungle palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "Curiosity in India",
                "text_template": (
                    "{name} visits a market bright and loud,\n"
                    "{He_She} walks with Priya through the colourful crowd.\n"
                    "Every smell and colour sparks a question new,\n"
                    "Curiosity leads to adventures true!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} wide-eyed with wonder at a vibrant Indian market bazaar, walking alongside an Indian girl friend Priya, surrounded by colourful fabrics, spices, marigold garlands, and lanterns. "
                    "Festive warm tones, curious joyful expression. Soft brush strokes, saffron and jewel-tone palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "Creativity in Italy",
                "text_template": (
                    "In Italy {name} paints with Giulia's brush,\n"
                    "{He_She} splashes colour in a creative rush.\n"
                    "There's no right or wrong in art, they agree,\n"
                    "Creativity sets both their spirits free!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} painting on a large canvas in an Italian piazza, alongside an Italian girl friend Giulia, both covered in happy paint splatters, a fountain and terracotta buildings behind them. "
                    "Cheerful artistic mess, Mediterranean warmth. Soft brush strokes, bright artistic palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "Gratitude in Australia",
                "text_template": (
                    "Down in Australia {name} meets Lily Mae,\n"
                    "They watch the kangaroos leap and play all day.\n"
                    "{He_She} feels so thankful for each wondrous sight,\n"
                    "Gratitude fills {his_her} heart with golden light!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} sitting on red Australian outback earth beside an Australian girl friend, both watching a family of kangaroos with joeys in the warm golden sunset light, serene grateful expressions. "
                    "Warm golden hour tones, peaceful atmosphere. Soft brush strokes, amber and rust palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "Listening in Canada",
                "text_template": (
                    "In snowy Canada {name} meets Lena bright,\n"
                    "They build a snowman in the fading light.\n"
                    "{He_She} listens to her stories, quiet and still,\n"
                    "A good friend listens — that's the greatest skill!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in a red winter coat building a snowman with a Canadian girl friend Lena in a snowy Canadian forest, both laughing, tall pine trees dusted with snow behind them. "
                    "Cosy winter wonderland warmth. Soft brush strokes, white and icy blue palette with red accents. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "Patience in China",
                "text_template": (
                    "{name} tries to learn a brush stroke slow and true,\n"
                    "{His_Her} friend Wei shows {him_her} what patience can do.\n"
                    "{He_She} breathes and tries again with steady care,\n"
                    "Patience blooms like lotus in the air!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} carefully painting Chinese calligraphy with a brush, guided by a patient Chinese boy friend Wei, in a peaceful garden pavilion with lotus pond and red lanterns. "
                    "Calm serene beauty, ink wash accents. Soft brush strokes, jade and crimson palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "Helpfulness in Egypt",
                "text_template": (
                    "By the pyramids tall {name} helps young Omar,\n"
                    "{He_She} carries water jars from near and far.\n"
                    "Together they laugh and share the heavy load,\n"
                    "Helping hands make lighter every road!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} helping carry a clay water jar alongside an Egyptian boy friend Omar near the majestic pyramids and golden desert sands under a warm blue sky. "
                    "Sun-baked golden warmth, archaeological wonder. Soft brush strokes, gold and sand palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 11,
                "profession_title": "All Friends Together",
                "text_template": (
                    "{name} calls all {his_her} friends across the miles,\n"
                    "{He_She} sees their faces bright with laughing smiles.\n"
                    "Though oceans wide and mountains tall divide,\n"
                    "True friendship reaches every place worldwide!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} video-calling on a tablet, showing a screen with small portraits of diverse international friends all waving and smiling together, world map decorating the bedroom wall. "
                    "Warm connected joy, global community. Soft brush strokes, cheerful multi-colour palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 12,
                "profession_title": "A Friend to the World",
                "text_template": (
                    "{name} has learned that kindness is the key,\n"
                    "That every friend is special as can be.\n"
                    "{He_She} opens {his_her} heart wherever {he_she} may roam,\n"
                    "The whole wide world can feel just like a home!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} standing on top of a gently glowing globe, arms spread wide with joy, surrounded by small illustrated friends from different countries waving up from around the world. "
                    "Uplifting, hopeful, globally united. Soft brush strokes, warm rainbow-accented palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
        ],
    },
    # ── Template 8: ABC Adventure ─────────────────────────────────────────────
    {
        "id": "a8888888-8888-8888-8888-888888888888",
        "name": "{name} Meets the Alphabet",
        "description": "An early-learning adventure where {name} meets a new letter friend on every page — from A for Ant to Z for Zebra!",
        "cover_image": "https://images.pexels.com/photos/1148998/pexels-photo-1148998.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 28,
        "tags": ["Early Learning", "Alphabet"],
        "age_range": "2 - 5",
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Hello, Alphabet!",
                "text_template": (
                    "{name} opens a big colourful book today,\n"
                    "{He_She} is ready to learn in every way.\n"
                    "Twenty-six letters waiting just for {him_her},\n"
                    "Let's meet them all — come along with {name}!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} sitting cross-legged, opening a giant colourful alphabet book, letters floating out magically around {name}, wide-eyed with delight. "
                    "Magical learning atmosphere. Soft brush strokes, bright rainbow palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Letter A",
                "text_template": (
                    "A is for Ant so tiny and small,\n"
                    "{name} watches it carry a crumb down the hall.\n"
                    "Ants work together the whole day through,\n"
                    "A, A, A — {name} loves ants too!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} crouching down on a garden path, peering with delight at a line of cheerful cartoon ants carrying crumbs, a giant letter A softly visible in the watercolor background. "
                    "Warm garden greens. Soft brush strokes, fresh spring palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Letter B",
                "text_template": (
                    "B is for Bear big and fluffy and brown,\n"
                    "{name} gives {his_her} bear a hug without a frown.\n"
                    "Bears love honey and sleeping in caves,\n"
                    "B, B, B — {name} always behaves!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} hugging a friendly round brown bear cub, both sitting in a sunny forest clearing with honeycomb details, a soft letter B watercolor wash in the background. "
                    "Cosy forest warmth. Soft brush strokes, honey-brown palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "Letter C",
                "text_template": (
                    "C is for Cat that purrs on the mat,\n"
                    "{name} strokes {his_her} fur and {he_she} likes that.\n"
                    "Cats curl up soft in the afternoon sun,\n"
                    "C, C, C — cuddling is so fun!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} sitting on a cosy rug gently stroking an orange tabby cat purring in {name}'s lap, warm afternoon sunlight through a window, soft letter C in the watercolor background. "
                    "Warm cosy home feeling. Soft brush strokes, amber and ginger palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "Letter D",
                "text_template": (
                    "D is for Dog that wags {his_her} tail with glee,\n"
                    "{name} runs across the garden wild and free.\n"
                    "Dogs are loyal and playful every day,\n"
                    "D, D, D — let's go outside and play!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} running joyfully across a green garden with a fluffy golden dog bounding beside {name}, both full of energy and happiness, soft letter D watercolor in background. "
                    "Bright outdoor energy. Soft brush strokes, fresh green and gold palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "Letter E",
                "text_template": (
                    "E is for Elephant grey and so tall,\n"
                    "{name} marvels at the biggest of all.\n"
                    "Elephants spray water up in the air,\n"
                    "E, E, E — they are gentle and rare!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} standing beside a gentle baby elephant that is spraying a playful arc of water, savanna grasses and soft sky, letter E in the watercolor corner wash. "
                    "Gentle awe and wonder. Soft brush strokes, warm grey and sky-blue palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "Letter F",
                "text_template": (
                    "F is for Frog that leaps with a spring,\n"
                    "{name} laughs at each hop and the splashing it brings.\n"
                    "Frogs love lily pads, puddles and rain,\n"
                    "F, F, F — let's count the hops again!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} sitting at the edge of a lily-pad pond, giggling as a cheerful bright green frog leaps between pads, water droplets catching the light, soft letter F watercolor wash. "
                    "Playful pond freshness. Soft brush strokes, leafy green and aqua palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "Letter G",
                "text_template": (
                    "G is for Giraffe with a neck so long,\n"
                    "{name} cranes {his_her} neck and sings a silly song.\n"
                    "Giraffes munch leaves at the very top,\n"
                    "G, G, G — they never seem to stop!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} looking up in delight at a tall friendly giraffe munching leaves from an acacia treetop, savanna landscape, soft letter G watercolor in the background. "
                    "Tall wonder and silliness. Soft brush strokes, golden savanna palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "Letter H",
                "text_template": (
                    "H is for Horse that gallops along,\n"
                    "{name} rides on {his_her} back feeling brave and strong.\n"
                    "Horses toss manes in the warm summer breeze,\n"
                    "H, H, H — {name} rides through the trees!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} sitting proudly on a gentle brown horse, riding through a sunny meadow with wild flowers, wind in {name}'s hair, soft letter H watercolor in background. "
                    "Bold and brave joy. Soft brush strokes, chestnut and meadow green palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "Letter I",
                "text_template": (
                    "I is for Igloo built of ice and snow,\n"
                    "{name} peeks inside where warm lanterns glow.\n"
                    "Igloos keep families cosy in the cold,\n"
                    "I, I, I — what a story to be told!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in a warm winter coat bending down to peek into the entrance of a cosy igloo, warm golden lantern light glowing inside, soft arctic blue surroundings, letter I watercolor wash. "
                    "Cosy arctic wonder. Soft brush strokes, icy blue and warm gold palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 11,
                "profession_title": "Letter J",
                "text_template": (
                    "J is for Jellyfish floating so light,\n"
                    "{name} watches them glow like lanterns at night.\n"
                    "Jellyfish shimmer in purple and blue,\n"
                    "J, J, J — what a beautiful view!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} floating underwater in a diving suit, gazing with wonder at glowing purple and blue jellyfish drifting around {name}, soft light beams from above, letter J watercolor wash. "
                    "Magical underwater luminescence. Soft brush strokes, deep ocean blue and violet palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 12,
                "profession_title": "Letter K",
                "text_template": (
                    "K is for Kangaroo with a joey inside,\n"
                    "{name} watches the little one peek out with pride.\n"
                    "Kangaroos hop and hop without a stop,\n"
                    "K, K, K — {name} bounces on top!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} crouching with delight beside a mother kangaroo in the Australian outback, a tiny joey peeking out from the pouch, red earth and eucalyptus trees behind, letter K watercolor wash. "
                    "Warm outback wonder. Soft brush strokes, rust and dusty green palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 13,
                "profession_title": "Letter L",
                "text_template": (
                    "L is for Lion with a magnificent mane,\n"
                    "{name} listens to {his_her} roar like rolling thunder and rain.\n"
                    "Lions lead their pride with courage and care,\n"
                    "L, L, L — leadership is rare!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} sitting confidently beside a majestic friendly lion on an African savanna rock, golden sunset sky behind them, letter L soft watercolor wash. "
                    "Regal golden warmth. Soft brush strokes, golden lion mane palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 14,
                "profession_title": "Letter M",
                "text_template": (
                    "M is for Monkey swinging up high,\n"
                    "{name} laughs as {he_she} reaches up toward the sky.\n"
                    "Monkeys are cheeky and clever and bright,\n"
                    "M, M, M — what a mischievous delight!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} laughing up at a cheeky brown monkey swinging on a jungle vine, {name} reaching up playfully, lush jungle canopy background, letter M watercolor wash. "
                    "Playful jungle energy. Soft brush strokes, tropical green and brown palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 15,
                "profession_title": "Letter N",
                "text_template": (
                    "N is for Narwhal with a twirly horn,\n"
                    "{name} waves as it swims since the early morn.\n"
                    "Narwhals are the unicorns of the sea,\n"
                    "N, N, N — as magical as can be!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} in a submarine porthole waving at a beautiful grey narwhal swimming past with its spiral horn glinting, deep arctic blue ocean, soft letter N watercolor wash. "
                    "Magical arctic ocean. Soft brush strokes, deep blue and silver palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 16,
                "profession_title": "Letter O",
                "text_template": (
                    "O is for Octopus with eight wiggly arms,\n"
                    "{name} counts every one with laughter and charms.\n"
                    "Octopuses are clever and change colour too,\n"
                    "O, O, O — what a trick to do!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in snorkelling gear underwater, playfully counting the waving arms of a friendly purple and orange octopus, colourful coral reef background, letter O watercolor wash. "
                    "Vivid underwater fun. Soft brush strokes, coral and ocean blue palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 17,
                "profession_title": "Letter P",
                "text_template": (
                    "P is for Penguin in a black and white suit,\n"
                    "{name} waddles along — isn't that cute?\n"
                    "Penguins slide on ice and huddle up tight,\n"
                    "P, P, P — what a penguin delight!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} in a puffy winter jacket waddling beside a huddle of round penguins on an icy Antarctic shore, laughing and mimicking the penguin walk, soft letter P watercolor wash. "
                    "Chilly penguin fun. Soft brush strokes, black, white and icy blue palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 18,
                "profession_title": "Letter Q",
                "text_template": (
                    "Q is for Queen bee that hums in the hive,\n"
                    "{name} watches the buzzing bees come alive.\n"
                    "Every bee has a job and a very big role,\n"
                    "Q, Q, Q — teamwork makes them whole!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} wearing a beekeeper's hat, peering with wonder at a golden honeycomb hive with cheerful bees buzzing around, one large queen bee in the centre, soft letter Q watercolor wash. "
                    "Sunny honey warmth. Soft brush strokes, golden amber and yellow palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 19,
                "profession_title": "Letter R",
                "text_template": (
                    "R is for Rabbit with ears fluffy and tall,\n"
                    "{name} chases it gently across the back wall.\n"
                    "Rabbits hop fast through the clover and grass,\n"
                    "R, R, R — they're gone in a flash!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} in a garden gently chasing a fluffy white rabbit through tall clover and daisies, both mid-hop, flower details everywhere, soft letter R watercolor wash. "
                    "Springtime garden delight. Soft brush strokes, soft green and white palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 20,
                "profession_title": "Letter S",
                "text_template": (
                    "S is for Shark that swims with a fin,\n"
                    "{name} sees it and gives a wide brave grin.\n"
                    "Sharks keep the ocean balanced and right,\n"
                    "S, S, S — sharks are a beautiful sight!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} in a glass underwater submarine pod, gazing out with a brave grin at a magnificent great white shark swimming peacefully past, ocean blue surroundings, soft letter S watercolor wash. "
                    "Ocean awe and bravery. Soft brush strokes, deep blue and silver palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 21,
                "profession_title": "Letter T",
                "text_template": (
                    "T is for Tiger striped orange and black,\n"
                    "{name} spots {him_her} prowling and waves from the track.\n"
                    "Tigers are powerful, graceful, and strong,\n"
                    "T, T, T — {name} cheers them along!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} on a jungle observation platform waving at a magnificent Bengal tiger walking gracefully through tall orange and green grass below, letter T watercolor wash. "
                    "Bold jungle power. Soft brush strokes, tiger orange and deep green palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 22,
                "profession_title": "Letter U",
                "text_template": (
                    "U is for Umbrella in the pattering rain,\n"
                    "{name} jumps in every puddle again and again.\n"
                    "Umbrellas keep us dry and bright and bold,\n"
                    "U, U, U — the best story ever told!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} jumping gleefully into a large muddy puddle under a bright red umbrella in the rain, rain drops and splashes everywhere, letter U soft watercolor wash. "
                    "Rainy day joy. Soft brush strokes, red umbrella and grey-blue rain palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 23,
                "profession_title": "Letter V",
                "text_template": (
                    "V is for Vulture soaring up so high,\n"
                    "{name} shields {his_her} eyes to watch it in the sky.\n"
                    "Vultures clean the land and keep it well,\n"
                    "V, V, V — what stories they could tell!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} on a sunny hilltop shading {name}'s eyes to watch a wide-winged vulture circling majestically in the blue sky above, golden rolling hills below, letter V watercolor wash. "
                    "Open sky wonder. Soft brush strokes, sky blue and golden hill palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 24,
                "profession_title": "Letter W",
                "text_template": (
                    "W is for Whale the biggest of all,\n"
                    "{name} hears {his_her} song like an ocean-wide call.\n"
                    "Whales sing to each other across the deep blue,\n"
                    "W, W, W — {name} sings too!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} on the bow of a small sailing boat, mouth open in joyful song, beside an enormous friendly blue whale surfacing and spouting a rainbow arc of water, letter W watercolor wash. "
                    "Ocean grandeur and joy. Soft brush strokes, ocean blue and white palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 25,
                "profession_title": "Letter X",
                "text_template": (
                    "X marks the spot on a treasure map bright,\n"
                    "{name} digs up a chest in the golden sunlight.\n"
                    "X is the letter that marks something grand,\n"
                    "X, X, X — treasures across every land!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} digging excitedly on a sandy beach, a treasure map with an X in {name}'s hand, an old wooden chest just unearthed, golden coins glinting, letter X soft watercolor wash. "
                    "Adventure and discovery. Soft brush strokes, golden sand and treasure palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 26,
                "profession_title": "Letter Y",
                "text_template": (
                    "Y is for Yak all shaggy and wide,\n"
                    "{name} pats {his_her} thick coat and rides by {his_her} side.\n"
                    "Yaks carry loads over mountain and snow,\n"
                    "Y, Y, Y — how far they can go!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} bundled in warm mountain clothes patting the thick shaggy coat of a friendly yak on a snowy Himalayan mountain path, misty peaks behind, letter Y watercolor wash. "
                    "High altitude warmth. Soft brush strokes, snow white and deep brown palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 27,
                "profession_title": "Letter Z",
                "text_template": (
                    "Z is for Zebra with stripes black and white,\n"
                    "{name} counts every stripe from morning to night.\n"
                    "No two zebras have the same pattern at all,\n"
                    "Z, Z, Z — {name} is unique like them all!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the left of the frame, clear white space on the right side for text. "
                    "A {age}-year-old {gender} child named {name} standing beside a beautiful zebra in the golden savanna, carefully counting the black and white stripes with one finger, looking thoughtful and amazed, letter Z watercolor wash. "
                    "Unique pattern wonder. Soft brush strokes, black, white and golden savanna palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
            {
                "page_number": 28,
                "profession_title": "The Whole Alphabet!",
                "text_template": (
                    "{name} has met every letter from A to Z,\n"
                    "{He_She} knows all the alphabet now — hooray!\n"
                    "Letters are friends that help us to read and say,\n"
                    "All the wonderful words we use every day!"
                ),
                "image_prompt_template": (
                    "Semi-realistic watercolor portrait storybook illustration. "
                    "White background with soft watercolor paint splashes at the corners. "
                    "The child is the single hero subject, rendered with photographic facial accuracy "
                    "(real face shape, skin tone, hair colour and texture). "
                    "Child positioned slightly to the right of the frame, clear white space on the left side for text. "
                    "A {age}-year-old {gender} child named {name} standing triumphantly holding a banner reading the alphabet, surrounded by all 26 animal friends from the book arranged in a joyful crowd, confetti and letters floating everywhere. "
                    "Grand celebratory finale. Soft brush strokes, bright rainbow celebration palette. "
                    "Professional premium children's book illustration quality. No text, no watermarks."
                ),
            },
        ],
    },
]


def get_available_templates() -> List[Dict]:
    """Return the built-in template list (no database call needed)."""
    logger.info(f"Returning {len(DEFAULT_TEMPLATES)} built-in templates")
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t.get("description", ""),
            "cover_image": t.get("cover_image", ""),
            "total_pages": t.get("total_pages", len(t.get("pages", []))),
            "tags": t.get("tags", []),
            "age_range": t.get("age_range", ""),
        }
        for t in DEFAULT_TEMPLATES
    ]


def get_template_pages(template_id: str) -> List[Dict]:
    """Return pages for a given template ID from the in-memory DEFAULT_TEMPLATES list."""
    for tmpl in DEFAULT_TEMPLATES:
        if tmpl["id"] == template_id:
            return sorted(tmpl.get("pages", []), key=lambda p: p["page_number"])
    logger.error(f"Template ID {template_id} not found in DEFAULT_TEMPLATES")
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


    if not templates:
        st.warning("No templates available. Please contact support.")
        return

    st.markdown("### Choose a template")
    st.caption(f"Select from {len(templates)} available templates below:")

    # Template cards grid - use 3 columns for better layout
    if "selected_template_id" not in st.session_state:
        st.session_state.selected_template_id = None
        st.session_state.selected_template_name = None

    # Display templates in a Diffrun-style card grid (3 columns, wraps to next row)
    num_cols = 3
    for row_start in range(0, len(templates), num_cols):
        cols = st.columns(num_cols)
        for col_idx, col in enumerate(cols):
            idx = row_start + col_idx
            if idx < len(templates):
                tmpl = templates[idx]
                with col:
                    is_selected = st.session_state.selected_template_id == tmpl.get("id")
                    total_pages = tmpl.get("total_pages") or tmpl.get("page_count") or 0
                    tags = tmpl.get("tags", [])
                    age_range = tmpl.get("age_range", "")
                    cover_img = tmpl.get("cover_image", "")
                    desc = tmpl.get("description", "")
                    if len(desc) > 100:
                        desc = desc[:97] + "..."

                    # Build badge HTML for tags and pages
                    badge_html = ""
                    if age_range:
                        badge_html += (
                            f'<span style="background:#FFF3E0;color:#E65100;border-radius:999px;'
                            f'padding:2px 10px;font-size:11px;font-weight:600;margin-right:4px;">'
                            f'Ages {age_range}</span>'
                        )
                    for tag in tags:
                        badge_html += (
                            f'<span style="background:#FCE4EC;color:#AD1457;border-radius:999px;'
                            f'padding:2px 10px;font-size:11px;font-weight:600;margin-right:4px;">'
                            f'{tag}</span>'
                        )
                    if total_pages:
                        badge_html += (
                            f'<span style="background:#E3F2FD;color:#1565C0;border-radius:999px;'
                            f'padding:2px 10px;font-size:11px;font-weight:600;margin-right:4px;">'
                            f'{total_pages} pages</span>'
                        )

                    border_color = "#4A90E2" if is_selected else "#e8e8e8"
                    shadow = "0 4px 16px rgba(74,144,226,0.18)" if is_selected else "0 2px 8px rgba(0,0,0,0.07)"

                    st.markdown(
                        f"""
                        <div style="
                            border: 2px solid {border_color};
                            border-radius: 16px;
                            overflow: hidden;
                            margin-bottom: 20px;
                            background: #fff;
                            box-shadow: {shadow};
                        ">
                        """,
                        unsafe_allow_html=True,
                    )

                    # Fixed-height cover image so all cards align
                    img_html = (
                        f'<div style="height:200px;overflow:hidden;background:#f0f4f8;">'
                        f'<img src="{cover_img}" style="width:100%;height:100%;object-fit:cover;display:block;" />'
                        f'</div>'
                    ) if cover_img else (
                        '<div style="height:200px;background:linear-gradient(135deg,#FFE0F0,#E0F0FF);'
                        'display:flex;align-items:center;justify-content:center;font-size:48px;">📖</div>'
                    )
                    st.markdown(img_html, unsafe_allow_html=True)

                    st.markdown(
                        f"""
                        <div style="padding: 14px 14px 4px 14px;">
                            <div style="margin-bottom:8px;">{badge_html}</div>
                            <div style="font-size:17px;font-weight:700;color:#1a1a2e;margin-bottom:6px;line-height:1.3;">
                                {tmpl.get('name', 'Template')}
                            </div>
                            <div style="font-size:13px;color:#555;margin-bottom:10px;line-height:1.5;">
                                {desc}
                            </div>
                            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                                <span style="font-size:15px;color:#1a1a2e;font-weight:600;">From</span>
                                <span style="font-size:20px;font-weight:800;color:#1a1a2e;">&#8377;149</span>
                            </div>
                            <div style="font-size:12px;color:#2E86AB;margin-bottom:12px;">
                                3 plans available — view details
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    btn_col, _ = st.columns([4, 1])
                    with btn_col:
                        if st.button(
                            "View Book →",
                            key=f"use_template_{tmpl.get('id')}",
                            use_container_width=True,
                            type="primary",
                        ):
                            st.session_state.selected_template_id = tmpl.get("id")
                            st.session_state.selected_template_name = tmpl.get("name")
                            st.session_state.template_preview_mode = True
                            st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

    if not st.session_state.get("selected_template_id") or not st.session_state.get("template_preview_mode"):
        st.caption("Select a template above to preview and purchase.")
        return

    # ══════════════════════════════════════════════════════════════════════
    # TEMPLATE PREVIEW PAGE (shown after clicking "View Book")
    # ══════════════════════════════════════════════════════════════════════
    selected_template_id = st.session_state.selected_template_id
    selected_template_name = st.session_state.selected_template_name
    template_info = next((t for t in templates if t["id"] == selected_template_id), None)

    if not template_info:
        st.error("Template not found.")
        return

    # Back button
    if st.button("← Back to all templates"):
        st.session_state.selected_template_id = None
        st.session_state.template_preview_mode = False
        st.rerun()

    # Cover and info
    template_pages = get_template_pages(selected_template_id)
    cover_img = template_info.get("cover_image", "")

    st.markdown("---")
    col_cover, col_info = st.columns([1, 2])
    with col_cover:
        if cover_img:
            st.image(cover_img, use_container_width=True)
        else:
            st.markdown('<div style="height:250px;background:#f0f4f8;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:48px;">📖</div>', unsafe_allow_html=True)
    with col_info:
        st.markdown(f"## {template_info['name']}")
        st.write(template_info.get("description", "").replace("{name}", "*your child*"))
        st.write(f"**{template_info.get('total_pages', len(template_pages))} pages**")

    # Page preview
    with st.expander(f"Preview all {len(template_pages)} pages", expanded=False):
        for i, page in enumerate(template_pages):
            preview_text = personalize_template_text(page['text_template'], "your child", "Neutral")
            pool_img = get_any_pool_image_for_page(selected_template_id, page['page_number'])
            if pool_img:
                img_col, txt_col = st.columns([1, 2])
                with img_col:
                    try:
                        if pool_img.startswith("data:image"):
                            import base64 as _b64p
                            _raw = _b64p.b64decode(pool_img.split(",", 1)[1])
                            st.image(_raw, use_container_width=True)
                        else:
                            st.image(pool_img, use_container_width=True)
                    except Exception:
                        pass
                with txt_col:
                    st.markdown(f"**Page {page['page_number']}: {page['profession_title']}**")
                    st.write(preview_text)
            else:
                st.markdown(f"**Page {page['page_number']}: {page['profession_title']}**")
                st.write(preview_text)
            if i < len(template_pages) - 1:
                st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════
    # PRICING TIERS
    # ══════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### Choose your plan")

    tier_cols = st.columns(3)

    with tier_cols[0]:
        st.markdown("""
        <div style="border:2px solid #e0e0e0;border-radius:16px;padding:24px 18px;text-align:center;background:#fff;min-height:320px;">
            <div style="font-size:14px;font-weight:700;color:#666;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Basic</div>
            <div style="font-size:36px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">&#8377;149</div>
            <div style="font-size:12px;color:#999;margin-bottom:16px;">Download as-is</div>
            <div style="text-align:left;padding:0 8px;">
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Full template book PDF</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; High quality pages</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Instant download</div>
                <div style="font-size:13px;color:#aaa;margin-bottom:6px;">&#10007; No personalization</div>
                <div style="font-size:13px;color:#aaa;margin-bottom:6px;">&#10007; No custom images</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Download Template - Rs.149", key="tier_basic", use_container_width=True):
            st.session_state.template_purchase_tier = "basic"
            st.session_state.template_purchase_amount = 149
            st.session_state.template_purchase_trigger = True
            st.rerun()

    with tier_cols[1]:
        st.markdown("""
        <div style="border:2px solid #2E86AB;border-radius:16px;padding:24px 18px;text-align:center;background:#f0f9ff;min-height:320px;position:relative;">
            <div style="position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:#2E86AB;color:#fff;padding:3px 14px;border-radius:999px;font-size:11px;font-weight:700;">POPULAR</div>
            <div style="font-size:14px;font-weight:700;color:#2E86AB;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Personalized</div>
            <div style="font-size:36px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">&#8377;249</div>
            <div style="font-size:12px;color:#999;margin-bottom:16px;">Customized with AI images</div>
            <div style="text-align:left;padding:0 8px;">
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Child's name throughout</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; AI-generated illustrations</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Upload child's photo</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Instant PDF download</div>
                <div style="font-size:13px;color:#aaa;margin-bottom:6px;">&#10007; No printed copy</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Personalize - Rs.249", key="tier_personalized", use_container_width=True, type="primary"):
            st.session_state.template_purchase_tier = "personalized"
            st.session_state.template_purchase_amount = 249
            st.session_state.template_show_form = True
            st.rerun()

    with tier_cols[2]:
        st.markdown("""
        <div style="border:2px solid #F4A261;border-radius:16px;padding:24px 18px;text-align:center;background:#fffcf5;min-height:320px;">
            <div style="font-size:14px;font-weight:700;color:#E76F51;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">Premium</div>
            <div style="font-size:36px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">&#8377;699</div>
            <div style="font-size:12px;color:#999;margin-bottom:16px;">Personalized + Printed copy</div>
            <div style="text-align:left;padding:0 8px;">
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Everything in Personalized</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Printed hardcover book</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Delivered to your door</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Premium paper quality</div>
                <div style="font-size:13px;color:#444;margin-bottom:6px;">&#10003; Gift-ready packaging</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Personalize + Print - Rs.699", key="tier_premium", use_container_width=True):
            st.session_state.template_purchase_tier = "premium"
            st.session_state.template_purchase_amount = 699
            st.session_state.template_show_form = True
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════
    # BASIC TIER: Just pay and download
    # ══════════════════════════════════════════════════════════════════════
    if st.session_state.get("template_purchase_trigger") and st.session_state.get("template_purchase_tier") == "basic":
        st.session_state.template_purchase_trigger = False
        st.markdown("---")
        st.markdown("### Complete your purchase")
        st.write(f"**{template_info['name']}** — Template PDF download")
        st.write("Amount: **Rs.149**")
        from payments import create_payment_link
        user_id_pay = st.session_state.get("auth_user", {}).get("id", "")
        user_email_pay = st.session_state.get("auth_user", {}).get("email", "")
        if user_id_pay:
            link_result = create_payment_link(user_id_pay, user_email_pay, 149, f"Template: {selected_template_name}")
            if link_result and link_result.get("link_url"):
                st.markdown(f'<a href="{link_result["link_url"]}" target="_blank" style="display:inline-block;background:#2E86AB;color:#fff;padding:12px 32px;border-radius:8px;text-decoration:none;font-weight:600;">Pay Rs.149 & Download</a>', unsafe_allow_html=True)
            else:
                error_msg = link_result.get("error", "Could not generate payment link.") if link_result else "Could not generate payment link."
                st.error(error_msg)
        else:
            st.warning("Please log in to purchase.")

    # ══════════════════════════════════════════════════════════════════════
    # PERSONALIZED / PREMIUM: Show customize form
    # ══════════════════════════════════════════════════════════════════════
    if st.session_state.get("template_show_form") and st.session_state.get("template_purchase_tier") in ("personalized", "premium"):
        tier_label = "Personalized" if st.session_state.template_purchase_tier == "personalized" else "Premium (Print + Digital)"
        amount = st.session_state.get("template_purchase_amount", 249)

        st.markdown("---")
        st.markdown(f"### Customize your book ({tier_label} — Rs.{amount})")

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

        st.markdown("#### Upload Photos (Optional)")
        st.caption("Upload up to 3 photos of the child to personalize the illustrations.")

        uploaded_files = st.file_uploader(
            "Upload photos",
            type=['png', 'jpg', 'jpeg'],
            accept_multiple_files=True,
            key="template_photos_multi",
            help="Select up to 3 photos",
        )
        photos = list(uploaded_files or [])[:3]
        if photos:
            photo_cols = st.columns(min(len(photos), 3))
            for i, (col, photo) in enumerate(zip(photo_cols, photos)):
                with col:
                    st.image(photo, caption=f"Photo {i + 1}", use_container_width=True)

        st.markdown("---")

        if st.button(f"Generate My Personalized Book (Rs.{amount})", type="primary", use_container_width=True):
            if not child_name:
                st.error("Please enter the child's name")
                return

            with st.spinner("Creating your personalized book..."):
                st.session_state.template_book_data = {
                    'template_id': selected_template_id,
                    'template_name': selected_template_name,
                    'child_name': child_name,
                    'gender': gender,
                    'age': age,
                    'photos': photos,
                    'tier': st.session_state.template_purchase_tier,
                    'amount': amount,
                }
                st.session_state.generate_template_book = True
                st.rerun()


def generate_template_book(api_key: str, book_data: Dict):
    """Generate a complete template book with AI-generated images, using cache when available."""
    try:
        template_id = book_data['template_id']
        child_name = book_data['child_name']
        gender = book_data['gender']
        age = book_data['age']
        photos = book_data.get('photos', [])

        # --- Check Supabase cache first ---
        user_id = st.session_state.get("auth_user", {}).get("id", "")
        if user_id:
            cached = get_cached_template_book(user_id, template_id, child_name, gender, age)
            if cached:
                st.success("✅ Loaded your previously generated book from cache — no regeneration needed!")
                # Re-attach reference image if photos were uploaded this session
                if photos:
                    cached["reference_image_base64"] = convert_uploaded_file_to_base64(photos[0])
                st.session_state.template_generated_book = cached
                return

        pages = get_template_pages(template_id)
        if not pages:
            st.error("No pages found for this template")
            return

        reference_image_base64 = None
        if photos:
            reference_image_base64 = convert_uploaded_file_to_base64(photos[0])

        openrouter_key = st.session_state.get("openrouter_api_key", "")

        generated_book = {
            'template_id': template_id,
            'template_name': book_data['template_name'],
            'child_name': child_name,
            'gender': gender,
            'age': age,
            'reference_image_base64': reference_image_base64,
            'pages': []
        }

        progress_bar = st.progress(0)
        status_text = st.empty()
        total_pages = len(pages)
        age_group = _age_to_group(age)
        use_shared_pool = not bool(reference_image_base64)  # only share generic images

        # Payment gate: non-admin users get 3 free images, then must pay
        from auth import ADMIN_EMAILS
        from payments import FREE_IMAGES_PER_BOOK, template_book_price_inr
        _current_email = st.session_state.get("auth_user", {}).get("email", "")
        _is_admin = _current_email in ADMIN_EMAILS
        book_paid = st.session_state.get("current_book_payment_status") == "paid"
        gen_limit = total_pages if (_is_admin or book_paid) else FREE_IMAGES_PER_BOOK

        import time as _time
        _images_generated_since_pause = 0
        _preview_container = st.container()

        for idx, page in enumerate(pages):
            status_text.text(f"Generating page {idx + 1} of {total_pages}: {page['profession_title']}")

            personalized_text = personalize_template_text(page['text_template'], child_name, gender)
            personalized_image_prompt = personalize_template_image_prompt(
                page['image_prompt_template'], child_name, gender, age
            )

            # Check shared pool first (skip if reference photo -- image is person-specific)
            image_url = None
            if use_shared_pool:
                image_url = get_shared_pool_image(template_id, page['page_number'], age_group, gender)
                if image_url:
                    status_text.text(f"Loading cached image for page {idx + 1}...")

            if not image_url:
                # Enforce payment gate: only generate images up to gen_limit
                if idx < gen_limit:
                    # Retry logic: 2 attempts with a SHORT 8s pause on failure.
                    # Hard rate-limit responses (429) are handled by exponential
                    # backoff inside vertex_client — we don't need a global
                    # proactive sleep here. The old 60s-every-3-images pause
                    # cost 4 minutes on a 12-page book for no real benefit.
                    for _attempt in range(2):
                        image_url = generate_page_image(api_key, personalized_image_prompt, reference_image_base64, openrouter_key=openrouter_key)
                        if image_url:
                            break
                        if _attempt == 0:
                            status_text.text(f"Retrying page {idx + 1}…")
                            _time.sleep(8)

                    if image_url and use_shared_pool:
                        save_to_shared_pool(template_id, page['page_number'], age_group, gender, image_url)
                else:
                    image_url = None

            generated_book['pages'].append({
                'page_number': page['page_number'],
                'profession_title': page['profession_title'],
                'text': personalized_text,
                'image_prompt': personalized_image_prompt,
                'image_url': image_url
            })

            # Show image progressively as it's generated
            if image_url:
                with _preview_container:
                    st.image(image_url, caption=f"Page {page['page_number']}: {page['profession_title']}", width=300)

            progress_bar.progress((idx + 1) / total_pages)

        # Inform non-admin users about payment requirement
        if not _is_admin and not book_paid and total_pages > FREE_IMAGES_PER_BOOK:
            generated_count = len([p for p in generated_book['pages'] if p.get('image_url')])
            if generated_count <= FREE_IMAGES_PER_BOOK:
                status_text.text(f"Preview ready! {FREE_IMAGES_PER_BOOK} free images generated. Purchase to unlock all {total_pages} pages.")
            else:
                status_text.text("Book generation complete!")
        else:
            status_text.text("Book generation complete!")
        st.session_state.template_generated_book = generated_book

        # --- Persist to Supabase cache ---
        if user_id:
            save_template_book_to_cache(user_id, template_id, child_name, gender, age, generated_book)

    except Exception as e:
        logger.error(f"Error generating template book: {e}")
        st.error(f"Failed to generate book: {e}")



def _template_page_image_to_pil(page: Dict) -> Optional[Image.Image]:
    """Convert template page image_url (data URL) to PIL Image."""
    url = page.get("image_url")
    if not url:
        return None
    try:
        if url.startswith("data:image"):
            b64 = url.split(",", 1)[-1]
            raw = base64.b64decode(b64)
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            return img
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

            img_io = io.BytesIO()
            img_pil.save(img_io, format="PNG")
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
            img_io = io.BytesIO()
            img_pil.save(img_io, format="PNG")
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


def generate_page_image(api_key: str, prompt: str, reference_image_base64: Optional[str] = None, openrouter_key: str = "") -> Optional[str]:
    """Generate a single image using Gemini API with optional reference image.

    Falls back to OpenRouter (Gemini models) when the primary call fails.
    """
    no_text_instruction = "CRITICAL: NO TEXT in this image. No words, letters, numbers, speech bubbles, captions, signs, or labels. Pure illustration only."
    if "cartoon animated" in prompt.lower() or "cel-shaded" in prompt.lower():
        style_modifiers = "Children's book art, high quality, bold clean outlines, smooth cel shading"
    else:
        style_modifiers = "Watercolor illustration style, soft edges, gentle colors, children's book art, high quality"
    likeness_note = ""
    if reference_image_base64:
        likeness_note = (
            " The child character MUST match the reference photo exactly -- same face shape, "
            "skin tone, hair color, hair style, eye color, and overall appearance. "
            "Keep the child recognizable across all pages."
        )
    enhanced_prompt = f"{no_text_instruction}. {prompt}.{likeness_note} {style_modifiers}. {no_text_instruction}"

    result_url = _call_gemini_image_api(api_key, enhanced_prompt, reference_image_base64)
    if result_url:
        return result_url

    # --- OpenRouter fallback (Gemini models, no ChatGPT/DALL-E) ---
    if openrouter_key:
        logger.info("Gemini image API failed, trying OpenRouter fallback")
        result_url = _call_openrouter_image(openrouter_key, enhanced_prompt)
        if result_url:
            return result_url

    logger.warning("All image generation attempts failed for this page")
    return None


def _call_gemini_image_api(api_key: str, enhanced_prompt: str, reference_image_base64: Optional[str] = None) -> Optional[str]:
    """Call Vertex AI image generation (primary) with Google AI fallback. Returns data URL or None."""
    try:
        from vertex_client import call_gemini_image
        return call_gemini_image(enhanced_prompt, api_key=api_key, reference_image_b64=reference_image_base64)
    except Exception as e:
        logger.warning(f"Gemini image API exception: {e}")
    return None


def _call_openrouter_image(openrouter_key: str, prompt: str) -> Optional[str]:
    """Try to generate an image via OpenRouter using Gemini models (no DALL-E/ChatGPT)."""
    models = [
        "google/gemini-2.0-flash-exp:free",
        "google/gemini-flash-1.5-8b",
        "google/gemini-flash-1.5",
    ]
    for model in models:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://children-book-generator.app",
                    "X-Title": "Children's Book Generator",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                },
                timeout=120,
            )
            if response.status_code != 200:
                logger.warning(f"OpenRouter {model} returned {response.status_code}")
                continue
            result = response.json()
            choices = result.get("choices", [])
            if not choices:
                continue
            content = choices[0].get("message", {}).get("content", "")
            # Look for inline image data in list or string content
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "image_url":
                        img_url = part.get("image_url", {}).get("url", "")
                        if img_url.startswith("data:image"):
                            return img_url
                        if img_url:
                            img_resp = requests.get(img_url, timeout=30)
                            if img_resp.status_code == 200:
                                b64 = base64.b64encode(img_resp.content).decode()
                                return f"data:image/jpeg;base64,{b64}"
            if isinstance(content, str) and content.startswith("data:image"):
                return content
            logger.info(f"OpenRouter {model} returned text only — no image in response")
        except Exception as ex:
            logger.warning(f"OpenRouter {model} exception: {ex}")
    return None


def display_template_book_preview(book_data: Dict, api_key: Optional[str] = None):
    """Display the generated template book for preview with edit, regenerate, and download."""

    # --- Handle page deletion ---
    if st.session_state.get("delete_template_page_idx") is not None:
        idx = st.session_state.delete_template_page_idx
        st.session_state.delete_template_page_idx = None
        pages = book_data.get("pages", [])
        if 0 <= idx < len(pages):
            del book_data["pages"][idx]
            # Clear all per-page session keys so they reinitialise correctly
            for key in list(st.session_state.keys()):
                if (key.startswith("template_page_text_") or
                        key.startswith("template_page_prompt_") or
                        key.startswith("template_text_area_") or
                        key.startswith("template_prompt_area_")):
                    del st.session_state[key]
            st.rerun()

    # --- Handle single-page image regeneration ---
    if api_key and st.session_state.get("regenerate_template_page_idx") is not None:
        idx = st.session_state.regenerate_template_page_idx
        st.session_state.regenerate_template_page_idx = None
        pages = book_data.get("pages", [])
        if 0 <= idx < len(pages):
            page = pages[idx]
            # Use the edited prompt from session state (allows bypassing guardrails)
            prompt_key = f"template_page_prompt_{idx}"
            edited_prompt = st.session_state.get(prompt_key, page.get("image_prompt", ""))
            ref_b64 = book_data.get("reference_image_base64")
            openrouter_key = st.session_state.get("openrouter_api_key", "")
            with st.spinner(f"Regenerating image for page {idx + 1}..."):
                new_url = generate_page_image(api_key, edited_prompt, ref_b64, openrouter_key=openrouter_key)
            if new_url:
                book_data["pages"][idx]["image_url"] = new_url
                book_data["pages"][idx]["image_prompt"] = edited_prompt
                user_id = st.session_state.get("auth_user", {}).get("id", "")
                if user_id:
                    save_template_book_to_cache(
                        user_id,
                        book_data.get("template_id", ""),
                        book_data.get("child_name", ""),
                        book_data.get("gender", ""),
                        book_data.get("age", 0),
                        book_data,
                    )
            else:
                st.error(f"Image generation failed for page {idx + 1}. Edit the image prompt below to try a different description, then click Regenerate again.")

    # Payment gate check for template book preview
    from auth import ADMIN_EMAILS
    from payments import (
        FREE_IMAGES_PER_BOOK, pdf_price_inr, print_price_inr,
        is_cashfree_configured, create_payment_link, confirm_payment_and_credit,
        save_pending_payment_for_reminders, template_book_price_inr,
    )
    _current_email_tpl = st.session_state.get("auth_user", {}).get("email", "")
    _is_admin_tpl = _current_email_tpl in ADMIN_EMAILS
    book_paid_tpl = st.session_state.get("current_book_payment_status") == "paid"
    total_tpl_pages = len(book_data.get("pages", []))
    images_with_content = len([p for p in book_data.get("pages", []) if p.get("image_url")])
    needs_payment_tpl = (
        not _is_admin_tpl
        and total_tpl_pages > FREE_IMAGES_PER_BOOK
        and not book_paid_tpl
    )

    if needs_payment_tpl:
        _pdf_price = pdf_price_inr()
        _print_price = print_price_inr()
        st.warning(f"Preview: {FREE_IMAGES_PER_BOOK} free images generated. Unlock the full {total_tpl_pages}-page book below.")
        st.markdown(
            f"""
            | Option | What you get | Price |
            |--------|-------------|-------|
            | **PDF Download** | Digital PDF file, download instantly | **Rs.{_pdf_price}** |
            | **Printed Book** | Physical copy shipped to your address | **Rs.{_print_price}** |
            """,
        )
        user_id_pay = st.session_state.get("auth_user", {}).get("id", "")
        if is_cashfree_configured():
            pending_link_id = st.session_state.get("pending_payment_link_id")
            if pending_link_id:
                col_check, col_new = st.columns(2)
                with col_check:
                    if st.button("I've paid -- continue", type="primary", use_container_width=True, key="tpl_pay_confirm"):
                        if confirm_payment_and_credit(pending_link_id, user_id_pay):
                            st.session_state.current_book_payment_status = "paid"
                            st.session_state.pending_payment_link_id = None
                            st.session_state.pending_payment_url = None
                            st.success("Payment confirmed! Generating remaining images...")
                            st.rerun()
                        else:
                            st.error("Payment not confirmed yet. Complete the payment and try again.")
                with col_new:
                    if st.button("New payment link", use_container_width=True, key="tpl_pay_new"):
                        st.session_state.pending_payment_link_id = None
                        st.session_state.pending_payment_url = None
                        st.rerun()
                pending_url = st.session_state.get("pending_payment_url", "")
                if pending_url:
                    st.markdown(
                        f'<a href="{pending_url}" target="_blank" style="display:inline-block;'
                        f'background:#2563eb;color:white;padding:10px 24px;border-radius:8px;'
                        f'font-weight:700;text-decoration:none;">Open payment page</a>',
                        unsafe_allow_html=True,
                    )
            else:
                user_email_pay = _current_email_tpl or "user@example.com"
                child_name_pay = book_data.get("child_name", "")
                col_pdf, col_print = st.columns(2)
                with col_pdf:
                    if st.button(f"PDF Download -- Rs.{_pdf_price}", type="primary", use_container_width=True, key="tpl_pay_pdf"):
                        with st.spinner("Creating payment link..."):
                            result = create_payment_link(
                                user_id_pay, user_email_pay, _pdf_price,
                                f"PDF book for {child_name_pay} – {total_tpl_pages} pages"
                            )
                        if result:
                            save_pending_payment_for_reminders(
                                user_id=user_id_pay, user_email=user_email_pay,
                                amount_inr=_pdf_price, child_name=child_name_pay,
                                book_title=book_data.get("template_name", ""),
                                product_type="pdf",
                                template_id=book_data.get("template_id", ""),
                                payment_link_id=result["link_id"],
                                payment_link_url=result["link_url"],
                            )
                            st.session_state.pending_payment_link_id = result["link_id"]
                            st.session_state.pending_payment_url = result["link_url"]
                            st.session_state.current_book_payment_status = "pending"
                            st.rerun()
                        else:
                            st.error("Could not create payment link.")
                with col_print:
                    if st.button(f"Printed Book -- Rs.{_print_price}", use_container_width=True, key="tpl_pay_print"):
                        with st.spinner("Creating payment link..."):
                            result = create_payment_link(
                                user_id_pay, user_email_pay, _print_price,
                                f"Printed book for {child_name_pay} – {total_tpl_pages} pages"
                            )
                        if result:
                            save_pending_payment_for_reminders(
                                user_id=user_id_pay, user_email=user_email_pay,
                                amount_inr=_print_price, child_name=child_name_pay,
                                book_title=book_data.get("template_name", ""),
                                product_type="print",
                                template_id=book_data.get("template_id", ""),
                                payment_link_id=result["link_id"],
                                payment_link_url=result["link_url"],
                            )
                            st.session_state.pending_payment_link_id = result["link_id"]
                            st.session_state.pending_payment_url = result["link_url"]
                            st.session_state.current_book_payment_status = "pending"
                            st.rerun()
                        else:
                            st.error("Could not create payment link.")
        else:
            st.info("Payment gateway not configured.")
            if _is_admin_tpl or st.button("Unlock (no payment gateway)", key="tpl_unlock_bypass"):
                st.session_state.current_book_payment_status = "paid"
                st.rerun()

    # After payment: if some pages still lack images, offer to generate them
    pages_without_images = [i for i, p in enumerate(book_data.get("pages", [])) if not p.get("image_url")]
    if (book_paid_tpl or _is_admin_tpl) and pages_without_images and api_key:
        st.info(f"{len(pages_without_images)} page(s) still need images. Click below to generate them.")
        if st.button("Generate remaining images", type="primary", key="tpl_gen_remaining"):
            st.session_state.generate_remaining_template_pages = True
            st.rerun()
        if st.session_state.get("generate_remaining_template_pages"):
            import time as _time_rem
            st.session_state.generate_remaining_template_pages = False
            openrouter_key = st.session_state.get("openrouter_api_key", "")
            ref_b64 = book_data.get("reference_image_base64")
            use_pool_rem = not bool(ref_b64)
            age_group_rem = _age_to_group(book_data.get("age", 5))
            template_id_rem = book_data.get("template_id", "")
            gender_rem = book_data.get("gender", "boy")
            progress = st.progress(0)
            status = st.empty()
            preview_ctr = st.container()
            _gen_count = 0
            for count, pidx in enumerate(pages_without_images):
                page = book_data["pages"][pidx]
                status.text(f"Generating image for page {pidx + 1}...")

                # Check shared pool first
                img_url = None
                if use_pool_rem:
                    img_url = get_shared_pool_image(template_id_rem, page.get("page_number", pidx + 1), age_group_rem, gender_rem)

                if not img_url:
                    for _attempt in range(2):
                        img_url = generate_page_image(api_key, page.get("image_prompt", ""), ref_b64, openrouter_key=openrouter_key)
                        if img_url:
                            break
                        if _attempt == 0:
                            status.text(f"Retrying page {pidx + 1}…")
                            _time_rem.sleep(8)

                    if img_url and use_pool_rem:
                        save_to_shared_pool(template_id_rem, page.get("page_number", pidx + 1), age_group_rem, gender_rem, img_url)

                if img_url:
                    book_data["pages"][pidx]["image_url"] = img_url
                    with preview_ctr:
                        st.image(img_url, caption=f"Page {pidx + 1}: {page.get('profession_title', '')}", width=300)

                progress.progress((count + 1) / len(pages_without_images))

            status.text("All images generated!")
            user_id_cache = st.session_state.get("auth_user", {}).get("id", "")
            if user_id_cache:
                save_template_book_to_cache(
                    user_id_cache, book_data.get("template_id", ""),
                    book_data.get("child_name", ""), book_data.get("gender", ""),
                    book_data.get("age", 0), book_data,
                )
            st.rerun()

    st.success(f"Your personalized book for **{book_data['child_name']}** is ready!")
    st.markdown("---")
    st.markdown("### Book Preview")

    for idx, page in enumerate(book_data["pages"]):
        # Lock pages beyond free limit for unpaid non-admin users
        if needs_payment_tpl and idx >= FREE_IMAGES_PER_BOOK:
            # Show image preview (read-only) if available from pool, otherwise show locked
            if page.get("image_url"):
                with st.container():
                    st.markdown(f"**Page {page['page_number']}: {page['profession_title']}**")
                    try:
                        if page["image_url"].startswith("data:image"):
                            _pil = _template_page_image_to_pil(page)
                            if _pil:
                                _buf = io.BytesIO()
                                _pil.save(_buf, format="JPEG", quality=70)
                                st.image(_buf.getvalue(), use_container_width=True)
                            else:
                                _raw = base64.b64decode(page["image_url"].split(",", 1)[1])
                                st.image(_raw, use_container_width=True)
                        else:
                            st.image(page["image_url"], use_container_width=True)
                    except Exception:
                        pass
                    st.caption("Purchase to download and customize this page")
                    st.markdown("---")
            else:
                st.markdown(
                    f"<div style='background:#f0f0f0;border-radius:8px;padding:20px;margin:8px 0;"
                    f"text-align:center;color:#999;'>"
                    f"Page {page['page_number']}: {page['profession_title']} -- Purchase to unlock.</div>",
                    unsafe_allow_html=True,
                )
            continue

        with st.container():
            # Page header + delete button on the same row
            hcol1, hcol2 = st.columns([5, 1])
            with hcol1:
                st.markdown(f"#### Page {page['page_number']}: {page['profession_title']}")
            with hcol2:
                if st.button("Delete", key=f"del_tpl_page_{idx}", use_container_width=True, help="Remove this page from the book"):
                    st.session_state.delete_template_page_idx = idx
                    st.rerun()

            col1, col2 = st.columns([1, 1])

            with col1:
                # Image display
                if page.get("image_url"):
                    try:
                        if page["image_url"].startswith("data:image"):
                            pil_img = _template_page_image_to_pil(page)
                            if pil_img is not None:
                                buf = io.BytesIO()
                                pil_img.save(buf, format="JPEG", quality=90)
                                st.image(buf.getvalue(), use_container_width=True)
                            else:
                                image_bytes = base64.b64decode(page["image_url"].split(",", 1)[1])
                                st.image(image_bytes, use_container_width=True)
                        else:
                            st.image(page["image_url"], use_container_width=True)
                    except Exception as e:
                        st.error(f"Failed to display image: {e}")
                else:
                    st.info("No image generated for this page")

                # Regenerate button: only show for paid users or admins, max 5 regenerations
                _max_regenerates = 5
                _regen_count = st.session_state.get("template_regen_count", 0)
                if api_key and (book_paid_tpl or _is_admin_tpl):
                    if _regen_count < _max_regenerates or _is_admin_tpl:
                        if st.button(f"Regenerate image ({_max_regenerates - _regen_count} left)", key=f"regen_tpl_img_{idx}", use_container_width=True):
                            st.session_state.template_regen_count = _regen_count + 1
                            st.session_state.regenerate_template_page_idx = idx
                            st.rerun()
                    else:
                        st.caption("Maximum regenerations reached (5/5)")

            with col2:
                # Editable story text
                st.markdown("**Story text:**")
                key_text = f"template_page_text_{idx}"
                if key_text not in st.session_state:
                    st.session_state[key_text] = page.get("text", "")
                current_text = st.text_area(
                    "Story text",
                    value=st.session_state[key_text],
                    height=100,
                    key=f"template_text_area_{idx}",
                    label_visibility="collapsed",
                )
                st.session_state[key_text] = current_text
                book_data["pages"][idx]["text"] = current_text

                # Editable image prompt
                st.markdown("**Image prompt** *(edit to bypass guardrails, then regenerate):*")
                key_prompt = f"template_page_prompt_{idx}"
                if key_prompt not in st.session_state:
                    st.session_state[key_prompt] = page.get("image_prompt", "")
                current_prompt = st.text_area(
                    "Image prompt",
                    value=st.session_state[key_prompt],
                    height=120,
                    key=f"template_prompt_area_{idx}",
                    label_visibility="collapsed",
                )
                st.session_state[key_prompt] = current_prompt
                book_data["pages"][idx]["image_prompt"] = current_prompt

            st.markdown("---")

    # Download section -- only for paid users or admins
    if book_paid_tpl or _is_admin_tpl:
        st.markdown("### Download your book")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            buf = io.BytesIO()
            create_template_pdf(book_data, buf)
            pdf_bytes = buf.getvalue()
            st.download_button(
                label="Download PDF",
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
    elif needs_payment_tpl:
        st.markdown("---")
        st.info("Purchase the book above to download the PDF or order a printed copy.")

    col_json, col_another = st.columns(2)
    with col_json:
        if book_paid_tpl or _is_admin_tpl:
            try:
                ts_json = datetime.now().strftime("%Y%m%d_%H%M%S")
                json_str = json.dumps(book_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"book-template-{ts_json}.json",
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
                if (key in ("template_generated_book", "template_book_data", "generate_template_book") or
                        key.startswith("template_page_text_") or
                        key.startswith("template_page_prompt_") or
                        key == "regenerate_template_page_idx" or
                        key == "delete_template_page_idx"):
                    del st.session_state[key]
            st.rerun()
