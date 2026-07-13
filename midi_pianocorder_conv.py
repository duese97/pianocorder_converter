from dataclasses import dataclass
from pianocorder import FRAME_PERIOD_S, pianocorder_frame
from mido import MidiFile
from collections import Counter


@dataclass
class note_state:
    abs_time: float
    note: int
    pressed: bool


class midi_converter:
    # MIDI note #21 equals piano key 1 (A0), #22 is key 2 (A#) and so on
    PIANO_KEY_OFFSET = 20

    def __init__(self, midi_path_str: str, target_channel: int = 0):
        self.midifile = MidiFile(midi_path_str)
        self.target_channel = target_channel

        print(f"Ticks per beat {self.midifile.ticks_per_beat}")

        self.note_count = Counter()

        channels = []
        for track_num, track in enumerate(self.midifile.tracks):
            channels.append({msg.channel for msg in track if hasattr(msg, "channel")})

            for msg in track:
                if msg.type == "note_on" and msg.velocity > 0:
                    self.note_count[msg.channel] += 1

        for track_num, track in enumerate(self.midifile.tracks):
            for ch in channels[track_num]:
                print(
                    f"Track num {track_num}, name {track.name}, channel {ch}, total notes used {self.note_count[ch]}"
                )

    def find_most_used_channel(self):

        # get array with most common notes (key-values)
        tmp_channel = self.note_count.most_common()

        # most common key-value -> most common key (channel)
        tmp_channel = tmp_channel[0][0]

        self.target_channel = tmp_channel

    def _collect_channel(self):

        print(f"Collecting target channel {self.target_channel}")

        # reset notes
        self.note_states: list[note_state] = []

        # Absolute time in seconds, since start of file
        current_time = 0.0

        # Collect note info
        for msg in self.midifile:
            current_time += msg.time

            if not hasattr(msg, "channel"):
                continue

            if msg.channel != self.target_channel:
                continue

            if msg.type == "note_on" and msg.velocity > 0:
                press = True
            elif msg.type == "note_off" or (
                msg.type == "note_on" and msg.velocity == 0
            ):
                press = False
            else:
                continue

            if msg.note <= self.PIANO_KEY_OFFSET:  # note too low to play on piano
                continue

            converted_note = msg.note - self.PIANO_KEY_OFFSET
            # special case: out of bounds, very high and -low nots cant be played
            if converted_note < 5 or converted_note > 84:
                continue

            self.note_states.append(note_state(current_time, converted_note, press))

    def _build_frames(self):
        frame_boundary = self.note_states[0].abs_time + FRAME_PERIOD_S

        self.frames: list[pianocorder_frame] = []

        new_frame = pianocorder_frame()

        for n in self.note_states:
            # check if note is within current frame
            if n.abs_time < frame_boundary:
                note_key = f"note_{n.note}"
                new_frame.set_member(note_key, n.pressed)
                continue  # continue to collect for current frame

            # not not anymore in frame, finalize it
            self.frames.append(new_frame)

            # shift new boundary
            frame_boundary += FRAME_PERIOD_S

            new_frame = pianocorder_frame()  # create empty frame

            # append empty frames in case the pause is longer
            while frame_boundary < n.abs_time:
                self.frames.append(new_frame)
                frame_boundary += FRAME_PERIOD_S

            # finally add the note into the proper frame
            note_key = f"note_{n.note}"
            new_frame.set_member(note_key, n.pressed)

        # Make sure we end with silence
        new_frame = pianocorder_frame()  # create empty frame
        self.frames.append(new_frame)

    def convert(self):
        self._collect_channel()
        self._build_frames()
