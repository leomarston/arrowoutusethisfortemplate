"""Board pitch from a lossless shot: periodicity of the ink (dark px) column + row profiles (autocorrelation peak),
validated on start shots of known pitch. Usage: pitchest.py SHOT... -> prints pitch estimates (pt)."""
import sys
import numpy as np
from PIL import Image
def est(path):
    im = np.array(Image.open(path).convert('RGB')).astype(float); k = im.shape[1] / 393
    D = (im.mean(2) < 100)[int(150 * k):int(760 * k)]
    res = []
    for prof in (D.sum(0), D.sum(1)):
        p = prof - prof.mean(); ac = np.correlate(p, p, 'full')[len(p) - 1:]; ac /= ac[0]
        lo = int(8 * k); hi = int(60 * k)
        j = lo + int(np.argmax(ac[lo:hi]))
        # parabolic refine
        y0, y1, y2 = ac[j - 1], ac[j], ac[j + 1]; dj = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2)
        res.append(((j + dj) / k, ac[j]))
    return res
for f in sys.argv[1:]:
    r = est(f); print(f, ' x-period %.2f pt (ac %.2f)  y-period %.2f pt (ac %.2f)' % (r[0][0], r[0][1], r[1][0], r[1][1]))
