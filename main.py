from pathlib import Path

from llama_cpp import Llama

MODEL_PATH = Path(__file__).parent / "models" / "Phi-3-mini-4k-instruct-q4.gguf"


def main():
    llm = Llama(model_path=str(MODEL_PATH), n_ctx=4096, verbose=False)
    prompt = input("Prompt: ")
    response = llm.create_chat_completion(messages=[{"role": "user", "content": prompt}])
    print(response["choices"][0]["message"]["content"].strip())


if __name__ == "__main__":
    main()
