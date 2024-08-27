from uuid import UUID
import time
import asyncio
from agents.researcher import ResearchAgent
from agents.host import HostAgent
from agents.transitioner import TransitionAgent
from agents.scripter import ScriptAgent
import concurrent.futures
from qurrent import (
    Message,
    QurrentConfig,
    Workflow,
)

from utils.audio_generator import AudioGenerator
from utils.voice import VoiceInfo


class SimplyNews(Workflow):
    def __init__(self, config: QurrentConfig, workflow_instance_id: UUID) -> None:
        super().__init__(config, workflow_instance_id)

        self.openai_api_key = config["LLM_KEYS"]["OPENAI_API_KEY"]
        self.voice_info = VoiceInfo()

        self.researcher: ResearchAgent
        self.host: HostAgent
        self.transitioner: TransitionAgent
        self.scripters: list[ScriptAgent]

    @classmethod
    async def create(cls, config: QurrentConfig) -> "SimplyNews":
        self = await super().create(config)

        self.researcher = await ResearchAgent.create(
            yaml_config_path="./config/researcher.yaml",
            database=self.db,
            workflow_instance_id=self.workflow_instance_id,
            perplexity_api_key=config["PERPLEXITY_API_KEY"],
        )

        # hard-code a max of four topics per podcast
        self.scripters = await self.create_scripters(4)

        self.transitioner = await TransitionAgent.create(
            yaml_config_path="./config/transitioner.yaml",
            database=self.db,
            workflow_instance_id=self.workflow_instance_id,
        )

        self.host = await HostAgent.create(
            yaml_config_path="./config/host.yaml",
            database=self.db,
            workflow_instance_id=self.workflow_instance_id,
        )

        return self

    async def create_scripters(self, num_scripters: int) -> list[ScriptAgent]:
        async def scripter_factory():
            return await ScriptAgent.create(
                yaml_config_path="./config/scripter.yaml",
                database=self.db,
                workflow_instance_id=self.workflow_instance_id,
            )

        async with asyncio.TaskGroup() as group:
            tasks = [
                group.create_task(scripter_factory()) for _ in range(num_scripters)
            ]

        return [task.result() for task in tasks]

    async def run(self, description, name) -> bool:
        # gather research
        self.researcher.message_thread.append(
            Message(
                role="user",
                content=f"The description of the podcast is: {description}",
            )
        )

        _, action_output = await self.researcher(run_actions_in_parallel=True)

        # generate conversations
        scripts = []
        async with asyncio.TaskGroup() as group:
            for i, (action, event_description) in enumerate(action_output.items()):
                if i < len(self.scripters):
                    script_task = group.create_task(
                        self.scripters[i].write_script(
                            event_description,
                            self.voice_info.get_next_speaker("David"),
                        )
                    )
                    scripts.append((action, script_task))

        all_convos = [await script_task for _, script_task in scripts]

        date, intro, outro = await self.host.write_host_statements(all_convos)

        # Get voice of first author
        first_author = all_convos[0][0]["author"] if all_convos[0][0] else "David"

        # Add intro and outro messages
        all_convos.insert(
            0, [{"author": first_author, "message": "We start off with "}]
        )
        all_convos.append([{"author": first_author, "message": outro}])

        # Smooth out script with transitions
        edited_conversation = (await self.transitioner.smooth_script(all_convos))[0]

        # Add intro
        edited_conversation[0:0] = [
            {
                "author": first_author,
                "message": f"Welcome, {name}, this is Simply News.",
                "chapter_topic": "Introduction",
            },
            {"author": first_author, "message": date},
            {"author": first_author, "message": intro},
            {
                "author": first_author,
                "message": f"I'm David, and you're listening to Simply News.",
            },
        ]

        # generate audio
        file_path = self.produce_pod_v2(edited_conversation)
        print(f"finished generating. file path: {file_path}")
        return True

    def produce_pod_v2(self, conversations):
        audio_generator = AudioGenerator(self.openai_api_key)
        audio_filename = f"{time.strftime('%Y-%m-%d')}_simply.mp3"

        chapters = []
        combined_message = ""

        # Function to generate audio for a single dialogue
        def generate_audio(dialogue):
            voice_id = self.voice_info.get_voice_id_openai(dialogue["author"])
            return audio_generator.generate_openai(dialogue["message"], voice_id)

        # Use ThreadPoolExecutor to parallelize audio generation
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_fragments = list(executor.map(generate_audio, conversations))

        # Process results in order
        for index, fragment in enumerate(future_fragments):
            dialogue = conversations[index]

            current_timestamp = audio_generator.get_timestamp(chapter_mode=False)
            conversations[index]["timestamp"] = current_timestamp

            if dialogue.get("chapter_topic"):
                chapters.append(
                    {
                        "title": dialogue["chapter_topic"],
                        "start_time": audio_generator.get_timestamp(chapter_mode=True),
                    }
                )

            if index == 0:
                combined_message += dialogue["message"] + " "
                audio_generator.create_opening(fragment, future_fragments[1])
            elif index == 1:
                combined_message += dialogue["message"] + " "
                continue
            elif index == 2:
                combined_message += dialogue["message"] + " "
                audio_generator.create_preview(fragment, future_fragments[3])
            elif index == 3:
                combined_message += dialogue["message"]
                conversations[0]["message"] = combined_message
                conversations[3]["timestamp"] = current_timestamp + 0.01
                continue
            elif index == (len(conversations) - 1):
                audio_generator.create_outro(fragment)
            else:
                audio_generator.insert_text_fragment(fragment)

        # After processing all dialogues, merge 0-3 into a single opening message
        conversations = [conversations[0]] + conversations[4:]

        # Update episode description with chapters
        episode_description = "Outline:<br>"
        for chapter in chapters:
            formatted_timestamp = audio_generator.format_timestamp(
                chapter["start_time"]
            )
            episode_description += f"({formatted_timestamp}) {chapter['title']}<br>"

        # Write audio fragments saved in audio_generator to file
        audio_generator.export_audio(audio_filename)

        return audio_filename
