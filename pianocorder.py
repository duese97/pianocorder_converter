import random
from random import randrange
import math
from math import sin
from ctypes import (
    Structure,
    c_byte,
    c_float,
)
from enum import Enum
import os

from wav_util import wav_writer


class manchester_state(Enum):
    LOW = 0b00
    LOW_HIGH = 0b01
    HIGH_LOW = 0b10
    HIGH = 0b11


class pianocorder_frame(Structure):
    _fields_ = [
        # bit number 0, byte 0
        ("soft_pedal", c_byte, 1),
        ("sustain_pedal", c_byte, 1),
        ("none_1", c_byte, 1),
        ("bass_intensity", c_byte, 5),
        # byte 1
        # first playable, lowest note: c# (5th note from the left start)
        ("none_2", c_byte, 8),
        # byte 2
        ("note_5", c_byte, 1),
        ("note_6", c_byte, 1),
        ("note_7", c_byte, 1),
        ("note_8", c_byte, 1),
        ("note_9", c_byte, 1),
        ("note_10", c_byte, 1),
        ("note_11", c_byte, 1),
        ("note_12", c_byte, 1),
        # byte 3
        ("note_13", c_byte, 1),
        ("note_14", c_byte, 1),
        ("note_15", c_byte, 1),
        ("note_16", c_byte, 1),
        ("note_17", c_byte, 1),
        ("note_18", c_byte, 1),
        ("note_19", c_byte, 1),
        ("note_20", c_byte, 1),
        # byte 4
        ("note_21", c_byte, 1),
        ("note_22", c_byte, 1),
        ("note_23", c_byte, 1),
        ("note_24", c_byte, 1),
        ("note_25", c_byte, 1),
        ("note_26", c_byte, 1),
        ("note_27", c_byte, 1),
        ("note_28", c_byte, 1),
        # byte 5
        ("note_29", c_byte, 1),
        ("note_30", c_byte, 1),
        ("note_31", c_byte, 1),
        ("note_32", c_byte, 1),
        ("note_33", c_byte, 1),
        ("note_34", c_byte, 1),
        ("note_35", c_byte, 1),
        ("note_36", c_byte, 1),
        # byte 6
        ("note_37", c_byte, 1),
        ("note_38", c_byte, 1),
        ("note_39", c_byte, 1),
        ("note_40", c_byte, 1),
        ("note_41", c_byte, 1),
        ("note_42", c_byte, 1),
        ("note_43", c_byte, 1),
        ("note_44", c_byte, 1),
        # byte 7
        ("none_3", c_byte, 8),
        # expression control:
        #   00 -> note 44 bass, note 45/46 treble
        #   10 -> note 44..46 treble
        #   01 -> note 44..46 bass
        #   11 -> not used
        # byte 8
        ("control", c_byte, 2),
        ("none_4", c_byte, 1),
        ("treble_intensity", c_byte, 5),
        # byte 9
        ("note_45", c_byte, 1),
        ("note_46", c_byte, 1),
        ("note_47", c_byte, 1),
        ("note_48", c_byte, 1),
        ("note_49", c_byte, 1),
        ("note_50", c_byte, 1),
        ("note_51", c_byte, 1),
        ("note_52", c_byte, 1),
        # byte 10
        ("note_53", c_byte, 1),
        ("note_54", c_byte, 1),
        ("note_55", c_byte, 1),
        ("note_56", c_byte, 1),
        ("note_57", c_byte, 1),
        ("note_58", c_byte, 1),
        ("note_59", c_byte, 1),
        ("note_60", c_byte, 1),
        # byte 11
        ("note_61", c_byte, 1),
        ("note_62", c_byte, 1),
        ("note_63", c_byte, 1),
        ("note_64", c_byte, 1),
        ("note_65", c_byte, 1),
        ("note_66", c_byte, 1),
        ("note_67", c_byte, 1),
        ("note_68", c_byte, 1),
        # byte 12
        ("note_69", c_byte, 1),
        ("note_70", c_byte, 1),
        ("note_71", c_byte, 1),
        ("note_72", c_byte, 1),
        ("note_73", c_byte, 1),
        ("note_74", c_byte, 1),
        ("note_75", c_byte, 1),
        ("note_76", c_byte, 1),
        # byte 13
        ("note_77", c_byte, 1),
        ("note_78", c_byte, 1),
        ("note_79", c_byte, 1),
        ("note_80", c_byte, 1),
        ("note_81", c_byte, 1),
        ("note_82", c_byte, 1),
        ("note_83", c_byte, 1),
        ("note_84", c_byte, 1),  # highest possible note
        # byte 14
        ("none_5", c_byte, 8),
        # byte 15
        ("sync", c_byte, 8),
        # bit number 127
    ]

    def __init__(self, init_random: bool = False):

        # sync word has a different value
        self.sync = 0b1011_1111

        self.control = 0b11  # no bass or treble expression

        self.note_fields = [
            name for name, *_ in pianocorder_frame._fields_ if name.startswith("note_")
        ]

        if not init_random:
            return

        num_played_notes = randrange(1, 10)
        for i in range(num_played_notes):
            random_note = random.choice(self.note_fields)
            self.set_member(random_note)

    def set_member(self, member: str):  # set member as active
        setattr(self, member, 1)

    def reset_member(self, member: str):  # set member as inactive
        setattr(self, member, 0)


class manchester_encoder:
    """
    Realizes a differential manchester encoding. Also called biphase mark encoding (BMC).
    At each bit-time the line signal HAS to change.
    At each half-bit-time a transition may occur (depends on given input to encode, two versions exist)
    See also
        https://en.wikipedia.org/wiki/Differential_Manchester_encoding
        https://cheeseepedia.org/?v=cep-js&=sv6qppgx2iim6t0g

    """

    def __init__(self, previous_lvl: int = 0, no_transition_zero: bool = True):
        self.manchester_states: list[
            manchester_state
        ] = []  # contains the manchester encoded states

        self._previous_lvl = previous_lvl
        self._no_transition_zero = no_transition_zero  # make no half-bit time transition for zero (or one) as input data
        self._first_lvl = (
            previous_lvl  # to remember the very first level, not to be altered
        )

    def encode_append(self, frame: pianocorder_frame):
        self._last_frame = frame
        for byte in bytes(frame):  # will iterate from bit 0..127
            for bit_num in range(8):
                current_bit = (
                    byte & (1 << bit_num)
                ) & 0xFF  # check if respective bit set or not

                if self._previous_lvl == 0:  # must start with high level
                    if current_bit == 0 and self._no_transition_zero:
                        new_state = manchester_state.HIGH
                    else:
                        new_state = manchester_state.HIGH_LOW
                else:  # must start with low level
                    if current_bit == 0 and self._no_transition_zero:
                        new_state = manchester_state.LOW
                    else:
                        new_state = manchester_state.LOW_HIGH

                self.manchester_states.append(new_state)
                self._previous_lvl = new_state.value & 0b01  # remember previous level

    def make_loopable(self):
        # I have no idea if this will deadlock or what exactly the math behind is to safely
        # execute this. Just use a sanity counter and call it a day.
        sanity_count = 0
        while (
            self._first_lvl != self._previous_lvl
        ):  # level needs to change when looping from the start again
            # insert last frame again
            self.encode_append(self._last_frame)
            sanity_count += 1
            if sanity_count > 3:
                raise ValueError("Unable to loop selected data")


class pianocorder_wav(wav_writer):
    """Generates an audio file for the pianocorder tape"""

    FREQ_NO_TRANSITION_HZ = 2250
    FREQ_TRANSITION_HZ = 4500

    FREQ_FACTOR_NO_TRANSITION = 1
    FREQ_FACTOR_TRANSITION = int(FREQ_TRANSITION_HZ / FREQ_NO_TRANSITION_HZ)

    SAMPLES_PER_STATE = 20
    SAMPLES_PER_SEC = FREQ_TRANSITION_HZ * SAMPLES_PER_STATE

    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

    def __init__(self, output_path=os.path.join(SCRIPT_DIR, "example.wav")):
        super().__init__(
            output_path,
            channels=1,
            sampling_freq=self.SAMPLES_PER_SEC,
            bits_per_sample=32,
        )

        # build lookup tables for tones, only needs to be done once
        self.high = self._create_tone_lookup(
            samples=self.SAMPLES_PER_STATE, freq=self.FREQ_FACTOR_NO_TRANSITION
        )
        self.low = self._create_tone_lookup(
            samples=self.SAMPLES_PER_STATE, freq=-self.FREQ_FACTOR_NO_TRANSITION
        )
        self.high_low = self._create_tone_lookup(
            samples=self.SAMPLES_PER_STATE, freq=self.FREQ_FACTOR_TRANSITION
        )
        self.low_high = self._create_tone_lookup(
            samples=self.SAMPLES_PER_STATE, freq=-self.FREQ_FACTOR_TRANSITION
        )

    def _create_tone_lookup(self, samples: int, freq: float = 1) -> bytes:
        lookup_table: list[float] = []

        for sample in range(samples):
            x = (float(sample) / samples) * math.pi
            lookup_table.append(sin(freq * x))

        cfloat_arr = (c_float * samples)(*lookup_table)
        return bytes(cfloat_arr)

    def write_manchester_data(self, manchester: list[manchester_state]):
        for m in manchester:
            match m:
                case manchester_state.HIGH:
                    wav.write_data(wav.high)
                case manchester_state.LOW:
                    wav.write_data(wav.low)
                case manchester_state.HIGH_LOW:
                    wav.write_data(wav.high_low)
                case manchester_state.LOW_HIGH:
                    wav.write_data(wav.low_high)
                case _:
                    raise ValueError("Unknown manchester state")


encoder = manchester_encoder()
frame = pianocorder_frame()
# frame.set_member("note_84")
# frame.set_member("soft_pedal")

encoder.encode_append(frame)

encoder.make_loopable()


wav = pianocorder_wav()

with wav:
    wav.write_manchester_data(encoder.manchester_states)
