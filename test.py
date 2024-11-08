from openai import OpenAI
import os

GPT_TOKEN = os.getenv("GPT_TOKEN")
client = OpenAI(api_key=GPT_TOKEN)

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Write a haiku about recursion in programming."}
    ]
)

print(completion.choices[0].message.content)
