from pianocorder import manchester_encoder, pianocorder_wav
from midi_pianocorder_conv import midi_converter


mc = midi_converter(r"/home/daniel/Downloads/badnerlied.mid")
mc.find_most_used_channel()
mc.convert()

encoder = manchester_encoder()
for frame in mc.frames:
    encoder.encode_append(frame)
encoder.make_loopable()

wav = pianocorder_wav()

with wav:
    wav.write_manchester_data(encoder.manchester_states)
