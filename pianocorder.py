from this import s
import math
from math import sin
from ctypes import Structure, c_byte, memset, sizeof, byref, c_int32, c_int16, c_float, c_int32, Array, LittleEndianStructure
from enum import Enum
import os


class manchester_state(Enum):
    LOW = 0b00
    LOW_HIGH = 0b01
    HIGH_LOW = 0b10
    HIGH = 0b11
    
class pianocorder_frame(Structure):
    _fields_ = [
        # bit number 0
        ("soft_pedal", c_byte, 1),
        ("sustain_pedal", c_byte, 1),
        ("none_1", c_byte, 1),
        ("bass_intensity", c_byte, 5),

        ("none_2", c_byte, 8),

        ("note_5", c_byte, 1),
        ("note_6", c_byte, 1),
        ("note_7", c_byte, 1),
        ("note_8", c_byte, 1),
        ("note_9", c_byte, 1),
        ("note_10", c_byte, 1),
        ("note_11", c_byte, 1),
        ("note_12", c_byte, 1),

        ("note_13", c_byte, 1),
        ("note_14", c_byte, 1),
        ("note_15", c_byte, 1),
        ("note_16", c_byte, 1),
        ("note_17", c_byte, 1),
        ("note_18", c_byte, 1),
        ("note_19", c_byte, 1),
        ("note_20", c_byte, 1),

        ("note_21", c_byte, 1),
        ("note_22", c_byte, 1),
        ("note_23", c_byte, 1),
        ("note_24", c_byte, 1),
        ("note_25", c_byte, 1),
        ("note_26", c_byte, 1),
        ("note_27", c_byte, 1),
        ("note_28", c_byte, 1),

        ("note_29", c_byte, 1),
        ("note_30", c_byte, 1),
        ("note_31", c_byte, 1),
        ("note_32", c_byte, 1),
        ("note_33", c_byte, 1),
        ("note_34", c_byte, 1),
        ("note_35", c_byte, 1),
        ("note_36", c_byte, 1),

        ("note_37", c_byte, 1),
        ("note_38", c_byte, 1),
        ("note_39", c_byte, 1),
        ("note_40", c_byte, 1),
        ("note_41", c_byte, 1),
        ("note_42", c_byte, 1),
        ("note_43", c_byte, 1),
        ("note_44", c_byte, 1),

        ("none_3", c_byte, 8),

        ("control", c_byte, 2),
        ("none_4", c_byte, 1),
        ("treble_intensity", c_byte, 5),

        ("note_45", c_byte, 1),
        ("note_46", c_byte, 1),
        ("note_47", c_byte, 1),
        ("note_48", c_byte, 1),
        ("note_49", c_byte, 1),
        ("note_50", c_byte, 1),
        ("note_51", c_byte, 1),
        ("note_52", c_byte, 1),

        ("note_53", c_byte, 1),
        ("note_54", c_byte, 1),
        ("note_55", c_byte, 1),
        ("note_56", c_byte, 1),
        ("note_57", c_byte, 1),
        ("note_58", c_byte, 1),
        ("note_59", c_byte, 1),
        ("note_60", c_byte, 1),

        ("note_61", c_byte, 1),
        ("note_62", c_byte, 1),
        ("note_63", c_byte, 1),
        ("note_64", c_byte, 1),
        ("note_65", c_byte, 1),
        ("note_66", c_byte, 1),
        ("note_67", c_byte, 1),
        ("note_68", c_byte, 1),

        ("note_69", c_byte, 1),
        ("note_70", c_byte, 1),
        ("note_71", c_byte, 1),
        ("note_72", c_byte, 1),
        ("note_73", c_byte, 1),
        ("note_74", c_byte, 1),
        ("note_75", c_byte, 1),
        ("note_76", c_byte, 1),
    
        ("note_77", c_byte, 1),
        ("note_78", c_byte, 1),
        ("note_79", c_byte, 1),
        ("note_80", c_byte, 1),
        ("note_81", c_byte, 1),
        ("note_82", c_byte, 1),
        ("note_83", c_byte, 1),
        ("note_84", c_byte, 1),

        ("none_5", c_byte, 8),

        ("sync", c_byte, 8),
        # bit number 127
    ]
    def __init__(self):
        # All note words are low active
        memset(byref(self), 0xFF, sizeof(self))

        # sync word has a different value
        self.sync = 0b1011_1111

    #def random_notes(self, random_min:int, random_max: int):


class manchester_encoder():
    """
    Realizes a differential manchester encoding. Also called biphase mark encoding (BMC).
    At each bit-time the line signal HAS to change.
    At each half-bit-time a transition may occur (depends on given input to encode, two versions exist)
    See also
        https://en.wikipedia.org/wiki/Differential_Manchester_encoding
        https://cheeseepedia.org/?v=cep-js&=sv6qppgx2iim6t0g

    """

    def __init__(self, previous_lvl: int = 0, no_transition_zero: bool = True):
        self.manchester_states : list[manchester_state] = [] # contains the manchester encoded states

        self._previous_lvl = previous_lvl
        self._no_transition_zero = no_transition_zero # make no half-bit time transition for zero (or one) as input data
        self._first_lvl = previous_lvl # to remember the very first level, not to be altered

    def encode_append(self, frame: pianocorder_frame):
        self._last_frame = frame
        for byte in bytes(frame): # will iterate from bit 0..127
            for bit_num in range(8):
                current_bit = (byte & (1 << bit_num)) & 0xFF # check if respective bit set or not

                if self._previous_lvl == 0: # must start with high level
                    if current_bit == 0 and self._no_transition_zero:
                        new_state =  manchester_state.HIGH
                    else:
                        new_state = manchester_state.HIGH_LOW
                else: # must start with low level
                    if current_bit == 0 and self._no_transition_zero:
                        new_state =  manchester_state.LOW
                    else:
                        new_state = manchester_state.LOW_HIGH
                
                self.manchester_states.append(new_state)
                self._previous_lvl = new_state.value & 0b01 # remember previous level

    def make_loopable(self):
        # I have no idea if this will deadlock or what exactly the math behind is to safely
        # execute this. Just use a sanity counter and call it a day.
        sanity_count = 0
        while self._first_lvl != self._previous_lvl: # level needs to change when looping from the start again
             # insert last frame again
            self.encode_append(self._last_frame)
            sanity_count += 1
            if sanity_count > 3:
                raise ValueError("Unable to loop selected data")



class wav_header(LittleEndianStructure):
    """ For structure definition/wording see https://en.wikipedia.org/wiki/WAV """
    _pack_ = 1
    _fields_ = [
        # Master RIFF chunk
        ("FileTypeBlocID", c_byte * 4 ), # Identifier « RIFF » 
        ("FileSize", c_int32), # Overall file size minus 8 bytes
        ("FileFormatID", c_byte * 4), # Format = « WAVE »

        # Chunk describing the data format
        ("FormatBlocID", c_byte * 4), # Identifier « fmt␣ »
        ("BlocSize", c_int32), # Chunk size minus 8 bytes, which is 16 bytes here  (0x10)
        ("AudioFormat", c_int16), # Audio format (1: PCM integer, 3: IEEE 754 float)
        ("NbrChannels", c_int16), # Number of channels
        ("Frequency", c_int32), # Sample rate (in hertz)
        ("BytePerSec", c_int32), # Number of bytes to read per second (Frequency * BytePerBloc)
        ("BytePerBloc", c_int16), # Number of bytes per block (NbrChannels * BitsPerSample / 8)
        ("BitsPerSample", c_int16), # Number of bits per sample

        # Chunk containing the sampled data
        ("DataBlocID",  c_byte * 4), # Identifier « data »
        ("DataSize", c_int32), # SampledData size
        
        # SampledData follows
    ]

    def __init__(self):
        self.FileTypeBlocID = (c_byte * 4)(0x52, 0x49, 0x46, 0x46)
        self.FileFormatID = (c_byte * 4)(0x57, 0x41, 0x56, 0x45)
        self.FormatBlocID = (c_byte * 4)(0x66, 0x6D, 0x74, 0x20)
        self.DataBlocID = (c_byte * 4)(0x64, 0x61, 0x74, 0x61)

        self.BlocSize = 0x10

class wav_writer():
    """ Simple class to write an arbitrary wav file """
    def __init__(self, output_path: str, channels:int, sampling_freq:int, bits_per_sample:int):
        # generate wav header
        self.wav_header = wav_header()
        self.wav_header.AudioFormat = 3 # float
        self.wav_header.NbrChannels = channels
        self.wav_header.Frequency = sampling_freq
        self.wav_header.BitsPerSample = bits_per_sample

        # redundant info
        self.wav_header.BytePerBloc = int((self.wav_header.BitsPerSample / 8) * self.wav_header.NbrChannels)
        self.wav_header.BytePerSec = int(self.wav_header.BytePerBloc * self.wav_header.Frequency)

        self.output_path = output_path
        self.sound_data = bytes()


    def __enter__(self):
        self.fd = open(self.output_path, "wb+")
        return self
    
    def __exit__(self, exception_type, exception_value, exception_traceback):

        self.wav_header.DataSize = len(self.sound_data)

        self.wav_header.FileSize = sizeof(wav_header) - 8 + self.wav_header.DataSize

        self.fd.write(bytes(self.wav_header))
        self.fd.write(self.sound_data)

        self.fd.close()

    def write_data(self, sample_data:bytes):
        self.sound_data += sample_data

class pianocorder_wav(wav_writer) :
    FREQ_NO_TRANSITION_HZ = 2250
    FREQ_TRANSITION_HZ = 4500

    FREQ_FACTOR_NO_TRANSITION = 1
    FREQ_FACTOR_TRANSITION = int(FREQ_TRANSITION_HZ / FREQ_NO_TRANSITION_HZ)

    SAMPLES_PER_STATE = 20
    SAMPLES_PER_SEC = FREQ_TRANSITION_HZ * SAMPLES_PER_STATE

    SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

    def __init__(self, output_path = os.path.join(SCRIPT_DIR, "example.wav")):
        super().__init__(
            output_path, channels=1, sampling_freq=self.SAMPLES_PER_SEC, bits_per_sample=32
        )

        # build lookup tables for tones, only needs to be done once
        self.high =  self._create_tone_lookup(samples = self.SAMPLES_PER_STATE, freq=self.FREQ_FACTOR_NO_TRANSITION)
        self.low =  self._create_tone_lookup(samples = self.SAMPLES_PER_STATE, freq=-self.FREQ_FACTOR_NO_TRANSITION)
        self.high_low =  self._create_tone_lookup(samples = self.SAMPLES_PER_STATE, freq=self.FREQ_FACTOR_TRANSITION)
        self.low_high =  self._create_tone_lookup(samples = self.SAMPLES_PER_STATE, freq=-self.FREQ_FACTOR_TRANSITION)


    def _create_tone_lookup(self, samples: int, freq: float = 1) -> Array[c_float]:
        lookup_table : list[float] = []

        for sample in range(samples):
            x = (float(sample) / samples) * math.pi
            lookup_table.append(sin(freq * x))

        return (c_float * samples)(*lookup_table)

    def write_manchester_data(self, manchester:list[manchester_state]):
        for m in manchester:
            match m:
                case manchester_state.HIGH:
                    wav.write_data(bytes(wav.high))
                case manchester_state.LOW:
                    wav.write_data(bytes(wav.low))
                case manchester_state.HIGH_LOW:
                    wav.write_data(bytes(wav.high_low))
                case manchester_state.LOW_HIGH:
                    wav.write_data(bytes(wav.low_high))

silent_frame = pianocorder_frame()
encoder = manchester_encoder()
encoder.encode_append(silent_frame)
encoder.encode_append(silent_frame)

encoder.make_loopable()


#encoder.encode_append(silent_frame)

wav = pianocorder_wav()

with wav:
    #wav.write_manchester_data([manchester_state.LOW_HIGH, manchester_state.LOW])
    #wav.write_manchester_data([manchester_state.HIGH_LOW, manchester_state.HIGH])
    #wav.write_data(bytes(wav.high_low))
    #wav.write_data(bytes(wav.high))
    wav.write_manchester_data(encoder.manchester_states)
