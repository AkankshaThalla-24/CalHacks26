"""The 5 sign languages under test, with concise grammar notes.

These notes steer both the translator (system under test) and the judge so that
scoring is grounded in each language's actual syntax rather than English word order.
"""

SIGN_LANGUAGES = {
    "ASL": {
        "name": "American Sign Language",
        "grammar_notes": (
            "Topic-comment structure. Common order: TIME - TOPIC - COMMENT. "
            "No copula (is/are). Tense set once via time markers. "
            "Rhetorical questions and non-manual markers carry grammar. Glosses in CAPS."
        ),
    },
    "BSL": {
        "name": "British Sign Language",
        "grammar_notes": (
            "Topic-comment, heavily spatial. Often TIME - SUBJECT - OBJECT - VERB. "
            "Placement (proforms) used to track referents. Distinct from ASL. Glosses in CAPS."
        ),
    },
    "LSF": {
        "name": "Langue des Signes Française (French Sign Language)",
        "grammar_notes": (
            "Topic-comment with strong use of spatial referencing and classifiers. "
            "Time markers placed early. Facial grammar marks questions/negation. Glosses in CAPS."
        ),
    },
    "CSL": {
        "name": "Chinese Sign Language",
        "grammar_notes": (
            "Topic-prominent, generally SVO-leaning with topic fronting. "
            "Time and location set before action. Uses directional verbs. Glosses in CAPS."
        ),
    },
    "JSL": {
        "name": "Japanese Sign Language (Nihon Shuwa)",
        "grammar_notes": (
            "Topic-comment, broadly SOV. Time/topic fronted, verb last. "
            "Mouth morphemes and facial markers carry grammar. Glosses in CAPS."
        ),
    },
}

# Sports scenarios the test generator should cover.
SCENARIOS = [
    "goal scored",
    "penalty awarded",
    "yellow/red card / foul",
    "substitution",
    "offside call",
    "player injury",
    "crowd reaction",
    "final whistle / result",
]
