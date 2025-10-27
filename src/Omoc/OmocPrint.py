'''
Created on Oct 27, 2025

@author: matze
'''
import OmocImgKiosk

#simple script that saves the omoc imag img to a file so it can be used by impressive.

def run():
    imgIO = OmocImgKiosk.render_image()
    with open("omoc.png","wb") as fileImage:
        fileImage.write(imgIO.read())
    

if __name__ == '__main__':
    run()