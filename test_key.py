import tomllib
from openai import OpenAI

with open(".streamlit/secrets.toml", "rb") as f:
    key = tomllib.load(f)["GROQ_API_KEY"]

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=key,
)

r = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Say hello in 5 words."}],
)
print(r.choices[0].message.content)
