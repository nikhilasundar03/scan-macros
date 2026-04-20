import os
from clarifai.client import Model

# Set PAT in the shell before running:
#   export CLARIFAI_PAT='your_key'
# Windows (cmd): set CLARIFAI_PAT=your_key

# Initialize with model URL
model = Model(url="https://clarifai.com/openai/chat-completion/models/gpt-oss-120b", pat="b6d990e956104e1693006e2f1d329b59")

response = model.predict_by_bytes(
    input_type="text",
    input_bytes=b"What is the future of AI?"
)
print(response)