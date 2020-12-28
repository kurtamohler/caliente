import pyaudio
import wave
import numpy as np

class Signal:
    def __init__(self, init_type, file_path_or_data, sample_width=None, framerate=None):
        if init_type == 'file':
            self._load_file(file_path_or_data)
        elif init_type == 'data':
            if not sample_width:
                raise ValueError(f'need sample_width for init type "data"')
            if not framerate:
                raise ValueError(f'need framerate for init type "data"')
            self.sample_width = sample_width
            self.framerate = framerate
            self.data = file_path_or_data.copy()
        else:
            raise ValueError(f'init_type="{init_type}" not supported')

    def _load_file(self, file_path):
        self.file_path = file_path

        with wave.open(self.file_path, 'rb') as wave_f:
            if wave_f.getnchannels() != 1:
                raise ValueError(f'only mono WAV files are supported')
            
            self.sample_width = wave_f.getsampwidth()
            self.framerate = wave_f.getframerate()

            dtype = self.get_dtype()
            wave_chunk = wave_f.readframes(wave_f.getnframes())
            self.data = np.fromstring(wave_chunk, dtype=dtype)

    def get_dtype(self):
        dtype = {1: np.int8, 2: np.int16, 4: np.int32}.get(self.sample_width)
        if not dtype:
            raise ValueError(f'sample width {sample_width} not supported')
        return dtype


    def get_data(self):
        return self.data

    def play(self, chunk_size=1024):
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=audio.get_format_from_width(
                self.sample_width
            ),
            channels=1,
            rate=self.framerate,
            output=True)


        num_chunks = int((self.data.size - 1) / chunk_size) + 1

        chunked_data = np.array_split(self.data, num_chunks)

        chunked_data_bytes = []

        for chunk in chunked_data:
            chunked_data_bytes.append(chunk.tobytes())

        idx = 0
        for chunk in chunked_data_bytes:
            stream.write(chunk)


        stream.stop_stream()
        stream.close()

        audio.terminate()

