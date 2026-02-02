
from flask import Flask, request, jsonify, render_template
from transformers import pipeline

app = Flask(__name__)


sentiment_model = pipeline(
    "sentiment-analysis",
    model="nlptown/bert-base-multilingual-uncased-sentiment"
)


ADMIN_PASSWORD = "admin123"

events = {}



def analyze_feedback(feedbacks):
    positives = []
    negatives = []

    for fb in feedbacks:
        result = sentiment_model(fb)[0]
        stars = int(result["label"][0])  # 1–5
        if stars >= 4:
            positives.append(fb)
        elif stars <= 2:
            negatives.append(fb)

    like_count = len(positives)
    dislike_count = len(negatives)

    if len(feedbacks) > 0:
        percent_positive = round((like_count / len(feedbacks)) * 100)
    else:
        percent_positive = 0

    if like_count > dislike_count:
        summary = "Most participants enjoyed the event."
    elif dislike_count > like_count:
        summary = "Several participants were dissatisfied with the event."
    else:
        summary = "Participants had mixed opinions about the event."

    return {
        "summary": summary,
        "likes": like_count,
        "dislikes": dislike_count,
        "positive_example": positives[0] if positives else "No positive feedback available",
        "negative_example": negatives[0] if negatives else "No negative feedback available",
        "percent_positive": percent_positive
    }


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/events")
def get_events():
    return jsonify(list(events.keys()))

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    data = request.json
    event = data.get("event")
    feedback = data.get("feedback")
    if event not in events:
        return jsonify({"error": "Event not found"}), 404
    events[event].append(feedback)
    return jsonify({"message": "Feedback submitted"})

@app.route("/add_event", methods=["POST"])
def add_event():
    data = request.json
    event = data.get("event")
    if event in events:
        return jsonify({"error": "Event already exists"}), 400
    events[event] = []
    return jsonify({"message": "Event added"})

@app.route("/delete_event", methods=["POST"])
def delete_event():
    data = request.json
    event = data.get("event", "").strip()
    if event in events:
        del events[event]
        return jsonify({"message": "Event deleted"})
    return jsonify({"error": f"Event '{event}' not found"}), 404

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    password = data.get("password")
    event = data.get("event")

    if password != ADMIN_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    feedbacks = events.get(event, [])
    result = analyze_feedback(feedbacks)
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)


