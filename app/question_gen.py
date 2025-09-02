import random

def generate_dummy_questions(topics, num_questions: int = 5):
    """Generate simple practice questions from topics"""
    questions = []
    for i in range(num_questions):
        topic = random.choice(topics) if topics else "General Knowledge"
        q_type = random.choice(["Explain", "Define", "Discuss", "Give an example of"])
        questions.append(f"{q_type} {topic}.")
    return questions
