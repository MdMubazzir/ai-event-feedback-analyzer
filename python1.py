import csv
import io
import os

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

sentiment_model = None
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
events = {}

FEEDBACK_COLUMN_ALIASES = (
    "feedback",
    "feedback_text",
    "review",
    "comment",
    "message",
    "text",
    "Tweet Text",
)


def get_sentiment_model():
    global sentiment_model
    if sentiment_model is None:
        from transformers import pipeline

        sentiment_model = pipeline(
            "sentiment-analysis",
            model="nlptown/bert-base-multilingual-uncased-sentiment",
        )
    return sentiment_model


def normalize_feedback(value):
    if value is None:
        return ""
    return str(value).strip()


def feedback_from_row(row):
    normalized_row = {
        str(key).strip().casefold(): value
        for key, value in row.items()
    }
    for alias in FEEDBACK_COLUMN_ALIASES:
        feedback = normalize_feedback(normalized_row.get(alias.casefold()))
        if feedback:
            return feedback
    return ""


def unique_feedbacks(feedbacks):
    seen = set()
    clean_feedbacks = []
    for feedback in feedbacks:
        clean_feedback = normalize_feedback(feedback)
        if not clean_feedback or clean_feedback in seen:
            continue
        seen.add(clean_feedback)
        clean_feedbacks.append(clean_feedback)
    return clean_feedbacks


def append_feedbacks(event, feedbacks):
    if event not in events:
        return False, 0
    clean_feedbacks = unique_feedbacks(feedbacks)
    events[event].extend(clean_feedbacks)
    return True, len(clean_feedbacks)


def analyze_feedback(feedbacks):
    feedbacks = unique_feedbacks(feedbacks)
    positives = []
    negatives = []

    for feedback in feedbacks:
        result = get_sentiment_model()(feedback)[0]
        stars = int(result["label"][0])
        if stars >= 4:
            positives.append(feedback)
        elif stars <= 2:
            negatives.append(feedback)

    like_count = len(positives)
    dislike_count = len(negatives)

    if feedbacks:
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
        "percent_positive": percent_positive,
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
    feedback = normalize_feedback(data.get("feedback"))
    if event not in events:
        return jsonify({"error": "Event not found"}), 404
    if not feedback:
        return jsonify({"error": "Feedback is required"}), 400
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


@app.route("/import_feedback", methods=["POST"])
def import_feedback():
    event = request.form.get("event")
    feedbacks = []

    if "file" in request.files:
        stream = io.StringIO(request.files["file"].read().decode("utf-8-sig"))
        rows = csv.DictReader(stream)
        feedbacks = [feedback_from_row(row) for row in rows]
    else:
        data = request.get_json(silent=True) or {}
        event = data.get("event", event)
        if "feedbacks" in data:
            feedbacks = data.get("feedbacks", [])
        else:
            feedbacks = [feedback_from_row(row) for row in data.get("rows", [])]

    ok, added_count = append_feedbacks(event, feedbacks)
    if not ok:
        return jsonify({"error": "Event not found"}), 404
    if added_count == 0:
        return jsonify({"error": "No valid feedback found"}), 400
    return jsonify({"message": "Feedback imported", "count": added_count})


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
