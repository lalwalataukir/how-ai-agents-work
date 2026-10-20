"""E3 lab: a terminal chatbot that remembers the conversation and shows what each turn costs.

Run it with:
    uv run chat.py
"""
import anthropic
from dotenv import load_dotenv

load_dotenv()  # copies ANTHROPIC_API_KEY from the .env file into the environment

MODEL = "claude-haiku-5-5"  # the cheapest model; try "claude-sonnet-5-5" for harder questions
PRICE_IN = 0.10  # dollars per million input tokens, for this model
PRICE_OUT = 0.50  # dollars per million output tokens
SYSTEM = (
    "You are a research assistant. Answer in at most 120 words. "
    "If you are not sure about a fact, say so instead of guessing."
)

client = anthropic.Anthropic()  # finds ANTHROPIC_API_KEY by itself


def turn_cost(usage):
    """Dollars for one request, from the token counts the API reports."""
    return (usage.input_tokens * PRICE_IN + usage.output_tokens * PRICE_OUT) / 1_000_000


def ask(messages):
    """Send the whole conversation, print the reply as it arrives, and return the full response."""
    with client.messages.stream(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM,
        messages=messages,
        output_config={"effort": "low"},  # less thinking: faster and cheaper for chat
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
        return stream.get_final_message()


def main():
    messages = []  # the conversation so far: the API remembers nothing between requests
    total = 0.0
    print(f"Chatting with {MODEL}. Type quit to stop.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("quit", "exit"):
            break
        if not question:
            continue

        messages.append({"role": "user", "content": question})
        print("Claude: ", end="")
        try:
            response = ask(messages)
        except anthropic.AuthenticationError:
            print("\nThe API key was rejected. Check ANTHROPIC_API_KEY in your .env file.")
            break
        except anthropic.APIConnectionError:
            print("\nCould not reach the API. Check your internet connection and try again.")
            messages.pop()  # forget the question that got no answer
            continue
        except anthropic.APIStatusError as error:  # 402, 429, 500 and others, after the SDK's own retries
            print(f"\nThe API answered {error.status_code}: {error.message}")
            messages.pop()
            continue

        # Keep the whole reply, not just its text, so the next request has the full conversation
        messages.append({"role": "assistant", "content": response.content})
        cost = turn_cost(response.usage)
        total += cost
        print(f"\n  [{response.usage.input_tokens} tokens in, {response.usage.output_tokens} out, "
              f"${cost:.5f} this turn, ${total:.5f} so far]\n")
        if response.stop_reason == "max_tokens":
            print("  (The reply was cut off. Raise max_tokens for longer answers.)\n")
        elif response.stop_reason == "refusal":
            print("  (Claude declined to answer that one.)\n")

    print(f"Session cost: ${total:.5f}")


if __name__ == "__main__":
    main()
