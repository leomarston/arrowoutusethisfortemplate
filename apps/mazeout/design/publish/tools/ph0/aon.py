import wave, numpy as np, sys
w = wave.open(sys.argv[1]); sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float) / 32768
win = int(0.005 * sr)
e = np.array([np.sqrt((a[i:i+win]**2).mean()) for i in range(0, len(a) - win, win)])
db = 20 * np.log10(e + 1e-9)
print('dur %.2f max dB %.1f' % (len(a) / sr, db.max()))
segs = []; on = None
for i, v in enumerate(db):
    if v > -45 and on is None: on = i
    if v <= -50 and on is not None:
        segs.append((on * 0.005, i * 0.005, db[on:i].max())); on = None
if on is not None: segs.append((on * 0.005, len(db) * 0.005, db[on:].max()))
for s_, e_, m in segs: print('sound %.3f-%.3f peak %.1f dB' % (s_, e_, m))
