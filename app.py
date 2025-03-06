import os
from playwright.sync_api import sync_playwright

# Ensure Playwright is properly set up on Render (this installs browsers)
def install_playwright_browsers():
    if not os.path.exists("/tmp/playwright_browsers"):
        with sync_playwright() as p:
            p.chromium.download(channel="chrome")  # You can also specify "firefox" or "webkit"
            os.makedirs("/tmp/playwright_browsers", exist_ok=True)

# Call to install browsers if they aren't already present
install_playwright_browsers()

import asyncio
import random
from flask import Flask, render_template, request, jsonify
from playwright.async_api import async_playwright
import nest_asyncio
import indian_names

# Apply nest_asyncio for running asyncio in a web framework like Flask
nest_asyncio.apply()

app = Flask(__name__)

# Global variables
running = True
join_audio_event = asyncio.Event()

# Hardcoded password for validation
HARDCODED_PASSWORD = "Fly@1234"

# Verify password function
def verify_password(password):
    return password == HARDCODED_PASSWORD

# Function to generate a random unique user
def generate_unique_user():
    first_name = indian_names.get_first_name()
    last_name = indian_names.get_last_name()
    return f"{first_name} {last_name}"

# Async function to start participants and join meeting
async def start(wait_time, meetingcode, passcode):
    global join_audio_event
    global running

    try:
        # Generate unique user name
        user = generate_unique_user()
        print(f"{user} attempting to join with Chromium.")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--use-fake-ui-for-media-stream',
                    '--use-fake-device-for-media-stream',
                    f'--disk-cache-size={random.randint(200, 500)}000000',
                    f'--max-active-views={random.randint(5, 15)}'
                ]
            )

            context = await browser.new_context()

            page = await context.new_page()
            await page.goto(f'http://app.zoom.us/wc/join/{meetingcode}', timeout=200000)

            for _ in range(5):
                await page.evaluate('() => { navigator.mediaDevices.getUserMedia({ audio: true, video: true }); }')

            try:
                await page.click('//button[@id="onetrust-accept-btn-handler"]', timeout=5000)
            except Exception:
                pass

            try:
                await page.click('//button[@id="wc_agree1"]', timeout=5000)
            except Exception:
                pass

            try:
                await page.wait_for_selector('input[type="text"]', timeout=200000)
                await page.fill('input[type="text"]', user)

                password_field_exists = await page.query_selector('input[type="password"]')
                if password_field_exists:
                    await page.fill('input[type="password"]', passcode)
                    join_button = await page.wait_for_selector('button.preview-join-button', timeout=200000)
                    await join_button.click()
                else:
                    join_button = await page.wait_for_selector('button.preview-join-button', timeout=200000)
                    await join_button.click()
            except Exception:
                pass

            retry_count = 5
            while retry_count > 0:
                try:
                    await page.wait_for_selector('button.join-audio-by-voip__join-btn', timeout=300000)
                    query = 'button[class*="join-audio-by-voip__join-btn"]'
                    mic_button_locator = await page.query_selector(query)
                    await asyncio.sleep(2)
                    await mic_button_locator.evaluate_handle('node => node.click()')
                    print(f"{user} successfully joined audio.")

                    join_audio_event.set()
                    break
                except Exception as e:
                    print(f"Attempt {5 - retry_count + 1}: {user} failed to join audio. Retrying...", e)
                    retry_count -= 1
                    await asyncio.sleep(2)

            if retry_count == 0:
                print(f"{user} failed to join audio after multiple attempts.")

            print(f"{user} will remain in the meeting for {wait_time} seconds ...")
            while running and wait_time > 0:
                await asyncio.sleep(1)
                wait_time -= 1
            print(f"{user} has left the meeting.")

        await context.close()
        await browser.close()

    except Exception as e:
        print(f"An error occurred: {e}")

# Flask routes
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start")
async def start_meeting():
    meetingid = request.args.get("meetingid")
    password = request.args.get("password")
    waittime = int(request.args.get("waittime"))

    # Start 5 participants
    tasks = []
    for _ in range(5):
        task = asyncio.create_task(start(waittime, meetingid, password))
        tasks.append(task)

    await asyncio.gather(*tasks)
    return "Participants started!"

@app.route("/end")
def end_meeting():
    global running
    running = False
    return jsonify(message="Meeting ended!")

if __name__ == "__main__":
    app.run(debug=True)
