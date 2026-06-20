CLIP_LIBRARY = [
    # Actions
    "WALK", "RUN", "TALK", "THINK", "KNOW", "WANT", "NEED",
    "LIKE", "LOVE", "HATE", "SEE", "HEAR", "EAT", "DRINK",
    "GO", "COME", "STOP", "START", "FINISH", "HELP",
    "GIVE", "TAKE", "MAKE", "WORK", "PLAY", "LEARN",
    "TEACH", "SHOW", "TELL", "BUY", "SELL", "OPEN", "CLOSE",
    "MOVE", "WAIT", "HAPPEN", "CHANGE", "FIND", "LOOK",
    # Descriptors
    "GOOD", "BAD", "BIG", "SMALL", "FAST", "SLOW",
    "NEW", "OLD", "HOT", "COLD", "HAPPY", "SAD",
    "ANGRY", "AFRAID", "SURPRISED", "TIRED", "IMPORTANT",
    "DIFFERENT", "SAME", "EASY", "HARD", "WRONG", "RIGHT",
    "BEAUTIFUL", "FUNNY",
    # Time
    "NOW", "BEFORE", "AFTER", "TODAY", "TOMORROW", "YESTERDAY",
    "MORNING", "AFTERNOON", "NIGHT", "WEEK", "MONTH", "YEAR",
    "MINUTE", "HOUR", "SOON", "ALWAYS", "NEVER", "AGAIN",
    # People / roles
    "PERSON", "MAN", "WOMAN", "CHILD", "FRIEND", "FAMILY",
    "GROUP", "TEAM",
    # Question words
    "WHO", "WHAT", "WHERE", "WHEN", "WHY", "HOW",
    # Quantity / degree
    "MORE", "LESS", "ALL", "MANY", "FEW", "SOME", "FIRST", "LAST",
    # Common nouns
    "HOUSE", "CAR", "FOOD", "WATER", "MONEY", "PLACE",
    "THING", "WORLD", "LIFE", "DAY",
    # Affirmation / negation
    "YES", "NO", "NOT",
] + [f"NUMBER_{i}" for i in range(0, 100)]

CLIP_LIBRARY_SET = set(CLIP_LIBRARY)
