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
        "id": "b1111111-1111-1111-1111-111111111111",
        "name": "Legends in the Making",
        "description": (
            "Seventeen real, full-page childhood stories of world champions in cricket, "
            "football, tennis, F1, chess, athletics, swimming, basketball, gymnastics and "
            "boxing. Each page tells the moment that made them keep showing up — and "
            "ends with a quiet note to {name}."
        ),
        "cover_image": "https://images.pexels.com/photos/863988/pexels-photo-863988.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 19,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "A Book of Legends, for You",
                "text_template": (
                    "Hello, {name}! Every legend you'll meet in this book started as a child just like you. They tripped, they fell, they doubted themselves — and kept going. Their stories are not just about winning; they are about the moments that made them keep showing up. As you read, ask yourself after each one: which spark inside *me* could one day light up the world like theirs?"
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a warm cosy bedroom with a child looking out a window at a starry night sky. Soft glowing silhouettes of a tennis racket, a cricket bat, a football, a chess king, a javelin, a swim cap, a racing helmet and a basketball float like constellations among the stars. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Sachin Tendulkar — Cricket · India",
                "text_template": (
                    "In the heart of Mumbai, in a small flat in the Sahitya Sahawas colony, lived a four-year-old boy named Sachin. He was so full of restless energy that his family did not know what to do with him. He climbed cupboards, mimicked John McEnroe, and drove everyone mad with mischief. His older brother Ajit, ten years his senior, watched him carefully. Ajit saw something nobody else had spotted — when Sachin held a tennis racket and swung at a ball, his hand-eye coordination was strange and extraordinary.\\n\\nWhen Sachin was eleven, Ajit took him to Shivaji Park to meet a quiet, watchful coach named Ramakant Achrekar. The first time Sachin batted, Achrekar shook his head — too tense, too eager. He told Ajit, 'He has talent, but he plays like he is already trying to win Test matches.' Ajit asked: would the coach take him on anyway? Yes — but there would be conditions.\\n\\nEvery morning Sachin woke at 5 a.m., caught the local train from Bandra, and batted for hours before school. After school he returned to bat again until dark. Achrekar invented an unusual exercise: he placed a single one-rupee coin on top of Sachin's middle stump. Any bowler who got him out kept it. If Sachin survived the day, the coin was his. In his early years Sachin collected thirteen coins. He still keeps them in a small box. They mean more to him than any trophy.\\n\\nBy fourteen, Sachin and Vinod Kambli put on a school record partnership of 664 runs in a Harris Shield match — over two full days at the crease. Selectors could not ignore him. At sixteen, while his classmates studied for board exams, Sachin Tendulkar walked out at Karachi against Pakistan — against Wasim Akram, Waqar Younis and Imran Khan, three of the fastest bowlers in cricket history. He was hit on the nose by a Waqar bouncer and bled. He waved away medical help and kept batting.\\n\\nOver the next twenty-four years, Sachin scored 100 international centuries — more than any human in history. A billion people learned to stand still each time he walked to the crease. Schools paused assemblies. Taxis pulled over. Surgeons rescheduled procedures.\\n\\nYears later, asked what he had learned that mattered most, Sachin pointed to the coins. 'Achrekar Sir did not just teach me cricket. He taught me discipline. He taught me to respect every single ball. He taught me that very big things are built from very, very small days.'\\n\\n{name}, the smallest daily habit you have right now — the tiny thing you do without anyone watching — is the seed of everything you will one day become."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: an 11-year-old curly-haired Indian boy in white cricket clothes at a sunny Mumbai maidan, gripping a wooden cricket bat almost as tall as him. Coach watches from behind the stumps where a one-rupee coin glints. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Sachin_Tendulkar_at_the_BMW_Pro-Am_Golf_event,_New_Delhi,_2009.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 3,
                "profession_title": "Virat Kohli — Cricket · India",
                "text_template": (
                    "On the night of 18 December 2006, eighteen-year-old Virat Kohli was batting for Delhi in a Ranji Trophy match at the Feroz Shah Kotla stadium. He was 40 not out at the close of play. He went home, ate dinner with his father Prem — and a few hours later, in the middle of the night, his father suffered a sudden heart attack and died. Virat was nineteen days short of his nineteenth birthday. He cried until dawn.\\n\\nIn the morning, instead of staying home with his grieving mother and brother, Virat called his coach Rajkumar Sharma. His voice was unsteady. He asked one question: would the team let him bat? The funeral could wait a few hours. The team had a chance to save the match. He wanted to be there. His coach agreed — but with worry. Was he sure?\\n\\nVirat walked out at number five with red eyes. He faced over a hundred and forty deliveries. He scored 90 runs. He stayed at the crease for the morning session and most of the afternoon, helping save the match for Delhi. Then he took off his pads, walked off the field, went home, and lit his father's funeral pyre.\\n\\nYears later, in an interview, Virat said something every cricketer remembers: 'My father's belief in me was my only fuel that day. I felt closer to him on that field than I would have felt sitting at home.'\\n\\nWhat Virat chose that morning was not cricket over grief. It was discipline as a way of carrying someone he loved with him. He turned the worst day of his life into a small unbreakable promise: I will never let down the thing my father believed in.\\n\\nThat promise became the engine of everything that came after. The captaincy of India. The Test, ODI and T20 records. The 80-plus international centuries. The obsession with fitness that single-handedly changed how Indian cricket trains. The hunger that made him one of the most feared chasers in the history of the sport.\\n\\nA famous photograph from late in his career shows Virat after a century — kissing his wedding ring and pointing skyward in the same motion. He has explained the gesture: it is for two people. His wife, and his father.\\n\\n{name}, sometimes the people we love most leave us before we get to show them everything we can become. The way we honour them is not by stopping. It is by showing up the next morning, eyes still red, and saying — quietly, only to ourselves — 'watch me. This one is for you.'"
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a young Indian cricketer in white kit walking out of a dressing room at dawn with quiet determination, bat under arm, teammate's hand on shoulder. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Virat_Kohli_in_PMs_residence.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 4,
                "profession_title": "Steve Smith — Cricket · Australia",
                "text_template": (
                    "Stephen Peter Devereux Smith grew up in the suburbs of Sydney, Australia. He was a thin, intense boy who could not bear to stop moving. His father Peter, a chemist, built him a fold-up cricket cage in the back garden — a concrete pitch, fishing-line stumps — and bowled to him for hours every weekend.\\n\\nWhen Steve was thirteen, a coach at his school watched him bat and said quietly, 'He plays the wrong way.' Steve's bat did not go straight back. His feet moved before the bowler released. His hands fidgeted before every delivery. To classical coaches, it looked all wrong.\\n\\nBut Steve did something unusual for a teenager — he started a notebook. Every net session, every backyard innings, he scribbled down what worked and what did not. Where his back foot landed. Where his head was. How tense his hands were. His friends laughed at him. Steve kept writing.\\n\\nWhen he was first picked for Australia at twenty-one, it was as a leg-spinner who could bat a bit. The selectors did not trust his batting. He took only nine wickets in his early Tests and was dropped. People said he did not have the technique. He disappeared from the Australian team for two years.\\n\\nWhile he was gone, he did not try to fix his unorthodox style. He doubled down on understanding it. He filmed every practice. He worked with coach Trent Woodhill to map his own movements with surgical precision. He realised his shuffle was not a flaw — it was how he gathered information about the ball. His fidget was not nervousness — it was rhythm.\\n\\nIn 2013 he returned. Two years later he was Australia's captain. By 2017 his Test batting average was a stunning 70 — second only to Sir Donald Bradman in the entire history of cricket. He scored seven double centuries. He turned the strangest stance in modern cricket into the most accurate run-scoring engine of his generation.\\n\\nIn an interview at the height of his career, Smith said: 'Every batsman gets told what is wrong with their game. I just decided to fall in love with what was different about mine instead of trying to copy what everyone else looked like.'\\n\\n{name}, the world will spend its whole life trying to tell you what is wrong with you. The trick is not to argue with them. The trick is to study yourself so carefully and so honestly that one day even your weaknesses become a kind of weapon."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a thin teenage Australian boy with sandy hair in his suburban Sydney backyard at dusk, batting with a famously twitchy stance. A weathered notebook open on the grass. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Steve_Smith_June_2015.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 5,
                "profession_title": "Lionel Messi — Football · Argentina",
                "text_template": (
                    "In a working-class neighbourhood of Rosario, Argentina, a tiny boy named Lionel Andrés Messi grew up kicking footballs in the dust with his older brothers. By age five he was already so much better than other children that adults gathered to watch him play. His grandmother Celia — the one who first signed him up at a local club at age six — used to say, 'This child is something else.'\\n\\nWhen Leo was eleven, his family noticed he had stopped growing. Doctors diagnosed him with a growth hormone deficiency. He needed daily injections that cost almost a thousand US dollars a month. His father Jorge worked at a steel factory. His mother Celia cleaned houses. They could not afford it. The Argentine club Newell's Old Boys paid for part of the treatment for a while, then stopped.\\n\\nIn September 2000, a thirteen-year-old Leo flew to Barcelona for a trial. He was so small the coaches called him 'la pulga' — the flea. The technical director, Carles Rexach, watched him play for ten minutes and tore the trial short. He took a napkin from a café table, wrote a one-line contract on it, and handed it to Leo's father: 'I commit, on this napkin, to sign the player Lionel Messi to FC Barcelona.' The club would pay for the rest of his treatment. The family had to move to Spain.\\n\\nFor three years Leo gave himself those injections in his own legs each night before bed. Sometimes he cried because he missed his grandmother, who had passed away while he was in Argentina. He pointed at the sky every time he scored — a small private thank-you to her — and he has done it ever since, in every stadium, on every continent.\\n\\nHe grew up to win eight Ballon d'Or trophies — the most ever. He won the Champions League four times. In 2022, at age thirty-five, he led Argentina to victory in the FIFA World Cup — the only thing missing from his career. In the final he scored, he led, he wept on the pitch. The whole of Argentina shut down to mourn its way into joy.\\n\\nThe injections nobody saw shaped the legend everybody now sees.\\n\\n{name}, the hardest, quietest, most painful work of your life will probably be invisible to everyone except you. Do it anyway. That work is the foundation. The trophies you might one day hold are just the part that catches the light."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a small Argentine boy with brown hair dribbling a worn rubber football down a Rosario street at sunset. Older kids chase but can't catch him. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Lionel_Messi_20180626.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 6,
                "profession_title": "Cristiano Ronaldo — Football · Portugal",
                "text_template": (
                    "On the small Atlantic island of Madeira, Portugal, a boy named Cristiano Ronaldo dos Santos Aveiro grew up in a tiny tin-roofed house his family rented. His father José Dinis was the kit-man at the local club and struggled with alcoholism. His mother Dolores worked as a cook. Four of them lived in one shared room. There was often not enough food.\\n\\nFootball was Cristiano's escape. He played in the streets until past midnight, kicking a ball against the cobblestone walls of his neighbourhood, infuriating the neighbours. The teachers at school called him 'crybaby' because he wept whenever his team lost. He did not see losing as something normal. He saw it as something to refuse.\\n\\nWhen he was twelve, he was scouted by Sporting Lisbon — one of Portugal's biggest clubs. He had to move alone to Lisbon, hundreds of kilometres from his family. He was bullied at the academy for his thick Madeiran accent. He cried into his pillow every night. He thought about quitting and going home.\\n\\nHe did not. Instead, he made a small daily promise that has not changed in the twenty-five years since: be the first on the training pitch, the last to leave.\\n\\nAt fourteen, he was diagnosed with a racing heart condition called tachycardia that could have ended his football career. He underwent surgery and was back training a few days later. At sixteen, in a friendly against Manchester United, he played so well that the United players begged Sir Alex Ferguson to sign him. Ferguson did. Six years later, Cristiano was the best footballer in the world.\\n\\nHe has won five Ballon d'Or trophies. Five Champions Leagues. He has scored more international goals than any other male footballer in history — over 130 for Portugal alone. At nearly forty years old, he is still training six hours a day.\\n\\nPeople often ask the secret. Cristiano says the same thing every time: 'Talent without working hard is nothing. I never let myself believe I am talented. That is what keeps me improving.'\\n\\n{name}, the most dangerous belief in the world is that talent is a gift you were either born with or you weren't. The truth is the opposite. Talent is a name people give you after they see how hard you have already worked. Don't wait for the talent to arrive. Start the work."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a thin 12-year-old Portuguese boy kicking a ball against a stone wall under moonlight on a quiet Madeira street. Stars above. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Cristiano_Ronaldo_2018.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 7,
                "profession_title": "Roger Federer — Tennis · Switzerland",
                "text_template": (
                    "Roger Federer grew up in Basel, Switzerland, the youngest child of South African mother Lynette and Swiss father Robert. He started swinging at tennis balls at age three. By eight he was on competitive courts. By ten he had a serious problem nobody talked about: a terrible, ungovernable temper.\\n\\nWhen things went wrong on court, young Roger would scream, swear, throw his racket, sometimes break it. He cried after wins. He cried after losses. He would tell his coaches that everything was their fault. His parents were embarrassed. His own talent was becoming his prison.\\n\\nOne coach, Peter Carter — an Australian who would later become a second father to Roger — sat him down at age fourteen and said: 'You have to choose. You can be very good and very angry, and the world will never love you. Or you can be great, and your name will mean something more than just trophies.'\\n\\nRoger spent the next four years wearing his short fuse down the way you wear down a sharp stone — slowly, against itself. He learned to breathe between points. He learned to compliment opponents who beat him. He learned to bow, very slightly, to each crowd after each win.\\n\\nIn 2002, Peter Carter died in a car accident in South Africa, on holiday. Roger was twenty-one. He flew to the funeral and wept for a man who had taught him not just tennis but who he wanted to be. From that day on, every match he played was, in part, for Peter.\\n\\nHe won his first Wimbledon a year later. He went on to win twenty Grand Slam titles. He played for twenty-five years. He held world number one for 237 consecutive weeks — a record nobody is close to.\\n\\nWhen he retired in 2022, his great rival Rafael Nadal cried on the bench beside him, holding his hand. The whole world watched two grown men cry, hand in hand, at the end of an era. Roger was not just remembered for the tennis. He was remembered for the elegance, the grace under pressure, the bowing to crowds, the deep love for opponents. That was the temper he had chosen, day by day, to leave behind.\\n\\n{name}, the parts of yourself you are most ashamed of right now are the same parts you have the most power to change. The person you can become if you keep choosing — gently, daily — is bigger than you can possibly imagine."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a 12-year-old Swiss boy with curly brown hair sitting alone on a clay tennis court, racket on his lap, eyes closed in thought. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/R_Federer_2009_Madrid_(7).jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 8,
                "profession_title": "Serena Williams — Tennis · USA",
                "text_template": (
                    "In Compton, California, in the late 1980s, a man named Richard Williams sat watching a TV news clip about a tennis player who had just won a tournament cheque. He turned to his wife Oracene and said, 'Our daughters are going to play tennis.' He did not know how to play. The couple had two little girls — Venus and Serena, ages five and four.\\n\\nCompton in those years was one of the toughest neighbourhoods in America. The tennis courts where Richard took his daughters had cracks running through them. There was broken glass on the lines. Sometimes there was gunfire in the distance. Richard would sweep the courts each morning before practice. He told his daughters: 'You do not play tennis to belong somewhere. You play because you love it. Belonging will follow.'\\n\\nSerena trained six days a week from age four. She and Venus were the only Black children at almost every tournament. Other parents whispered. Coaches said the girls were 'too aggressive,' 'too muscular,' 'too loud.' Richard told them all to ignore it. He pulled the girls out of competitive junior tennis entirely to protect them from the racism and the burnout. He coached them himself.\\n\\nSerena turned professional at fourteen. At seventeen, she won her first US Open. She would go on to win twenty-three Grand Slam singles titles — more than any player, male or female, in the Open Era of tennis. She won the Australian Open in 2017 while two months pregnant. She came back to the US Open final ten weeks after giving birth, after a difficult childbirth that nearly killed her.\\n\\nShe fought through racism, sexism, near-fatal blood clots, and the loss of her older sister Yetunde to gun violence. Through all of it she kept showing up. She built a fashion company. She invested in over a hundred startups. She used her voice for women's health and for women of colour.\\n\\nShe did all of this because of two people who refused to ask anyone's permission — her father, who decided his daughters would play tennis, and herself, who decided no one would stop her.\\n\\n{name}, the world will give you a hundred reasons why you don't belong somewhere. Most of them will not be true. The only reason you ever actually need to belong somewhere is this: you love it, you are willing to work for it, and you are willing to keep coming back even when you are not invited."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: two young African-American sisters around six and seven in white tennis outfits on a cracked Compton court, dad in a tracksuit feeding balls. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Serena_Williams_at_2013_US_Open.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 9,
                "profession_title": "Lewis Hamilton — Formula 1 · UK",
                "text_template": (
                    "Lewis Carl Davidson Hamilton was born in Stevenage, England, a small town outside London, in 1985. His father Anthony was a railway engineer with roots in Grenada. When Lewis's parents separated, Anthony worked four jobs at once — sometimes a contractor, sometimes washing dishes — so he could afford to buy his son a go-kart. They could not afford new equipment, so they bought second-hand karts and fixed them in the family garage.\\n\\nAt eight years old, Lewis was already winning national karting championships. He was the only Black child at every track. Other parents stared. Some refused to shake Anthony's hand. Lewis would say later: 'I felt the eyes on me before I knew what racism was.'\\n\\nWhen Lewis was ten, his father took him to the McLaren-Mercedes annual awards dinner in London — they were guests of someone Anthony knew through karting. Lewis spotted McLaren's team principal, Ron Dennis, on the other side of the room. He walked straight up, shook his hand, looked him in the eye and said: 'Hello, sir. My name is Lewis Hamilton. I won the British Karting Championship. One day I want to race for you.'\\n\\nRon Dennis kept the autograph book Lewis had asked him to sign. Two years later, McLaren placed Lewis on a young driver development programme — making him the first driver in motorsport history to be signed by a Formula 1 team as a child.\\n\\nLewis worked his way through every junior single-seater championship without losing one. In 2007 — nine years after that handshake — he made his Formula 1 debut. For McLaren. He missed the World Championship in his rookie year by one single point. He won it the very next year, at age twenty-three.\\n\\nHe went on to win seven World Championships in total — tying the all-time record held by Michael Schumacher. He became the most successful Formula 1 driver in history, and the only Black driver in the entire history of the sport.\\n\\nHe used his platform to push the sport to confront racism — founding The Hamilton Commission to study why so few Black engineers and racers existed in motorsport, then helping fund pathways for them.\\n\\n{name}, when you say the thing you want out loud to the right people, the world starts arranging itself differently around you. The handshake at the awards dinner was just words. But the words mattered. Say what you want. Say it clearly. Then go and do everything you can to make it true."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a 10-year-old Black British boy in a yellow racing suit shaking hands with a smiling team principal at an indoor karting awards event. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Lewis_Hamilton_2016_Malaysia_2.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 10,
                "profession_title": "Carlos Sainz Jr. — Formula 1 · Spain",
                "text_template": (
                    "Carlos Sainz Jr. was born into one of motorsport's most famous families. His father, Carlos Sainz Sr., had won the World Rally Championship twice and the Dakar Rally three times. In Spain the Sainz name was a national institution. Carlos Jr. grew up around cars, mechanics, podiums and trophies. He could change a wheel before he could ride a bicycle.\\n\\nThat sounds glamorous. It was not. Imagine starting a sport where every conversation begins with: 'Yes, but his father…' Every win felt like other people's pride. Every loss felt like a failure to live up to a name that was already in the record books.\\n\\nWhen Carlos was sixteen, he made a decision that surprised even his father. He moved alone to Italy — the heartland of competitive go-karting — without his family, without a translator, with very little Italian. He rented a small apartment. He bought basic groceries. He started racing against drivers who had been training on faster karts than him for years. He learned Italian in six months. English the year after.\\n\\nBy twenty-one he had been signed by Red Bull Racing's junior programme. Toro Rosso put him in a Formula 1 car at age twenty. For years he was 'Sainz Jr.' — a competent driver, never quite a star. He moved to Renault. Then McLaren. Then Ferrari.\\n\\nAt Ferrari, finally driving the most famous racing car in the world, Carlos started winning. He won the British Grand Prix. He won at Singapore. He won at Monza in front of Ferrari's home crowd, with red flags flying and 50,000 Italians singing his name. After that win he climbed onto the podium, took the trophy, and pointed it toward his father standing in the crowd. They both wept.\\n\\nCarlos has said in interviews: 'My father is the most important driver I will ever know. But I am not him. I had to learn to stop trying to be him before I could become me.'\\n\\n{name}, no shadow is so big that you cannot grow taller than it — but you have to be willing to grow in a different direction than the one casting it. Sometimes the only way to honour the people you love most is to become someone different from them."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a 16-year-old Spanish boy in a karting suit alone next to his go-kart in a small Italian paddock at sunrise. A photo of his rally-champion father pinned to the toolbox. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Carlos_Sainz_Jr.,_2017_Malaysia_2.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 11,
                "profession_title": "Magnus Carlsen — Chess · Norway",
                "text_template": (
                    "Sven Magnus Øen Carlsen was born in Tønsberg, Norway, in 1990. By the age of two he could solve fifty-piece jigsaw puzzles. By age four he had memorised the names, populations, flags and capital cities of every country in the world. By five he was assembling Lego sets meant for fourteen-year-olds. His parents wondered if their son was simply a very fast child — or something more.\\n\\nMagnus did not start playing chess seriously until eight. His older sister Ellen had been playing competitively, and Magnus — frustrated at being unable to beat her — asked their father Henrik to teach him properly. Henrik bought him a small wooden chess set and a beginner's book. Magnus read the book once. He never put it down.\\n\\nWithin two years, Magnus was beating his father. Within three years, he was beating every adult at his local chess club. He spent entire weekends locked in his room with chess books — memorising openings, replaying historic games, working through endgames. He played correspondence chess against opponents around the world from age ten.\\n\\nAt thirteen years and four months, in 2004, Magnus became a Grandmaster — the third-youngest in chess history. At an age when most children worry about homework, Magnus was being interviewed by international newspapers.\\n\\nThe defining moment came that same year, at the Reykjavik Rapid tournament in Iceland. The 13-year-old Magnus was paired with Garry Kasparov, the man widely considered the greatest chess player of all time. Kasparov was 41, a former World Champion, an icon. The match was scheduled as a brief exhibition. Magnus drew it. Kasparov reportedly told reporters afterward: 'This boy will be the strongest player in the world.'\\n\\nIt took nine more years. In 2013, Magnus defeated the reigning World Champion Viswanathan Anand in Chennai, India, to become World Chess Champion at twenty-two. He defended the title for ten years — the longest reign of any modern champion. He holds the highest Elo rating in chess history. He plays at a level the computers themselves have to strain to predict.\\n\\nEven at the top of the sport, he still spends six hours a day studying chess.\\n\\n{name}, your brain is a muscle. The fastest mind in the world is not the one that thinks the quickest in the moment. It is the one that has spent the most quiet hours getting curious about something nobody else has bothered to look at as closely."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a focused 13-year-old Norwegian boy with messy blond hair sitting across a chess board from a much older world-famous champion. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Magnus_Carlsen_(30238051906)_(cropped).jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 12,
                "profession_title": "R Praggnanandhaa — Chess · India",
                "text_template": (
                    "Rameshbabu Praggnanandhaa — known to the world as 'Pragg' — was born in Chennai, India, in 2005. His father Rameshbabu is a bank manager. His mother Nagalakshmi is a homemaker. His older sister, Vaishali, is also a chess Grandmaster.\\n\\nThe chess story actually began with Vaishali. Their parents wanted to limit the time she spent watching television, so they enrolled her in a chess class at the local club. She loved it. Pragg, then age three, would sit beside her at home, watching her solve puzzles. He asked to learn too. Vaishali taught him. Within two years he was beating her.\\n\\nWhen he was seven, Pragg won the World Youth Chess Championship in the Under-8 category. Three years later, at age ten years and ten months, he became the youngest International Master in chess history.\\n\\nHis mother Nagalakshmi made an extraordinary decision: she would travel with him to every single tournament, anywhere in the world. She did not know chess. But she knew her son needed familiar food, fresh clothes, and the smell of his own mother nearby when he was playing against fifty-year-old Grandmasters. So she went. To Norway. To Spain. To Argentina. To Iran. She packed his lunches. She watched from a quiet corner of every hall. She held his hand when he won and when he lost.\\n\\nAt twelve years, ten months, Pragg became a Grandmaster — at the time the second-youngest in chess history. In 2024, at age eighteen, he did something almost nobody had done: he defeated reigning World Champion Magnus Carlsen three times in classical and rapid formats within a single year. He reached the Candidates Tournament. He crossed an Elo rating of 2750 — a number very few humans have ever crossed.\\n\\nAfter each big win, the cameras would pan to the crowd and find his mother, smiling quietly, often crying. He would walk over and hug her before anyone else.\\n\\nPragg said in an interview: 'My sister taught me chess. My mother gave me the strength to keep going. Every game I play has both of them in it.'\\n\\n{name}, behind every champion you'll ever meet there is someone quietly making the small things possible — packing the lunch, washing the clothes, sitting in the corner of every room they were ever scared to walk into alone. Notice that person. Thank them. Become that person for someone else one day."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a small Indian boy in a tournament shirt staring intently at a chessboard. His mother in a sari smiles proudly from a few rows back. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Praggnanandhaa_R_2018.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 13,
                "profession_title": "Usain Bolt — Athletics · Jamaica",
                "text_template": (
                    "Usain St. Leo Bolt was born in 1986 in Sherwood Content, a tiny village in the parish of Trelawny in Jamaica. His parents Wellesley and Jennifer ran a small grocery store. Usain was a tall, lanky boy who could not sit still. He ran everywhere — to the shop for his mother, to school, between the cricket wickets in the schoolyard. Walking, for him, was something other people did.\\n\\nUsain's first sporting love was cricket. He bowled fast. He was a wicketkeeper. He dreamed of playing for the West Indies. His high school cricket coach was the one who, one day, told him to put down the cricket ball and try track. 'Boy,' the coach said, 'with those legs, you are not a cricketer. You are a sprinter.'\\n\\nUsain was furious. He did not want to be a sprinter. But the coach made him a deal: try one season. If he hated it, he could go back to cricket.\\n\\nHe won his first sprint race at the school championships easily. He hated it less than he expected. He won the next one. And the next. At fifteen, in 2002, he won the 200m gold at the World Junior Championships — the youngest junior gold medalist ever. He was nearly six feet five inches tall. For a sprinter, this was unheard of. Tall sprinters get out of the blocks slowly. Every coach said his height would be a disadvantage.\\n\\nIt was not. His long stride became his weapon. He took 41 steps to run 100 metres while everyone else took 45. He covered more ground per stride than any sprinter in history.\\n\\nIn 2008 at the Beijing Olympics, Usain ran the 100m final in 9.69 seconds — while slowing down to beat his own chest in the last ten metres. A year later in Berlin, he set the still-standing world record: 9.58 seconds. The fastest a human being has ever moved unassisted by gravity.\\n\\nHe won eight Olympic gold medals across three Games. He held world records in the 100m, 200m and 4×100m relay. He brought joy to athletics — chest-beating, dancing on the line, joking with his rivals before races. He showed the world that excellence and joy could be the same person.\\n\\nHe retired at thirty-one and went back to Jamaica, to the same village, with a small football academy and a quiet, happy life.\\n\\n{name}, sometimes the thing you do without thinking — the gift that has been with you since you were a tiny child — is the very thing the world is waiting for you to take seriously."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a tall lanky 12-year-old Jamaican boy sprinting barefoot through a sun-drenched field. Other kids run far behind. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Usain_Bolt_Rio_100m_final_2016k.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 14,
                "profession_title": "Neeraj Chopra — Athletics · India",
                "text_template": (
                    "In a small farming village called Khandra, in the Panipat district of Haryana, India, an 11-year-old boy named Neeraj Chopra was a little overweight and a little restless. His joint family of seventeen people — uncles, aunts, cousins — were dairy farmers. His grandfather worried about his health and sent him to jog at the Shivaji Stadium in Panipat, twenty kilometres away.\\n\\nNeeraj did not enjoy the jogging. But one day, while running laps, he wandered over to where older boys were practising throws with a long stick. He picked one up. It felt right in his hand. The boys laughed and let him try a throw. The stick — the javelin — flew further than anyone expected from an eleven-year-old.\\n\\nThere was no proper coach in the area. There were no proper grounds. There were almost no Indian javelin throwers worth speaking of at international level. Neeraj had nothing — except a feeling.\\n\\nHe kept showing up. He learned the basics from videos at internet cafés in Panipat. He practised on rutted fields. He scraped money together from his father to buy his first proper javelin. He joined the Sports Authority of India training centre in Patiala at fourteen. Slowly, the village boy started winning national junior titles.\\n\\nAt eighteen, in 2016, he set a world under-20 record at the World Junior Championships in Poland: 86.48 metres. He flew home as the first Indian to ever hold any track-and-field world record. The village erupted. They danced for three days.\\n\\nBut for years after, Neeraj kept getting injured — a shoulder here, an elbow there. He almost retired. He kept going.\\n\\nAt the Tokyo Olympics in August 2021, in the men's javelin final, twenty-three-year-old Neeraj Chopra threw 87.58 metres on his second attempt. It was good enough for gold. India had never won an Olympic gold medal in any individual athletics event in its entire history. Neeraj stood on the podium with the Indian flag held high, watching the tricolour rise above every other flag.\\n\\nA billion people watched the village boy from Khandra make a sport India had ignored for a century finally matter.\\n\\n{name}, the path that nobody else is walking is often the one waiting for you. It looks scary because no one has cleared it ahead of you. That is exactly what makes it yours."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: an 11-year-old Indian boy in t-shirt and shorts at a dusty village stadium in Haryana, picking up a long javelin for the first time. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Neeraj_Chopra_(2018).jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 15,
                "profession_title": "Michael Phelps — Swimming · USA",
                "text_template": (
                    "Michael Fred Phelps II was born in Baltimore, Maryland, USA, in 1985. He was the youngest of three, with two older sisters who already swam competitively. At school he was hyperactive, struggled to sit still, and was diagnosed with attention-deficit/hyperactivity disorder. One of his teachers, in elementary school, told his mother Debbie: 'Your son will never be able to focus on anything.'\\n\\nDebbie, a school principal herself, refused to accept that. She enrolled Michael in the local swim club. At first he was terrified of putting his face in the water — he wore goggles backwards and floated mostly on his back. A coach taught him to start with backstroke until he was comfortable. By age ten he held a national record for his age group. By eleven he was being coached by a man named Bob Bowman, who would remain his coach for the next twenty-five years.\\n\\nBob saw something almost no one else did: Michael's so-called weakness — his inability to focus on ordinary tasks — became a kind of superpower in the pool. He could swim for six hours a day, six days a week, fifty-two weeks a year, for fifteen years, without losing concentration. The same brain that could not sit still in math class could swim 50,000 metres a week without flinching.\\n\\nAt fifteen, Michael became the youngest male American Olympic swimmer in 68 years. At eighteen, at the Athens 2004 Olympics, he won six gold and two bronze medals. At twenty-three, at Beijing 2008, he won eight gold medals — the most ever by a single athlete at a single Olympics, surpassing Mark Spitz's legendary record from 1972.\\n\\nBy the time he retired in 2016, Michael had won 23 Olympic gold medals — more than any other human in any sport in Olympic history. Twenty-three.\\n\\nAfter retiring, Michael spoke publicly about his battles with depression and the loneliness of being at the top. He started the Michael Phelps Foundation to fund free water-safety and mental-health programmes for children. He became one of the world's most outspoken advocates for mental health in athletes.\\n\\nHe still says, every time someone asks him for advice: 'The thing that made me different was the thing teachers wanted me to fix. Find the thing about you that does not fit anywhere. Then find the place where it does.'\\n\\n{name}, what looks like a weakness in one room is often a superpower in another. You just have to keep looking until you find the right room. Don't let anyone fix the thing about you that doesn't fit in classrooms. That thing might be the door."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a 10-year-old American boy floating on his back in a swimming pool, arms outstretched, coach smiling at the pool's edge. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Michael_Phelps_Rio_2016.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 16,
                "profession_title": "Michael Jordan — Basketball · USA",
                "text_template": (
                    "Michael Jeffrey Jordan was born in Brooklyn, New York, in 1963, the fourth of five children, and grew up in Wilmington, North Carolina. His father James was an equipment supervisor. His mother Deloris was a bank teller. Michael was an obsessive child — he had to win at everything. Card games. Marbles. Sprints with his brothers. He cried hard when he lost.\\n\\nIn tenth grade, fifteen-year-old Michael tried out for the varsity basketball team at Emsley A. Laney High School. The coach posted the list of names on the locker-room wall. Michael scanned it. His name was not on it. He had been cut.\\n\\nHe went home, walked into his bedroom, closed the door, and cried for hours. His mother sat outside. When he finally came out, his eyes were red. She did not tell him it was fine. She asked: 'What do you want to do about it?'\\n\\nThat night Michael wrote down a number in a notebook: how many hours he was going to practise per day, every single day, until the next tryout. He stuck to it. The next year he made the team. The year after that, he was being scouted by every major college in America.\\n\\nHe went to the University of North Carolina and, as a freshman, hit the buzzer-beater that won the NCAA championship in 1982. He joined the NBA in 1984 as the third overall pick. He was 6 feet 6 inches. He could jump higher than anyone in the league.\\n\\nWhat followed was a basketball revolution. Six NBA championships. Five MVP awards. Two Olympic gold medals. Ten scoring titles. A career so dominant that decades later nearly every basketball fan on Earth still says his name first when asked who the greatest of all time was. The Air Jordan brand he built with Nike would go on to sell billions of dollars of shoes every year — more than the entire NBA combined.\\n\\nLate in his career, Michael gave a speech that has become famous in classrooms around the world. He said: 'I have missed more than nine thousand shots in my career. I have lost almost three hundred games. Twenty-six times I have been trusted to take the game-winning shot — and missed. I have failed over, and over, and over again in my life. And that is why I succeed.'\\n\\n{name}, the day someone tells you no can be the worst day of your life — or it can be the day you start the journey nobody else has the patience for. The choice is not whether you'll be told no. The choice is what you do the morning after."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a 15-year-old African-American boy alone in a school gym, practising a layup as the sun sets through high windows. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Michael_Jordan_in_2014.jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 17,
                "profession_title": "Simone Biles — Gymnastics · USA",
                "text_template": (
                    "Simone Arianne Biles was born in Columbus, Ohio, USA, in 1997. Her biological mother struggled with addiction. When Simone was three, she and her younger sister Adria were placed in foster care. Her maternal grandparents, Ron and Nellie Biles, adopted them. They moved the girls to a small town near Houston, Texas, and raised them as their own daughters. Simone called Nellie 'Mom' from then on.\\n\\nAt age six, on a school day trip to Bannon's Gymnastix gym, Simone copied a routine she had seen on TV. A coach watching from the corner stopped what she was doing, called Nellie that night, and said: 'Your daughter is a once-in-a-generation talent. Please bring her in to train properly.' Nellie did. From that day Simone spent six days a week at the gym. She was four feet eight inches tall. She would never grow much beyond that. In gymnastics, that helps.\\n\\nShe trained for fifteen years before her first Olympics. She landed moves so difficult that judges had to invent new scoring rules for them. Four skills in gymnastics are named after her — moves so dangerous and complex that nobody else even attempts them in competition.\\n\\nAt the Rio 2016 Olympics, when she was nineteen, Simone won four gold medals and one bronze. She became the first American gymnast to win four golds at a single Games.\\n\\nThen, at Tokyo 2020, something happened that surprised the world: Simone — leading the team competition, already an icon — withdrew. She had developed 'the twisties,' a mental block where gymnasts lose track of where their body is in mid-air, an injury risk that can kill them. She prioritised her mental health publicly, at the cost of medals. Many people criticised her. Many more applauded her. The conversation about mental health in elite sport was changed forever by her courage.\\n\\nShe came back. She won at the World Championships in 2023. She won gold and silver at the Paris 2024 Olympics. By the end of those Games, she had 11 Olympic medals and 30 World Championship medals — more than any gymnast, male or female, in the history of the sport.\\n\\nShe also adopted, alongside Ron and Nellie, the same family value that had once saved her — taking in foster children of her own when the time came.\\n\\n{name}, your superpower might already be living quietly inside you, waiting for the moment you say yes to it. And when you become the strongest version of yourself, you will know that being strong also means knowing when to stop and ask for help. The strongest people in the world are not the ones who never break. They are the ones who tell the truth about their breaking."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a tiny 6-year-old African-American girl in a leotard mid-cartwheel on a sunlit gymnasium mat, a kind coach clapping from the side. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Simone_Biles_at_2016_Olympics_all-around_gold_medal_(28262782114).jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 18,
                "profession_title": "Mary Kom — Boxing · India",
                "text_template": (
                    "Mangte Chungneijang Mary Kom was born in 1982 in Kangathei, a tiny village in the Churachandpur district of Manipur, India. Her parents were poor farmers. As a child, Mary helped them work the fields, looked after her younger siblings, and walked four kilometres to school each day. There was no electricity. There was no running water. There was certainly no money for sport.\\n\\nWhen she was fourteen, Mary watched a small black-and-white television in a neighbour's house. On it, the Manipuri boxer Dingko Singh — a man from her own state — had just won gold at the 1998 Asian Games. He had returned to Imphal a hero, crowds cheering, flowers thrown at his feet. Mary watched the video clip, transfixed, for a long time. Something inside her went very quiet, then very loud.\\n\\nShe went to a small boxing gym in Imphal and asked to train. The male coaches laughed. There was no women's boxing in India then. Women boxers were almost unheard of in the country. Her father, Tonpa Kom, forbade it outright. Boxing was a 'rough sport,' he said. 'Your face is your future, Mary. You will be unmarriageable if it is broken.'\\n\\nMary trained in secret. She used her milk money for a bus ticket. She wore men's shorts, borrowed gloves. When she finally won her first state-level title at sixteen and her photograph appeared in the local newspaper, her father found out — and was furious. Then she won the next title. And the next. Then she won the gold at the 2001 AIBA World Women's Boxing Championships — the very first edition.\\n\\nHer father came to watch her bout in person for the first time. He cried.\\n\\nMary went on to win six gold medals at the World Boxing Championships — the only female boxer in history with six World Championship golds. She also won a bronze at the London 2012 Olympics. She kept boxing into her late thirties — through marriage, through giving birth to twin boys, through breastfeeding while training. Many doubted she could come back after motherhood. She did. Twice.\\n\\nShe has spent decades building boxing academies for poor children in Manipur, mostly girls, using her own money. She believes that talent is everywhere — it is opportunity that is rare.\\n\\n{name}, the people who tell you 'no' the loudest when you start are often the same people who will cry the proudest at the back of the crowd when you win. Don't argue with them in the beginning. Just keep training. The 'yes' you are working toward is so much bigger than any 'no' you have ever heard."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a 14-year-old Manipuri girl shadow-boxing alone at dusk in a quiet barn, hand wraps on, sunset light pouring through gaps in the wood. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
                "static_image_url": "https://commons.wikimedia.org/wiki/Special:FilePath/Mary_Kom_at_Rio_(cropped).jpg",
                "image_credit": "Photo: Wikimedia Commons",
            },
            {
                "page_number": 19,
                "profession_title": "And Now… It's Your Turn, {name}",
                "text_template": (
                    "Did you notice something, {name}? Every legend in this book started as a child. Tiny. Doubted. Sometimes ignored. None of them knew yet that they would change the world. They just kept showing up, kept practising, kept caring — even on the days nobody was watching. Somewhere right now, a future legend is reading these very words. Maybe that legend is you. {name}, the world is waiting for the story only you can write. Start today. Start small. Just don't stop."
                ),
                "image_prompt_template": (
                    "Children's storybook illustration: a young child silhouetted at sunrise on a hill, arms wide open, looking toward a horizon filled with soft glowing silhouettes — tennis racket, cricket bat, football, chess king, javelin, swim cap, basketball, racing helmet — all rising in a warm halo of light. Bold outlines, animated quality, no text. If a child reference photo is provided, also include the child (clearly matching the reference face) standing next to the main subject in the same scene, doing the same activity in the same posture, looking like a friend or teammate; child sized appropriately, expression admiring or joyful. If no reference photo is provided, draw only the main subject as described."
                ),
            },
        ],
    },
    {
        "id": "b2222222-2222-2222-2222-222222222222",
        "name": "Riya Says Goodbye to Tara",
        "description": (
            "Riya's best friend Tara is moving far away. With help from {name}, Riya learns that saying goodbye doesn't have to mean the end of a friendship."
        ),
        "cover_image": "https://images.pexels.com/photos/1648387/pexels-photo-1648387.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "A Surprise at School",
                "text_template": (
                    "It was a sunny Tuesday at school. Riya and her best friend Tara were giggling on the swings when Tara suddenly went quiet. 'Riya,' she said softly, 'Mummy got a new job. We are moving to another country next week.' Riya stopped swinging. {name}, Riya's other dear friend, walked over and saw both their faces."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Two 5-year-old girls — one with curly black hair (Riya), one with two brown braids (Tara) — sitting side by side on a wooden playground swing under a leafy tree on a sunny morning. Tara looking serious. Riya looking shocked. Another child friend approaches from the side. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Riya is Very Sad",
                "text_template": (
                    "At home, Riya flopped onto the sofa with a big sigh. 'Ma, Tara is going away FOREVER!' Mum sat down beside her and gave her a long, gentle hug. 'Not forever, beta. Far away places are not as far as they feel.' Even so, a tiny tear rolled down Riya's cheek."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A warm Indian living room. A mother in a soft cotton kurta hugs her tearful 5-year-old daughter with curly hair on a beige sofa. A father with a small sympathetic smile peeks in from the kitchen doorway. Warm late afternoon light through the window, soft watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "{name} Has An Idea",
                "text_template": (
                    "The next day at school, {name} tapped Riya on the shoulder. 'Riya, why don't we throw Tara a HUGE goodbye party? With cake! And presents! And music! And jumping in puddles!' Riya's eyes lit up like fireworks. 'That,' she said slowly, 'is the best idea anyone has ever had.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A bright primary-school classroom. Riya hugs her child friend with both arms, both of them bouncing happily. Crayon drawings of balloons and a cake taped to the wall behind them. The teacher Ms. Asha (a kind young Indian woman in a sari) smiles warmly from the side. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "Planning Together",
                "text_template": (
                    "Riya, {name}, and Mum sat at the kitchen table making a list. Cake — tick. Balloons — tick. Music — tick. A jumping puddle in the garden — TICK! Mum laughed. 'You will give Tara the biggest goodbye in this whole neighbourhood.' Riya said proudly, 'In the whole CITY, Ma.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A cheerful Indian kitchen. Riya and another child sit at a round wooden table covered in coloured pens, a long paper checklist, and biscuits. A mother in casual clothes pours juice into glasses in the background. Warm sunny light. Soft watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "Friends Arrive",
                "text_template": (
                    "On Saturday afternoon everyone came: Reema, Dev, Ella, Zoya, and Riya's little brother Arjun too. 'SURPRISE, TARA!' they all shouted at once. Tara gasped, then laughed, then nearly cried — all at the same time."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A garden party in the back of an Indian home. A diverse group of six 4-to-6-year-old kids — different skin tones, different outfits — gathered under colourful bunting and balloons. Riya (curly hair) gives Tara (braids) a big welcome hug. A toddler (Arjun) holds a balloon. Sunny afternoon, soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "Cake and Puddle Jumps",
                "text_template": (
                    "They ate cake. They sang loud silly songs. And then, because the sprinkler had made the garden squishy, every single child jumped in the biggest puddle of the year. 'SPLASH!' giggled Tara, drenched. 'I will miss this so much.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Six excited 4-to-6-year-old kids mid-jump in a wide muddy puddle in a sunny garden, water splashing in every direction, all laughing wildly. A tiered birthday cake on a nearby table. Warm afternoon light. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "A Special Gift",
                "text_template": (
                    "Riya pulled out a small box. Inside was a friendship bracelet that broke into two halves — one for Tara, one for Riya. 'When you wear it,' Riya said, 'you will know I am thinking of you, even from across the world.' Tara hugged her so tightly Riya had to gently say, 'Tara… breathing.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Close-up of Riya giving Tara a small wrapped gift box tied with a yellow ribbon. Both girls tearfully smiling. Soft warm sunset light in the garden behind them. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "Goodbye at the Airport",
                "text_template": (
                    "On the day Tara left, Riya's family drove her family to the airport. Riya, {name}, Arjun and Mum waved until their arms ached. 'Goodbye, Tara! Goodbye!' Tara waved back through the big glass window until she was just a small dot."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A bright airport terminal with a huge window onto the runway. Riya, her child friend, a toddler brother and their mother wave goodbye as Tara walks toward an airplane carrying her small backpack, looking back with a brave smile. Other travellers in the background. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "A Video Call",
                "text_template": (
                    "A week later, the family laptop chimed DING-DING-DING. It was Tara! 'Riya! {name}! Look at my new bedroom!' She gave them a wobbly video tour. Riya pressed her face right up to the screen. 'I miss you so much, Tara,' she whispered. 'But I can SEE you. That helps a lot.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Riya and her child friend leaning close to a laptop screen on a wooden desk in a cosy Indian home. On the screen, Tara waves happily from a sunlit new bedroom. Warm lamp light, evening scene. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "Best Friends, Always",
                "text_template": (
                    "That night Riya snuggled into bed, her half of the bracelet around her wrist. {name} sat at the foot of her bed and said, 'See, Riya? Tara didn't go away from your heart. Only from your street.' Riya smiled the biggest smile she had smiled all week. 'Best friends forever — even across the whole wide world.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A 5-year-old girl with curly hair in pyjamas tucked into a cosy bed, friendship bracelet on her wrist, looking through a window at a starry sky. A small framed photo of her best friend on the bedside table. Warm bedroom night light. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
        ],
    },
    {
        "id": "b3333333-3333-3333-3333-333333333333",
        "name": "Cousins Come to Visit",
        "description": (
            "Cousin Maya and baby Aarav come over for a weekend of games, spaghetti chaos and one very sleepy lullaby. {name} is right in the middle of all the fun."
        ),
        "cover_image": "https://images.pexels.com/photos/1620760/pexels-photo-1620760.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "Cousins are Coming!",
                "text_template": (
                    "'Riya! Arjun! Cousin Maya and baby Aarav are coming today!' Mum called from the hall. Riya squealed and ran in three circles. Arjun copied her in two and a half circles because he was three. {name}, already playing in the garden, came running in. 'Yay! Cousins!'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A cheerful Indian living room. A 5-year-old girl with curly hair and her 3-year-old younger brother hop excitedly in circles. A child friend runs in from the open garden door. A mother stands by the front door smiling. Bright sunny afternoon. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Knock, Knock!",
                "text_template": (
                    "DING DONG! At the door stood Uncle Vikram, Auntie Priya, big Cousin Maya, and tiny baby Aarav in a soft blue carrier. 'Hello, hello, hello!' shouted everyone at once. Dad laughed his big rumbly laugh. 'Welcome, family!'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A front-door scene of an Indian apartment. An uncle and aunt with two children — a 10-year-old girl (Maya) and a baby in a soft carrier (Aarav) — arrive with suitcases. The father opens the door wide; the mother and Riya wave from behind him. Bright afternoon. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Meet {name}",
                "text_template": (
                    "'Maya, Aarav, meet my friend {name}!' Riya said proudly. Maya smiled and fist-bumped {name}. Baby Aarav stared with very wide eyes, then said, 'Goo goo gaa gaa.' Everyone laughed. Riya whispered to {name}, 'I think that means hello.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Inside the family living room. A 10-year-old Indian girl (Maya) gently fist-bumps another child. A baby boy (Aarav) in a high chair points curiously. The 5-year-old girl with curly hair grins between them. Family photos on the wall. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "Maya's Sparkly Tablet",
                "text_template": (
                    "Maya pulled out her sparkly tablet. 'Want to see my new puzzle game?' Riya, {name}, and Arjun crowded round in three seconds flat. 'Wow!' said Arjun (his favourite word this month). They took turns solving the levels, cheering for each other every time someone got one right."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Four children — Riya (curly hair), Arjun (toddler), Maya (older Indian girl), and another child friend — sitting cross-legged on a soft rug, all leaning over a glowing tablet held by Maya. Soft afternoon light. Pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "Spaghetti Disaster",
                "text_template": (
                    "At lunch, Mum made spaghetti with red tomato sauce. Baby Aarav gripped a fistful and went SPLAT! Sauce on the table, sauce on the wall, sauce on Dad's glasses. Everyone burst out laughing — even Aarav, who was very proud of himself."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A chaotic but cheerful family lunch scene at a wooden dining table. A baby boy in a high chair flings spaghetti, sauce splattering the wall and the father's glasses. The mother, two children (Riya, Maya, plus a friend) and a toddler all laughing around the table. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "Hide and Seek",
                "text_template": (
                    "'Let's play hide and seek!' said Maya. Riya hid behind the curtains. {name} ducked under a pillow fort. Arjun squeezed inside a big toy basket and went very, very still. Baby Aarav wobbled around the room with his hands over his eyes, giggling, looking for everyone in completely the wrong corners."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A bright apartment mid hide-and-seek. A 5-year-old peeking from behind curtains. A toddler hiding in a toy basket. Another child crouched inside a pillow fort. A baby in the middle of the room with hands over his eyes, laughing. The mother watches from the kitchen doorway. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "Uh Oh, Baby Aarav Cries",
                "text_template": (
                    "Suddenly baby Aarav started to cry. 'Waaaaa!' Auntie Priya came running. 'He's tired and missing his own cot.' Riya whispered to {name}, 'How do we help?' {name} thought for a moment and said gently, 'Maybe a cuddle?'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. An aunt in a soft cotton sari holding a tearful baby boy. The 5-year-old Indian girl with curly hair and a child friend stand close by, looking concerned and sympathetic. Soft lamp-lit evening living room. Pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "The Lullaby",
                "text_template": (
                    "Auntie Priya began to hum a slow, gentle song her own mother used to sing her. Mum joined in. Then Riya, then {name}, then even Arjun (mostly humming). Aarav's eyes grew sleepy. Soon he was snoring the tiniest snores. Everyone smiled very, very quietly."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A peaceful family scene. The aunt gently rocks the baby boy to sleep on a sofa. The mother, the 5-year-old girl, her 3-year-old brother and a child friend stand around humming softly. Soft yellow lamp glow, dim cosy room. Pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "Bedtime Stories",
                "text_template": (
                    "Cousin Maya stayed up with Riya and {name}. Dad read them a story about a brave little girl who climbed a mountain so she could see the whole world. By the end, all three were yawning at exactly the same time. 'Goodnight, cousins,' whispered Riya."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A father sitting on a bed in casual evening clothes reading a storybook. Three children — Riya, an older girl (Maya) and another child friend — cuddled in pillows around him, yawning. A small bedside lamp and stars visible through the window. Soft pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "See You Soon!",
                "text_template": (
                    "The next morning the cousins packed up to leave. 'Promise you'll come visit US next time?' said Maya. Riya and {name} nodded together very seriously. Baby Aarav waved a chubby little hand. 'Goo goo gaa gaa,' he said again. Riya smiled. 'I love that he means goodbye too.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Front entrance of an Indian apartment in morning sun. An uncle and aunt loading the car. An older girl (Maya) waving. A baby boy in his carrier blowing a kiss. Riya (curly hair) and a child friend waving from the doorstep with the mother. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
        ],
    },
    {
        "id": "b4444444-4444-4444-4444-444444444444",
        "name": "Police Officers Visit Our School",
        "description": (
            "Two friendly police officers visit Sunshine Primary School. {name} asks the bravest question of the day — and takes home a paper police hat that says they could be one too."
        ),
        "cover_image": "https://images.pexels.com/photos/532001/pexels-photo-532001.jpeg?auto=compress&cs=tinysrgb&w=800",
        "total_pages": 10,
        "pages": [
            {
                "page_number": 1,
                "profession_title": "A Special Visitor Today",
                "text_template": (
                    "It was Tuesday morning at Sunshine Primary School. Ms. Asha clapped her hands. 'Children! Today we have very special guests visiting our classroom. Can you guess who?' Riya, {name}, Reema, Dev, Ella and Zoya looked at each other with wide curious eyes."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A bright primary classroom. Ms. Asha (a kind young Indian woman in a sari) stands at the front, clapping her hands gently. A diverse group of 5-year-old children — Riya (curly hair), a child friend, and four other classmates — sit cross-legged on a rug looking intrigued. Colourful posters on the wall. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 2,
                "profession_title": "Hello, Officers!",
                "text_template": (
                    "The door opened, and in walked Officer Singh and Officer Khan, smart in their navy blue uniforms. 'Hello, children!' they said with warm friendly smiles. The whole classroom said back, in one big cheerful voice, 'HELLOOO, OFFICERS!'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Two Indian police officers — one man with a turban (Officer Singh) and one woman with a neat ponytail (Officer Khan) — both in smart navy blue uniforms with badges, entering a bright classroom with kind smiles. The seated children wave back happily. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 3,
                "profession_title": "Look at the Uniform!",
                "text_template": (
                    "Officer Singh pointed to his silver badge. 'This badge means I am trained to help people.' Officer Khan unclipped her radio. 'And this lets me talk to other officers far away — even from inside this classroom.' Everyone went, 'Wow!' at exactly the same time."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Close-up of Officer Singh holding up a silver police badge and Officer Khan holding up a black handheld radio. A semi-circle of children seated on a rug peer up in wonder. Bright classroom, sunlight from a window. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 4,
                "profession_title": "{name}'s Brave Question",
                "text_template": (
                    "{name} raised one hand very high. 'What does a police officer actually DO every day?' Both officers smiled. Ms. Asha smiled too. Riya beamed at {name} for being so brave. 'That,' said Officer Khan kindly, 'is the best question of the day.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A child sitting cross-legged on a classroom rug, one hand raised confidently. The two Indian police officers — Singh and Khan — turn warmly toward the child. Riya next to them, eyes wide with pride. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 5,
                "profession_title": "We Help People",
                "text_template": (
                    "'We help anyone who needs us,' said Officer Singh. 'If you ever feel lost, scared, or you've lost your mummy or daddy in a busy market, you can ALWAYS find a police officer and we will help you get safe.' Riya nodded very seriously. {name} nodded too."
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Officer Singh kneels gently to speak with the children at eye level, holding up two open palms in a calming gesture. The seated children — Riya, a child friend, and four classmates — look attentive and reassured. Soft warm classroom light. Pastel watercolour palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 6,
                "profession_title": "Outside to the Police Jeep",
                "text_template": (
                    "'Everyone follow us!' said Officer Khan. The class lined up in pairs and walked out to the school driveway. Parked there was a real police jeep, shiny white and blue, with red and blue lights on the roof. The whole class gasped, 'OOOOH!'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A shiny white-and-blue Indian police jeep with red and blue light bar parked on a school driveway. A line of six children — Riya, a child friend and four classmates — walking out hand-in-hand with Ms. Asha and the two officers, eyes wide with excitement. Sunny day, soft palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 7,
                "profession_title": "WHOOP WHOOP!",
                "text_template": (
                    "Officer Singh turned the siren on for just one second. WHOOP-WHOOP! Everyone covered their ears and then burst out laughing. Riya squealed, '{name}, that was the loudest thing I have ever heard in my whole entire life!'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. A police jeep with the roof light flashing softly and motion lines suggesting a quick siren burst. Six children — diverse, ages 5-6 — covering their ears and giggling. Sunny day, school building in the background. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 8,
                "profession_title": "Hats For Everyone",
                "text_template": (
                    "Back inside, the officers handed each child a folded paper police hat with a shiny badge sticker. Riya wore hers proudly. {name} did a careful salute. Arjun (visiting from the toddler classroom) stood VERY straight and VERY serious. Ms. Asha laughed warmly. 'You all look very official today!'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Classroom scene. Each child wears a paper police hat with a sticker badge. Riya grinning, a child friend saluting, a toddler standing extra straight, four other classmates smiling. The two Indian officers in the background looking pleased. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 9,
                "profession_title": "Can I Be One Too?",
                "text_template": (
                    "Riya raised her hand. 'When I grow up, can I be a police officer?' Officer Khan smiled gently. 'If you are kind, honest, brave and you never stop learning — absolutely yes.' Riya looked at {name}. 'Then I will. And {name} too — we'll do it together!'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Riya (5-year-old girl with curly hair) standing confidently in her paper hat. Officer Khan kneels and gives her a warm nod. A child friend stands beside Riya, looking inspired. Other classmates watch from the rug. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
                ),
            },
            {
                "page_number": 10,
                "profession_title": "Thank You, Officers!",
                "text_template": (
                    "When it was time for the officers to leave, the whole class shouted together, 'THANK YOU, OFFICERS!' The officers waved warmly from their police jeep as it drove gently away. Riya whispered to {name}, 'Today was the best day of school in the whole world.'"
                ),
                "image_prompt_template": (
                    "Warm modern children's book illustration. Diverse human characters with friendly expressive faces, soft watercolor textures, gentle pastel palette (warm peach, sage, soft blue), clean bold line work, original character designs. IMPORTANT: only human children and adults — no pigs, no anthropomorphic animals, no sheep, no dogs, no rabbits, no panda, no squirrels, no elephants, no zebras. Do NOT imitate Peppa Pig, Bluey, Paw Patrol, or any animated TV franchise. Standard human proportions, naturalistic faces, watercolour storybook aesthetic. No text, no logos. Officer Singh and Officer Khan waving from inside their police jeep as it slowly drives down a sunny street outside a school gate. The whole class — Riya, a child friend, four classmates, a toddler and Ms. Asha — wave back happily, all wearing paper police hats. Soft pastel palette. If a child reference photo is provided, also draw a child character matching the reference face (skin tone, hair, facial features) standing alongside the main scene, doing the same activity in the same pose; child sized for the age, joyful expression. If no reference photo, draw the scene without that extra child."
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
    """Convert template page image_url to a PIL Image.

    Supports:
      * data:image/*;base64,... URLs (everything the AI pipeline produces)
      * http(s) URLs (real-photo pages like the Legends template — Wikipedia
        Commons portraits). Downloaded on first use; the PDF generator
        already calls this per page so caching here would be premature.
    """
    url = page.get("image_url")
    if not url:
        return None
    try:
        if url.startswith("data:image"):
            b64 = url.split(",", 1)[-1]
            raw = base64.b64decode(b64)
            return Image.open(io.BytesIO(raw)).convert("RGB")
        if url.startswith(("http://", "https://")):
            import urllib.request
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "StorytimeStudioBook/1.0 (https://example.com)"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read()
            return Image.open(io.BytesIO(raw)).convert("RGB")
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
                    "HTTP-Referer": "https://example.com",
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
