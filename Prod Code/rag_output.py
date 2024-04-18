
from transformers import AutoTokenizer
import torch
from transformers import BitsAndBytesConfig, AutoModelForCausalLM

from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain.embeddings.huggingface import HuggingFaceEmbeddings

import transformers
from langchain.llms import HuggingFacePipeline
from langchain.prompts import PromptTemplate
from langchain.embeddings.huggingface import HuggingFaceEmbeddings
from langchain.chains import LLMChain


# base_model = "mistralai/Mistral-7B-Instruct-v0.2"
base_model = "hingeankit/e2Apr9" #our finetuned model

tokenizer = AutoTokenizer.from_pretrained(
    base_model,
    padding_side = "left",
    add_eos_token = True,

)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.add_bos_token, tokenizer.add_eos_token

bnb_config = BitsAndBytesConfig(
    load_in_4bit= True,
    bnb_4bit_quant_type= "nf4",
    bnb_4bit_compute_dtype= torch.bfloat16,
    bnb_4bit_use_double_quant= False,
)

model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
)


loader = CSVLoader(file_path='context_v2.csv') # pop context of 5 crops used for vectorstore
data = loader.load()

db = FAISS.from_documents(data, 
                          HuggingFaceEmbeddings(model_name='sentence-transformers/all-mpnet-base-v2'))


# Connect query to FAISS index using a retriever
retriever = db.as_retriever(
    search_type="similarity_score_threshold", 
    search_kwargs={"score_threshold": 0.25, "k": 4}
)

def fetch(query):
    res = retriever.get_relevant_documents(query)
    docs = []
    for i in res:
        docs.append(i.page_content[5:])
    return docs
    

text_generation_pipeline = transformers.pipeline(
    model=model,
    tokenizer=tokenizer,
    task="text-generation",
    temperature=0.000001,
    repetition_penalty=1.2,
    top_k=50,
    top_p=0.95,
    return_full_text=True,
    max_new_tokens=512,
    do_sample=True
)

# Do not answer if you are not sure, just say I don't know

prompt_template = """
### [INST] 
Instruction: You are an expert Agronomist have a fruitful conversation with the user. Answer the question based on your knowledge. Just say I don't know if you are not sure of the answer. Here is some context to enhance your response:
NOTE: Don't use the context if it is not factually related to the question. Don't mention you are answering based on the documents or context, rather you can say based on your training knowledge.
{context}

### USER
{question} 

[/INST]
"""

mistral_llm = HuggingFacePipeline(pipeline=text_generation_pipeline)

# Create prompt from prompt template 
prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=prompt_template,
)

# Create llm chain 
llm_chain = LLMChain(llm=mistral_llm, prompt=prompt)

from langchain.schema.runnable import RunnablePassthrough

rag_chain = ( 
    {"context": fetch, "question": RunnablePassthrough()}
    | llm_chain
)


def rag_response(query):
    res = rag_chain.invoke(query)
    return res['text']




    