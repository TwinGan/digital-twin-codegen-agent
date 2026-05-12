from openai import OpenAI

from .config import Config


class LLMClient:
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )

    def call(self, system_prompt: str, user_prompt: str) -> str:
        from openai.types.chat import ChatCompletion

        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            stream=False,
        )
        assert isinstance(response, ChatCompletion)
        return response.choices[0].message.content or ""
