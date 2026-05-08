from flask import Flask, render_template, request, jsonify, session
import random
import time

game = Flask(__name__)
game.secret_key = "number_guessing_secret_2026"

# Difficulty settings: (range_max, max_attempts, hint_count)
DIFFICULTIES = {
    "easy":   {"max": 50,  "attempts": 12, "hints": 3, "label": "Easy (1–50)"},
    "medium": {"max": 100, "attempts": 8,  "hints": 2, "label": "Medium (1–100)"},
    "hard":   {"max": 200, "attempts": 6,  "hints": 1, "label": "Hard (1–200)"},
}


def new_game(difficulty="medium"):
    """Initialize a fresh game session."""
    config = DIFFICULTIES[difficulty]
    session["target"] = random.randint(1, config["max"])
    session["difficulty"] = difficulty
    session["range_max"] = config["max"]
    session["max_attempts"] = config["attempts"]
    session["hints_left"] = config["hints"]
    session["attempts"] = 0
    session["history"] = []
    session["start_time"] = time.time()
    session["won"] = False
    session["best_scores"] = session.get("best_scores", {})


@game.route("/")
def home():
    return render_template("game.html")


@game.route("/start", methods=["POST"])
def start():
    data = request.get_json()
    difficulty = data.get("difficulty", "medium")
    if difficulty not in DIFFICULTIES:
        difficulty = "medium"
    new_game(difficulty)
    config = DIFFICULTIES[difficulty]
    return jsonify({
        "range_max": config["max"],
        "max_attempts": config["attempts"],
        "hints": config["hints"],
        "label": config["label"],
    })


@game.route("/guess", methods=["POST"])
def guess():
    if "target" not in session:
        new_game()

    if session.get("won"):
        return jsonify({"status": "over", "message": "🎉 You already won! Start a new game."})

    data = request.get_json()
    try:
        user_guess = int(data["guess"])
    except (ValueError, KeyError):
        return jsonify({"status": "error", "message": "❌ Please enter a valid number."})

    range_max = session["range_max"]
    if user_guess < 1 or user_guess > range_max:
        return jsonify({"status": "error", "message": f"❌ Pick a number between 1 and {range_max}."})

    target = session["target"]
    session["attempts"] += 1
    attempts = session["attempts"]
    max_attempts = session["max_attempts"]
    diff = abs(target - user_guess)

    # Record in history
    direction = "correct" if user_guess == target else ("low" if user_guess < target else "high")
    session["history"] = session.get("history", []) + [{"guess": user_guess, "direction": direction}]
    session.modified = True

    remaining = max_attempts - attempts

    if user_guess == target:
        elapsed = round(time.time() - session["start_time"], 1)
        score = max(10, round((1000 / attempts) * (range_max / 100)))
        session["won"] = True

        # Track best score
        difficulty = session["difficulty"]
        best = session.get("best_scores", {})
        if difficulty not in best or score > best[difficulty]:
            best[difficulty] = score
            session["best_scores"] = best
            session.modified = True

        return jsonify({
            "status": "win",
            "message": f"🎉 Correct! The number was {target}!",
            "attempts": attempts,
            "time": elapsed,
            "score": score,
            "best_score": session["best_scores"].get(difficulty, score),
        })

    if remaining <= 0:
        session["won"] = True
        return jsonify({
            "status": "lose",
            "message": f"💀 Game Over! The number was {target}.",
            "attempts": attempts,
        })

    # Proximity feedback
    if diff <= 2:
        heat = "🔥🔥🔥 Burning hot!"
    elif diff <= 5:
        heat = "🔥🔥 Very warm!"
    elif diff <= 10:
        heat = "🔥 Getting warm."
    elif diff <= 25:
        heat = "❄️ Cold."
    else:
        heat = "🧊 Freezing cold!"

    arrow = "⬆️ Go higher" if user_guess < target else "⬇️ Go lower"

    return jsonify({
        "status": "wrong",
        "message": f"{heat} {arrow}",
        "attempts": attempts,
        "remaining": remaining,
    })


@game.route("/hint", methods=["POST"])
def hint():
    if "target" not in session:
        return jsonify({"hint": "Start a game first!"})

    if session.get("won"):
        return jsonify({"hint": "Game is over. Start a new one!"})

    hints_left = session.get("hints_left", 0)
    if hints_left <= 0:
        return jsonify({"hint": "❌ No hints remaining!", "hints_left": 0})

    target = session["target"]
    hint_type = random.choice(["parity", "range", "divisible"])

    if hint_type == "parity":
        h = f"The number is {'even' if target % 2 == 0 else 'odd'}."
    elif hint_type == "range":
        low = max(1, target - random.randint(5, 15))
        high = min(session["range_max"], target + random.randint(5, 15))
        h = f"The number is between {low} and {high}."
    else:
        for d in [3, 5, 7, 4, 6]:
            if target % d == 0:
                h = f"The number is divisible by {d}."
                break
        else:
            h = f"The number is {'prime' if all(target % i != 0 for i in range(2, int(target**0.5)+1)) and target > 1 else 'not prime'}."

    session["hints_left"] = hints_left - 1
    session.modified = True

    return jsonify({"hint": f"💡 {h}", "hints_left": session["hints_left"]})


@game.route("/stats")
def stats():
    return jsonify({
        "attempts": session.get("attempts", 0),
        "history": session.get("history", []),
        "best_scores": session.get("best_scores", {}),
    })


if __name__ == "__main__":
    game.run(debug=True)
