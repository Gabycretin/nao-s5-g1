#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

# Lien pour utiliser le flux video et entrainer un modele
# https://teachablemachine.withgoogle.com/

# Needed packages to use exported model
# pip install tensorflow==2.12.1 numpy==1.23.5 opencv-python==4.9.0.80

import qi
import argparse
import sys
import time
import cv2
import numpy as np

from keras.models import load_model  # TensorFlow is required for Keras to work


def main(session):
    video_service = session.service("ALVideoDevice")
    # Camera settings
    resolution = 2  # VGA (640x480)
    color_space = 11  # RGB
    fps = 15
    camera_index = 1  # Use 0 or 1 depending on which one works

    np.set_printoptions(suppress=True)

    # Load the model
    model = load_model("keras_model.h5", compile=False)
    # Load the labels
    class_names = open("labels.txt", "r").readlines()

    subscribers = video_service.getSubscribers()
    print("Abonnements actifs :", subscribers)

    # Forcer le desabonnement de tous
    for name in subscribers:
        try:
            video_service.unsubscribe(name)
            print("Desabonne :", name)
        except Exception as e:
            print("Erreur lors du desabonnement de", name, ":", e)

    # Subscribe
    name_id = ""
    name_id = video_service.subscribeCamera(name_id, camera_index, resolution, color_space, fps)
    print("Subscribed to camera:", name_id)

    while True:
        image = video_service.getImageRemote(name_id)
        if image is None:
            print("No image.")
            continue

        width, height = image[0], image[1]
        array = image[6]
        img = np.frombuffer(array, dtype=np.uint8).reshape((height, width, 3))

        img2 = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        cv2.imshow("Robot Camera", img2)
        
        img = cv2.resize(img, (224, 224), interpolation=cv2.INTER_AREA)


        # Make the image a numpy array and reshape it to the models input shape.
        img = np.asarray(img, dtype=np.float32).reshape(1, 224, 224, 3)

        # Normalize the image array
        img = (img / 127.5) - 1

        # Predicts the model
        prediction = model.predict(img)
        index = np.argmax(prediction)
        class_name = class_names[index]
        confidence_score = prediction[0][index]

        # Print prediction and confidence score
        print("Class:", class_name[2:], end="")
        print("Confidence Score:", str(np.round(confidence_score * 100))[:-2], "%")

        # # Mise en place motion_service
        # motion_service  = session.service("ALMotion")

        # # Wake up robot
        # motion_service.wakeUp()

        # # Marcher devant 
        # motion_service.moveToward(0.5, 0.0, 0.0, [["Frequency", 1.0]])
        # time.sleep(10)
        # motion_service.stopMove()

        # # Marcher derriere
        # motion_service.moveToward(-0.5, 0.0, 0.0, [["Frequency", 1.0]])
        # motion_service.stopMove()

        # # Mettre debout
        # posture_service = session.service("ALRobotPosture")
        # posture_service.goToPosture("StandInit", 1.0)



        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("Unsubscribing...")
    video_service.unsubscribe(name_id)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", type=str, default="127.0.0.1",
                        help="Robot IP address. On robot or Local Naoqi: use '127.0.0.1'.")
    parser.add_argument("--port", type=int, default=9559,
                        help="Naoqi port number")

    args = parser.parse_args()
    session = qi.Session()
    try:
        session.connect("tcp://" + args.ip + ":" + str(args.port))
    except RuntimeError:
        print ("Can't connect to Naoqi at ip \"" + args.ip + "\" on port " + str(args.port) +".\n"
               "Please check your script arguments. Run with -h option for help.")
        sys.exit(1)
    main(session)
