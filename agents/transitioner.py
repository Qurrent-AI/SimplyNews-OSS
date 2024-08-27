from uuid import UUID
from qurrent import Agent, Message, Database


class TransitionAgent(Agent):
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

    async def concatenate_sentences(self, first, second):
        self.message_thread.append(
            Message(
                role="user",
                content=f"Here is the closing sentence: {first}\nHere is the opening sentence: {second}",
            )
        )

        response, _ = await self()
        transition = response.get("transition")

        return transition

    async def smooth_script(self, all_conversations: list[dict]) -> list[dict]:
        # Base case: if there's only one conversation or none, no merging is needed
        if len(all_conversations) <= 1:
            return all_conversations

        first_conversation = all_conversations[0]
        second_conversation = all_conversations[1]

        if first_conversation[-1]["author"] == second_conversation[0]["author"]:
            merged_message = await self.concatenate_sentences(  # Add 'await' here
                first_conversation[-1]["message"], second_conversation[0]["message"]
            )
            first_conversation[-1]["message"] = merged_message

            # Check and preserve 'chapter_topic' if present in either message being merged
            if "chapter_topic" in second_conversation[0]:
                first_conversation[-1]["chapter_topic"] = second_conversation[0][
                    "chapter_topic"
                ]

            second_conversation.pop(0)

        # Merge lists
        merged_conversation = first_conversation + second_conversation

        # Recursively merge the rest of the conversations
        remaining_conversations = [merged_conversation] + all_conversations[2:]

        return await self.smooth_script(remaining_conversations)
