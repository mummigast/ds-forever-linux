# Changes in DS Forever Linux Streaming Edition

Newest first. Based on DS Forever 1.0.34 (upstream add-on set 402). What differs from DS Forever in general: [FORK.md](FORK.md).

## 2026-11-18: DS Forever 1.0.34, add-on set 410

- **Merged DS Forever 1.0.34**: Edit layout (move and save the top-screen pieces), the Buffs / XP bar / Damage meter / Cooldown
  Manager switches, Smart pet (replaces this edition's pet-follow memory), map and stream fixes from upstream.
- Edit layout and those switches work while streaming: their hidden row is pressed by keyboard shortcuts too.
- Shortcut columns no longer use punctuation keys, which never arrived on non-US keyboard layouts (friendly nameplates and the
  layout editor were affected).
- The pairing screen fits the Thor's top screen (Stream quality, PC address and Back beside the keypad).
- No "Save your Battle.net login" button: the PC signs in.
- Known: the XP bar switch does nothing yet; the Damage meter is untested.

## 2026-11-18: add-on set 407

**Fixed**
- **Buttons with a WoW window open** (vendor, quest giver): quests (pick, accept, reward), *Sell junk*, *Repair*, buy and sell now
  work every time. The app presses the add-ons' hidden buttons with keyboard shortcuts (Ctrl+Shift + two keys) instead of clicks,
  so WoW's controller cursor no longer sends them to the middle of the screen.
- **Top-screen switches** (player frame, target frame, nameplates, minimap, chat, tracker...) go as shortcuts too: no more stray
  clicks in the middle of the screen. Ctrl+Shift+PageDown is bound in the game, so those rows use other keys.
- The start screen keeps its Stream button, and the app never downloads a game client onto the device.

**New**
- **Instant relog:** the add-ons remember the HUD switches, the layout (minimap, chat, tracker) and the cast bar per character and
  put them back at login, instead of the app re-sending about 20 taps. The Start button's mode and B's pet follow are no longer
  re-told after every login either.
- **Normal game UI** (Settings > Top screen > Game windows): minimap, chat, tracker and cast bar back in one tap, for
  `/` commands or playing on the PC. Typing `/wcui reset` in the game's chat brings back the whole UI, including the frames.

**Known problems and untested parts:** see [FORK.md](FORK.md) (*Known problems*, *Untested*). In short: chat commands typed in
the app's chat aren't sent (use the game's chat with *Normal game UI* on), and the pet and party frame switches are untested.

Updating: rebuild the app (`./linux-build.sh`) and pull the repository on the PC; the helper installs the add-ons (set 407) when the
Thor connects, then `/reload` in game.
