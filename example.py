import caliente

in_signal = caliente.Signal(
    'file',
    '/home/endoplasm/Bitwig Studio/Projects/waltz/exported/20201226/waltz-mono.wav')

filter_circuit = caliente.Circuit(
    '/home/endoplasm/Documents/LTspiceXVII/filter_circuit.asc',
    '/home/endoplasm/.wine/drive_c/Program Files/LTC/LTspiceXVII/XVIIx64.exe')

out_signal = filter_circuit.simulate(in_signal, 9)

in_signal.play()
out_signal.play()

