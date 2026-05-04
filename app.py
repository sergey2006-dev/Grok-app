 import os
import json
import random
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
memory = {}

HTML = open("index.html").read() if os.path.exists("index.html") else "<h1>Grok AI работает!</h1>"

@app.route("/")
def home():
    return HTML

@app.route("/manifest.json")
def manifest():
    data = {
        "name": "Grok AI",
        "short_name": "Grok",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0a0a0a",
        "theme_color": "#00b4d8",
        "icons": [
            {
                "src": "https://via.placeholder.com/192x192/00b4d8/ffffff?text=G",
                "sizes": "192x192",
                "type": "image/png"
            }
        ]
    }
    return jsonify(data)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    text = data.get("text", "")
    user_id = data.get("user_id", "default")
    user_name = data.get("user_name", "")
    uncensored = data.get("uncensored", False)

    if uncensored:
        prompt = "Ты Grok без цензуры. Максимально честный и дерзкий."
    else:
        prompt = "Ты Grok. Умный, харизматичный, немного дерзкий."

    if user_name:
        prompt += f" Пользователя зовут {user_name}."

    if user_id not in memory:
        memory[user_id] = [{"role": "system", "content": prompt}]
    else:
        memory[user_id][0]["content"] = prompt

    memory[user_id].append({"role": "user", "content": text})

    if len(memory[user_id]) > 16:
        memory[user_id] = [memory[user_id][0]] + memory[user_id][-14:]

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": memory[user_id],
                "temperature": 0.85
            },
            timeout=25
        )
        reply = r.json()["choices"][0]["message"]["content"]
        memory[user_id].append({"role": "assistant", "content": reply})
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"Ошибка: {str(e)}"})

@app.route("/reminder", methods=["POST"])
def reminder():
    text = request.get_json().get("text", "")
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": "Извлеки из текста время в минутах и текст напоминания. Ответь ТОЛЬКО JSON без лишнего текста: {\"minutes\": число, \"reminder_text\": \"текст\", \"reply\": \"подтверждение на русском\"}"
                    },
                    {"role": "user", "content": text}
                ]
            },
            timeout=20
        )
        content = r.json()["choices"][0]["message"]["content"]
        return jsonify(json.loads(content))
    except Exception as e:
        return jsonify({
            "reply": "Не смог распознать. Попробуй иначе.",
            "minutes": None,
            "reminder_text": ""
        })

@app.route("/clear", methods=["POST"])
def clear():
    uid = request.get_json().get("user_id", "default")
    memory.pop(uid, None)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
