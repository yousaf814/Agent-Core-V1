import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from get_lead_count import get_lead_count
import time

from google.genai import errors

# --------------------------------------------------
# 1. Load environment variables
# --------------------------------------------------

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY is not set in the .env file.")

client = genai.Client(api_key=api_key)

model_name = os.getenv("GEMINI_MODEL")

if not model_name:
    raise ValueError("GEMINI_MODEL is not set in the .env file. Or a wrong model is being named.")

# --------------------------------------------------
# 4. Available tools / allowlist
# --------------------------------------------------

available_tools = {
    "get_lead_count": get_lead_count
}

# --------------------------------------------------
# 5. Function declaration given to Gemini
# --------------------------------------------------

get_lead_count_declaration = types.FunctionDeclaration(
    name="get_lead_count",
    description=(
        "Returns the current total number of leads "
        "in the lead management system."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {},
        "required": [],
    },
)

lead_tools = types.Tool(
    function_declarations=[
        get_lead_count_declaration
    ]
)

# --------------------------------------------------
# Production: reliable Gemini API call
# --------------------------------------------------

def generate_response(contents, config):
    """
    Send a request to Gemini with controlled handling
    for transient API failures.
    """

    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )

        except errors.ServerError as exc:
            if attempt == max_retries:
                raise RuntimeError(
                    "Gemini is temporarily unavailable after "
                    "multiple retry attempts."
                ) from exc

            delay = base_delay * (2 ** attempt)

            print(
                f"Gemini temporarily unavailable. "
                f"Retrying in {delay} seconds..."
            )

            time.sleep(delay)

        except errors.ClientError:
            raise

# --------------------------------------------------
# 6. Continuous agent loop
# --------------------------------------------------

while True:

    user_input = input("You: ").strip()

    if not user_input:
        print("Please enter a question.")
        continue

    if user_input.lower() in {"exit", "quit", "q", "bye", "goodbye", "close", "end", "stop", "terminate", "finish"}:
        print("Agent: Goodbye!")
        break

    # --------------------------------------------------
    # Ask Gemini what to do
    # --------------------------------------------------

    response = generate_response(
        contents=user_input,
        config={
            "tools": [lead_tools],
            "automatic_function_calling": {
                "disable": True
            },
        },
    )

    # --------------------------------------------------
    # Check whether Gemini requested a tool
    # --------------------------------------------------

    if not response.function_calls:
        print("Gemini:", response.text)
        continue

    # --------------------------------------------------
    # Execute the requested tool
    # --------------------------------------------------

    function_call = response.function_calls[0]

    tool_name = function_call.name
    tool_args = dict(function_call.args)

    print("Requested tool:", tool_name)
    print("Arguments:", tool_args)

    tool = available_tools.get(tool_name)

    if tool is None:
        print(f"Agent: I don't have access to the tool '{tool_name}'.")
        continue

        # --------------------------------------------------
        # Production: safe tool execution
        # --------------------------------------------------

    try:
        tool_result = tool(**tool_args)

    except Exception as exc:
        print(f"Tool '{tool_name}' failed: {exc}")

        tool_result = {
        "success": False,
        "error": "The tool could not complete the requested operation.",
    }

    else:
        tool_result = {
        "success": True,
        "result": tool_result,
    }
    # --------------------------------------------------
    # Send tool result back to Gemini
    # --------------------------------------------------

    tool_response = types.Part.from_function_response(
        name=tool_name,
        response={
            "result" : tool_result
        },
    )

    final_response = generate_response(
        contents=[
            user_input,
            response.candidates[0].content,
            types.Content(
                role="user",
                parts=[tool_response],
            ),
        ],
        config={
            "tools": [lead_tools],
            "automatic_function_calling": {
                "disable": True
            },
        },
    )

    print("Gemini:", final_response.text)
