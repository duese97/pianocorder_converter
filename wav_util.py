from ctypes import LittleEndianStructure, c_byte, c_int32, c_int16, sizeof


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