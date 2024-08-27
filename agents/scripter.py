import aiohttp
from uuid import UUID
from qurrent import Agent, Database, Message


class ScriptAgent(Agent):
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

    async def write_script(self, description: str, replacement: str) -> str:
        self.message_thread.append(
            Message(
                role="user",
                content=f"The news description to write a script for: {description}",
            )
        )
        response, _ = await self()

        completion = response.get("script")

        for section in completion:
            if section["author"] == "_correspondent_":
                section["author"] = replacement

            section["message"] = section["message"].replace(
                "_correspondent_", replacement
            )

        return completion
