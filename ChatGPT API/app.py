import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import logging
from datetime import datetime
import json
import uuid
import requests

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

app = Flask(__name__)

# Store chats in memory (in production, use a database)
chats = {}

# Initialize OpenAI client with OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

# Store chat history
CHAT_HISTORY_FILE = 'chat_history.json'

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_chat_history(history):
    with open(CHAT_HISTORY_FILE,'w') as f:
        json.dump(history, f)

# Define the default route to return the index.html file
@app.route("/")
def home():
    return render_template("index.html")

# Get recent chats
@app.route("/api/chats", methods=["GET"])
def get_chats():
    # Return chats sorted by creation date (newest first)
    sorted_chats = sorted(
        chats.values(),
        key=lambda x: x["created_at"],
        reverse=True
    )
    return jsonify(sorted_chats)

# Get specific chat
@app.route("/api/chats/<chat_id>", methods=["GET"])
def get_chat(chat_id):
    if chat_id not in chats:
        return jsonify({"error": "Chat not found"}), 404
    return jsonify(chats[chat_id])

# Define the /api route to handle POST requests
@app.route("/api", methods=["POST"])
def chat():
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        message = data.get("message", "")
        if not message:
            return jsonify({"error": "Message is required"}), 400

        image_url = data.get("image_url")
        chat_id = data.get("chat_id")

        # Create new chat if no chat_id provided
        if not chat_id:
            chat_id = str(uuid.uuid4())
            chats[chat_id] = {
                "id": chat_id,
                "title": message[:50] + "..." if len(message) > 50 else message,
                "created_at": datetime.now().isoformat(),
                "messages": []
            }

        # Add user message to chat history
        chats[chat_id]["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })

        # Prepare messages array
        messages = []
        if image_url:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
        else:
            messages.append({
                "role": "user",
                "content": message
            })

        try:
            # Make API request using OpenAI client
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "http://localhost:5000",
                    "X-Title": "Spark8-AI_part-main",
                },
                model="deepseek/deepseek-r1:free",
                messages=messages
            )

            bot_response = completion.choices[0].message.content
            
            # Add bot response to chat history
            chats[chat_id]["messages"].append({
                "role": "assistant",
                "content": bot_response,
                "timestamp": datetime.now().isoformat()
            })

            return jsonify({
                "content": bot_response,
                "chat_id": chat_id
            })

        except Exception as e:
            logger.error(f"API request failed: {str(e)}")
            return jsonify({
                "error": "Failed to get response from AI service",
                "details": str(e)
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred",
            "details": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

