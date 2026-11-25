#!/usr/bin/env python3
"""The Best Meal You Ever Had — make.fun bounty entry.

The job: write ONE sentence, at most 200 characters, about the best meal
the entrant ever had, to /output/entry.txt.

How this program works: it carries a small set of candidate sentences,
each written as one person's memory, and scores every candidate against
the judge brief published with the bounty, in the brief's own order:

  1. stays on the subject (the best meal ever had),
  2. makes the meal concrete (named dish, place, texture, smell, one
     specific moment, not general praise),
  3. feels true to one person's memory, not a stock line,
  4. is one clean sentence that reads aloud well, fresh wording,
     no cliche,
  5. lands with an image, a turn or an ending that stays with the
     reader after a single reading.

Each criterion is its own function, so the reasoning behind the pick is
visible in the output. The highest-scoring candidate wins and is written
out verbatim. The choice is deterministic: the same input always yields
the same sentence, so the two grading runs agree byte for byte.
"""

import os
import re
import sys

MAX_CHARS = 200

# Candidate sentences. Each is one sentence about one remembered meal:
# a named dish, a real place, a sensory detail, one specific moment.
CANDIDATES = [
    "In a warung with plastic stools and no menu, my rawon arrived "
    "dark as a secret, and one spoonful of beef in kluwek broth made "
    "the whole noisy street go quiet.",

    "I ate nasi goreng from a cart at 2 a.m. in Jakarta, the wok fire "
    "lighting the cook's face, and the egg yolk broke over the rice "
    "like a small sun coming up.",

    "My mother ladled soto ayam into my bowl the morning I left home, "
    "turmeric steam fogging my glasses, and I have chased that exact "
    "warmth in every bowl since.",

    "The sate ayam at the Surabaya night market came off the charcoal "
    "still hissing, peanut sauce on my wrist, and the vendor nodded "
    "like we had known each other for years.",

    "At my grandmother's table in Bandung, the rendang had simmered "
    "since dawn, and the first spoonful tasted of smoke and coconut "
    "and every Sunday I could remember.",

    "Standing at a counter in Yogyakarta, I ate gudeg with krecek still "
    "crackling, jackfruit sweet as jam, and understood why my father "
    "drove three hours for it.",

    "The best meal I ever had was instant noodles on a rainy train "
    "platform, salt and steam and my sister laughing, eaten "
    "cross-legged while the world rushed past.",
]

# Words that mark a concrete, sensory memory rather than general praise.
SENSORY_WORDS = {
    "smoke", "coconut", "turmeric", "steam", "hissing", "crackling",
    "peanut", "kluwek", "broth", "charcoal", "wok", "yolk", "salt",
    "sweet", "jam", "fogging", "dripping", "simmered", "dark",
}

# Named dishes and places: concreteness the judge asks for by name.
NAMED_DISHES = {
    "rawon", "nasi goreng", "soto ayam", "sate ayam", "rendang",
    "gudeg", "krecek", "noodles",
}
PLACES = {
    "warung", "bandung", "jakarta", "surabaya", "yogyakarta",
    "night market", "train platform", "counter", "kitchen",
}

# Stock lines and cliches the brief penalises: fresh wording only.
CLICHES = [
    "melted in my mouth",
    "to die for",
    "food heaven",
    "taste of heaven",
    "best thing i ever tasted",
    "out of this world",
    "bursting with flavour",
    "bursting with flavor",
    "like no other",
    "unforgettable experience",
    "taste bud",
]

# A closing turn: the final clause lands an image or a change, instead
# of trailing off in praise. Look for it in the last third of the text.
CLOSING_TURNS = [
    "go quiet",
    "coming up",
    "since",
    "for years",
    "remember",
    "for it",
    "rushed past",
    "understood",
    "chased",
]

# Abbreviations whose dots are not sentence ends ("2 a.m." is one clause).
ABBREVIATIONS = ["a.m.", "p.m."]

EATING_VERBS = re.compile(
    r"\b(ate|eaten|meal|bowl|spoonful|tasted|ladled|split open)\b"
)
PERSON_MARKERS = re.compile(
    r"\b(my|i|we|mother|grandmother|father|sister|vendor|cook)\b"
)
MEMORY_MARKERS = re.compile(
    r"\b(first|exact|remember|since|left home|childhood|years)\b"
)
TIME_MARKERS = re.compile(
    r"\b(\d+\s*a\.m\.|\d+\s*p\.m\.|morning|dawn|midnight|since dawn"
    r"|rainy night|2 a\.m\.)\b"
)


def is_one_sentence(text):
    """One sentence: strip abbreviation dots, then exactly one terminator."""
    stripped = text
    for abbr in ABBREVIATIONS:
        stripped = stripped.replace(abbr, abbr.replace(".", ""))
    terminators = re.findall(r"[.!?]", stripped)
    return len(terminators) == 1 and text.rstrip().endswith((".", "!", "?"))


def criterion_subject(text, lowered):
    """1. Stays on the subject: a meal someone ate, or a named dish."""
    dish = any(d in lowered for d in NAMED_DISHES)
    if EATING_VERBS.search(lowered) or dish:
        return 2.0, "on subject: a meal being eaten"
    return 0.0, "off subject: no meal in the sentence"


def criterion_concrete(text, lowered):
    """2. Concrete: named dish, place, texture, smell, specific moment."""
    score = 0.0
    notes = []
    dishes = sorted(d for d in NAMED_DISHES if d in lowered)
    places = sorted(p for p in PLACES if p in lowered)
    sensory = sorted(w for w in SENSORY_WORDS if w in lowered)
    score += 2.0 * min(len(dishes), 2)
    score += 1.5 * min(len(places), 2)
    score += 1.0 * min(len(sensory), 4)
    notes.append("dish=%s place=%s sensory=%s" % (dishes, places, sensory))
    if TIME_MARKERS.search(lowered):
        score += 1.0
        notes.append("specific time or moment")
    return score, "; ".join(notes)


def criterion_personal(text, lowered):
    """3. True to one person's memory, not a stock line."""
    score = 0.0
    notes = []
    if PERSON_MARKERS.search(lowered):
        score += 1.5
        notes.append("personal voice")
    if MEMORY_MARKERS.search(lowered):
        score += 1.0
        notes.append("memory anchor")
    if re.search(r"\b(my|our)\s+(mother|father|grandmother|sister|rawon|table)\b", lowered):
        score += 0.5
        notes.append("a possessive memory: my ...")
    return score, "; ".join(notes) if notes else "no personal marker"


def criterion_clean(text, lowered):
    """4. One clean sentence, reads aloud well, fresh wording."""
    score = 0.0
    notes = []
    words = len(text.split())
    if 20 <= words <= 45:
        score += 1.0
        notes.append("good spoken length: %d words" % words)
    else:
        notes.append("spoken length off: %d words" % words)
    found = [c for c in CLICHES if c in lowered]
    if found:
        score -= 3.0 * len(found)
        notes.append("cliche: %s" % found)
    else:
        score += 1.0
        notes.append("no cliche")
    return score, "; ".join(notes)


def criterion_landing(text, lowered):
    """5. Lands with an image, a turn or an ending that stays."""
    tail = lowered[int(len(lowered) * 0.66):]
    turns = [t for t in CLOSING_TURNS if t in tail]
    if turns:
        return 2.0, "closing turn: %s" % turns
    return 0.0, "no closing turn in final third"


CRITERIA = [
    ("1 subject", criterion_subject),
    ("2 concrete", criterion_concrete),
    ("3 personal", criterion_personal),
    ("4 clean", criterion_clean),
    ("5 landing", criterion_landing),
]


def score_candidate(text):
    """Score one candidate against the judge brief. Returns (score, notes)."""
    lowered = text.lower()
    notes = []

    # Gate: one sentence, 1..200 characters, not only whitespace.
    if not text or not text.strip():
        return -100.0, ["empty"]
    if len(text) > MAX_CHARS:
        return -100.0, ["over 200 characters: %d" % len(text)]
    if not is_one_sentence(text):
        return -100.0, ["not exactly one sentence"]

    total = 0.0
    for name, fn in CRITERIA:
        points, note = fn(text, lowered)
        total += points
        notes.append("%s: %s (+%.1f)" % (name, note, points))
    return total, notes


def pick_best(candidates):
    """Return (text, score, notes, ranked) for the best-scoring candidate."""
    ranked = []
    for text in candidates:
        score, notes = score_candidate(text)
        ranked.append((score, text, notes))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    best_score, best_text, best_notes = ranked[0]
    return best_text, best_score, best_notes, ranked


def main():
    best, best_score, best_notes, ranked = pick_best(CANDIDATES)

    print("Candidates scored against the judge brief (best first):")
    for score, text, notes in ranked:
        print("  %6.1f  %d chars  %s" % (score, len(text), text))
        for note in notes:
            print("         - %s" % note)

    if best_score < 0:
        print("ERROR: no valid candidate", file=sys.stderr)
        return 1

    out_dir = "/output"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "entry.txt")
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(best)

    print()
    print("Winner (%d chars, score %.1f):" % (len(best), best_score))
    print(best)
    print("Wrote %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
