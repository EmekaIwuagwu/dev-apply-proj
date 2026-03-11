"""
typist.py — Human-like keyboard input.

Real people:
  - type at 40–90 WPM (varies per character)
  - occasionally make typos and correct them
  - pause longer after punctuation and spaces
  - sometimes delete and retype a word they second-guessed

This module drives Playwright's keyboard API with all of that behaviour.
"""
import asyncio
import logging
import random
import string

from playwright.async_api import Page

logger = logging.getLogger(__name__)

# Keyboard layout adjacency — characters likely to be mistyped
_ADJACENT: dict[str, str] = {
    "a": "sqwz", "b": "vghn", "c": "xdfv", "d": "serf c",
    "e": "wsdr", "f": "dcvg", "g": "fvbh", "h": "gbynj",
    "i": "ujko", "j": "hnkm", "k": "jlmi", "l": "kop",
    "m": "njk", "n": "bhjm", "o": "iklp", "p": "ol",
    "q": "wa", "r": "etfd", "s": "awde", "t": "rfgy",
    "u": "yhji", "v": "cfgb", "w": "qase", "x": "zsdc",
    "y": "tghu", "z": "asx",
}


class HumanTypist:
    """
    Types text into the focused page element character-by-character.
    Seeded from the user ID for a consistent typing personality.
    """

    def __init__(self, page: Page, seed: str = ""):
        self._page = page
        self._rng = random.Random(seed or "default")

        # Per-user personality parameters
        wpm = self._rng.randint(45, 85)
        chars_per_sec = (wpm * 5) / 60  # average chars per second
        self._base_delay = 1.0 / chars_per_sec  # seconds per char

        self._typo_rate = self._rng.uniform(0.02, 0.08)       # probability of typo
        self._rethink_rate = self._rng.uniform(0.005, 0.02)   # word-delete + retype
        self._pause_on_space = self._rng.uniform(0.04, 0.12)  # extra pause at spaces

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def type(self, text: str) -> None:
        """
        Type `text` into whatever element currently has focus.
        Simulates realistic human typing with typos, corrections, and pauses.
        """
        words = text.split(" ")
        for wi, word in enumerate(words):
            await self._type_word(word)
            if wi < len(words) - 1:
                # Type the space
                await self._page.keyboard.type(" ")
                await asyncio.sleep(
                    self._base_delay + self._rng.gauss(0, self._pause_on_space)
                )
                # Occasionally "think" before the next word
                if self._rng.random() < 0.05:
                    await asyncio.sleep(self._rng.uniform(0.3, 1.2))
                # Very occasionally delete the last word and retype it
                if self._rng.random() < self._rethink_rate and word:
                    await self._delete_word(word)
                    await asyncio.sleep(self._rng.uniform(0.2, 0.7))
                    await self._type_word(word)
                    await self._page.keyboard.type(" ")
                    await asyncio.sleep(self._base_delay)

    async def type_fast(self, text: str) -> None:
        """Type text quickly — used for fields like email where precision matters."""
        await self._page.keyboard.type(text)
        await asyncio.sleep(self._rng.uniform(0.05, 0.15))

    async def clear_and_type(self, text: str) -> None:
        """Select all and replace, then type — for pre-filled fields."""
        await self._page.keyboard.press("Control+a")
        await asyncio.sleep(0.05)
        await self._page.keyboard.press("Delete")
        await asyncio.sleep(0.05)
        await self.type(text)

    async def press(self, key: str) -> None:
        """Press a single key (e.g. 'Enter', 'Tab', 'Escape')."""
        await asyncio.sleep(self._rng.uniform(0.05, 0.15))
        await self._page.keyboard.press(key)
        await asyncio.sleep(self._rng.uniform(0.05, 0.15))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _type_word(self, word: str) -> None:
        for char in word:
            # Maybe produce a typo
            if char.isalpha() and self._rng.random() < self._typo_rate:
                wrong = self._adjacent_key(char)
                await self._page.keyboard.type(wrong)
                await asyncio.sleep(self._rng.uniform(0.08, 0.22))
                await self._page.keyboard.press("Backspace")
                await asyncio.sleep(self._rng.uniform(0.05, 0.12))

            await self._page.keyboard.type(char)
            delay = self._base_delay + self._rng.gauss(0, self._base_delay * 0.35)
            await asyncio.sleep(max(0.02, delay))

    async def _delete_word(self, word: str) -> None:
        """Delete `word` + its preceding space using backspace."""
        # +1 for the space before the word
        n = len(word) + 1
        for _ in range(n):
            await self._page.keyboard.press("Backspace")
            await asyncio.sleep(self._rng.uniform(0.04, 0.09))

    def _adjacent_key(self, char: str) -> str:
        """Return a plausible neighbouring key for the given character."""
        lower = char.lower()
        neighbours = _ADJACENT.get(lower, string.ascii_lowercase)
        wrong = self._rng.choice(neighbours.replace(" ", ""))
        return wrong.upper() if char.isupper() else wrong
