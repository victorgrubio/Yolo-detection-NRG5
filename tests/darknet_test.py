import cv2
from PIL import Image
import numpy as np
import darknet


def ordered_boxes(boxes):
    new_boxes = []
    for box in boxes:
        for x, y in zip(box[1::2], box[::2]):
            new_boxes.extend([x, y])
    new_boxes = [list(new_boxes)]
    return new_boxes


if __name__ == "__main__":
    net = darknet.load_net(b"cfg/yolov3.cfg",
                           b"weights/yolov3.weights", 0)
    meta = darknet.load_meta(b"cfg/coco.data")
    img = b"data/dog.jpg"
    results = darknet.detect(net, meta, img)
    img_array = np.array(Image.open(img.decode('utf-8')))
    img_shape = img_array.shape
    categories = [i[0].decode("utf-8") for i in results]
    scores = ['{}'.format(int(i[1] * 100)) for i in results]
    boxes = [list(i[2]) for i in results]
    ord_boxes = ordered_boxes(boxes)
    norm_boxes = np.array(
        [value / img_shape[1] if index % 2 == 0 else value / img_shape[0]
         for box in boxes for index, value in enumerate(box)])
    norm_boxes = norm_boxes.reshape((len(categories), 4))
#    norm_boxes = np.delete(norm_boxes, 4, axis=0)
    print(img_shape)
    print(categories)
    print(scores)
    mixed_list = list(zip(categories, scores))
    final_list = ['{}: {}%'.format(cat, score) for cat, score in mixed_list]
    print(final_list)
    print(boxes)
    print(ord_boxes)
    print(norm_boxes)
