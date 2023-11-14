""" example of how to use the OpenAI client with the Azure OpenAI Proxy """

from openai import OpenAI

client = OpenAI(
    base_url="YOUR_PROXY_API_URL",
    api_key="YOUR_EVENT_CODE/GITHUB_USERNAME",
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Who won the world series in 2020?"},
        {
            "role": "assistant",
            "content": "The Los Angeles Dodgers won the World Series in 2020.",
        },
        {"role": "user", "content": "Where was it played?"},
    ],
)

print(response.choices[0].message.content)