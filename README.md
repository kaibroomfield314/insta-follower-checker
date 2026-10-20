# insta-follower-checker

Finds Instagram accounts you follow who don't follow you back, lets you
review them one by one, and gives you a one-click open-in-browser button
to unfollow manually (safer than any auto-unfollow tool).

## 1. Get your Instagram data

Instagram no longer exposes followers/following via any public API, so
we use the official data export. It's free and takes anywhere from a
few minutes to ~24 hours.

1. Open Instagram (app or web) → **Settings** → **Accounts Center** →
   **Your information and permissions** → **Download your information**.
2. Pick the account.
3. Choose **Some of your information**, then under *Connections* select
   **Followers and following**. (You can request everything, but this
   is faster.)
4. Format: **JSON**. Date range: **All time**. Quality: any.
5. Submit. You'll get an email when it's ready; download the ZIP.
6. Unzip it anywhere.

Inside you'll find
`connections/followers_and_following/following.json` and
`followers_1.json` (sometimes `followers_2.json`, etc. if you have
many). The app finds them automatically — you just point it at the
unzipped folder.

## 2. Run the reviewer

Python 3.10+ with Tkinter (ships with the python.org installer; on
macOS the system Python also has it).

```bash
python3 insta_review.py
```

Then:

1. Click **Load export folder** and pick the unzipped export folder
   (or any folder above it).
2. The app computes `following − followers` and shows each
   non-follower one at a time.
3. For each one: click **Open in browser** to view the profile and
   unfollow manually on instagram.com, then mark **Keep** or
   **Mark to unfollow** in the app.
4. Decisions are saved to `decisions.json` next to the script, so you
   can quit and resume.
5. When you're done, **Export unfollow list** dumps the usernames you
   flagged into a text file for your records.

## Why manual unfollow

Instagram has no official API for unfollowing from a personal account.
Any automated tool (reverse-engineered private API, Playwright script,
etc.) violates the ToS and risks action-blocks or a ban, especially at
volume. Clicking unfollow yourself after the app surfaces the account
is the safe route.
