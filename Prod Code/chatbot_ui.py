import gradio as gr
import sqlite3
import pandas as pd
import time

from llm_pipeline import call_llm


DB_FILE = "datacollect.db"
db = sqlite3.connect(DB_FILE)

# Table for collecting data with like/dislike
try:
    db.execute("SELECT * FROM reviews").fetchall()
    # db.close()
except sqlite3.OperationalError:
    db.execute(
        '''
        CREATE TABLE reviews (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                              vote INTEGER,
                              input_output TEXT)
        ''')
    db.commit()
   # db.close()

try:
    db.execute("SELECT * FROM datacoll").fetchall()
    db.close()
except sqlite3.OperationalError:
    db.execute(
        '''
        CREATE TABLE datacoll (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                              created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
                              query TEXT,
                              output TEXT)
        ''')
    db.commit()
    db.close()


def get_latest_reviews(db: sqlite3.Connection):
    reviews = db.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
    total_reviews = db.execute("Select COUNT(id) from reviews").fetchone()[0]
    reviews = pd.DataFrame(reviews, columns=["id", "date_created", "vote", "input_output"])
    return reviews, total_reviews

def get_latest_datacoll(db: sqlite3.Connection):
    reviews = db.execute("SELECT * FROM datacoll ORDER BY id DESC").fetchall()
    total_reviews = db.execute("Select COUNT(id) from datacoll").fetchone()[0]
    reviews = pd.DataFrame(reviews, columns=["id", "date_created", "query", "output"])
    return reviews, total_reviews
    


def add_review(vote: int, inpout: str):
    db = sqlite3.connect(DB_FILE)
    cursor = db.cursor()
    cursor.execute("INSERT INTO reviews(vote, input_output) VALUES(?,?)", [vote, inpout])
    db.commit()
    reviews, total_reviews = get_latest_reviews(db)
    db.close()
    # gr.Info("Feedback received")
    return reviews, total_reviews

# def load_data():
#     db = sqlite3.connect(DB_FILE)
#     reviews, total_reviews = get_latest_reviews(db)
#     db.close()
#     return reviews, total_reviews

# def load_data2():
#     db = sqlite3.connect(DB_FILE)
#     datas, total_data = get_latest_datacoll(db)
#     db.close()
#     return datas, total_data


    
def llm_response(message, history):
    
    res = call_llm(message)
    
    db = sqlite3.connect(DB_FILE)
    cursor = db.cursor()
    cursor.execute("INSERT INTO datacoll(query, output) VALUES(?,?)", [message, res])
    db.commit()
    reviews, total_reviews = get_latest_datacoll(db)
    db.close()
    for i in range(len(res)):
        time.sleep(0.02)
        yield res[: i+1]
    # return res

def vote(response: gr.LikeData):
    if response.liked:
        add_review(1, response.value)
    else:
        add_review(0, response.value)
        

examples = ["What are the recommended NPK dosage for maize varieties?", 
            "What are the recommended chemical treatments to control army worms in wheat crops?", 
            "Heavy rains are predicted next week. Is my rice crop ready for this, or should I harvest early?", 
            "What crops can I grow during the dry season to use water more efficiently?", 
            "How can I improve the health of my soil after a wheat harvest, using natural methods?", 
            "Are there crop rotation techniques that can reduce fertilizer needs for barley?"]

# js_func = """
# function refresh() {
#     const url = new URL(window.location);

#     if (url.searchParams.get('__theme') !== 'light') {
#         url.searchParams.set('__theme', 'light');
#         window.location.href = url.href;
#     }
# }
# """



description = "Hi, I am an AI agronomist, here to help you with agriculture advisories for crops like paddy/rice, maize, wheat, barley and sorghum in Indian Subcontinent"

title = "Cropin's akṣara"
theme = gr.themes.Soft(primary_hue="sky",)

chatbot = gr.Chatbot(likeable=True, height="450px", show_copy_button=True, avatar_images=("user.webp","cropin.png"))


with gr.Blocks(theme=theme, title=title) as akshara:

    gr.HTML("""<h1 style='font-family: sans-serif; text-align: center; font-size: 34px'>
        <i style='color: #04A5D9' >akṣara</i> (Akshara)</h1>""")

    gr.HTML("""<h3 style='font-family: sans-serif; text-align: left'>
        Welcome to Cropin's Aksara </h3>""")

    # with gr.Column():

    chatbot.like(vote, None, None)

    gr.ChatInterface(fn=llm_response, 
                     examples=examples, 
                     # cache_examples=True, 
                     chatbot=chatbot,
                     description=description, 
                     retry_btn="Retry", 
                     undo_btn="Undo", 
                     clear_btn="Clear"
                    )

    gr.HTML("""<h3 style='font-family: sans-serif; text-align: left'>
        Disclaimer: Beta Test version #1.0 - aksara is your agricultural AI advisor. Expect inaccuracies. We’re in active development stage to constantly learn & improve.
 """)

def display_ui():
    akshara.launch(server_name="ec2-52-57-252-231.eu-central-1.compute.amazonaws.com", 
                server_port=8891, debug=True, share=True)


if __name__ == "__main__":
    display_ui()
    pass
