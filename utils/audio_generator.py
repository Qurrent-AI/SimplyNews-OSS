import io
import os
import time

from openai import OpenAI
from pydub import AudioSegment  # type: ignore


class AudioGenerator:
    def __init__(self, openai_api_key):
        self.openai_client = OpenAI(
            api_key=openai_api_key,
        )
        self.audio_fragments = AudioSegment.empty()

    def get_timestamp(self, chapter_mode) -> str:
        if chapter_mode:
            if len(self.audio_fragments) == 0:
                return "00.00"

        return round(len(self.audio_fragments) / 1000.0, 2)

    def generate_openai(self, text: str, voice: str) -> bytes:
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                response = self.openai_client.audio.speech.create(
                    model="tts-1-hd", voice=voice, input=text, response_format="aac"
                )
                return response.content
            except Exception as e:
                if attempt < max_attempts - 1:
                    print(
                        f"Error generating audio (attempt {attempt + 1}/{max_attempts}): {e}\n"
                        f"Waiting 10 seconds and trying again..."
                    )
                    time.sleep(10)
                else:
                    raise Exception(
                        f"Failed to generate audio after {max_attempts} attempts: {e}"
                    )

    def format_timestamp(self, timestamp):
        total_seconds = float(timestamp)

        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)

        formatted_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return formatted_time

    def insert_custom_audio(self, audio_file, audio_format):
        audio = AudioSegment.from_file(audio_file, format=audio_format)
        self.audio_fragments += audio

    def insert_text_fragment(self, fragment):
        buffer = io.BytesIO(fragment)
        sound = AudioSegment.from_file(buffer, format="aac")

        self.audio_fragments += sound

    def create_preview(self, preview_fragment, qurrent_fragment):
        buffer = io.BytesIO(preview_fragment)
        story_preview = AudioSegment.from_file(buffer, format="aac")
        pause = AudioSegment.silent(duration=(3000))
        story_preview += pause

        buffer = io.BytesIO(qurrent_fragment)
        qurrent_intro = AudioSegment.from_file(buffer, format="aac")
        story_preview += qurrent_intro

        silent_end = AudioSegment.silent(duration=(5000))
        story_preview += silent_end

        preview_filepath = os.path.join(
            os.path.dirname(__file__), "podcast_intros", "story_preview_sound.aac"
        )

        preview_sound = AudioSegment.from_file(preview_filepath, format="aac")
        preview_sound -= 15  # decrease decibles
        preview_sound = preview_sound[: len(story_preview)]
        preview_sound = preview_sound.fade_in(3000)
        preview_sound = preview_sound.fade_out(3000)

        preview = story_preview.overlay(preview_sound, position=0)
        silent_end = AudioSegment.silent(duration=(1000))

        preview += silent_end

        self.audio_fragments += preview

    def create_opening(self, hello_fragment, date_fragment):
        opening_filepath = os.path.join(
            os.path.dirname(__file__), "podcast_intros", "opening_sound.aac"
        )

        buffer = io.BytesIO(hello_fragment)
        good_morning = AudioSegment.from_file(buffer, format="aac")

        buffer = io.BytesIO(date_fragment)
        date_clip = AudioSegment.from_file(buffer, format="aac")

        intro_sound = AudioSegment.from_file(opening_filepath, format="aac")
        intro_sound -= 25  # decrease decibles

        # calculate silence to add
        silent_start = AudioSegment.silent(duration=4000)
        silence_buffer = AudioSegment.silent(duration=350)
        welcome_clip = silent_start + good_morning + silence_buffer + date_clip

        silent_end = AudioSegment.silent(
            duration=(len(intro_sound) - len(good_morning) - 11000)
        )
        welcome_buffer = welcome_clip + silent_end

        intro = welcome_buffer.overlay(intro_sound, position=0)
        final_intro = intro.fade_out(500)

        self.audio_fragments += final_intro

    def create_outro(self, fragment):
        outro_filepath = os.path.join(
            os.path.dirname(__file__), "podcast_intros", "outro_sound.aac"
        )

        buffer = io.BytesIO(fragment)
        goodbye = AudioSegment.from_file(buffer, format="aac")

        silence = AudioSegment.silent(duration=4000)
        goodbye += silence

        outro_clip = AudioSegment.from_file(outro_filepath, format="aac")
        outro_clip -= 20  # decrease by 20 decibels

        outro_position = len(goodbye) - 6500
        outro = goodbye.overlay(outro_clip, position=outro_position)

        silence = AudioSegment.silent(duration=2000)
        outro += silence

        self.audio_fragments += outro

    def export_audio(self, audio_filename):
        self.audio_fragments.export(audio_filename, format="mp3")
        self.audio_fragments = AudioSegment.empty()
