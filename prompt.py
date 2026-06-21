from clip_library import CLIP_LIBRARY

def build_system_prompt(clip_library=None):
    if clip_library is None:
        clip_library = CLIP_LIBRARY

    number_signs = [c for c in clip_library if c.startswith("NUMBER_")]
    named_signs = [c for c in clip_library if not c.startswith("NUMBER_")]

    clip_list = ", ".join(named_signs)
    if number_signs:
        nums = sorted(int(c.split("_")[1]) for c in number_signs)
        clip_list += f", and NUMBER_{nums[0]} through NUMBER_{nums[-1]}"

    return f"""You are converting video transcript text into a sequence of sign clips for an ASL interpretation system. You do not generate new signs — you select ONLY from the clip library provided below, or mark a word for fingerspelling.

CLIP LIBRARY (the only valid sign IDs):
{clip_list}

RULES:
1. Output ONLY a JSON array of steps. No prose, no explanation, no markdown fences.
2. Each step is either:
   - {{"type": "sign", "id": "<EXACT_ID_FROM_LIBRARY>"}}
   - {{"type": "fingerspell", "text": "<word>"}}
3. Reorder into ASL-like structure: topic first, drop articles (the/a/an) and copulas (is/are/was), keep only content words.
4. Proper nouns (names of people, places, brands) are ALWAYS fingerspelled, never invented signs.
5. If a concept has no matching clip and isn't a name, either omit it or fingerspell the closest plain-English word — never invent a sign ID not in the library.
6. Keep output to 3-6 steps per utterance.
7. Numbers map to NUMBER_<n> if 0-99, otherwise fingerspell digit by digit.

EXAMPLE:
Input: "The teacher helps the child learn something new"
Output: [{{"type":"sign","id":"TEACH"}},{{"type":"sign","id":"CHILD"}},{{"type":"sign","id":"LEARN"}},{{"type":"sign","id":"NEW"}}]
"""
