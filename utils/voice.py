import random


class VoiceInfo:
    def __init__(self):
        self.past_speakers = []
        self.past_names = []

        self.voices_oai = [
            {"alloy": ["Bella"]},
            {"echo": ["David"]},
            {"nova": ["Celeste"]},
            {"fable": ["James"]},
            {"shimmer": ["Abbey"]},
            {"onyx": ["Michael"]},
        ]

    def get_next_speaker(self, host):
        # Filter out the voices and names that have already been selected
        available_voices = [
            v
            for v in self.voices_oai
            if v not in self.past_speakers and list(v.keys())[0] != host
        ]

        # Simplify the available names collection process
        available_names = [
            name
            for voice in available_voices
            for names in voice.values()
            for name in names
            if name not in self.past_names and name != host
        ]

        if available_voices and available_names:
            # Select a voice and then a name from the filtered available names
            selected_name = random.choice(available_names)

            # Find the voice corresponding to the selected name
            selected_voice = next(
                v for v in available_voices if selected_name in list(v.values())[0]
            )

            self.past_speakers.append(selected_voice)
            self.past_names.append(selected_name)
            return selected_name
        else:
            return "Abbey"  # Default correspondent

    def get_voice_id_openai(self, author: str) -> str:
        for voice_group in self.voices_oai:
            for voice_name, authors in voice_group.items():
                if author in authors:
                    return voice_name

        # fall back option
        return "echo"
