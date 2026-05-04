import os
import json
from flask import Flask, request, jsonify, send_from_directory
import requests

app = Flask(__name__)

GROQ_KEY = os.getenv("GROQ_API_KEY", "")
memory = {}

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

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
        prompt = "Ты Grok. Умный и харизматичный."

    if user_name:
        prompt += " Пользователя зовут " + user_name + "."

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
            headers={"Authorization": "Bearer " + GROQ_KEY},
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
        return jsonify({"reply": "Ошибка: " + str(e)})

@app.route("/reminder", methods=["POST"])
def reminder():
    text = request.get_json().get("text", "")
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": "Bearer " + GROQ_KEY},
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {
                        "role": "system",
                        "content": "Извлеки время в минутах и текст. Ответь ТОЛЬКО JSON: {\"minutes\": число, \"reminder_text\": \"текст\", \"reply\": \"подтверждение\"}"
                    },
                    {"role": "user", "content": text}
                ]
            },
            timeout=20
        )
        content = r.json()["choices"][0]["message"]["content"]
        return jsonify(json.loads(content))
    except Exception as e:
        return jsonify({"reply": "Не смог распознать.", "minutes": None, "reminder_text": ""})

@app.route("/clear", methods=["POST"])
def clear():
    uid = request.get_json().get("user_id", "default")
    memory.pop(uid, None)
    return jsonify({"ok": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
