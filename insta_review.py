"""Instagram non-follower reviewer.

Loads your Instagram data export, finds accounts you follow who don't
follow you back, and lets you review each one. For each account you can
open it in your browser (where you unfollow manually) and mark it as
Keep or Unfollow. Decisions are saved to decisions.json next to this
script.
"""

from __future__ import annotations

import json
import tkinter as tk
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


DECISIONS_FILE = Path(__file__).resolve().parent / "decisions.json"


@dataclass
class Account:
    username: str
    url: str


def extract_usernames(payload) -> list[Account]:
    """Pull Account entries out of an Instagram export JSON blob.

    Instagram wraps followers as a top-level list and following under
    ``relationships_following``. Each entry carries one ``string_list_data``
    item with ``value`` (username) and ``href`` (profile URL).
    """
    if isinstance(payload, dict):
        entries = payload.get("relationships_following") or payload.get(
            "relationships_followers", []
        )
    else:
        entries = payload

    accounts: list[Account] = []
    for entry in entries:
        for item in entry.get("string_list_data", []):
            username = item.get("value") or ""
            url = item.get("href") or f"https://www.instagram.com/{username}"
            if username:
                accounts.append(Account(username=username, url=url))
    return accounts


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_connections_dir(root: Path) -> Path | None:
    """Locate the followers_and_following folder inside an export tree."""
    candidates = [
        root / "connections" / "followers_and_following",
        root / "followers_and_following",
        root,
    ]
    for candidate in candidates:
        if (candidate / "following.json").exists():
            return candidate
    for match in root.rglob("following.json"):
        return match.parent
    return None


def load_decisions() -> dict[str, str]:
    if DECISIONS_FILE.exists():
        try:
            return json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_decisions(decisions: dict[str, str]) -> None:
    DECISIONS_FILE.write_text(
        json.dumps(decisions, indent=2, sort_keys=True), encoding="utf-8"
    )


class ReviewerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Instagram non-follower reviewer")
        self.root.geometry("640x420")

        self.non_mutuals: list[Account] = []
        self.decisions: dict[str, str] = load_decisions()
        self.index = 0

        self._build_ui()
        self._refresh_view()

    def _build_ui(self) -> None:
        top = ttk.Frame(self.root, padding=12)
        top.pack(fill="x")

        ttk.Button(top, text="Load export folder", command=self.load_export).pack(
            side="left"
        )
        self.status_var = tk.StringVar(value="No data loaded.")
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=12)

        mid = ttk.Frame(self.root, padding=12)
        mid.pack(fill="both", expand=True)

        self.username_var = tk.StringVar(value="—")
        ttk.Label(
            mid, textvariable=self.username_var, font=("Helvetica", 22, "bold")
        ).pack(pady=6)

        self.url_var = tk.StringVar(value="")
        url_label = ttk.Label(mid, textvariable=self.url_var, foreground="#1565c0")
        url_label.pack()
        url_label.bind("<Button-1>", lambda _e: self.open_in_browser())

        self.decision_var = tk.StringVar(value="")
        ttk.Label(mid, textvariable=self.decision_var, foreground="#555").pack(pady=6)

        self.progress_var = tk.StringVar(value="")
        ttk.Label(mid, textvariable=self.progress_var).pack(pady=4)

        btns = ttk.Frame(self.root, padding=12)
        btns.pack(fill="x")

        ttk.Button(btns, text="Open in browser", command=self.open_in_browser).pack(
            side="left"
        )
        ttk.Button(btns, text="Keep", command=lambda: self.decide("keep")).pack(
            side="left", padx=4
        )
        ttk.Button(
            btns, text="Mark to unfollow", command=lambda: self.decide("unfollow")
        ).pack(side="left", padx=4)
        ttk.Button(btns, text="Skip", command=lambda: self.step(1)).pack(
            side="left", padx=4
        )
        ttk.Button(btns, text="Previous", command=lambda: self.step(-1)).pack(
            side="right"
        )
        ttk.Button(btns, text="Export unfollow list", command=self.export_list).pack(
            side="right", padx=8
        )

    def load_export(self) -> None:
        folder = filedialog.askdirectory(title="Pick your Instagram export folder")
        if not folder:
            return
        root = Path(folder)
        conn_dir = find_connections_dir(root)
        if conn_dir is None:
            messagebox.showerror(
                "Not found",
                "Could not find following.json under that folder. Pick the "
                "folder you got from Instagram's data export.",
            )
            return

        try:
            following = extract_usernames(load_json(conn_dir / "following.json"))
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to read following.json: {exc}")
            return

        follower_files = sorted(conn_dir.glob("followers_*.json"))
        if not follower_files:
            messagebox.showerror(
                "Not found",
                "No followers_*.json files in that export. Instagram usually "
                "ships at least followers_1.json.",
            )
            return

        followers: list[Account] = []
        for fp in follower_files:
            try:
                followers.extend(extract_usernames(load_json(fp)))
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to read {fp.name}: {exc}")
                return

        follower_set = {a.username.lower() for a in followers}
        self.non_mutuals = [
            a for a in following if a.username.lower() not in follower_set
        ]
        self.non_mutuals.sort(key=lambda a: a.username.lower())
        self.index = 0
        self.status_var.set(
            f"{len(following)} following, {len(followers)} followers, "
            f"{len(self.non_mutuals)} don't follow you back."
        )
        self._refresh_view()

    def _refresh_view(self) -> None:
        if not self.non_mutuals:
            self.username_var.set("—")
            self.url_var.set("")
            self.decision_var.set("")
            self.progress_var.set("")
            return

        self.index = max(0, min(self.index, len(self.non_mutuals) - 1))
        acc = self.non_mutuals[self.index]
        self.username_var.set(acc.username)
        self.url_var.set(acc.url)
        current = self.decisions.get(acc.username.lower(), "")
        self.decision_var.set(f"Current: {current}" if current else "Not reviewed")
        reviewed = sum(1 for a in self.non_mutuals if a.username.lower() in self.decisions)
        self.progress_var.set(
            f"{self.index + 1} of {len(self.non_mutuals)}  ·  {reviewed} reviewed"
        )

    def open_in_browser(self) -> None:
        if not self.non_mutuals:
            return
        acc = self.non_mutuals[self.index]
        webbrowser.open(acc.url, new=2)

    def decide(self, choice: str) -> None:
        if not self.non_mutuals:
            return
        acc = self.non_mutuals[self.index]
        self.decisions[acc.username.lower()] = choice
        save_decisions(self.decisions)
        self.step(1)

    def step(self, delta: int) -> None:
        if not self.non_mutuals:
            return
        self.index = (self.index + delta) % len(self.non_mutuals)
        self._refresh_view()

    def export_list(self) -> None:
        if not self.decisions:
            messagebox.showinfo("Nothing to export", "No decisions yet.")
            return
        to_unfollow = sorted(
            u for u, choice in self.decisions.items() if choice == "unfollow"
        )
        if not to_unfollow:
            messagebox.showinfo("Nothing to export", "No accounts marked for unfollow.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile="to_unfollow.txt",
            filetypes=[("Text", "*.txt")],
        )
        if not path:
            return
        Path(path).write_text("\n".join(to_unfollow) + "\n", encoding="utf-8")
        messagebox.showinfo("Exported", f"Wrote {len(to_unfollow)} usernames to {path}")


def main() -> None:
    root = tk.Tk()
    ReviewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
