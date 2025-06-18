
# Clipping Bot REST API Documentation (RanchBot API v1)

**API Version:** v1
**Documentation Date:** April 20, 2025

## Introduction

This API allows interaction with the functionalities of the Clipping Bot (likely based on the "Ranczo" series, judging by commands and examples) using standard HTTP REST requests. It enables searching, editing, managing, and retrieving video clips, as well as managing users and subscriptions (for administrators/moderators).

## Base URL

All endpoint paths described in this documentation are relative to the following base URL:

`https://ranchbot.pl/api/v1`

## Authentication

Interaction with the API requires authentication.

### 1. Obtaining Tokens

* **Endpoint:** `/auth/login`
* **Method:** `POST`
* **Rate Limit:** 5 requests / minute
* **Request Body:**
    ```json
    {
      "username": "your_username",
      "password": "your_password"
    }
    ```
* **Success Response (200 OK):**
    * Returns an `access_token` (JWT) in the JSON response body.
    * Sets a `refresh_token` in a secure, HTTP-only cookie (`refresh_token`).
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
      "token_type": "bearer"
    }
    ```
* **Error Response:**
    * `401 Unauthorized`: {"detail": "Invalid credentials"}

### 2. Refreshing the Access Token

* **Endpoint:** `/auth/refresh`
* **Method:** `POST`
* **Rate Limit:** 5 requests / minute
* **Requirements:** Valid `refresh_token` cookie.
* **Request Body:** Empty (`{}`)
* **Success Response (200 OK):**
    * Returns a new `access_token`.
    * Sets a new `refresh_token` in the HTTP-only cookie, invalidating the old one.
    ```json
    {
      "access_token": "new_eyJhbGciOiJIUzI1NiI...",
      "token_type": "bearer"
    }
    ```
* **Error Response:**
    * `401 Unauthorized`: {"detail": "No refresh token"} or {"detail": "Invalid refresh token"}
    * `404 Not Found`: {"detail": "User not found"}

### 3. Using the Access Token

For all other API command endpoints, the access token (`access_token`) must be passed in the `Authorization` header.

**Header:**
`Authorization: Bearer <YOUR_JWT_ACCESS_TOKEN>`

The JWT token contains user information (`user_id`, `username`, `full_name`), which is used by the API for identification and authorization.

## Request Format (For Command Endpoints)

* **Method:** `POST`
* **Headers:**
    * `Content-Type: application/json`
    * `Authorization: Bearer <YOUR_JWT_ACCESS_TOKEN>`
* **Request Body:**
    ```json
    {
      "args": ["argument1", "argument2", ...]
    }
    ```
    * `args`: A list of strings representing the arguments for the given command (endpoint). For REST API calls, the `reply_json` flag is implicitly true.

## Response Format (For Command Endpoints)

### Success Response (Status Code 200 OK)

* **Video Response:**
    * For endpoints that generate or send a video clip (`/k`, `/w`, `/d`, `/wytnij`, `/kom`, `/pk`, `/wys`).
    * **Header:** `Content-Type: video/mp4`
    * **Body:** Raw binary data of the video file.
* **JSON Response (Specific Data):**
    * For endpoints returning specific data structures (lists, statuses, search results, etc.).
    * **Header:** `Content-Type: application/json`
    * **Body:** A JSON object containing endpoint-specific data (see individual endpoint descriptions).
* **JSON Response (Text / Markdown):**
    * For endpoints returning a simple text message or Markdown-formatted text (e.g., confirmations, help messages).
    * **Header:** `Content-Type: application/json`
    * **Body:**
        ```json
        // For plain text
        {"type": "text", "content": "Message content..."}
        // For Markdown
        {"type": "markdown", "content": "Message content in **Markdown**..."}
        ```

### Error Response

* **Header:** `Content-Type: application/json`
* **Body:** Standard FastAPI error object.
    ```json
    {
      "detail": "Error description..."
    }
    ```
* **Status Codes (Probable Mappings):**
    * `400 Bad Request`: Invalid JSON format in request; Invalid arguments (count, format, length) for the command (e.g., `RK.INVALID_ARGS_COUNT`, `RK.CLIP_NAME_LENGTH_EXCEEDED`, `RK.INCORRECT_TIME_FORMAT`).
    * `401 Unauthorized`: Missing, invalid, or expired JWT token; Invalid data within the token.
    * `403 Forbidden`: Lacking required permissions for the action (e.g., no subscription (`RK.NO_SUBSCRIPTION`), user not whitelisted, attempt to use admin/moderator command without the appropriate role).
    * `404 Not Found`: Unknown endpoint (command); Resource not found (e.g., clip (`RK.CLIP_NOT_EXIST`), user (`RK.USER_NOT_FOUND`), previous search results (`RK.NO_PREVIOUS_SEARCH_RESULTS`), episodes (`RK.NO_EPISODES_FOUND`)).
    * `409 Conflict`: Attempt to create a resource that already exists (e.g., `RK.CLIP_NAME_EXISTS`, `RK.KEY_ALREADY_EXISTS`). *(Probable code; requires handler confirmation)*.
    * `429 Too Many Requests`: Rate limit exceeded.
    * `500 Internal Server Error`: Internal server error during request processing (e.g., database error, video extraction error (`RK.EXTRACTION_FAILURE`), subscription add error (`RK.SUBSCRIPTION_ERROR`)). *(Probable code; requires handler confirmation)*.

## Rate Limiting

The API employs rate limiting **per user**:
* **Command Endpoints:** **5 requests / 30 seconds**.
* **Authentication Endpoints** (`/auth/login`, `/auth/refresh`): **5 requests / minute**.

Exceeding the limit will result in a response with status code `429 Too Many Requests`.

## API Command Endpoints

The following endpoints correspond to the bot commands. All require the `POST` method and `Bearer Token` authentication. Endpoint paths often use the shorter command aliases.

---

### 🔍 Searching and Browse Clips 🔍

---

#### `/k` (Alias: `/klip`) - Find and Get Clip by Quote

Searches for the *first* clip matching the quote and returns it directly as a video file. Stores clip info as the "last used" clip for subsequent `/z` (save) or `/d` (adjust) commands.

* **Permissions:** Subscribed
* **Arguments (`args`):** `["<quote>"]`
    * `<quote>` (string): Text fragment to search for.
* **Success Response (200 OK):** Video file (`Content-Type: video/mp4`).
* **Possible Errors:** 400 (quote too short/long), 404 (segment not found), 500 (extraction error).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/k \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["genius"]}' \
      --output resulting_clip.mp4
    ```

---

#### `/sz` (Alias: `/szukaj`) - Find Matching Clips by Quote

Searches for clips matching the quote and returns a list of found segments (up to a limit, typically 5 initially, but full list stored for `/l`). Saves the search results for use with `/l` (list), `/w` (select), and `/kom` (compile) commands.

* **Permissions:** Subscribed
* **Arguments (`args`):** `["<quote>"]`
    * `<quote>` (string): Text fragment to search for.
* **Success Response (200 OK):** JSON
    ```json
    {
      "quote": "searched quote",
      "results": [
        {
          "id": "...", // Segment ID
          "text": "...", // Segment text
          "start": 123.45,
          "end": 126.78,
          "duration": 3.33,
          "video_path": "...", // Path to video file on server
          "episode_info": { "season": 1, "episode_number": 5, ... }
        },
        ... // Other matching segments
      ]
    }
    ```
* **Possible Errors:** 400 (quote too short/long), 404 (no segments found - `RK.NO_SEGMENTS_FOUND`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/sz \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["goat"]}'
    ```

---

#### `/l` (Alias: `/lista`) - List Full Search Results

Returns *all* segments found by the last successful `/sz` call for the current user.

* **Permissions:** Subscribed
* **Requires:** Prior successful `/sz` call.
* **Arguments (`args`):** `[]`
* **Success Response (200 OK):** JSON
    ```json
    {
      "query": "last searched quote",
      "segments": [
         // Full list of segments like in /sz
      ],
      "season_info": { ... } // Information about seasons
    }
    ```
* **Possible Errors:** 404 (no previous search results - `RK.NO_PREVIOUS_SEARCH_RESULTS`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/l \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": []}'
    ```

---

#### `/w` (Alias: `/wybierz`) - Select and Get Clip from List

Selects a clip from the list obtained via `/sz` (by number) and returns it directly as a video file. Stores clip info as the "last used" clip for subsequent `/z` (save) or `/d` (adjust) commands.

* **Permissions:** Subscribed
* **Requires:** Prior successful `/sz` call.
* **Arguments (`args`):** `["<clip_number>"]`
    * `<clip_number>` (string): The number of the clip from the `/sz` results list (starting from 1).
* **Success Response (200 OK):** Video file (`Content-Type: video/mp4`).
* **Possible Errors:** 400 (invalid number), 404 (no previous search results, invalid index - `RK.INVALID_SEGMENT_NUMBER`), 500 (extraction error).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/w \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["1"]}' \
      --output selected_clip.mp4
    ```

---

#### `/o` (Alias: `/odcinki`) - List Episodes for a Season

Displays a list of episodes for the specified season.

* **Permissions:** Subscribed
* **Arguments (`args`):** `["<season_number>"]`
    * `<season_number>` (string): The season number (integer).
* **Success Response (200 OK):** JSON
    ```json
    {
      "season": 2,
      "episodes": [
        {"episode_number": 1, "title": "Episode Title 1", "absolute_number": 14, ...},
        {"episode_number": 2, "title": "Episode Title 2", "absolute_number": 15, ...}
        // ... other episodes
      ],
      "season_info": { ... } // Information about seasons
    }
    ```
* **Possible Errors:** 400 (invalid season number), 404 (no episodes found for the season - `RK.NO_EPISODES_FOUND`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/o \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["2"]}'
    ```

---

#### `/wytnij` - Cut Clip Manually

Creates a new video clip by cutting a fragment from a specific episode based on the provided start and end times. Returns the clip as a video file. Stores clip info as the "last used" clip for `/z` (save) or `/d` (adjust).

* **Permissions:** Subscribed
* **Arguments (`args`):** `["<season_episode>", "<start_time>", "<end_time>"]`
    * `<season_episode>` (string): Episode identifier in `S<season_num>E<episode_num>` format, e.g., `S07E06`.
    * `<start_time>` (string): Start time in `MM:SS.ms` or `HH:MM:SS.ms` format, e.g., `36:47.50`.
    * `<end_time>` (string): End time, e.g., `36:49.00`.
* **Success Response (200 OK):** Video file (`Content-Type: video/mp4`).
* **Possible Errors:** 400 (invalid season/episode/time format - `RK.INCORRECT_SEASON_EPISODE_FORMAT` / `RK.INCORRECT_TIME_FORMAT`, end time earlier than start time - `RK.END_TIME_EARLIER_THAN_START`), 404 (video file for episode not found - `RK.VIDEO_FILE_NOT_EXIST`), 500 (extraction error).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/wytnij \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["S07E06", "36:47.50", "36:49.00"]}' \
      --output manually_cut_clip.mp4
    ```

---

### ✂️ Editing Clips ✂️

---

#### `/d` (Alias: `/dostosuj`) - Adjust Clip Timestamps

Modifies the start and end times of the *last generated/selected clip* (from `/k`, `/w`, `/d`, `/wytnij`, `/kom`, `/pk`) OR a specific clip from the last `/sz` search results. Returns the modified clip as a video file. Stores the adjusted clip info as the "last used" clip for `/z` (save) or `/d` (adjust).

* **Permissions:** Subscribed
* **Requires:** Prior call to a clip generation/selection command OR a `/sz` call (for the version with clip number).
* **Arguments (`args`):**
    * Version 1 (Adjust last clip): `["<extend_before>", "<extend_after>"]`
    * Version 2 (Adjust clip from `/sz` list): `["<clip_number>", "<extend_before>", "<extend_after>"]`
        * `<clip_number>` (string): Number of the clip from the `/sz` list (starting from 1).
        * `<extend_before>` (string): Value in seconds (can be negative) to shift the start time. E.g., `-5.5` means start 5.5 seconds earlier.
        * `<extend_after>` (string): Value in seconds (can be negative) to shift the end time. E.g., `1.2` means end 1.2 seconds later.
* **Success Response (200 OK):** Video file (`Content-Type: video/mp4`).
* **Possible Errors:** 400 (invalid arguments, adjustment limit exceeded - `RK.MAX_EXTENSION_LIMIT`), 404 (no last clip/search results found - `RK.NO_QUOTES_SELECTED` / `RK.NO_PREVIOUS_SEARCHES`, invalid clip number - `RK.INVALID_SEGMENT_INDEX`), 500 (extraction error).
* **Example Request (`curl` - Version 1):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/d \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["-5.5", "1.2"]}' \
      --output adjusted_clip.mp4
    ```
* **Example Request (`curl` - Version 2):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/d \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["1", "10.0", "-3"]}' \
      --output adjusted_clip_from_list.mp4
    ```

---

#### `/kom` (Alias: `/kompiluj`) - Compile Clips (from Search Results)

Combines multiple clips from the last search results list (`/sz`) into a single video file and returns it. Stores the compilation as the "last used" clip for `/z` (save) or `/d` (adjust).

* **Permissions:** Subscribed
* **Requires:** Prior successful `/sz` call.
* **Arguments (`args`):**
    * Version 1: `["wszystko"]` (or `all`)
    * Version 2: `["<range>"]` (e.g., `"1-4"`)
    * Version 3: `["<clip_number1>", "<clip_number2>", ...]` (e.g., `"1", "5", "7"`)
* **Success Response (200 OK):** Video file (`Content-Type: video/mp4`).
* **Possible Errors:** 400 (invalid range/number - `RK.INVALID_RANGE` / `RK.INVALID_INDEX`, exceeded clip count/total duration - `RK.MAX_CLIPS_EXCEEDED` / `RK.CLIP_TIME_EXCEEDED`), 404 (no previous search results, no matching segments found - `RK.NO_PREVIOUS_SEARCH_RESULTS` / `RK.NO_MATCHING_SEGMENTS_FOUND`), 500 (compilation error).
* **Example Request (`curl` - Version 3):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/kom \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["1", "5", "7"]}' \
      --output compilation_from_search.mp4
    ```

---

#### `/pk` (Alias: `/polaczklipy`) - Concatenate Saved Clips

Combines specified saved clips (from the `/mk` list) into a single new video file and returns it. Stores the compilation as the "last used" clip for `/z` (save) or `/d` (adjust).

* **Permissions:** Subscribed
* **Arguments (`args`):** `["<clip_number1>", "<clip_number2>", ...]`
    * `<clip_numberN>` (string): Numbers of the clips from the list returned by `/mk`.
* **Success Response (200 OK):** Video file (`Content-Type: video/mp4`).
* **Possible Errors:** 400 (invalid number, exceeded total duration), 404 (no saved clips, no matching clips found - `RK.NO_MATCHING_CLIPS_FOUND`), 500 (compilation error).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/pk \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["4", "2", "3"]}' \
      --output compilation_of_saved.mp4
    ```

---

### 📁 Managing Saved Clips 📁

---

#### `/z` (Alias: `/zapisz`) - Save Last Clip

Saves the *last generated/selected clip* (from `/k`, `/w`, `/d`, `/wytnij`, `/kom`, `/pk`) under the specified name to the user's account.

* **Permissions:** Subscribed
* **Requires:** Prior call to a clip generation/selection command.
* **Arguments (`args`):** `["<name>"]`
    * `<name>` (string): The name to save the clip under (max length defined in `settings.MAX_CLIP_NAME_LENGTH`).
* **Success Response (200 OK):** JSON (Type TEXT)
    ```json
    {"type": "text", "content": "Clip 'your_name' saved successfully."}
    ```
* **Possible Errors:** 400 (name not provided - `RK.CLIP_NAME_NOT_PROVIDED`, name too long - `RK.CLIP_NAME_LENGTH_EXCEEDED`, clip limit exceeded - `RK.CLIP_LIMIT_EXCEEDED`), 404 (no last clip to save - `RK.NO_SEGMENT_SELECTED`), 409 (clip name already exists - `RK.CLIP_NAME_EXISTS`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/z \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["tractor"]}'
    ```

---

#### `/mk` (Alias: `/mojeklipy`) - List My Saved Clips

Displays a list of clips saved by the user.

* **Permissions:** Subscribed
* **Arguments (`args`):** `[]`
* **Success Response (200 OK):** JSON
    ```json
    {
      "clips": [
        {"id": 1, "name": "tractor", "source": "S01E05 12:30.0-12:35.5", "duration": 5.5, "created_at": "...", "is_compilation": false},
        {"id": 2, "name": "compilation1", "source": "Compilation", "duration": 30.2, "created_at": "...", "is_compilation": true},
        ...
      ],
      "season_info": { ... } // Information about seasons
    }
    // Or if no clips:
    { "clips": [] }
    ```
* **Possible Errors:** No specific errors besides general ones.
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/mk \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": []}'
    ```

---

#### `/wys` (Alias: `/wyslij`) - Send Saved Clip

Retrieves a saved clip by its number (from the `/mk` list) or name and returns it as a video file.

* **Permissions:** Subscribed
* **Arguments (`args`):** `["<clip_number_or_name>"]`
    * `<clip_number_or_name>` (string): The number of the clip from the `/mk` list or its exact name.
* **Success Response (200 OK):** Video file (`Content-Type: video/mp4`).
* **Possible Errors:** 400 (argument missing - `RK.GIVE_CLIP_NAME`), 404 (clip not found by number/name - `RK.CLIP_NOT_FOUND_NUMBER` / `RK.CLIP_NOT_FOUND_NAME`), 500 (clip file is empty or corrupted - `RK.EMPTY_CLIP_FILE` / `RK.EMPTY_FILE_ERROR`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/wys \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["1"]}' \
      --output saved_clip.mp4
    ```

---

#### `/uk` (Alias: `/usunklip`) - Delete Saved Clip

Deletes a saved clip specified by its number (from the `/mk` list).

* **Permissions:** Subscribed
* **Arguments (`args`):** `["<clip_number>"]`
    * `<clip_number>` (string): The number of the clip from the `/mk` list.
* **Success Response (200 OK):** JSON (Type TEXT)
    ```json
    {"type": "text", "content": "Clip 'deleted_clip_name' deleted."}
    ```
* **Possible Errors:** 400 (invalid number), 404 (clip with the specified number does not exist - `RK.CLIP_NOT_EXIST`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/uk \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["2"]}'
    ```

---

### 🛠️ Error Reporting 🛠️

---

#### `/r` (Alias: `/report`) - Report an Issue

Sends an issue report to the administrator.

* **Permissions:** Subscribed
* **Arguments (`args`):** `["<issue_description>"]`
    * `<issue_description>` (string): Text description of the problem encountered (max length defined in `settings.MAX_REPORT_LENGTH`).
* **Success Response (200 OK):** JSON (Type TEXT)
    ```json
    {"type": "text", "content": "Thank you for your report."}
    ```
* **Possible Errors:** 400 (description missing - `RK.NO_REPORT_CONTENT`, description too long - `RK.LIMIT_EXCEEDED_REPORT_LENGTH`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/r \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["The /search command hangs on long quotes."]}'
    ```

---

### 🔔 Subscriptions 🔔

---

#### `/sub` (Alias: `/subskrypcja`) - Check Subscription Status

Checks the status and expiration date of the user's subscription.

* **Permissions:** Whitelisted
* **Arguments (`args`):** `[]`
* **Success Response (200 OK):** JSON
    ```json
    {
      "username": "your_username",
      "subscription_end": "YYYY-MM-DD", // Expiration date in ISO format
      "days_remaining": 30 // Number of remaining days
    }
    ```
* **Error Response:** 403 (no active subscription - `RK.NO_SUBSCRIPTION`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/sub \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": []}'
    ```

---

### 🔐 User Management (Admin/Moderator) 🔐

---

#### `/addw` (Alias: `/addwhitelist`) - Add User to Whitelist

Adds a user (identified by ID) to the whitelist, allowing bot/API usage. Requires Admin permissions.

* **Permissions:** Admin
* **Arguments (`args`):** `["<user_id>"]`
    * `<user_id>` (string): The user's ID (numeric).
* **Success Response (200 OK):** JSON
    ```json
    {"user_id": 123456789}
    ```
* **Possible Errors:** 400 (ID missing or not numeric - `RK.NO_USER_ID_PROVIDED`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/addw \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
      -d '{"args": ["123456789"]}'
    ```

---

#### `/rmw` (Alias: `/removewhitelist`) - Remove User from Whitelist

Removes a user from the whitelist. Requires Admin permissions.

* **Permissions:** Admin
* **Arguments (`args`):** `["<user_id>"]`
    * `<user_id>` (string): The user's ID (numeric).
* **Success Response (200 OK):** JSON (Type TEXT)
    ```json
    {"type": "text", "content": "User 123456789 removed from whitelist."}
    ```
* **Possible Errors:** 400 (ID missing or not numeric), 404 (user not found in database - `RK.USER_NOT_IN_WHITELIST`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/rmw \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
      -d '{"args": ["123456789"]}'
    ```

---

#### `/lw` (Alias: `/listwhitelist`) - List Whitelisted Users

Displays a list of all users on the whitelist. Requires Moderator permissions.

* **Permissions:** Moderator
* **Arguments (`args`):** `[]`
* **Success Response (200 OK):** JSON
    ```json
    {
      "whitelist": [
        { "user_id": 123, "username": "user1", "full_name": "User One", "note": null, "created_at": "...", "updated_at": "...", "role": "user", "subscription_end": null },
        // ... other users
      ]
      // Or if empty:
      // { "whitelist": [] }
    }
    ```
* **Possible Errors:** No specific errors.
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/lw \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <MODERATOR_JWT_TOKEN>" \
      -d '{"args": []}'
    ```

---

#### `/la` (Alias: `/listadmins`) - List Admins

Displays a list of administrators. Requires Moderator permissions.

* **Permissions:** Moderator
* **Arguments (`args`):** `[]`
* **Success Response (200 OK):** JSON (Structure similar to `/lw`, key is `"admins"`).
* **Possible Errors:** No specific errors.
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/la \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <MODERATOR_JWT_TOKEN>" \
      -d '{"args": []}'
    ```

---

#### `/lm` (Alias: `/listmoderators`) - List Moderators

Displays a list of moderators. Requires Moderator permissions.

* **Permissions:** Moderator
* **Arguments (`args`):** `[]`
* **Success Response (200 OK):** JSON (Structure similar to `/lw`, key is `"moderators"`).
* **Possible Errors:** No specific errors.
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/lm \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <MODERATOR_JWT_TOKEN>" \
      -d '{"args": []}'
    ```

---

#### `/klucz` (Alias: `/key`) - Use Subscription Key

Activates a subscription for the user making the request using the provided key.

* **Permissions:** AnyUser (Any authenticated user)
* **Arguments (`args`):** `["<subscription_key>"]`
    * `<subscription_key>` (string): The unique key to activate the subscription.
* **Success Response (200 OK):** JSON
    ```json
    {"days": 30} // Number of days the subscription was activated/extended for
    ```
* **Possible Errors:** 400 (key missing - `RK.NO_KEY_PROVIDED`), 404 (invalid or used key - `RK.INVALID_KEY`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/klucz \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <USER_JWT_TOKEN>" \
      -d '{"args": ["some_secret_key"]}'
    ```

---

#### `/lk` (Alias: `/listkey`) - List Subscription Keys

Displays a list of all generated subscription keys (active and used). Requires Admin permissions.

* **Permissions:** Admin
* **Arguments (`args`):** `[]`
* **Success Response (200 OK):** JSON
    ```json
    {
      "keys": [
        {"key": "key1", "days": 30, "is_used": false, "used_by": null, "used_at": null, "created_at": "..."},
        {"key": "key2", "days": 7, "is_used": true, "used_by": 12345, "used_at": "...", "created_at": "..."}
        // ... other keys
      ]
      // Or if empty:
      // { "keys": [] }
    }
    ```
* **Possible Errors:** No specific errors.
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/lk \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
      -d '{"args": []}'
    ```

---

#### `/addk` (Alias: `/addkey`) - Create Subscription Key

Generates a new subscription key. Requires Admin permissions.

* **Permissions:** Admin
* **Arguments (`args`):** `["<days>", "<note_or_key>"]`
    * `<days>` (string): Number of subscription days the key grants (must be > 0).
    * `<note_or_key>` (string): A descriptive note or the desired key content (can contain spaces).
* **Success Response (200 OK):** JSON
    ```json
    {"days": 30, "key": "generated_note_or_key"}
    ```
* **Possible Errors:** 400 (invalid number of days - `RK.CREATE_KEY_USAGE`), 409 (key/note already exists - `RK.KEY_ALREADY_EXISTS`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/addk \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
      -d '{"args": ["30", "secret key for X"]}'
    ```

---

#### `/rmk` (Alias: `/removekey`) - Remove Subscription Key

Deletes an existing subscription key, preventing its future use. Requires Admin permissions.

* **Permissions:** Admin
* **Arguments (`args`):** `["<key_to_delete>"]`
    * `<key_to_delete>` (string): The subscription key to remove.
* **Success Response (200 OK):** JSON (Type TEXT)
    ```json
    {"type": "text", "content": "Key 'key_to_delete' removed."}
    ```
* **Possible Errors:** 400 (key missing - `RK.REMOVE_KEY_USAGE`), 404 (key does not exist - `RK.REMOVE_KEY_FAILURE`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/rmk \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
      -d '{"args": ["some_secret_key"]}'
    ```

---

#### `/note` - Add/Update User Note

Adds or updates a note associated with a user. Requires Moderator permissions.

* **Permissions:** Moderator
* **Arguments (`args`):** `["<user_id>", "<note_content>"]`
    * `<user_id>` (string): The user's ID (numeric).
    * `<note_content>` (string): Any text content for the note.
* **Success Response (200 OK):** JSON (Type TEXT)
    ```json
    {"type": "text", "content": "Note updated."}
    ```
* **Possible Errors:** 400 (invalid arguments, ID not numeric - `RK.NO_NOTE_PROVIDED` / `RK.INVALID_USER_ID`), 404 (user not found).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/note \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <MODERATOR_JWT_TOKEN>" \
      -d '{"args": ["123456789", "Test note for user."]}'
    ```

---

### 💳 Subscription Management (Admin) 💳

---

#### `/addsub` (Alias: `/addsubscription`) - Add Subscription to User

Directly adds or extends a subscription for the specified user ID by a number of days. Requires Admin permissions.

* **Permissions:** Admin
* **Arguments (`args`):** `["<user_id>", "<days>"]`
    * `<user_id>` (string): The user's ID (numeric).
    * `<days>` (string): Number of days to add to the subscription (numeric).
* **Success Response (200 OK):** JSON
    ```json
    {
      "user_id": 123456789,
      "new_end_date": "YYYY-MM-DD" // New subscription end date
    }
    ```
* **Possible Errors:** 400 (invalid ID/days - `RK.NO_USER_ID_PROVIDED`), 404 (user not found), 500 (error adding subscription - `RK.SUBSCRIPTION_ERROR`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/addsub \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
      -d '{"args": ["123456789", "30"]}'
    ```

---

#### `/rmsub` (Alias: `/removesubscription`) - Remove User Subscription

Immediately removes (deactivates) the subscription for the specified user ID. Requires Admin permissions.

* **Permissions:** Admin
* **Arguments (`args`):** `["<user_id>"]`
    * `<user_id>` (string): The user's ID (numeric).
* **Success Response (200 OK):** JSON (Type TEXT)
    ```json
    {"type": "text", "content": "Subscription for user 123456789 removed."}
    ```
* **Possible Errors:** 400 (invalid ID), 404 (user not found).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/rmsub \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
      -d '{"args": ["123456789"]}'
    ```

---

### 🔍 Transcription Management 🔍

---

#### `/t` (Alias: `/transkrypcja`) - Search Transcriptions

Searches for the provided quote directly within the full transcriptions and returns the text fragment including context. Requires Moderator permissions.

* **Permissions:** Moderator
* **Arguments (`args`):** `["<quote>"]`
    * `<quote>` (string): Text to search for in transcriptions.
* **Success Response (200 OK):** JSON
    ```json
    {
      "quote": "searched quote",
      "segment": {
        "id": "...",
        "text": "... context before ... [searched quote] ... context after ...",
        "start": 123.45,
        "end": 126.78,
        "duration": 3.33,
        "video_path": "...",
        "episode_info": { "season": 1, "episode_number": 5, ... }
        // + potential additional context fields
      }
    }
    ```
* **Possible Errors:** 400 (quote missing - `RK.NO_QUOTE_PROVIDED`), 404 (quote not found in transcriptions - `RK.NO_SEGMENTS_FOUND`).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/t \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <MODERATOR_JWT_TOKEN>" \
      -d '{"args": ["Are you not sorry about this beautiful office?"]}'
    ```

---

### ⚙️ Other ⚙️

---

#### `/s` (Alias: `/start`) - Help / Main Menu

Displays basic information about the bot or a specific help section.

* **Permissions:** Whitelisted
* **Arguments (`args`):** `[]` (main menu) or `["<section>"]` (e.g., `"list"`, `"edit"`, `"shortcuts"`)
* **Success Response (200 OK):** JSON (Type MARKDOWN)
    ```json
    {"type": "markdown", "content": "<Help text in Markdown format...>"}
    ```
* **Possible Errors:** 400 (invalid argument count).
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/s \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <YOUR_JWT_TOKEN>" \
      -d '{"args": ["shortcuts"]}'
    ```

---

#### `/admin` - Admin Help

Displays administrative commands or their shortcuts. Requires Moderator permissions.

* **Permissions:** Moderator
* **Arguments (`args`):** `[]` (help) or `["skroty"]` (or similar for shortcuts)
* **Success Response (200 OK):** JSON (Type MARKDOWN)
    ```json
    {"type": "markdown", "content": "<Admin help text / shortcuts in Markdown...>"}
    ```
* **Possible Errors:** No specific errors.
* **Example Request (`curl`):**
    ```bash
    curl -X POST https://ranchbot.pl/api/v1/admin \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer <MODERATOR_JWT_TOKEN>" \
      -d '{"args": ["skroty"]}'
    ```

---