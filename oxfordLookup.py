import html
import logging
from typing import Optional

import requests


logger = logging.getLogger(__name__)

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"


def getDefinitions(word: str) -> Optional[dict]:
    """
    English so'z haqida to'liq ma'lumot oladi (dictionaryapi.dev bepul API).

    Returns:
        {
            "word": str,
            "phonetic": str,
            "getDefinitions": str,
            "examples": str,
            "synonyms": list,
            "antonyms": list,
            "audio": str | None
        }

        yoki None
    """

    word = word.strip().lower()

    if not word:
        return None

    try:

        response = requests.get(
            API_URL + requests.utils.quote(word),
            timeout=10
        )

        if response.status_code != 200:
            logger.warning(
                "Word topilmadi: %s | status=%s",
                word,
                response.status_code
            )
            return None

        data = response.json()

        if not isinstance(data, list) or not data:
            return None

        entry = data[0]

        # ==========================================
        # WORD
        # ==========================================

        real_word = entry.get("word", word)

        # ==========================================
        # PHONETIC
        # ==========================================

        phonetic = entry.get("phonetic", "")

        if not phonetic:

            for item in entry.get("phonetics", []):

                if item.get("text"):
                    phonetic = item["text"]
                    break

        # ==========================================
        # AUDIO
        # ==========================================

        audio = None

        for item in entry.get("phonetics", []):

            audio_url = item.get("audio")

            if audio_url:
                audio = audio_url
                break

        # ==========================================
        # DEFINITIONS
        # ==========================================

        definitions = []

        # ==========================================
        # EXAMPLES
        # ==========================================

        examples = []

        # ==========================================
        # SYNONYMS
        # ==========================================

        synonyms = []

        # ==========================================
        # ANTONYMS
        # ==========================================

        antonyms = []

        for meaning in entry.get("meanings", []):

            part_of_speech = meaning.get(
                "partOfSpeech",
                ""
            )

            for definition_item in meaning.get(
                "definitions",
                []
            ):

                definition = definition_item.get(
                    "definition"
                )

                example = definition_item.get(
                    "example"
                )

                local_synonyms = definition_item.get(
                    "synonyms",
                    []
                )

                local_antonyms = definition_item.get(
                    "antonyms",
                    []
                )

                if definition:

                    safe_definition = html.escape(
                        definition
                    )

                    if part_of_speech:

                        definitions.append(
                            f"• <b>{html.escape(part_of_speech)}</b>: "
                            f"{safe_definition}"
                        )

                    else:

                        definitions.append(
                            f"• {safe_definition}"
                        )

                if example:
                    examples.append(
                        html.escape(example)
                    )

                synonyms.extend(local_synonyms)
                antonyms.extend(local_antonyms)

            # meaning level synonyms
            synonyms.extend(
                meaning.get("synonyms", [])
            )

            # meaning level antonyms
            antonyms.extend(
                meaning.get("antonyms", [])
            )

        # ==========================================
        # REMOVE DUPLICATES
        # ==========================================

        synonyms = list(
            dict.fromkeys(synonyms)
        )

        antonyms = list(
            dict.fromkeys(antonyms)
        )

        examples = list(
            dict.fromkeys(examples)
        )

        # ==========================================
        # RESULT
        # ==========================================

        return {
            "word": real_word,

            "phonetic": phonetic,

            "getDefinitions": "\n".join(
                definitions
            ),

            "examples": examples,

            "synonyms": synonyms,

            "antonyms": antonyms,

            "audio": audio
        }

    except requests.Timeout:

        logger.error(
            "Dictionary API timeout: %s",
            word
        )

        return None

    except requests.RequestException as error:

        logger.error(
            "Dictionary API error: %s",
            error
        )

        return None

    except Exception as error:

        logger.exception(
            "Unexpected dictionary error: %s",
            error
        )

        return None