# Goal: Event Counter

Build a small Python 3.12 package named `event_counter` using only the standard library.

Requirements:

1. Implement `count_events(events)` where each event is a mapping with `type` and optional `value`.
2. Return a new dictionary mapping each non-empty string `type` to its count.
3. Reject a non-list input with `TypeError`.
4. Reject an event that is not a mapping, has a missing/blank/non-string `type`, with `ValueError` containing the zero-based event index.
5. Do not mutate the input.
6. Provide a CLI: `python -m event_counter FILE.json` reads a JSON array and writes the count dictionary as sorted JSON.
7. Add unit tests for normal input, empty input, repeated types, invalid events, non-mutation, and CLI success/failure.
8. Use no third-party runtime dependency.

Acceptance requires `python -m unittest discover -s tests -v` to exit 0.
