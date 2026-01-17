import json

import httpx

from app.core.configs import app_config
from app.core.services.prompt.base_service import PromptServiceInterface
from app.core.services.prompt.schemas import (
    PromptGenerationRequest,
    PromptProvider,
    PromptResult,
    PromptTemplate,
)


class OpenAIPromptService(PromptServiceInterface):
    """OpenAI prompt generation service implementation."""

    BASE_URL = 'https://api.openai.com/v1'

    def __init__(self):
        if not app_config.OPENAI_API_KEY:
            raise ValueError('OPENAI_API_KEY is not set. Please set it in your environment or .env file.')
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    'Authorization': f'Bearer {app_config.OPENAI_API_KEY}',
                    'Content-Type': 'application/json',
                },
                timeout=120.0,
            )
        return self._client

    async def generate(self, request: PromptGenerationRequest) -> PromptResult:
        """Generate content using the provided template and variables."""
        rendered_prompt = request.template.render(**request.variables)

        return await self.complete(
            prompt=rendered_prompt,
            system_prompt=request.template.system_prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            json_mode=request.json_mode,
        )

    async def generate_structured(
        self,
        template: PromptTemplate,
        variables: dict,
        model: str | None = None,
    ) -> dict:
        """Generate structured JSON output."""
        request = PromptGenerationRequest(
            template=template,
            variables=variables,
            model=model or 'gpt-4o-mini',
            json_mode=True,
        )

        result = await self.generate(request)

        if result.parsed:
            return result.parsed

        # Try to parse the content as JSON
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {'raw_content': result.content}

    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> PromptResult:
        """Simple completion without templates."""
        client = await self._get_client()

        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})

        payload = {
            'model': model or 'gpt-4o-mini',
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
        }

        if json_mode:
            payload['response_format'] = {'type': 'json_object'}

        response = await client.post('/chat/completions', json=payload)

        if response.status_code != 200:
            raise Exception(f'OpenAI API error: {response.text}')

        data = response.json()

        content = data['choices'][0]['message']['content']
        usage = data.get('usage', {})

        # Try to parse as JSON if json_mode was enabled
        parsed = None
        if json_mode:
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                pass

        return PromptResult(
            content=content,
            parsed=parsed,
            prompt_tokens=usage.get('prompt_tokens'),
            completion_tokens=usage.get('completion_tokens'),
            total_tokens=usage.get('total_tokens'),
            model=model or 'gpt-4o-mini',
            provider=PromptProvider.OPENAI,
        )

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
