#! /usr/bin/env python
# -*- encoding: UTF-8 -*-

import qi
import argparse
import sys
import time
import cv2
import numpy as np
import pyvirtualcam

# Needed packages to instantiate the virtual cam
# sudo apt install v4l2loopback-dkms v4l2loopback-utils 
# pip install qi argparse pyvirtualcam numpy==1.23.5 opencv-python==4.9.0.80

# Linux commands to reload the module
# sudo rmmod v4l2loopback
# sudo modprobe v4l2loopback devices=1 video_nr=10 card_label="NAOcam" exclusive_caps=1

def main(session):
    video_service = session.service("ALVideoDevice")
    # Camera settings
    resolution = 2  # VGA (640x480)
    color_space = 11  # RGB
    fps = 15
    camera_index = 1  # Use 0 or 1 depending on the working camera

    # Subscribe to the camera
    name_id = ""
    name_id = video_service.subscribeCamera(name_id, camera_index, resolution, color_space, fps)
    print("Subscribed to camera:", name_id)

    try:
        with pyvirtualcam.Camera(width=640, height=480, fps=20) as cam:
            print("Press Ctrl+C to exit cleanly.")
            while True:
                image = video_service.getImageRemote(name_id)
                if image is None:
                    print("No image.")
                    continue

                width, height = image[0], image[1]
                array = image[6]
                img = np.frombuffer(array, dtype=np.uint8).reshape((height, width, 3))

                cam.send(img)
                cam.sleep_until_next_frame()
    except KeyboardInterrupt:
        print("\nExit requested by user.")
    finally:
        print("Releasing resources...")
        try:
            video_service.unsubscribe(name_id)
            print("Unsubscribed successfully.")
        except Exception as e:
            print("Error during unsubscribe:", e)



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
