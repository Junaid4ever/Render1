import os
import subprocess
import asyncio
import random
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request
from playwright.async_api import async_playwright
import nest_asyncio
import indian_names

nest_asyncio.apply()

# Flag to indicate whether the script is running
running = True

# Event to synchronize threads
join_audio_event = asyncio.Event()

# Hardcoded password
HARDCODED_PASSWORD = "Fly@1234"

app = Flask(__name__)

# Install Playwright browsers (Chromium, Firefox, WebKit)
def install_playwright_browsers():
    # Check if Playwright browser binaries are installed; if not, install them
    if not os.path.exists("/tmp/playwright_browsers"):
        print("Installing Playwright browsers...")
        subprocess.run(["python3", "-m", "playwright", "install"], check=True)
        os.makedirs("/tmp/playwright_browsers", exist_ok=True)
        print("Playwright browsers installed successfully.")

# Verify password function
def verify_password(password):
    return password == HARDCODED_PASSWORD

# Generate a unique user name
def generate_unique_user():
    first_name = indian_names.get_first_name()
    last_name = indian_names.get_last_name()
    return f"{first_name} {last_name}"

# Playwright logic for joining Zoom
async def start(wait_time, meetingcode, passcode):
    global join_audio_event
    global running
    try:
        user = generate_unique_user()
        print(f"{user} attempting to join Zoom.")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(f'http://app.zoom.us/wc/join/{meetingcode}', timeout=200000)

            # Handle login and Zoom join logic here...

            await context.close()
            await browser.close()
    except Exception as e:
        print(f"Error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_meeting():
    meetingcode = request.form['meetingcode']
    password = request.form['password']
    waittime = int(request.form['waittime'])
    
    if verify_password(password):
        asyncio.run(start(waittime, meetingcode, password))
        return render_template('index.html', status="Joining the meeting...")
    else:
        return render_template('index.html', status="Invalid password!")

@app.route('/end', methods=['POST'])
def end_meeting():
    global running
    running = False
    return render_template('index.html', status="Meeting ended.")

if __name__ == "__main__":
    install_playwright_browsers()  # Ensure browsers are installed
    app.run(debug=True, host="0.0.0.0", port=5000)
