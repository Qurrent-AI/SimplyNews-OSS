import aiohttp
from datetime import datetime
from uuid import UUID
from qurrent import (
    Agent,
    Database,
    llmcallable,
)


class ResearchAgent(Agent):
    def __init__(
        self,
        yaml_config_path: str,
        workflow_instance_id: UUID,
        database: Database,
        agent_instance_id: UUID,
    ) -> None:
        super().__init__(
            yaml_config_path=yaml_config_path,
            workflow_instance_id=workflow_instance_id,
            database=database,
            agent_instance_id=agent_instance_id,
        )

    @classmethod
    async def create(
        cls, yaml_config_path, database, workflow_instance_id, perplexity_api_key
    ) -> "ResearchAgent":
        self = await super().create(
            yaml_config_path=yaml_config_path,
            database=database,
            workflow_instance_id=workflow_instance_id,
        )

        self.perplexity_api_key = perplexity_api_key

        return self

    async def call_perplexity(self, query: str) -> str:
        """
        Make an asynchronous API call to Perplexity with the given query.
        """
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.perplexity_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        data = {
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": f"Be precise and concise. You must always return a description of some news event, no matter what. Surface the most recent news available. Today's date is {datetime.now().strftime('%Y-%m-%d')}",
                },
                {"role": "user", "content": query},
            ],
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    return f"Error: Unable to fetch results. Status code: {response.status}"

    def get_query(self, topic: str) -> str:
        return f"Generate a summary of a specific, recent news event regarding {topic}"

    @llmcallable
    async def get_news_1(self, news_topic: str) -> str:
        """
        Args: "news_topic" (str): The topic of the news to return research on
        Description: The function will return a summary of a news event for a given topic
        """
        query = self.get_query(news_topic)
        return await self.call_perplexity(query)

    @llmcallable
    async def get_news_2(self, news_topic: str) -> str:
        """
        Args: "news_topic" (str): The topic of the news to return research on
        Description: The function will return a summary of a news event for a given topic
        """
        query = self.get_query(news_topic)
        return await self.call_perplexity(query)

    @llmcallable
    async def get_news_3(self, news_topic: str) -> str:
        """
        Args: "news_topic" (str): The topic of the news to return research on
        Description: The function will return a summary of a news event for a given topic
        """
        query = self.get_query(news_topic)
        return await self.call_perplexity(query)
