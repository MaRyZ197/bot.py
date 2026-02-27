import os
import json
import time
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright

BOARD_URL = os.getenv("THREAD_URL")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))
STATE_FILE = "last_post.json"

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"last_post_id": None}

def save_state(post_id):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_post_id": post_id}, f)

def send_to_discord(post):
    payload = {
        "username": "Metin2 Board Bot",
        "embeds": [{
            "title": "📢 Postare nouă Item Shop",
            "description": post["content"][:4000],
            "url": post["url"],
            "color": 15158332,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)

def main():
    print("🤖 Bot pornit (Playwright + Fly.io)")
    state = load_state()
    last_post_id = state.get("last_post_id")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        if not last_post_id:
            print("📌 Inițializare stare...")
            page.goto(BOARD_URL, timeout=60000)
            page.wait_for_selector("a[href*='/thread/']", timeout=30000)
            threads = list(set(
                page.eval_on_selector_all(
                    "a[href*='/thread/']",
                    "els => els.map(e => e.href)"
                )
            ))
            for thread in threads:
                page.goto(thread)
                posts = page.query_selector_all("article")
                if posts:
                    last_post_id = posts[-1].get_attribute("id")
            if last_post_id:
                save_state(last_post_id)
            time.sleep(CHECK_INTERVAL)

        while True:
            try:
                page.goto(BOARD_URL, timeout=60000)
                page.wait_for_selector("a[href*='/thread/']", timeout=30000)

                threads = list(set(
                    page.eval_on_selector_all(
                        "a[href*='/thread/']",
                        "els => els.map(e => e.href)"
                    )
                ))

                new_posts = []

                for thread in threads:
                    page.goto(thread)
                    posts = page.query_selector_all("article")
                    if not posts:
                        continue
                    last = posts[-1]
                    post_id = last.get_attribute("id")
                    if post_id != last_post_id:
                        content = last.inner_text()
                        new_posts.append({
                            "id": post_id,
                            "content": content,
                            "url": f"{thread}#{post_id}"
                        })

                if new_posts:
                    for post in reversed(new_posts):
                        send_to_discord(post)
                        save_state(post["id"])
                        last_post_id = post["id"]
                        print("🔥 Postare nouă trimisă")
                else:
                    print("ℹ️ Nicio postare nouă")

                time.sleep(CHECK_INTERVAL)

            except Exception as e:
                print("❌ Eroare:", e)
                time.sleep(30)

if __name__ == "__main__":
    main()
