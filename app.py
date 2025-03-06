import asyncio
import random
import nest_asyncio
from flask import Flask, render_template, request, jsonify
from playwright.async_api import async_playwright
import indian_names

# Apply asyncio patch for environments like Render
nest_asyncio.apply()

# Flask application
app = Flask(__name__)

# Global flag for running status
running = True

# Hardcoded password for validation
HARDCODED_PASSWORD = "Fly@1234"

# Verify password function
def verify_password(password):
    return password == HARDCODED_PASSWORD

# Generate a unique user name
def generate_unique_user():
    first_name = indian_names.get_first_name()
    last_name = indian_names.get_last_name()
    return f"{first_name} {last_name}"

# Async function to simulate participant joining
async def start_participant(wait_time, meetingcode, passcode):
    global running
    user = generate_unique_user()
    print(f"{user} attempting to join with Chromium.")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(f'http://app.zoom.us/wc/join/{meetingcode}', timeout=200000)

            await page.fill('input[type="text"]', user)
            password_field_exists = await page.query_selector('input[type="password"]')
            if password_field_exists:
                await page.fill('input[type="password"]', passcode)
                join_button = await page.wait_for_selector('button.preview-join-button', timeout=200000)
                await join_button.click()
            else:
                join_button = await page.wait_for_selector('button.preview-join-button', timeout=200000)
                await join_button.click()

            await page.wait_for_selector('button.join-audio-by-voip__join-btn', timeout=300000)
            mic_button_locator = await page.query_selector('button.join-audio-by-voip__join-btn')
            await mic_button_locator.evaluate_handle('node => node.click()')
            print(f"{user} successfully joined audio.")

            # Stay in the meeting for the specified time
            print(f"{user} will remain in the meeting for {wait_time} seconds ...")
            while running and wait_time > 0:
                await asyncio.sleep(1)
                wait_time -= 1
            print(f"{user} has left the meeting.")

            await context.close()
            await browser.close()

    except Exception as e:
        print(f"An error occurred: {e}")

@app.route('/')
def index():
    return render_template('index.html')  # This will render the HTML page with input fields

@app.route('/start', methods=['POST'])
def start_meeting():
    global running

    data = request.json
    meetingcode = data.get('meetingcode')
    passcode = data.get('passcode')

    if not verify_password(passcode):
        return jsonify({"error": "Incorrect password"}), 400

    try:
        tasks = []
        wait_time = data.get('wait_time', 7200)  # Default 2 hours

        # Start 5 participants concurrently
        loop = asyncio.get_event_loop()
        for _ in range(5):
            task = loop.create_task(start_participant(wait_time, meetingcode, passcode))
            tasks.append(task)

        asyncio.run(asyncio.gather(*tasks))
        return jsonify({"message": "Participants started successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/end', methods=['POST'])
def end_meeting():
    global running
    running = False
    return jsonify({"message": "Meeting ended, participants will be stopped."}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
