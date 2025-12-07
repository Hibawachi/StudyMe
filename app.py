import gradio as gr
import openai
from pypdf import PdfReader
import docx
from pptx import Presentation

import os
openai.api_key = os.environ.get("OPENAI_API_KEY")


# -------------------------------------------------------------------
# Helper: extract text from PDFs, Word docs, PPTs
# -------------------------------------------------------------------

def extract_text(file):
    if file.name.endswith(".pdf"):
        reader = PdfReader(file.name)
        return "\n".join([page.extract_text() for page in reader.pages])
    
    if file.name.endswith(".docx"):
        d = docx.Document(file.name)
        return "\n".join([p.text for p in d.paragraphs])
    
    if file.name.endswith(".pptx"):
        pres = Presentation(file.name)
        text = []
        for slide in pres.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    text.append(shape.text)
        return "\n".join(text)

    # fallback: plain text
    return file.read().decode("utf-8", errors="ignore")

# -------------------------------------------------------------------
# AI Generator
# -------------------------------------------------------------------

def generate_all(files, subject_name, exam_instructions):
    if not subject_name:
        return ("Please enter a subject name.", "", "", "", "")

    # combine text from all uploaded files
    full_corpus = ""
    for f in files:
        full_corpus += extract_text(f) + "\n\n"

    prompt = f"""
You are an AI tutor creating a full study system for the subject: {subject_name}.

Here is the course material:
{full_corpus}

Please generate ALL of the following in one message, separated clearly:

1. PRAACHI-GUIDE TEXTBOOK (written in Praachi’s casual academic voice):
- Clean, simple explanations
- Occasional conversational asides
- Knowledge checks every few paragraphs
- Build a structured chapter layout

2. FLASHCARDS:
Provide 15–25 flashcards in this format:
Q: ...
A: ...

3. QUESTION BANK:
Provide 10 MCQs + 10 short-answer questions.
For each MCQ, include:
- Correct answer
- Why each wrong option is wrong
- Link to textbook section keyword

4. EXAM TEMPLATE:
Generate an exam based on these instructions (if any):
"{exam_instructions}"

Include:
- 10 MCQs
- 5 short answers
- 1 longer applied question
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )

    output = response["choices"][0]["message"]["content"]

    # We split the output by known markers
    parts = output.split("FLASHCARDS:")
    textbook = parts[0].replace("PRAACHI-GUIDE TEXTBOOK:", "").strip()

    parts2 = parts[1].split("QUESTION BANK:")
    flashcards = parts2[0].strip()

    parts3 = parts2[1].split("EXAM TEMPLATE:")
    question_bank = parts3[0].strip()
    exam = parts3[1].strip()

    return textbook, flashcards, question_bank, exam


# -------------------------------------------------------------------
# Exam feedback generator
# -------------------------------------------------------------------

def grade_exam(user_answers, exam_text):
    prompt = f"""
You are grading the following exam.

Exam:
{exam_text}

Student answers:
{user_answers}

Please give:
1. Score out of 100
2. What they understood well
3. What they misunderstood
4. Exact topics to review
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )

    return response["choices"][0]["message"]["content"]

# -------------------------------------------------------------------
# Gradio UI
# -------------------------------------------------------------------

with gr.Blocks() as demo:
    gr.Markdown("# 📚 AI Study Tool (Praachi-Style Edition)")
    gr.Markdown("Upload your course materials and auto-generate textbook, flashcards, a question bank, and a full exam.")

    subject_name = gr.Textbox(label="Subject Name")
    exam_instr = gr.Textbox(label="Custom Exam Instructions (optional)")
    file_upload = gr.File(label="Upload syllabus, slides, PDFs, docs, etc.", file_count="multiple")

    generate_btn = gr.Button("Generate Study Pack")

    with gr.Tab("Textbook"):
        textbook_box = gr.Markdown()

    with gr.Tab("Flashcards"):
        flashcard_box = gr.Markdown()

    with gr.Tab("Question Bank"):
        question_box = gr.Markdown()

    with gr.Tab("Exam"):
        exam_box = gr.Markdown()
        user_answers = gr.Textbox(label="Paste your exam answers here")
        grade_btn = gr.Button("Submit Exam for Feedback")
        grade_output = gr.Markdown()

    generate_btn.click(
        generate_all,
        inputs=[file_upload, subject_name, exam_instr],
        outputs=[textbook_box, flashcard_box, question_box, exam_box]
    )

    grade_btn.click(
        grade_exam,
        inputs=[user_answers, exam_box],
        outputs=grade_output
    )

demo.launch()
