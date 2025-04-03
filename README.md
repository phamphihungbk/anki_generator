# 📚 Anki Deck Generator for LeetCode Practice

This project is a script-based tool designed to fetch LeetCode questions and generate Anki decks for practicing data structures and algorithms with spaced repetition. By integrating LeetCode problems into Anki flashcards, you can improve your problem-solving skills, retain solutions longer, and prepare effectively for coding interviews.


## 🚀 Key Features

✅ Automatically fetches questions, solutions, and submissions from LeetCode

✅ Generates customizable Anki decks with:

•	Problem descriptions

•	Solution approaches

•	Edge cases, clarifying questions, and common mistakes

•	Personal notes and code solutions

✅ Supports spaced repetition to boost long-term memory of problem patterns

✅ Simple CLI for generating and updating decks


## 🛠️ Installation Instructions

```bash
git clone https://github.com/your-username/anki-generator.git
cd anki-generator

# Install dependencies (creates virtual environment)
poetry install

# List the available commands:
poetry run python cli.py fetch-favourite-questions
poetry run python cli.py fetch_question_detail
poetry run python cli.py fetch-top-questions
poetry run python cli.py sync-leetcode-track
poetry run python cli.py generate-deck
```


## 🛠️ Demo

![front](./demo/front.png)
![back](./demo/back.png)