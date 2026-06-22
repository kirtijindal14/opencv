import cv2
import sys

img = cv2.imread('lena.jpg')
if img is None:
    sys.exit("Error: image file missing or path invalid.")

gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
cv2.imshow('Color', img)
cv2.imshow('Grayscale', gray_img)
cv2.waitKey(0)
cv2.destroyAllWindows()
