""""""

import ast
import urllib.request
import json
import os.path
import time
import string
from unidecode import unidecode

## Definitions
ALPHABET = string.punctuation + "1234567890" + string.ascii_uppercase
with open("keywords.json", mode="r", encoding="utf-8") as keywords_file:
    KEYWORDS = json.load(keywords_file)
with open("creature-types.json", mode="r", encoding="utf-8") as ctypes_file:
    CREATURETYPES = json.load(ctypes_file)
with open("card-types.json", mode="r", encoding="utf-8") as types_file:
    TYPES = json.load(types_file)

POSITIVE_ANSWERS = ["yes", "y", "true", "t", "1", "yup"]
NEGATIVE_ANSWERS = ["no", "n", "false", "f", "0", "nope"]
questions_left = 20
question_history = []
answer_history = []
remaining_cards = []
card_found = False


QUESTION_ANSWERS = {
    "Is your card a {insert}?": TYPES + CREATURETYPES,
    "Is your card {insert}?": ["White", "UBlue", "Black", "Red", "Green"],
    "Does your card have {insert}?": KEYWORDS,
    "Is your card legal in {insert}?": [
        "Standard",
        "Pioneer",
        "Modern",
        "Vintage",
        "Commander",
    ],
    "Is your card's CMC less than {insert}?": list(range(1, 5)),
    "Is your card's power less than {insert}?": list(range(1, 13)),
    "Is your card's toughness less than {insert}?": list(range(1, 13)),
    "Is your card's CMC {insert}?": list(range(1, 20)),
    "Is your card's power {insert}?": list(range(1, 20)),
    "Is your card's toughness {insert}?": list(range(1, 20)),
    "Is the first letter of your card's name {insert}?": ALPHABET,
    "Is your card multicolored?": "tf",
    "Is your card monocolored?": "tf",
    "Is your card colorless?": "tf",
    "Is your card on the reserve list?": "tf",
    "Is your card a game changer in EDH?": "tf",
}
# functions for each question type, takes card and insert as arguments, returns True/False
QUENTION_FUNCS = {
    "Is your card a {insert}?": lambda card, insert: insert in card["type_line"],
    "Is your card {insert}?": lambda card, insert: insert[0] in card["colors"],
    "Does your card have {insert}?": lambda card, insert: insert in card["keywords"],
    "Is your card legal in {insert}?": lambda card, insert: card["legalities"][
        insert.lower()
    ]
    == "legal",
    "Is your card's CMC less than {insert}?": lambda card, insert: card["cmc"] < insert,
    "Is your card's power less than {insert}?": lambda card, insert: desymbolize(
        card["power"]
    )
    < int(insert),
    "Is your card's toughness less than {insert}?": lambda card, insert: desymbolize(
        card["toughness"]
    )
    < int(insert),
    "Is your card's CMC {insert}?": lambda card, insert: card["cmc"] == insert,
    "Is your card's power {insert}?": lambda card, insert: card["power"] == insert,
    "Is your card's toughness {insert}?": lambda card, insert: card["toughness"]
    == insert,
    "Is the first letter of your card's name {insert}?": lambda card, insert: unidecode(
        card["name"][0]
    )
    == insert,
    "Is your card multicolored?": lambda card, insert: len(card["colors"]) > 1,
    "Is your card monocolored?": lambda card, insert: len(card["colors"]) == 1,
    "Is your card colorless?": lambda card, insert: card["colors"] == [],
    "Is your card on the reserve list?": lambda card, insert: card["reserved"] is True,
    "Is your card a game changer in EDH?": lambda card, insert: card["game_changer"]
    is True,
    "Is your card called {}?": lambda card, insert: card["name"] == insert,
}


def desymbolize(statstring):
    """convert non-numeric power/ toughness to numeric for comparison (X = 0 etc)"""
    if isinstance(statstring, (str)) is False:
        return statstring
    ZEROS = ["X", "*", "?"]
    if statstring in ZEROS:
        return 0
    else:
        return int(statstring[0])


def load_scryfall_data():
    """Load data from cache or download fresh data from scryfall api"""
    if os.path.isfile("oracle-cards.json"):  # if cache file exists
        if (
            os.path.getmtime("oracle-cards.json") > time.time() - 24 * 60 * 60
        ):  # if less than 24 hours old
            with open("oracle-cards.json", mode="r", encoding="utf-8") as cache_file:
                return json.load(cache_file)

    print("Downloading fresh data")
    scryfall_contents = urllib.request.urlopen(
        "https://data.scryfall.io/oracle-cards/oracle-cards-20250823090430.json"
    ).read()
    data = json.loads(scryfall_contents)  # list of all cards in scryfall database
    usable_data = []

    # filter out cards that are not useful for this game (ie tokens, art series, etc)
    # un-sets aren't included becuase they have weird mechanics like non-int cmc costs
    for raw_card in data:
        if (
            raw_card["set_type"] == "funny"
            or raw_card["set_type"] == "memorabilia"
            or "Art Series" in raw_card["set_name"]
            or "Token" in raw_card["type_line"]
            or "Card" in raw_card["type_line"]
        ):
            continue

        unused = [
            "id",
            "all_parts",
            "oracle_id",
            "mtgo_id",
            "tcgplayer_id",
            "cardmarket_id",
            "lang",
            "uri",
            "layout",
            "highres_image",
            "image_status",
            "image_uris",
            "foil",
            "nonfoil",
            "finishes",
            "oversized",
            "promo",
            "reprint",
            "variation",
            "set_id",
            "set_uri",
            "set_search_uri",
            "scryfall_set_uri",
            "rulings_uri",
            "prints_search_uri",
            "digital",
            "watermark",
            "card_back_id",
            "artist_ids",
            "illustration_id",
            "border_color",
            "frame",
            "frame_effects",
            "security_stamp",
            "full_art",
            "textless",
            "booster",
            "story_spotlight",
            "edhrec_rank",
            "preview",
            "related_uris",
            "purchase_uris",
        ]
        for characteristic in unused:  # remove unused characteristics to save space
            if characteristic in raw_card:
                del raw_card[characteristic]

        usable_data.append(raw_card)  # add the cleaned card to the usable data list

    with open("oracle-cards.json", mode="w", encoding="utf-8") as cache_file:
        json.dump(usable_data, cache_file, indent=2)  # save cleaned data to cache file

    with open("oracle-cards.json", mode="r", encoding="utf-8") as cache_file:
        data = json.load(cache_file)  # reload data from cache to ensure consistency
    return data


def check_card(card, question, question_insert):
    """check if a card answers a question (with exceptions for certain questions)"""
    # if question is color and its a multifaced card, combine colors of all faces
    if (
        (
            question == "Is your card {insert}?"
            or question == "Is your card multicolored?"
            or question == "Is your card monocolored?"
            or question == "Is your card colorless?"
        )
        and "colors" not in card
        and "card_faces" in card
    ):
        # create a amalgamation card with combined colors of all faces
        amalgamation_card = {
            "colors": list(
                card["card_faces"][0]["colors"] + card["card_faces"][1]["colors"]
            )
        }
        return QUENTION_FUNCS[question](amalgamation_card, question_insert)

    # if question isnt an exception above, just ask normally
    else:
        return QUENTION_FUNCS[question](card, question_insert)


def find_question(cards):
    """find the best question to ask to split the remaining cards in half"""

    best = []  # will contain question and insert
    # worst possible score, ie all questions will be better than this
    best_score = len(cards)
    target = int(len(cards) / 2)  # ideal score is half the remaining cards

    # go through each card and get a score of how many cards would answer yes to this question
    # it is aiming for a question that splits the remaining cards in half
    for question, inserts in QUESTION_ANSWERS.items():
        # Insert is the variable part of the question (ie "Artifact" in "Is your card an Artifact?")
        for question_insert in inserts:
            score = 0
            skip = True
            for current_card in cards:
                # if card doesnt have power/ toughness, skip questions about power/toughness
                if (
                    question
                    in (
                        "Is your card's power less than {insert}?",
                        "Is your card's toughness less than {insert}?",
                        "Is your card's power {insert}?",
                        "Is your card's toughness {insert}?",
                    )
                ) and "power" not in current_card:
                    break
                answer = check_card(current_card, question, question_insert)

                if answer:
                    score += 1
            else:
                skip = False
            # if this question is a better split than the best so far
            if abs(target - score) < abs(target - best_score):
                best = [question, question_insert]
                best_score = score
                # skip rest of search if perfect question found
                if best_score == target:
                    return best
            # if we didn't hit a break in the inner loop (ie it wasnt an invalid question)
            if skip:
                break
    if best_score != 0 and best_score != len(cards):  # if a valid question was found
        return best
    else:
        return False  # no valid question found


def filter_cards(cards, question, answer):
    """filter cards based on question and player given answer"""
    for card in cards:
        if check_card(card, question[0], question[1]) == answer:
            yield card


if __name__ == "__main__":
    remaining_cards = load_scryfall_data()

    while questions_left > 1 and len(remaining_cards) > 3:
        toask = find_question(remaining_cards)
        if toask is not False:  # if a valid question was found
            print(f"\n#### Question { 21 - questions_left } ####")
            questions_left -= 1
            print(toask[0].format(insert=toask[1]))
            inp = input(">>> ").lower()
            while (
                inp not in POSITIVE_ANSWERS + NEGATIVE_ANSWERS
            ):  # repeat until valid input
                print(inp + " is not a valid awnser.")
                print("Please answer yes or no")
                inp = input(">>> ").lower()
            # Record question and awnser
            question_history.append(toask)
            if inp in POSITIVE_ANSWERS:
                answer_history.append(True)
            else:
                answer_history.append(False)

            remaining_cards = list(
                filter_cards(remaining_cards, toask, inp in POSITIVE_ANSWERS)
            )
            print(f"{len(remaining_cards)} cards remaining")
        else:
            break

    # Final guesses
    while card_found is False and questions_left > 0:
        if len(remaining_cards) == 0:
            print("No cards match your awnsers, somethings gone wrong")
            break
        print(f"\n#### Question { 21 - questions_left } ####")
        print(f"Is your card {remaining_cards[-1]["name"]}?")
        inp = input(">>> ").lower()
        # repeat until valid input
        while inp not in POSITIVE_ANSWERS + NEGATIVE_ANSWERS:
            print(inp + " is not a valid awnser.")
            print("Please answer yes or no")
            inp = input(">>> ").lower()
        # Record question and awnser
        question_history.append(
            ["Is your card called {}?", remaining_cards[-1]["name"]]
        )
        if inp in POSITIVE_ANSWERS:
            answer_history.append(True)
            card_found = True
        else:
            answer_history.append(False)
            remaining_cards.pop()
            questions_left -= 1
    print("\n#### Results ####\n")
    if card_found:
        print(f"I guessed your card in {21 - questions_left} questions")
        print(f"Your card was {remaining_cards[-1]["name"]}")

    elif len(remaining_cards) != 0:
        print("I couldn't guess your card in 20 questions")
        print(f"There were {len(remaining_cards)} cards left?")
        print("The remaining cards were:")
        for unguessed_card in remaining_cards:
            print(unguessed_card["name"])
