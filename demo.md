# Demo Script — SignCast, Signed in Real Time (~2 min)

**Format:** one presenter, screen shared. Times are cumulative.

---

### 0:00 — The hook (15s)
> "Sports give us passion, connection, belonging. But for millions of Deaf and
> hard-of-hearing fans, a live match is mostly silence — captions lag, and they
> miss the *emotion* in a commentator's voice. We asked: what if the match could
> sign itself, live?"

### 0:15 — The product (20s)
*(Screen: a real YouTube live football stream playing full-screen.)*
> "This is any YouTube live broadcast. Watch the corner."
*(A translucent overlay appears — a signing avatar with a live caption underneath.)*
> "That's our accessibility layer, sitting on top of the broadcast. No special
> player, no separate feed — it rides on the stream people already watch."

### 0:35 — How it works (25s)
*(Screen: architecture diagram.)*
> "Commentary audio goes through Deepgram to text. Claude rewrites that English
> into the *grammar* of a sign language — not word-for-word, real signing structure.
> That drives a generated signing visual, cached in Redis so it stays in sync.
> End to end, a few seconds."

### 1:00 — Five languages (15s)
*(Screen: back to the overlay. Switch the language picker ASL → BSL → LSF.)*
> "And it's not just American Sign Language. We support five — ASL, BSL, French,
> Chinese, and Japanese sign language — switchable live, repositionable to any
> corner so it never blocks the play."

### 1:15 — The trust problem (30s)
> "But here's the hard question for any translation system: *how do you know it's
> right?* A wrong sign isn't a typo — it changes the meaning of the match."
*(Screen: the validation report — table of 5 languages × 5 metrics.)*
> "So we built a validation agent. It auto-writes test commentary across real match
> moments — goals, fouls, offside, substitutions — runs them through the translator
> for all five languages, and grades every output on grammar, meaning, completeness,
> gloss validity, and real-time fluency. It ships a report with scores and flags its
> own weakest cases. Quality you can measure, not just hope for."

### 1:45 — Close (15s)
> "A live broadcast that signs itself, in five languages, with a quality bar it
> holds itself to. We're turning 'yearning' into 'watching along with everyone
> else.' That's the experience every fan deserves."

---

**Backup talking points (if asked):**
- *Latency:* Deepgram <2s, Claude <3s, generation ~30s cold / <1s on cache hit.
- *Why gloss, not word-for-word:* sign languages have their own grammar (topic-comment,
  time-first); literal translation is unreadable to native signers.
- *Robustness:* the overlay reads from a WebSocket; if the live pipeline stalls, a
  cached clip library keeps the demo running.
