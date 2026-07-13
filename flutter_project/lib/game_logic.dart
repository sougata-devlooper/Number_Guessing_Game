import 'dart:math';
import 'package:shared_preferences/shared_preferences.dart';

class GameConfig {
  final int maxRange;
  final int attempts;
  final int hints;
  final String label;
  const GameConfig(this.maxRange, this.attempts, this.hints, this.label);
}

const Map<String, GameConfig> difficulties = {
  'easy': GameConfig(50, 12, 3, 'Easy (1–50)'),
  'medium': GameConfig(100, 8, 2, 'Medium (1–100)'),
  'hard': GameConfig(200, 6, 1, 'Hard (1–200)'),
};

class HistoryPip {
  final int guess;
  final String direction; // 'correct', 'low', 'high'
  HistoryPip(this.guess, this.direction);
}

class GameState {
  String difficulty = 'medium';
  late int target;
  late int rangeMax;
  late int maxAttempts;
  late int hintsLeft;
  int attempts = 0;
  List<HistoryPip> history = [];
  bool won = false;
  bool over = false;
  late DateTime startTime;
  double elapsedTime = 0.0;
  Map<String, int> bestScores = {};
  
  String message = "";
  String messageStatus = "normal"; // normal, win, lose, error
  int currentScore = 0;

  final Random _rand = Random();

  GameState() {
    startNewGame('medium');
  }

  Future<void> loadBestScores() async {
    final prefs = await SharedPreferences.getInstance();
    bestScores['easy'] = prefs.getInt('bestScore_easy') ?? 0;
    bestScores['medium'] = prefs.getInt('bestScore_medium') ?? 0;
    bestScores['hard'] = prefs.getInt('bestScore_hard') ?? 0;
  }

  void startNewGame(String diff) {
    difficulty = diff;
    final config = difficulties[diff]!;
    rangeMax = config.maxRange;
    maxAttempts = config.attempts;
    hintsLeft = config.hints;
    target = _rand.nextInt(rangeMax) + 1;
    attempts = 0;
    history = [];
    won = false;
    over = false;
    startTime = DateTime.now();
    elapsedTime = 0.0;
    message = "Guess between 1-$rangeMax!";
    messageStatus = "normal";
  }

  void makeGuess(int guess) {
    if (over) return;
    
    if (guess < 1 || guess > rangeMax) {
      message = "❌ Pick a number between 1 and $rangeMax.";
      messageStatus = "error";
      return;
    }

    attempts++;
    int diff = (target - guess).abs();
    int remaining = maxAttempts - attempts;

    String direction = guess == target ? 'correct' : (guess < target ? 'low' : 'high');
    history.add(HistoryPip(guess, direction));

    if (guess == target) {
      won = true;
      over = true;
      elapsedTime = DateTime.now().difference(startTime).inMilliseconds / 1000.0;
      int score = (1000.0 / attempts * (rangeMax / 100.0)).round();
      score = max(10, score);
      currentScore = score;
      
      int best = bestScores[difficulty] ?? 0;
      if (score > best) {
        bestScores[difficulty] = score;
        SharedPreferences.getInstance().then((prefs) {
          prefs.setInt('bestScore_$difficulty', score);
        });
      }
      
      message = "🎉 Correct! The number was $target!";
      messageStatus = "win";
      return;
    }

    if (remaining <= 0) {
      over = true;
      elapsedTime = DateTime.now().difference(startTime).inMilliseconds / 1000.0;
      message = "💀 Game Over! The number was $target.";
      messageStatus = "lose";
      return;
    }

    String heat;
    if (diff <= 2) {
      heat = "🔥🔥🔥 Burning hot!";
    } else if (diff <= 5) {
      heat = "🔥🔥 Very warm!";
    } else if (diff <= 10) {
      heat = "🔥 Getting warm.";
    } else if (diff <= 25) {
      heat = "❄️ Cold.";
    } else {
      heat = "🧊 Freezing cold!";
    }

    String arrow = guess < target ? "⬆️ Go higher" : "⬇️ Go lower";
    message = "$heat $arrow";
    messageStatus = "wrong";
  }

  String requestHint() {
    if (over) return "Game is over. Start a new one!";
    if (hintsLeft <= 0) return "❌ No hints remaining!";

    List<String> hintTypes = ['parity', 'range', 'divisible'];
    String hintType = hintTypes[_rand.nextInt(hintTypes.length)];
    String h = "";

    if (hintType == 'parity') {
      h = "The number is ${target % 2 == 0 ? 'even' : 'odd'}.";
    } else if (hintType == 'range') {
      int low = max(1, target - (_rand.nextInt(11) + 5));
      int high = min(rangeMax, target + (_rand.nextInt(11) + 5));
      h = "The number is between $low and $high.";
    } else {
      bool divFound = false;
      for (int d in [3, 5, 7, 4, 6]) {
        if (target % d == 0) {
          h = "The number is divisible by $d.";
          divFound = true;
          break;
        }
      }
      if (!divFound) {
        bool isPrime(int n) {
          if (n <= 1) return false;
          for (int i = 2; i * i <= n; i++) {
            if (n % i == 0) return false;
          }
          return true;
        }
        h = "The number is ${isPrime(target) ? 'prime' : 'not prime'}.";
      }
    }

    hintsLeft--;
    return "💡 $h";
  }
}
