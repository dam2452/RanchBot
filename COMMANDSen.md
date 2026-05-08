
---

# 📝 Full Command List

## 🌐 REST API — Batch

- **`POST /api/v1/batch`**: 📦 Send multiple commands in a single request. Example:
  ```json
  {
    "commands": [
      {"command": "szukaj", "args": ["geniusz"]},
      {"command": "wybierz", "args": ["4"]}
    ]
  }
  ```
  Response contains `results` (per-command results) and `summary` (total/succeeded/failed). Max 20 commands per request. `reply_json` defaults to `true`.

## 🚀 Command Shortcuts

- **`/start`**: 👋 Launches the main menu.
- **`/clip <quote>`** / **`/k <quote>`**: 🎥 Clip search.
- **`/search <quote>`** / **`/sz <quote>`**: 🔍 Find clips.
- **`/searchcharacter <character> [emotion]`** / **`/szp`**: 👤 Search scenes by character.
- **`/searchobject <object> [filter]`** / **`/szo`**: 🎯 Search scenes by object.
- **`/sens <query>`** / **`/meaning <query>`** / **`/sen <query>`**: 🧠 Semantic search - text mode.
- **`/sensklatki <query>`** / **`/sensk <query>`**: 🧠 Semantic search - frames mode.
- **`/sensodcinek <query>`** / **`/senso <query>`**: 🧠 Semantic search - episode mode.
- **`/klipsens <query>`** / **`/ksen <query>`** / **`/ks <query>`**: 🎬 Semantic search clip (sends top result).
- **`/list`** / **`/l`**: 📋 List of clips.
- **`/select <clip_number>`** / **`/w <clip_number>`**: 🎯 Clip selection.
- **`/episodes <season>`** / **`/o <season>`**: 🎞️ List of episodes.
- **`/cut <season_episode> <start_time> <end_time>`**: ✂️ Cutting a clip.
- **`/adjust <before> <after>`** / **`/d`**: ⏳ Adjust clip (relative).
- **`/aadjust <before> <after>`** / **`/ad`**: ⏳ Adjust clip (absolute).
- **`/sadjust <n_before> <n_after>`** / **`/sd`**: 🎬 Adjust clip to scene cut boundaries.
- **`/snap`** / **`/dopasuj`** / **`/sp`**: 🎯 Snap last clip to scene cuts.
- **`/klatka [index]`** / **`/frame [index]`** / **`/kl [index]`**: 🖼️ Keyframe from the last clip.
- **`/transcription <quote>`** / **`/t <quote>`**: 📝 Transcription with context for a quote.
- **`/compile all`** / **`/kom all`**: 🎬 Compile all clips.
- **`/compile <range>`** / **`/kom <range>`**: 🎬 Compile a range of clips.
- **`/compile <num1> <num2> ...`** / **`/kom ...`**: 🎬 Compile selected clips.
- **`/concatclips <num1> <num2> ...`** / **`/pk ...`**: 🔗 Concatenate saved clips.
- **`/save <name>`** / **`/z <name>`**: 💾 Save a clip.
- **`/myclips [serial]`** / **`/mk [serial]`**: 📂 Your clips.
- **`/send <name>`** / **`/wys <name>`**: 📤 Send a clip.
- **`/deleteclip <clip_name>`** / **`/uk <clip_name>`**: 🗑️ Delete a clip.
- **`/filter <filters>`** / **`/filtr <filters>`** / **`/f <filters>`**: 🔎 Set search filters (applies to all search commands).
- **`/filter reset`**: 🔄 Clear all active filters.
- **`/filter info`**: ℹ️ Show active filters.
- **`/characters`** / **`/p`**: 👤 Browse characters and scenes.
- **`/klippostac <character> [emotion]`** / **`/kp`**: 🎭 Clip with a character (and optional emotion).
- **`/klipobiekt <object>`** / **`/ko`**: 🎯 Clip with a detected object.
- **`/emotion`** / **`/e`**: 😊 List of available emotions.
- **`/object`** / **`/obj`**: 🎯 Browse scenes with objects.
- **`/objl`** / **`/objlista`**: 🎯 Full list of objects or scenes (as document).
- **`/link <code>`**: 🔗 Link Telegram account to REST account.
- **`/kodkonta`** / **`/accountcode`**: 🔑 Generate a code to create REST API credentials for an existing Telegram account.
- **`/saveclipbyindex <index> [left_adj right_adj] <name>`** / **`/zn`**: 💾 Save a clip from search results by index.
- **`/savedclipthumbnail <name_or_index> [frame]`** / **`/kk`**: 🖼️ Keyframe from a saved clip.
- **`/subscription`** / **`/sub`**: 🔔 Subscription status.
- **`/report <description>`** / **`/r <description>`**: ⚠️ Report an issue.
- **`/serial <series_name>`** / **`/ser <series_name>`**: 📺 Change active series.
- **`/reindex`** / **`/rei`**: 🔄 Reindex series data.
- **`/admin`**: 🔧 Administrative commands.
- **`/addwhitelist <id>`** / **`/addw <id>`**: 📝 Add to whitelist.
- **`/removewhitelist <id>`** / **`/rmw <id>`**: 🚫 Remove from whitelist.
- **`/listwhitelist`** / **`/lw`**: 📄 Whitelist of users.
- **`/listadmins`** / **`/la`**: 🛡️ List of administrators.
- **`/listmoderators`** / **`/lm`**: 🛡️ List of moderators.
- **`/note <user_id> <note>`**: 🗒️ Add a note to a user.
- **`/key <key_content>`** / **`/klucz`**: 🔑 Use a subscription key.
- **`/listkeys`** / **`/lk`**: 🔑 List of subscription keys.
- **`/addkey <days> <note>`** / **`/addk`**: 🔑 Create a new subscription key.
- **`/removekey <key>`** / **`/rmk <key>`**: 🚫 Remove a subscription key.
- **`/addsubscription <user_id> <days>`** / **`/addsub`**: 🔔 Add subscription to a user.
- **`/removesubscription <user_id>`** / **`/rmsub`**: 🚫 Remove a user's subscription.

## 👥 Basic User Commands

- **`/start`** / **`/s`**: 👋 Displays a welcome message with basic commands.
- **`/clip <quote>`** / **`/k <quote>`**: 🎥 Searches for a clip based on a quote. Example: `/clip genius`.
- **`/search <quote>`** / **`/sz <quote>`**: 🔍 Finds clips matching the quote (first 5 results). Example: `/search goat`.
- **`/sens <query>`** / **`/meaning <query>`** / **`/sen <query>`**: 🧠 Semantic search by text (embeddings). Example: `/sens escape from problems`.
- **`/sensklatki <query>`** / **`/sensk <query>`**: 🧠 Semantic search by video frames. Example: `/sensklatki feast`.
- **`/sensodcinek <query>`** / **`/senso <query>`**: 🧠 Semantic search by episode. Example: `/sensodcinek wedding`.
- **`/klipsens <query>`** / **`/ksen <query>`** / **`/ks <query>`**: 🎬 Semantic search - sends top result as clip. Example: `/klipsens escape`.
- **`/list`** / **`/l`**: 📋 Displays all clips found with `/search`.
- **`/select <clip_number>`** / **`/w <clip_number>`**: 🎯 Selects a clip from the list generated by `/search` for further operations. Example: `/select 1`.
- **`/episodes <season>`** / **`/o <season>`**: 🎞️ Displays a list of episodes for the given season. Example: `/episodes 2`.
- **`/cut <season_episode> <start_time> <end_time>`**: ✂️ Cuts a segment from a clip. Example: `/cut S02E10 20:30.11 21:32.50`.
- **`/adjust [clip_number] <before> <after>`** / **`/d`**: ⏳ Adjusts clip RELATIVELY (based on last state). Example: `/adjust -1.5 2.0`.
- **`/aadjust [clip_number] <before> <after>`** / **`/ad`**: ⏳ Adjusts clip ABSOLUTELY (based on original). Example: `/aadjust -5.5 1.2`.
- **`/sadjust <n_before> <n_after>`** / **`/sd`**: 🎬 Expands clip by the given number of scene cuts in each direction. Example: `/sadjust 1 2`.
- **`/snap`** / **`/dopasuj`** / **`/sp`**: 🎯 Snaps the last clip to the nearest scene cuts. No change → informs user.
- **`/klatka [result] [frame]`** / **`/frame`** / **`/kl`**: 🖼️ Returns a keyframe as a JPEG image. `result` (1-5, default 1) — result number from `/search`; falls back to last clip when no active search. `frame` — selector: `0`/`p`/`pierwsza`/`first` = first, `-1`/`o`/`ostatnia`/`last` = last, any integer (0-based, negative counts from end). Examples: `/klatka` · `/klatka 3` · `/klatka 2 last` · `/klatka 1 -2`.
- **`/transcription <quote>`** / **`/t <quote>`**: 📝 Displays transcription with context for the found quote. Example: `/transcription genius`.
- **`/compile all`** / **`/kom all`**: 🎬 Compiles all clips.
- **`/compile <range>`** / **`/kom <range>`**: 🎬 Compiles clips within a range. Example: `/compile 1-4`.
- **`/compile <num1> <num2> ...`** / **`/kom ...`**: 🎬 Compiles selected clips. Example: `/compile 1 5 7`.
- **`/concatclips <num1> <num2> ...`** / **`/pk ...`**: 🔗 Concatenates saved clips into one. Example: `/concatclips 4 2 3`.
- **`/save <name>`** / **`/z <name>`**: 💾 Saves the selected clip with a specified name. Example: `/save my_clip`.
- **`/myclips [serial]`** / **`/mk [serial]`**: 📂 Displays a list of saved clips from all series. With the `serial` parameter, filters to the series set by `/serial`.
- **`/send <name>`** / **`/wys <name>`**: 📤 Sends the saved clip with the specified name. Example: `/send my_clip`.
- **`/deleteclip <clip_name>`** / **`/uk <clip_name>`**: 🗑️ Deletes the saved clip with the specified name. Example: `/uk my_clip`.
- **`/filter <filters>`** / **`/filtr <filters>`** / **`/f <filters>`**: 🔎 Sets search filters that apply to all search commands. Example: `/filter season:2 character:Pawlak`.
- **`/filter reset`**: 🔄 Removes all active filters.
- **`/filter info`**: ℹ️ Shows active filters. Filters expire after 1h of inactivity.
  - `season:X` – filter by season (e.g. `season:2`, `season:1-3`, `season:1,3,5`)
  - `episode:X` – filter by episode (e.g. `episode:S01E05`, `episode:S01E03-S01E07`)
  - `title:X` – filter by episode title (fuzzy match)
  - `character:X` – character visible on scene (e.g. `character:Pawlak`, `character:Pawlak,Kusy`)
  - `emotion:X` – character emotion on scene (e.g. `emotion:happy`)
  - `object:X` – object on scene with optional quantity filter (e.g. `object:chair`, `object:chair>3`)
- **`/clipfilter`** / **`/klipfiltr`** / **`/kf`**: 🎬 Sends a clip based on the active filter. Can take an optional quote (acts like `/k` but with filters applied). Example: `/kf genius`.
- **`/searchfilter`** / **`/szukajfiltr`** / **`/szf`**: 🔎 Returns a list of segments matching the active filter. Can take an optional quote (acts like `/sz` but with filters applied). Example: `/szf genius`. Results saved in `last_search`, accessible for `/select` and `/list`.
- **`/characters`** / **`/p`**: 👤 Displays a list of all characters with episode count.
- **`/characters <character_name>`** / **`/p <character_name>`**: 👤 Displays scenes with the given character. Example: `/characters Wilkowyska`.
- **`/characters <character_name> <emotion>`** / **`/p <character_name> <emotion>`**: 👤 Scenes with character and emotion. Example: `/p Wilkowyska happy`.
- **`/pl`** / **`/postacie_lista`**: 👤 Full list of characters or scenes (as document).
- **`/klippostac <character> [emotion]`** / **`/kp`**: 🎭 Sends a clip with the given character (and optional emotion). Example: `/kp Wilkowyska happy`.
- **`/szukajpostac <character> [emotion]`** / **`/szp`**: 👤 Lists scenes with the given character without sending a clip — results available via `/select` and `/list`. Example: `/szp Wilkowyska happy`.
- **`/klipobiekt <object>`** / **`/ko`**: 🎯 Sends a clip with the given detected object. Example: `/klipobiekt dog`.
- **`/szukajobiekt <object> [filter]`** / **`/szo`**: 🎯 Lists scenes with the given object without sending a clip — results available via `/select` and `/list`. Example: `/szo dog >3`.
- **`/emotion`** / **`/e`**: 😊 Displays a list of available emotions.
- **`/object`** / **`/obj`**: 🎯 Displays a list of all detected objects (most frequent first).
- **`/object <name>`** / **`/obj <name>`**: 🎯 List of scenes with the given object. Example: `/object dog`.
- **`/object <name> <filter>`** / **`/obj <name> <filter>`**: 🎯 List of scenes with count filter. Example: `/obj dog >3`.
- **`/objl`**: 🎯 Full list of all objects (as document).
- **`/objl <name>`**: 🎯 Full list of scenes with the given object (as document).
- **`/objl <name> <filter>`**: 🎯 Full list of scenes with filter (as document).
- **`/link <code>`**: 🔗 Links your Telegram account to a REST API account using a verification code. The code is generated by the REST API (website). Use this when you already have a REST account and want to attach Telegram to it. Example: `/link abc123`.
- **`/kodkonta`** / **`/accountcode`**: 🔑 Generates a one-time code (valid 30 minutes) to create REST API credentials for an existing Telegram account. Use this when you have a bot account (via Telegram) and want to add a login/password for the website. Enter the code on the registration page instead of the standard form.
- **`/zapisznumer <index> <name>`** / **`/zn <index> <name>`**: 💾 Saves a clip from the last search results by index. Optionally with boundary adjustments: `/zn <index> <left_adj> <right_adj> <name>`. Example: `/zn 2 my_clip`.
- **`/klatkaklipu <name_or_index> [frame]`** / **`/kk <name_or_index>`**: 🖼️ Returns a keyframe from a saved clip. `name_or_index` — clip name or its number from `/myclips`. `frame` — selector like in `/klatka`. Example: `/kk my_clip` · `/kk 1 last`.
- **`/subscription`** / **`/sub`**: 🔔 Checks your subscription status.
- **`/report <issue_description>`** / **`/r <issue>`**: ⚠️ Reports an issue to administrators.
- **`/serial <series_name>`** / **`/ser <series_name>`**: 📺 Changes the active series for the user. Example: `/serial ranczo`.

## 🔧 Administrative Commands

- **`/admin`**: 🔧 Displays administrative commands.
- **`/addwhitelist <id>`** / **`/addw <id>`**: 📝 Adds a user to the whitelist. Example: `/addwhitelist 123456789`.
- **`/removewhitelist <id>`** / **`/rmw <id>`**: 🚫 Removes a user from the whitelist. Example: `/removewhitelist 123456789`.
- **`/listwhitelist`** / **`/lw`**: 📄 Displays a list of all users on the whitelist.
- **`/listadmins`** / **`/la`**: 🛡️ Displays a list of all administrators.
- **`/listmoderators`** / **`/lm`**: 🛡️ Displays a list of all moderators.
- **`/note <user_id> <note>`**: 🗒️ Adds or updates a note for a user. Example: `/note 123456789 This is a note`.
- **`/key <key_content>`** / **`/klucz <key_content>`**: 🔑 Uses a subscription key. Example: `/key some_secret_key`.
- **`/listkeys`** / **`/lk`**: 🔑 Displays a list of all subscription keys.
- **`/addkey <days> <note>`** / **`/addk <days> <note>`**: 🔑 Creates a new subscription key for a specified number of days. Example: `/addkey 30 secret_key`.
- **`/removekey <key>`** / **`/rmk <key>`**: 🚫 Removes an existing subscription key. Example: `/removekey some_secret_key`.
- **`/addsubscription <user_id> <days>`** / **`/addsub <user_id> <days>`**: 🔔 Adds subscription to a user for the given number of days. Example: `/addsubscription 123456789 30`.
- **`/removesubscription <user_id>`** / **`/rmsub <user_id>`**: 🚫 Removes a user's subscription. Example: `/removesubscription 123456789`.
- **`/reindex`** / **`/rei`**: 🔄 Reindexes data for the currently selected series (requires administrator privileges).

---
