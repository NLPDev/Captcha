

from keras.models import load_model
from helpers import resize_to_fit
from imutils import paths
from imutils import perspective
import numpy as np
import imutils
import cv2
import pickle

import pytesseract


def crop_minAreaRect(img, rect):

    # rotate img
    angle = rect[2]
    rows,cols = img.shape[0], img.shape[1]
    M = cv2.getRotationMatrix2D((cols/2,rows/2),angle,1)
    img_rot = cv2.warpAffine(img,M,(cols,rows))

    # rotate bounding box
    rect0 = (rect[0], rect[1], 0.0)
    box = cv2.boxPoints(rect0)
    pts = np.int0(cv2.transform(np.array([box]), M))[0]
    pts[pts < 0] = 0

    # crop
    img_crop = img_rot[pts[1][1]:pts[0][1],
                       pts[1][0]:pts[2][0]]

    print(pytesseract.image_to_string(img_crop))

    return img_crop

def rotate_image(mat, angle):

    height, width = mat.shape[:2]
    image_center = (width/2, height/2)

    rotation_mat = cv2.getRotationMatrix2D(image_center, angle, 1.)

    abs_cos = abs(rotation_mat[0,0])
    abs_sin = abs(rotation_mat[0,1])

    bound_w = int(height * abs_sin + width * abs_cos)
    bound_h = int(height * abs_cos + width * abs_sin)

    rotation_mat[0, 2] += bound_w/2 - image_center[0]
    rotation_mat[1, 2] += bound_h/2 - image_center[1]

    rotated_mat = cv2.warpAffine(mat, rotation_mat, (bound_w, bound_h))
    return rotated_mat


# MODEL_FILENAME = "captcha_model.hdf5"
# MODEL_LABELS_FILENAME = "model_labels.dat"
CAPTCHA_IMAGE_FOLDER = "generated_captcha_images"


# Load up the model labels (so we can translate model predictions to actual letters)
# with open(MODEL_LABELS_FILENAME, "rb") as f:
#     lb = pickle.load(f)

# Load the trained neural network
# model = load_model(MODEL_FILENAME)

# Grab some random CAPTCHA images to test against.
# In the real world, you'd replace this section with code to grab a real
# CAPTCHA image from a live website.
captcha_image_files = list(paths.list_images(CAPTCHA_IMAGE_FOLDER))
# captcha_image_files = np.random.choice(captcha_image_files, size=(10,), replace=False)

# loop over the image paths
for image_file in captcha_image_files:
    # print("afd")
    # Load the image and convert it to grayscale
    image = cv2.imread(image_file)
    im=image


    image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Add some extra padding around the image
    # image = cv2.copyMakeBorder(image, 20, 20, 20, 20, cv2.BORDER_REPLICATE)

    # threshold the image (convert it to pure black and white)
    thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]

    # find the contours (continuous blobs of pixels) the image
    contours = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Hack for compatibility with different OpenCV versions
    contours = contours[0] if imutils.is_cv2() else contours[1]

    letter_image_regions = []

    # Now we can loop through each of the four contours and extract the letter
    # inside of each one
    for contour in contours:
        # Get the rectangle that contains the contour
        (x, y, w, h) = cv2.boundingRect(contour)

        # cv2.rectangle(im, (x, y), (x+w, y+h), (0, 255, 0), 3)

        peri=cv2.arcLength(contour, True)


        box=cv2.minAreaRect(contour)

        crop=crop_minAreaRect(im, box)


        print(box)
        box=cv2.BoxPoint(box) if imutils.is_cv2() else cv2.boxPoints(box)

        box=np.array(box, dtype="int")

        box=perspective.order_points(box)

        cv2.imshow("cropped", crop)
        cv2.waitKey(0)

        cv2.drawContours(im, [box.astype("int")], -1, (0, 255, 0), 2)

        # approx=cv2.approxPolyDP(contour, 0.02*peri, True)

        # cv2.drawContours(im, [approx], -1, (255, 0, 0), 2)



        cv2.imshow("contour", im)
        cv2.waitKey(0)

        # Compare the width and height of the contour to detect letters that
        # are conjoined into one chunk
        if w / h > 1.25:
            # This contour is too wide to be a single letter!
            # Split it in half into two letter regions!
            half_width = int(w / 2)
            letter_image_regions.append((x, y, half_width, h))
            letter_image_regions.append((x + half_width, y, half_width, h))
        else:
            # This is a normal letter by itself
            letter_image_regions.append((x, y, w, h))

    # If we found more or less than 4 letters in the captcha, our letter extraction
    # didn't work correcly. Skip the image instead of saving bad training data!

    # cv2.imshow("Image", im)
    # cv2.waitKey(0)

    # if len(letter_image_regions) != 4:
    #     continue



    # Sort the detected letter images based on the x coordinate to make sure
    # we are processing them from left-to-right so we match the right image
    # with the right letter
    letter_image_regions = sorted(letter_image_regions, key=lambda x: x[0])

    # Create an output image and a list to hold our predicted letters
    output = cv2.merge([image] * 3)
    predictions = []

    # loop over the lektters
    for letter_bounding_box in letter_image_regions:
        # Grab the coordinates of the letter in the image
        x, y, w, h = letter_bounding_box

        # Extract the letter from the original image with a 2-pixel margin around the edge
        letter_image = image[y:y + h, x:x + w+2]

        # cv2.imshow("letter", letter_image)


        # print(pytesseract.image_to_string(letter_image))

        # cv2.waitKey(0)

        # Re-size the letter image to 20x20 pixels to match training data
        letter_image = resize_to_fit(letter_image, 20, 20)

        # print(pytesseract.image_to_string(letter_image))

        # Turn the single image into a 4d list of images to make Keras happy
        letter_image = np.expand_dims(letter_image, axis=2)
        letter_image = np.expand_dims(letter_image, axis=0)

        # Ask the neural network to make a prediction
        # prediction = model.predict(letter_image)

        # Convert the one-hot-encoded prediction back to a normal letter
        # letter = lb.inverse_transform(prediction)[0]
        # predictions.append(letter)

        # draw the prediction on the output image
        cv2.rectangle(output, (x - 2, y - 2), (x + w + 4, y + h + 4), (0, 255, 0), 1)
        # cv2.putText(output, letter, (x - 5, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    # Print the captcha's text
    # captcha_text = "".join(predictions)
    # print("CAPTCHA text is: {}".format(captcha_text))

    # Show the annotated image
    # cv2.imshow("Output", output)
    # cv2.waitKey(0)


