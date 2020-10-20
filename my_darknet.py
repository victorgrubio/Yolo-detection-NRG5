import darknet_numpy


class MyDarknet():

    def __init__(self, dirname, cfg, weights, names,
                 thresh=.5, hier_thresh=.5, nms=.45):
        self.net = darknet_numpy.load_net(
            bytes(dirname + cfg, encoding="utf-8"),
            bytes(dirname + weights, encoding="utf-8"), 0)
        self.meta = darknet_numpy.load_meta(bytes(dirname + names,
                                                  encoding="utf-8"))
        self.thresh = thresh
        self.hier_thresh = hier_thresh
        self.nms = nms

    def detect(self, np_img):
        return darknet_numpy.detect_np(
            self.net, self.meta, np_img,
            self.thresh, self.hier_thresh, self.nms)
