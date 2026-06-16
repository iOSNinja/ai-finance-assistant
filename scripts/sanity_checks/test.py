import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # reads .env in the current working directory

client = OpenAI()  # auto-picks up OPENAI_API_KEY from env, no need to pass it
r = client.embeddings.create(
    model="text-embedding-3-small",
    input="Ravi",
)
print(r)
