"""Helper code for the "Build Your AI Clone" workshop.

This file has the hard parts (reading WhatsApp exports, charts, cards, the Style DNA,
the chat window and the game), so the notebook can stay short and easy to read.
You don't need to understand this file to do the workshop, but you're welcome to look around!
"""

import re
import zipfile
from datetime import datetime

# WhatsApp puts this invisible character before media and system messages
INVISIBLE_MARK = "‎"

# A new message starts with a date and a time, for example:
#   iPhone:  [16/3/25, 18:27:06] Name: text
#   Android: 16/11/2026, 16:51 - Name: text
#   English: 11/16/26, 6:27 PM - Name: text
MESSAGE_START = re.compile(
    r"^\[?(\d{1,4})[/.\-](\d{1,2})[/.\-](\d{1,4}),?\s+"   # date
    r"(\d{1,2}):(\d{2})(?::(\d{2}))?"                     # time
    r"\s*([ap])?\.?\s?(?:m\.?)?"                          # optional AM / PM
    r"\]?\s*(?:-\s*)?(.*)$",                              # rest of the line
    re.IGNORECASE,
)


def load_chat_text(filename, content):
    """Return the text of the chat, from a .txt file or from a .zip export."""
    if filename.lower().endswith(".zip"):
        with zipfile.ZipFile(filename) as archive:
            txt_files = [name for name in archive.namelist() if name.lower().endswith(".txt")]
            content = archive.read(txt_files[0])
    return content.decode("utf-8-sig")


def clean_line(line):
    """Remove invisible characters at the start and turn special spaces into normal ones."""
    line = line.replace(" ", " ").replace(" ", " ")
    return line.lstrip(INVISIBLE_MARK)


def find_day_first(raw_messages):
    """Decide if dates are day/month (Spain) or month/day (USA)."""
    for message in raw_messages:
        first, second = message["date_parts"][0], message["date_parts"][1]
        if first > 31:          # year first, like 2026-11-16
            continue
        if first > 12:
            return True
        if second > 12:
            return False
    return True  # can't tell: use day/month


def make_date(date_parts, time_parts, day_first):
    first, second, third = date_parts
    hour, minute, second_of_time, am_pm = time_parts

    if first > 31:              # year first
        year, month, day = first, second, third
    elif day_first:
        day, month, year = first, second, third
    else:
        month, day, year = first, second, third
    if year < 100:
        year += 2000

    if am_pm == "p" and hour < 12:
        hour += 12
    if am_pm == "a" and hour == 12:
        hour = 0

    return datetime(year, month, day, hour, minute, second_of_time)


def read_chat(chat_text):
    """Turn an exported WhatsApp chat into a list of messages."""
    raw_messages = []

    for line in chat_text.split("\n"):
        line = clean_line(line.rstrip("\r"))
        match = MESSAGE_START.match(line)

        if match:
            numbers = match.groups()
            rest = numbers[7]
            raw_messages.append({
                "date_parts": (int(numbers[0]), int(numbers[1]), int(numbers[2])),
                "time_parts": (int(numbers[3]), int(numbers[4]), int(numbers[5] or 0),
                               (numbers[6] or "").lower()),
                "rest": rest,
            })
        elif raw_messages:
            # A line without a date continues the previous message
            raw_messages[-1]["rest"] += "\n" + line

    day_first = find_day_first(raw_messages)
    messages = []

    for raw in raw_messages:
        # Messages without "Name: " are system messages (Android)
        if ": " not in raw["rest"]:
            continue
        author, text = raw["rest"].split(": ", 1)

        # Media and system messages start with the invisible mark (iPhone)
        if text.startswith(INVISIBLE_MARK):
            continue
        # Media on Android looks like <Media omitted>
        if text.startswith("<") and text.endswith(">"):
            continue

        messages.append({
            "date": make_date(raw["date_parts"], raw["time_parts"], day_first),
            "author": author.strip(),
            "text": text.strip(),
        })

    return messages


# ---------------------------------------------------------------------------
# Words and colors
# ---------------------------------------------------------------------------

import random
import urllib.request
from collections import Counter

import matplotlib.pyplot as plt
from IPython.display import HTML, display
from matplotlib.ticker import MaxNLocator

CREAM, RED, BLUE, INK = "#F3EEE3", "#FF4D2E", "#2F4BFF", "#111111"

# Common words that don't say much about how you text
STOP_WORDS = {
    # Spanish
    "a", "al", "algo", "ante", "así", "como", "con", "cual", "cuando", "de", "del",
    "donde", "e", "el", "ella", "ellas", "ellos", "en", "entre", "era", "es", "esa",
    "ese", "eso", "esta", "está", "este", "esto", "fue", "ha", "hay", "la", "las",
    "le", "les", "lo", "los", "me", "mi", "mis", "muy", "más", "ni", "no", "nos",
    "o", "para", "pero", "por", "porque", "que", "qué", "se", "sea", "si", "sí",
    "sin", "sobre", "son", "su", "sus", "también", "te", "ti", "tu", "tus", "tú",
    "u", "un", "una", "uno", "unos", "y", "ya", "yo", "él",
    # English
    "about", "an", "and", "are", "as", "at", "be", "but", "by", "do", "for", "from",
    "have", "he", "her", "him", "his", "i", "if", "in", "is", "it", "its", "just",
    "me", "my", "of", "on", "or", "our", "she", "so", "that", "the", "their", "them",
    "they", "this", "to", "was", "we", "were", "what", "with", "you", "your",
    "am", "did", "does", "not", "will", "can", "all", "how", "why", "when", "there",
    "here", "too", "very", "really", "then", "than", "one", "has", "had", "been", "out", "up",
    "i'm", "im", "it's", "that's", "don't", "yes", "ok", "who", "would", "should",
    "could", "must", "more", "some", "any", "now", "got", "get",
    "like", "okay", "going", "gonna", "you're", "i'll", "i've", "we're", "they're", "he's", "she's", "let",
    "know", "think", "want", "even", "only", "said", "into", "off", "over", "back",
    # Links
    "http", "https", "www", "com",
}


def get_words(text):
    """Split a message into lowercase words."""
    text = text.lower().replace("’", "'")
    return [word for word in re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)*", text) if len(word) > 1]


# ---------------------------------------------------------------------------
# Showing things nicely
# ---------------------------------------------------------------------------

def card(title, body, color=BLUE):
    """Show a colored card with a title and some text inside."""
    display(HTML(f"""
    <div style="background:{CREAM}; color:{INK}; border-left:10px solid {color}; border-radius:14px;
                padding:20px 26px; margin:10px 0; font-family:Arial, sans-serif; max-width:760px;">
      <div style="font-size:24px; font-weight:800; margin-bottom:10px;">{title}</div>
      <div style="font-size:16px; line-height:1.6;">{body}</div>
    </div>"""))


def bar_chart(items, title, color=BLUE):
    """Draw a horizontal bar chart from a list of (label, count) pairs."""
    if not items:
        print("Nothing to show here.")
        return
    labels = [label for label, count in items][::-1]
    counts = [count for label, count in items][::-1]

    fig, ax = plt.subplots(figsize=(9, 0.6 * len(items) + 1.4), facecolor=CREAM)
    ax.set_facecolor(CREAM)
    bars = ax.barh(labels, counts, color=color, height=0.65)
    ax.bar_label(bars, padding=6, fontsize=12, fontweight="bold", color=INK)
    ax.set_title(title, fontsize=18, fontweight="bold", color=INK, loc="left", pad=16)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.tick_params(colors=INK, labelsize=12, length=0)
    ax.set_xticks([])
    for side in ["top", "right", "bottom", "left"]:
        ax.spines[side].set_visible(False)
    plt.tight_layout()
    plt.show()


def show_messages(messages, how_many=5):
    """Show how many messages were read and the first few."""
    if len(messages) == 0:
        card("No messages found", "We couldn't read any messages from this file. Ask an officer for help!", RED)
        return
    preview = "".join(
        f"<div style='margin:6px 0;'><b>{message['author']}</b> "
        f"<span style='color:#777; font-size:13px;'>{message['date']:%d %b %Y, %H:%M}</span><br>{message['text']}</div>"
        for message in messages[:how_many]
    )
    card(f"Read {len(messages):,} messages!", f"<div style='color:#555; margin-bottom:6px;'>The first {how_many}:</div>{preview}")


def show_people(authors):
    """Show a numbered list of the people in the chat."""
    people = "".join(f"<div style='font-size:18px; margin:4px 0;'><b style='color:{RED};'>{number}.</b> {author}</div>"
                     for number, author in enumerate(authors, start=1))
    card("Who's in this chat?", people)


# ---------------------------------------------------------------------------
# Step 1 · Getting the chat
# ---------------------------------------------------------------------------

SAMPLE_CHAT_URL = ("https://raw.githubusercontent.com/MateoNeiraCastillo/coding-club-workshops/"
                   "main/01-ai-clone/data/sample_chat.txt")


def get_chat():
    """Ask for the sample chat or for your own export, and return its text."""
    if input("Do you want to use the sample chat instead of your own? (y/n): ").strip().lower() == "y":
        filename = "sample_chat.txt"
        urllib.request.urlretrieve(SAMPLE_CHAT_URL, filename)
        card("Sample chat loaded", "The <b>Mentors Anonymous</b> group with Tony Stark, Yoda and Haymitch. "
                                   "Pick one of them to clone!")
        return load_chat_text(filename, open(filename, "rb").read())

    from google.colab import files
    uploaded = files.upload()
    filename = list(uploaded.keys())[0]
    return load_chat_text(filename, uploaded[filename])


# ---------------------------------------------------------------------------
# Step 5 · Messages for the clone and the game
# ---------------------------------------------------------------------------

def save_game_moments(messages, my_name, how_many=5):
    """Keep a few real (message, your reply) pairs for the game, and return the rest of your messages.

    The clone never sees these replies, so the game is fair."""
    moments = []
    for previous, reply in zip(messages, messages[1:]):
        answered_quickly = (reply["date"] - previous["date"]).total_seconds() < 3600
        if (previous["author"] != my_name and reply["author"] == my_name and answered_quickly
                and len(reply["text"].split()) >= 3):
            moments.append((previous["text"], reply["text"]))
    game_moments = random.sample(moments, min(how_many, len(moments)))
    saved_replies = {reply for _, reply in game_moments}

    candidates = [message["text"] for message in messages
                  if message["author"] == my_name and len(message["text"].split()) >= 3
                  and message["text"] not in saved_replies]
    return game_moments, candidates


# ---------------------------------------------------------------------------
# Step 6 · Style DNA
# ---------------------------------------------------------------------------

LAUGHS = {
    "jaja": r"\b(?:j+a+){2,}\w*",
    "jeje": r"\b(?:j+e+){2,}\w*",
    "jsjs": r"\b(?:j+s+){2,}\w*",
    "haha": r"\b(?:h+a+){2,}\w*",
    "lol": r"\blo+l\b",
    "lmao": r"\blmf?a+o+\b",
    "heh": r"\bhe+h\b",
    "xd": r"\bxd+\b",
}


def percent(count, total):
    return round(100 * count / total) if total else 0


def make_style_dna(messages, my_name, examples):
    """Measure how you text and ask the AI to describe your vibe. Returns a dictionary."""
    my_messages = [message for message in messages if message["author"] == my_name]
    texts = [message["text"] for message in my_messages]
    total = len(texts)

    average_words = sum(len(text.split()) for text in texts) / total

    laugh_counts = Counter()
    for text in texts:
        for laugh, pattern in LAUGHS.items():
            laugh_counts[laugh] += len(re.findall(pattern, text.lower()))
    favorite_laugh = laugh_counts.most_common(1)[0][0] if sum(laugh_counts.values()) else None

    word_counts = Counter()
    phrase_counts = Counter()
    for text in texts:
        words = get_words(text)
        word_counts.update(word for word in words if word not in STOP_WORDS)
        for size in (3, 2):
            for start in range(len(words) - size + 1):
                phrase = words[start:start + size]
                if not all(word in STOP_WORDS for word in phrase):
                    phrase_counts[" ".join(phrase)] += 1
    signature_phrase, phrase_times = phrase_counts.most_common(1)[0] if phrase_counts else (None, 0)

    turns = 0
    previous_author = None
    for message in messages:
        if message["author"] == my_name and previous_author != my_name:
            turns += 1
        previous_author = message["author"]

    # A new conversation starts after 1 hour of silence
    reply_seconds = []
    conversations = 0
    started_by_me = 0
    for previous, current in zip([None] + messages, messages):
        gap = (current["date"] - previous["date"]).total_seconds() if previous else None
        if gap is None or gap >= 3600:
            conversations += 1
            if current["author"] == my_name:
                started_by_me += 1
        elif previous["author"] != my_name and current["author"] == my_name:
            reply_seconds.append(gap)

    reply_seconds.sort()
    median_reply = reply_seconds[len(reply_seconds) // 2] if reply_seconds else None
    if median_reply is None:
        reply_speed = "No replies"
    elif median_reply < 60:
        reply_speed = "Under 1 min"
    else:
        reply_speed = f"{round(median_reply / 60)} min"

    if average_words < 5:
        length = "short"
    elif average_words < 12:
        length = "medium"
    else:
        length = "long"

    from google.colab import ai
    sample = "\n".join(random.sample(examples, min(80, len(examples))))
    vibe = ai.generate_text(
        f"These are WhatsApp messages written by one person:\n{sample}\n\n"
        "Describe this person's texting personality in one short, funny and honest sentence "
        "(maximum 12 words, in English, no emojis). Only write the sentence."
    ).strip().strip('"')

    return {
        "vibe": vibe,
        "average_words": round(average_words, 1),
        "length": length,
        "favorite_laugh": favorite_laugh,
        "starts_lowercase": percent(sum(1 for text in texts if text[:1].islower()), total),
        "ends_with_period": percent(sum(1 for text in texts if text.endswith(".")), total),
        "double_punctuation": percent(sum(1 for text in texts if "??" in text or "!!" in text), total),
        "messages_in_a_row": round(total / turns, 1) if turns else 1,
        "busiest_hour": Counter(message["date"].hour for message in my_messages).most_common(1)[0][0],
        "signature_phrase": signature_phrase,
        "phrase_times": phrase_times,
        "reply_speed": reply_speed,
        "starts_conversations": percent(started_by_me, conversations),
        "top_words": [word for word, count in word_counts.most_common(5)],
    }


def show_style_dna(style, my_name):
    """Show the Style DNA as a grid of tiles."""
    tiles = [
        ("Signature phrase", f"“{style['signature_phrase']}”" if style["signature_phrase"] else "None",
         f"you said it {style['phrase_times']} times"),
        ("Reply speed", style["reply_speed"], "how long you take to answer"),
        ("Starts the conversation", f"{style['starts_conversations']}%", "of the conversations in this chat"),
        ("Favorite hour", f"{style['busiest_hour']}:00", "when you text the most"),
        ("Message length", f"{style['average_words']} words", f"{style['length']} messages on average"),
        ("Top words", ", ".join(style["top_words"][:3]) or "None", "what you say the most"),
    ]
    html = "".join(f"""
    <div style="background:white; border-radius:12px; padding:18px; border:2px solid {INK};">
      <div style="font-size:13px; text-transform:uppercase; letter-spacing:1px; color:#666;">{label}</div>
      <div style="font-size:26px; font-weight:800; color:{BLUE}; margin:6px 0; word-break:break-word;">{value}</div>
      <div style="font-size:13px; color:#666;">{note}</div>
    </div>""" for label, value, note in tiles)

    display(HTML(f"""
    <div style="background:{CREAM}; color:{INK}; border-radius:16px; padding:24px; font-family:Arial, sans-serif; max-width:820px;">
      <div style="font-size:30px; font-weight:900;">{my_name}'s Style DNA</div>
      <div style="font-size:15px; color:#555; margin-bottom:16px;">This is what your AI clone will learn from.</div>
      <div style="background:{RED}; color:white; border-radius:12px; padding:20px 22px; margin-bottom:12px;">
        <div style="font-size:13px; text-transform:uppercase; letter-spacing:1px; opacity:0.85;">Your vibe, according to the AI</div>
        <div style="font-size:26px; font-weight:800; margin-top:6px;">{style['vibe']}</div>
      </div>
      <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:12px;">{html}</div>
    </div>"""))


# ---------------------------------------------------------------------------
# Step 7 · The prompt for the clone
# ---------------------------------------------------------------------------

# Who the characters of the sample chat are, so the clone knows their story
CHARACTERS = {
    "Tony Stark": ("Tony Stark (Iron Man) from the Marvel movies. Genius, billionaire, arrogant and very sarcastic. "
                   "Talks fast in full, confident sentences with dry humor, gives everyone nicknames and makes "
                   "pop culture references, never internet slang. Hides his feelings behind jokes, drinks too much "
                   "coffee, builds suits and never sleeps. Mentor of Peter Parker (Spider-Man), partner of Pepper "
                   "Potts, best friend of Rhodey."),
    "Yoda": ("Yoda, the 900 year old Jedi Master from Star Wars. Talks with the words in a strange order, is wise, "
             "cryptic and a bit of a troll. Lived through the fall of the Jedi and hides on Dagobah. "
             "Mentor of Luke Skywalker, knew his father Anakin."),
    "Haymitch": ("Haymitch Abernathy from The Hunger Games. Won the 50th Games, lost his family to President Snow and "
                 "drinks to forget. Cynical, blunt, rude, dark humor, but cares more than he admits. "
                 "Mentor of Katniss Everdeen and Peeta Mellark, annoyed by Effie Trinket."),
}


def build_prompt(my_name, style, examples, extra_rules, history, new_message):
    """Write the instructions that tell the AI how to text like you."""
    example_lines = "\n".join(f"- {text}" for text in examples)

    conversation = ""
    for turn in history:
        if isinstance(turn, dict):   # newer versions of Gradio
            speaker = "Friend" if turn["role"] == "user" else my_name
            conversation += f"{speaker}: {turn['content']}\n"
        else:                        # older versions: (friend, clone) pairs
            conversation += f"Friend: {turn[0]}\n{my_name}: {turn[1]}\n"

    character = ""
    if my_name in CHARACTERS:
        character = (f"\nWho {my_name} is: {CHARACTERS[my_name]} You know their whole story and world, "
                     "so answer any question about it in character, with their real personality from the movies "
                     "and books. Don't make them nicer than they are.\n")

    extra = f"- {extra_rules}\n" if extra_rules else ""

    return f"""You are the AI clone of {my_name}. Reply to the friend exactly like {my_name} texts on WhatsApp.
{character}
How {my_name} texts:
- Vibe: {style['vibe']}
- Messages are {style['length']}, about {style['average_words']} words each
- Favorite laugh: {style['favorite_laugh'] or 'none'}
- Starts in lowercase in {style['starts_lowercase']}% of messages
- Ends with a period in {style['ends_with_period']}% of messages
- Uses ?? or !! in {style['double_punctuation']}% of messages
- Sends about {style['messages_in_a_row']} messages in a row (put each one on a new line)
- Favorite words: {', '.join(style['top_words']) or 'none'}
- Signature phrase: {style['signature_phrase'] or 'none'}

Real messages from {my_name}:
{example_lines}

Rules:
- Reply in the same language {my_name} uses in the real messages.
- Copy the length, slang and laughs. Don't use emojis unless the example messages use them. Don't sound like an assistant.
- Only write {my_name}'s reply, nothing else.
{extra}
Conversation:
{conversation}Friend: {new_message}
{my_name}:"""


# ---------------------------------------------------------------------------
# Step 8 · Chat
# ---------------------------------------------------------------------------

def start_chat(clone_reply, my_name):
    """Open a chat window with your clone and print a link you can share."""
    import gradio as gr

    def respond(message, history):
        return clone_reply(message, history)

    gr.ChatInterface(respond, title=f"Chat with {my_name}'s AI clone").launch(share=True)


# ---------------------------------------------------------------------------
# Step 9 · Real or Clone?
# ---------------------------------------------------------------------------

def prepare_game(game_moments, clone_reply):
    """For each saved moment, ask the clone to answer and mix its answer with the real one."""
    rounds = []
    for friend_message, real_reply in game_moments:
        clone_answer = clone_reply(friend_message).split("\n")[0]
        options = [real_reply, clone_answer]
        random.shuffle(options)
        rounds.append({"friend": friend_message, "real": real_reply, "options": options})
        print(f"Round {len(rounds)} ready")
    print(f"\n{len(rounds)} rounds ready!")
    return rounds


def start_game(rounds, my_name):
    """Open the Real or Clone? game and print a link you can share."""
    import gradio as gr

    if not rounds:
        raise ValueError("Not enough messages to play. Try again with the sample chat!")

    def show_round(index):
        current = rounds[index]
        return (
            f"### Round {index + 1} of {len(rounds)}\n\n**Someone texted:** {current['friend']}",
            f"**A:** {current['options'][0]}",
            f"**B:** {current['options'][1]}",
        )

    def guess(choice, state):
        if state["index"] >= len(rounds):
            return state, gr.update(), gr.update(), gr.update(), gr.update()
        current = rounds[state["index"]]
        correct = current["options"][choice] == current["real"]
        state = {"index": state["index"] + 1, "score": state["score"] + int(correct)}
        feedback = "Correct!" if correct else f"Fooled you! The real one was: *{current['real']}*"
        if state["index"] == len(rounds):
            final = f"{feedback}\n\n## Final score: {state['score']} / {len(rounds)}"
            return state, "### Game over!", "", "", final
        question, option_a, option_b = show_round(state["index"])
        return state, question, option_a, option_b, feedback

    with gr.Blocks(title="Real or Clone?") as game:
        gr.Markdown(f"# Real or Clone?\nOne reply was sent by the real **{my_name}**, the other one by their AI clone. "
                    "Which one is real?")
        state = gr.State({"index": 0, "score": 0})
        question = gr.Markdown()
        option_a = gr.Markdown()
        option_b = gr.Markdown()
        with gr.Row():
            button_a = gr.Button("A is real")
            button_b = gr.Button("B is real")
        result = gr.Markdown()

        outputs = [state, question, option_a, option_b, result]
        button_a.click(lambda current: guess(0, current), state, outputs)
        button_b.click(lambda current: guess(1, current), state, outputs)
        game.load(lambda: show_round(0), None, [question, option_a, option_b])

    game.launch(share=True)
