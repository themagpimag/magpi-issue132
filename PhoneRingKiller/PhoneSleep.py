#!/usr/bin/python3
#
# This program uses two GPIO pins to control a telephone ring suppressor
# circuit.  Two command line parameters determine the wake and sleep times
# in the (HH * 100) + MM format.  To Wake at 7:15AM and Sleep at 10:45PM, start
# the program with this command line:
# ./PhoneSleep.py 715 2245
# The range of both SleepTime and WakeTime is 0 to 2359
#
from datetime import *              #datetime functions
import sys                          #Needed for argv command line args
import RPi.GPIO as GPIO             #GPIO functions
import time                         #time.sleep function
GPIO.setwarnings(False)             #Disable warnings on relaunch
# The input is on GPIO pin 23 configured as an input with a pullup resistor
In=23                               #Input on Pin 23
GPIO.setmode(GPIO.BCM)              #Use Broadcom (gpioxx) pin numbers
GPIO.setup(In, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# The output is on GPIO pin 18 configured as an output
Out=18                              #Output on Pin 18
GPIO.setup(Out, GPIO.OUT)           #Configure as an output
Sleeping = 0                        # Start in Awake mode
GPIO.output(Out, Sleeping)          #Default state is Awake
WakeTime = 730                      #Default WakeTime 7:30AM
SleepTime = 2245                    #Default SleepTime 10:45PM
argc = len(sys.argv)                #Get the number of commmand line args
if (argc > 2):                      #If 2nd command line argument exists
    try:
        ValidTime = abs(int(sys.argv[2])) #Get SleepTime 
        if (((ValidTime % 100) < 60) and (int(ValidTime / 100) < 24)):
            SleepTime = ValidTime   #Only use valid sleep times
    except (NameError, SyntaxError, ValueError): #Keep default on error
        ValidTime = 0               #Handle Exception
if (argc > 1):                      #If 1st command line argument exists
    try:
        ValidTime = abs(int(sys.argv[1])) #Get WakeTime 
        if (((ValidTime % 100) < 60) and (int(ValidTime / 100) < 24)):
            WakeTime = ValidTime     #Only use valid wake times
    except (NameError, SyntaxError, ValueError): #Keep default on error
        ValidTime = 0                #Handle Exception
# Show the WakeTime and SleepTime settings
CurrentTime = datetime.now()        #Get CurrentTime
iHour = int(CurrentTime.strftime("%H"))    #Extract integer hour
iMinute = int(CurrentTime.strftime("%M"))  #Extract integer minute
OldTime = (iHour * 100) + iMinute   #Combine into (HH * 100) + MM format
sTime = CurrentTime.strftime("%H:%M") #String value of time
print ("Now %s, Wake at %04d, Sleep at %04d" % (sTime, WakeTime, SleepTime))
# Initial state for integer variables
HoldDown = 0                        #Assume button not pressed to start
LockOut = 0                         #Only LockOut when button pressed
FirstLoop = 1                       #On first loop sync state to Sleep/Wake
while 1:                            #Main loop never ends
    CurrentTime = datetime.now()    #Get CurrentTime on each loop
    iHour = int(CurrentTime.strftime("%H"))    #Extract integer hour
    iMinute = int(CurrentTime.strftime("%M"))  #Extract integer minute
    iTime = (iHour * 100) + iMinute #Combine into (HH * 100) + MM format
    sTime = CurrentTime.strftime("%H:%M") #String value of time
    # Sometimes on cold boot the program starts before NTP time gets updated
    DeltaTime = abs(iTime - OldTime) #Detect NTP time updates.
    # Detect abnormal time changes (Hourly and Daily Wrap changes are normal)
    if ((DeltaTime > 1) and (DeltaTime != 41) and (DeltaTime != 2359)): 
        FirstLoop = 1               # Re-sync sleep state to Sleep/Wake times
        print("Time updated, Now %s" % sTime) #Show updated time
    #
    # Synchronize the sleep state with CurrentTime when program first starts
    #
    if (FirstLoop == 1):            #FirstLoop / Which range is non-wrapping
        if (WakeTime < SleepTime):  #Wake to Sleep times non-wrapping
            if ((iTime >= WakeTime) and (iTime < SleepTime)):
                Sleeping = 0        #in-range state is awake
            else:
                Sleeping = 1        #out-of-range state is sleep
        else:                       #Sleep to Wake times non-wrapping
            if ((iTime >= SleepTime) and (iTime < WakeTime)):
                Sleeping = 1        #in-range state is sleep
            else:
                Sleeping = 0        #out-of-range state is awake
        #Now show state and output to port
        GPIO.output(Out,Sleeping)
        if (Sleeping == 1):
            print ("At %s sync to sleep state" % sTime)
        else:
            print ("At %s sync to wake state" % sTime)
    FirstLoop = 0                   #Clear FirstLoop flag after syncing
    #
    # Toggle the Sleeping state on debounced button press. Input Button state.
    #
    button = GPIO.input(In)         #0=Pressed, 1=Released
    # Debounce the button by counting HoldDown time
    if (button == 0):               #When button is pressed
        if (HoldDown < 3):          #Limit HoldDown
            HoldDown += 1           #increment to 3
    else:                           #When button is released
        if (HoldDown > 0):          #Limit HoldDown
            HoldDown -= 1           #decrement to 0
        if (HoldDown == 0):         #Fully released when HoldDown reaches 0
            LockOut = 0             #Clear LockOut when fully released
    # When HoldDown first reaches 3 LockOut and toggle Sleeping state
    if ((HoldDown == 3) and (LockOut == 0)):
        LockOut = 1                 #LockOut till button fully released
        Sleeping ^= 1               #Toggle sleeping state
        GPIO.output(Out,Sleeping)   #Output to GPIO pin
        if (Sleeping == 1):
            print ("At %s toggle to sleep state" % sTime)
        else:
            print ("At %s toggle to wake state" % sTime)
    #
    # Switch to Sleeping at SleepTime and Awake at WakeTime
    #
    # At transition to SleepTime turn on sleep mode
    if ((OldTime != iTime) and (iTime == SleepTime)): #SleepTime Transition 
        Sleeping = 1
        GPIO.output(Out,Sleeping)   #Output to GPIO port
        print("At %s switching to sleep state" % sTime)
    # At transistion to WakeTime turn off sleep mode
    if ((OldTime != iTime) and (iTime == WakeTime)):  #WakeTime Transition
        Sleeping = 0
        GPIO.output(Out,Sleeping)   #Output to GPIO port
        print("At %s switching to wake state" % sTime)
    OldTime = iTime                 #Update transition detector
    # Now sleep for 20 milliseconds
    time.sleep(0.02)                #Allow other processes some time
