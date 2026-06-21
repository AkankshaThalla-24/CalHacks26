"""The 5 accuracy metrics and their scoring rubrics (1-5 scale)."""

METRICS = {
    "grammatical_accuracy": (
        "Does the gloss follow the TARGET sign language's grammar/word order "
        "(topic-comment, time markers, verb placement) rather than English order?"
    ),
    "semantic_accuracy": (
        "Is the meaning of the original English commentary faithfully preserved "
        "(no contradictions, no invented facts)?"
    ),
    "completeness": (
        "Are the key facts retained: teams/players, score, action, and time/minute "
        "where present?"
    ),
    "gloss_validity": (
        "Is it valid gloss notation (signs in CAPS, no leftover English sentence "
        "structure, no untranslatable filler)?"
    ),
    "realtime_fluency": (
        "Is it concise and natural enough to be signed live without lag "
        "(no redundant or overly long output)?"
    ),
}

# A test case fails overall if its average across metrics is below this.
PASS_THRESHOLD = 4.0
