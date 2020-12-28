import numpy as np
import os
import matplotlib.pyplot as plt
import subprocess

from PyLTSpice.LTSpice_RawRead import RawRead

from ._signal import Signal

class Circuit():
    def __init__(self, circuit_file, ltspice_path):
        self.circuit_dir = os.path.dirname(circuit_file)
        self.circuit_file = os.path.basename(circuit_file)
        self.ltspice_path = ltspice_path
        self.sim_dtype = np.float32

    def _double_resolution(self, signal_data):
        output = np.empty(signal_data.size * 2, dtype=signal_data.dtype)
        output[0::2] = signal_data
        output[1::2] = (signal_data + np.roll(signal_data, -1)) / 2
        output[-1] = signal_data[-1]
        return output

    def _map_output_to_input_time(self, input_data, input_time, output_data, output_time):
        output_data_fixed = []
        output_time_fixed = []
        input_idx = 0
        input_time_s = input_time[0]

        for output_idx, output_time_s in enumerate(output_time):
            if output_time_s >= input_time_s:
                output_data_fixed.append(output_data[output_idx])
                #output_time_fixed.append(output_time_s)
                output_time_fixed.append(input_time_s)
                if len(output_data_fixed) == input_data.size:
                    break
                input_idx += 1
                if input_idx >= input_time.size:
                    break
                input_time_s = input_time[input_idx]

        '''
        print(f'adding {input_data.size - len(output_data_fixed)} repeats')
        while len(output_data_fixed) < input_data.size:
            output_data_fixed.append(output_data_fixed[-1])
        '''

        output_data_fixed = np.array(output_data_fixed, dtype=np.float32)

        return output_data_fixed, output_time_fixed


    def simulate(self, input_signal, amplitude_volts, offset_volts=0):
        input_data = input_signal.get_data().astype(self.sim_dtype)

        max_val = np.iinfo(input_signal.get_dtype()).max
        min_val = np.iinfo(input_signal.get_dtype()).min

        input_data = (input_data - min_val) * (amplitude_volts / (max_val - min_val)) + offset_volts

        sim_length = -1
        input_data = input_data[:sim_length]

        #input_data = self._double_resolution(input_data)

        input_time = np.arange(input_data.size, dtype=self.sim_dtype) / input_signal.framerate

        # Write input signal timeseries to the file that LTSpice simulation
        # expects
        with open(os.path.join(self.circuit_dir, 'sig_in.csv'), 'w') as f:
            for idx in range(input_data.size):
                f.write('{:.10E}\t{:.10E}\n'.format(
                    input_time[idx],
                    input_data[idx]))

        frame_period_s = 1.0 / input_signal.framerate

        # Look at this page for advice on how to set sim options:
        #   https://gist.github.com/turingbirds/c90672c3b126d0d5f37f90494d5057cb
        with open(os.path.join(self.circuit_dir, 'trancmd.txt'), 'w') as f:
            f.write('.param transtop {:.10E}\n'.format(input_time[-1]))
            f.write('.param transtart {:.10E}\n'.format(0))
            f.write('.param timestep {:.10E}\n'.format(frame_period_s/4))

            # TODO:
            # This increases the resolution of LTSpice's output. It's probably
            # about 10x what it needs to be, so look into how to change that.
            f.write('.OPTIONS plotwinsize=0\n')

        ltspice_cmd = [
            'wine',
            self.ltspice_path,
            '-Run',
            '-b',
            self.circuit_file]

        subprocess.check_output(
            ltspice_cmd,
            cwd=self.circuit_dir)
        
        raw_file_path = os.path.join(
            self.circuit_dir,
            '.'.join(self.circuit_file.split('.')[:-1] + ['raw']))
        print('======================')
        print(f'reading {raw_file_path}')
        print('======================')

        ltspice_raw_output = RawRead(raw_file_path)


        output_data = ltspice_raw_output.get_trace('V(vout)').get_wave(0)
        output_time = abs(ltspice_raw_output.get_trace('time').get_wave(0))

        print(f'frame_period_s: {frame_period_s}')
        print(f'input timesteps: {input_data.size}')
        print(f'output timesteps: {output_data.size}')
        #print(input_time)
        #print(output_time)

        output_time_increments = output_time - np.roll(output_time, 1)

        #print(output_time_increments)


        # LTSpice's output time series does not have a fixed period, sometimes
        # it outputs significantly more or fewer data points than the input
        # time series.  A simple but unfortunate way to handle this is to drop
        # our output signal's framerate to half that of the input and only take
        # samples from the output that align best with the corresponding
        # period.  It would be much better if we could increase the simulation
        # resolution in LTSpice, but I haven't been successful with that.
        # Another possibility could be to add artificial resolution to the
        # input--between each pair of values, insert the average of the two.
        #
        # However, I have a hunch that LTSpice figures that it should be
        # allowed to omit samples if they are very close to the surrounding
        # samples. In these cases, I should probably add those back in. A
        # simple linear extrapolation would probably work acceptably. This
        # solution has the potential to produce the least distortion, I think.
        # And I might need to do this anyway, even if I use any of the
        # aforementioned ideas.
        #
        # Design idea: Perhaps I should create an API into the simulator so I
        #   can experiment with the above ideas more easily
        output_data_fixed, output_time_fixed = self._map_output_to_input_time(
            input_data, input_time, output_data, output_time)




        '''
        input_data = input_signal.get_data().astype(self.sim_dtype)

        input_data = (input_data - min_val) * (amplitude_volts / (max_val - min_val)) + offset_volts
        '''

        max_val = np.iinfo(input_signal.get_dtype()).max
        min_val = np.iinfo(input_signal.get_dtype()).min

        output_data = output_data_fixed

        output_data = output_data * ((max_val - min_val) / amplitude_volts) + min_val
        output_data = output_data.astype(input_signal.get_dtype())

        output_signal = Signal(
            'data',
            output_data,
            input_signal.sample_width,
            input_signal.framerate)

        #output_signal.play()

        '''
        plt.plot(
            input_time,
            input_data,
            label='Input signal')
        plt.plot(
            output_time,
            output_data,
            label='Output signal')
        plt.plot(
            output_time_fixed,
            output_data_fixed,
            label='Output signal (fixed)')
        '''


        '''
        plt.plot(
            input_time,
            input_signal.data[:sim_length],
            label='Input signal')
        plt.plot(
            input_time[:output_data.size],
            output_signal.data,
            label='Output signal')
        plt.xlabel('Time, s')
        plt.ylabel('WAV signed 32bit')
        plt.grid(True)
        plt.legend()
        plt.show()
        '''
        return output_signal


