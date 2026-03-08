import ollama

response = ollama.chat(
    model="mistral",
    messages=[
        {
            "role": "user",
            "content": "Explain QSAR models briefly."
        }
    ]
)

print(response["message"]["content"])