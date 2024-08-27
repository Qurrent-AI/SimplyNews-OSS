import aiohttp
import json
from datetime import datetime
import pytz
from uuid import UUID
from qurrent import Agent, Database, Message


class HostAgent(Agent):
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

    async def write_host_statements(self, all_conversations: list) -> str:
        self.message_thread.append(
            Message(
                role="user",
                content=f"Here is the content of the podcast: {all_conversations}\nHere is today's date: {datetime.now(pytz.timezone('America/Los_Angeles')).strftime('%A %B %d')}",
            )
        )
        response, _ = await self()

        date: str = response.get("date")
        intro: str = response.get("intro")
        outro: str = response.get("outro")

        return date, intro, outro
