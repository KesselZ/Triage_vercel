from openai import OpenAI


API_KEY = "sk-bpmbUPhf3msR5fM_06Is2VTgUvvq1w4st6q-pR2-1sUIBCWrdm7EdgoO6mo"


def main():
    client = OpenAI(
        base_url="https://hk.uniapi.io/v1",
        api_key=API_KEY,
    )

    completion = client.chat.completions.create(
        model="deepseek-reasoner",
        max_tokens=128,
        messages=[
            {"role": "user", "content": "hi"}
        ],
    )

    print(completion)


if __name__ == "__main__":
    main()
