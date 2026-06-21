"""The sign language(s) under test, with concise grammar notes.

These notes steer both the translator (system under test) and the judge so that
scoring is grounded in the language's actual syntax rather than English word order.

Only ASL is wired up in the real pipeline right now, so that's all we validate.
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
