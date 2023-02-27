"""
PIXVAL Framework Decode Script v1.1
-----------------------------------
Script Owners:
Amanjyot Singh (amanjyot.singh@intel.com)
Bhanu Prakash (bhanu.prakash.k@intel.com)
----------------------------------------------------------------------------------------------------

sample command:
python .\decode.py 
    mandatory
    --app MFX                                           MFX, Sample Decode, FFMPEG
    --codec AVC                                         AV1, HEVC, VP9, AVC, JPEG
    --inputfile Bluesky_1080p_25fps_8bit_420_5s.264     should be in Source\<codec>
    optional
    --compare on                                        ON, OFF
    --appoptions "option1 option 2" 
    --playback false 
    --log my_logname

for more:
python .\decode.py --help
----------------------------------------------------------------------------------------------------
What's NOT yet working:
VP9 Compare Mode

version 1.1
Added supported_InputPlaybackMFX in MFX 2 command lines
Removed -no_render option
Added OTHER in supported codecs for .mp4 files & mpeg2 files support

"""
# --------------------------------------------------
# <start> setup environment ------------------------
# imports, argument parser, logger, variables ------
# --------------------------------------------------

# Import Modules
# --------------------------------------------------
#import sys
from asyncio.subprocess import PIPE, STDOUT
from asyncio.windows_utils import Popen
from genericpath import isdir, isfile
import os
import platform
import argparse
import subprocess
import logging
from shutil import copy, copyfile
import sys

# Time Stamp
# --------------------------------------------------
import datetime
from unittest import TestResult
time_TimeStamp=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
time_Start=datetime.datetime.now()

# Argument Parsing
# --------------------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument("--app", "-a", required=True, help="application to be used - MFX, FFMPEG, MDA, Sample_Decode")
ap.add_argument("--appoptions", "-appops", required=False, help="additional app commandline options")
ap.add_argument("--codec", "-c", required=True, help="codec to be decoded - AV1, HEVC, VP9, AVC, VP8, VC1, MPEG2, JPEG")
ap.add_argument("--inputfile", "-f", required=True, help="file to be decoded")
ap.add_argument("--playback", "-pb", required=False, help="playback on display on/off")
ap.add_argument("--compare", "-cmp", required=False, help="comparison of HW Decode with SW Deocde")
ap.add_argument("--log", "-l", required=False, help="custom log name, default log name is pixval*.log")
ap.add_argument("--loglevel", "-ll", required=False, help="select log level, (for future)")
ap.add_argument("--debug","-dbg", required=False, help="debug options (for future)")
ap.add_argument("--dx","-dx", required=False, help="DX Options")

#ap.add_argument("-srch", "--searchfiles" , required=False, help="search required files in repository if not present locally")
args = vars(ap.parse_args())

# Variables - Input Arguments to Command Parameters
# --------------------------------------------------
cmd_InputOperation="Decode"
cmd_InputApp=str(args['app']).upper()
cmd_InputAppOptions=str(args['appoptions'])
cmd_InputCodec=str(args['codec']).upper()
cmd_InputFile=str(args['inputfile'])
cmd_InputCompare=str(args['compare']).upper() 
cmd_InputPlayback=str(args['playback']).upper()
cmd_InputCompareFlag=False
cmd_InputPlaybackFlag=False
cmd_InputLogName=str(args['log'])
cmd_InputLogLevel=str(args['loglevel']).upper()
cmd_InputDebugOption=str(args['debug']).upper()
cmd_InputDX=str(args['dx']).upper()
errorCode_DecodeHW = -1
errorCode_DecodeSW = -1
errorCode_DecodeCompare = -1
# Variables - Directories
# --------------------------------------------------
dir_Current=os.getcwd()
dir_Source=dir_Current+"\\source\\"+cmd_InputCodec+"\\"
dir_Source_InputFile = dir_Source+cmd_InputFile
dir_Apps=dir_Current+"\\apps\\"
dir_AppSelected=dir_Apps
dir_Results=dir_Current+"\\results\\"+cmd_InputOperation+"\\"+cmd_InputCodec+"\\"+str(cmd_InputFile.split('.',1)[0])+"_"+time_TimeStamp+"\\"
dir_Logs=dir_Current+"\\logs\\"

# Create Directories
# ------------------
from pathlib import Path
#Path(dir_Results).mkdir(parents=True, exist_ok=True)
Path(dir_Logs).mkdir(parents=True, exist_ok=True)

# Supported Inputs - define
# --------------------------------------------------
supported_InputApps={'MFX':'MSDK\\mfx_player.exe','SAMPLE_DECODE':'MSDK\\sample_decode.exe','FFMPEG':'FFMPEG\\ffmpeg.exe','MDA':'MDA\\mv_decoder_adv.exe'}
supported_InputCodecs=['AV1','HEVC','VP9','AVC','VP8','VC1','MPEG2','JPEG','OTHER']
supported_InputAppsWithPlaybackControl=['MFX']
supported_InputDX=['11','12']

# Variables - Debug and Logging
# --------------------------------------------------

# Set Log Name and Log Level
if (cmd_InputLogName == "None"):
    log_FileName="pixval"
else:
    log_FileName=cmd_InputLogName
log_FileName=log_FileName+"_"+cmd_InputOperation+"_"+cmd_InputCodec+"_"+cmd_InputFile.split('.',1)[0]+"_"+time_TimeStamp+".log"
global log_File 
log_File=dir_Logs+log_FileName

if (cmd_InputLogLevel == "NONE"):
    log_Level=logging.INFO
else:
    log_Level=logging.INFO
#logging.basicConfig(filename=log_File,level=log_Level,format='%(message)s')

logger = logging.getLogger(__name__)
logger.setLevel(log_Level)
log_Formatter=logging.Formatter('%(message)s')
file_Handler = logging.FileHandler(log_File)
file_Handler.setLevel(log_Level)
file_Handler.setFormatter(log_Formatter)
stream_Handler=logging.StreamHandler()
stream_Handler.setFormatter(log_Formatter)
logger.addHandler(file_Handler)
logger.addHandler(stream_Handler)


# Variables - Random
# --------------------------------------------------
tf_Indent01=20 # Text Formatting Indent
"""
dir_Lib=dir_Current+"\\lib"
print("Lib path is",dir_Lib)
sys.path.append(dir_Lib)
from sysinfo import target_details
"""
# --------------------------------------------------
# <end> setup environment --------------------------
# --------------------------------------------------



# --------------------------------------------------
# <start> check_inputs() function ------------------
# checks the validity of input parameters ----------
# --------------------------------------------------
def check_inputs():
    global cmd_InputCompareFlag
    global cmd_InputPlaybackFlag
    global cmd_InputApp
    global cmd_InputDX
    global cmd_InputAppOptions
    global supported_InputApps
    global supported_InputDX
    global dir_AppSelected
    global log_File
    global log_Level
    errorCode_Inputs=0
    
    logger.info('\nChecking Inputs\n---------------')
    # Check App : cmd_InputApp
    if ((errorCode_Inputs==0) and (cmd_InputApp not in supported_InputApps.keys())):
        logger.error('\nError!\n------\nUnrecognised application: {}\nSupported apps are: {}'.format(cmd_InputApp,list(supported_InputApps.keys())))
        errorCode_Inputs=101
    else:
        if (os.path.isdir(dir_Apps) == True):
            dir_AppSelected=dir_Apps+supported_InputApps.get(cmd_InputApp)  
            if (os.path.isfile(dir_AppSelected) == False):
                logger.error('\nError!\n------\nMissing files:\nApplication {} not found at {}'.format(cmd_InputApp,dir_AppSelected))
                errorCode_Inputs=102
        else:
            logger.error('\nError!\n------\nMissing files:\nApplication {} not found at {}'.format(cmd_InputApp,dir_Apps))
            errorCode_Inputs=102
    
    # Check Codec : cmd_InputCodec
    if  ((errorCode_Inputs==0) and (cmd_InputCodec not in supported_InputCodecs)):
        logger.error('\nError!\n------\nUnrecognised codec: {}\nSupported codecs are:{}'.format(cmd_InputCodec,supported_InputCodecs))
        errorCode_Inputs=192
    
    # Check Input File : cmd_InputFilePath
    if ((errorCode_Inputs==0) and (os.path.isfile(dir_Source_InputFile) == False)):
        logger.error('\nError!\n------\nMissing files:\nInput file {} not found at {}'.format(cmd_InputFile,dir_Source)) 
        errorCode_Inputs=191

    # Set Playback : cmd_Playback
    if ((errorCode_Inputs==0) and ((cmd_InputPlayback == "TRUE") or (cmd_InputPlayback == "ON") or (cmd_InputPlayback == "YES"))):
        cmd_InputPlaybackFlag=True
    else:
        cmd_InputPlaybackFlag=False
    
    # Set Compare : cmd_Compare
    if ((errorCode_Inputs==0) and ((cmd_InputCompare == "TRUE") or (cmd_InputCompare == "ON") or (cmd_InputCompare == "YES"))):
        cmd_InputCompareFlag = True
    else:
        cmd_InputCompareFlag = False

    # Set DX
    if ((errorCode_Inputs==0) and (cmd_InputDX not in supported_InputDX)):
        cmd_InputDX="11"

    # Set cmd_InputAppOptions
    if ((errorCode_Inputs==0) and ((cmd_InputAppOptions == "NONE") or (cmd_InputAppOptions == "None"))):
        cmd_InputAppOptions = ""

    if (errorCode_Inputs == 0):
        logger.info('\nInfo: User inputs processed successfully, proceeding with test run.')
    else:
        logger.error('\nError! User input(s) incorrect.')

    return errorCode_Inputs
# --------------------------------------------------
# <end> check_inputs() function --------------------
# --------------------------------------------------



# --------------------------------------------------
# <start> details_test() function ------------------
# prints the test details --------------------------
# --------------------------------------------------
def details_test():
    # Print Test Details
    logger.info("\n\nTest Details\n------------")
    logger.info('{}: {}'.format('Operation'.ljust(tf_Indent01),cmd_InputOperation))
    logger.info('{}: {}'.format('Application'.ljust(tf_Indent01),cmd_InputApp))
    logger.info('{}: {}'.format('Codec'.ljust(tf_Indent01),cmd_InputCodec))
    logger.info('{}: {}'.format('Input File'.ljust(tf_Indent01),cmd_InputFile))
    logger.info('{}: {}'.format('Compare Mode'.ljust(tf_Indent01),str(cmd_InputCompareFlag)))
    logger.info('{}: {}'.format('Playback Mode'.ljust(tf_Indent01),str(cmd_InputPlaybackFlag)))
    
    # Print Directory Paths
    logger.info("\n\nDirectories\n-----------")
    logger.info('{}: {}'.format('Source Directory'.ljust(tf_Indent01),dir_Source))
    logger.info('{}: {}'.format('Result Directory'.ljust(tf_Indent01),dir_Results))
    logger.info('{}: {}'.format('App Directory'.ljust(tf_Indent01),dir_Apps))
    logger.info('{}: {}'.format('Log Directory'.ljust(tf_Indent01),dir_Logs))
    #logger.info('{} :{}'.format('Log File Name'.ljust(tf_Indent01),log_FileName))
# --------------------------------------------------
# <end> details_test() function --------------------
# --------------------------------------------------

def log_subprocess_output(pipe):
    for line in iter(pipe.readline, b''): # b'\n'-separated lines
        logging.info('got line from subprocess: %r', line)

# --------------------------------------------------
# <start> decode_hw() function ---------------------
# runs reference decoder ---------------------------
# --------------------------------------------------
def decode_hw():
#def decode_hw(cmd_InApp, cmd_InCodec, cmd_InFilePath, cmd_InFlagCompare, cmd_InFlagPlayback, cmd_OutFilePath):
    # Global Variables - new declaration
    logger.info('\n\nDecode - Hardware\n-----------------')
    global cmd_RunHW
    global dir_Results_OutputFile
    
    # Global Variables - global mapping
    global dir_AppSelected
    global dir_Source_InputFile
    global cmd_InputCodec
    global cmd_InputFile
    global cmd_InputPlaybackFlag
    global cmd_InputAppOptions
    global cmd_InputDX
    global errorCode_DecodeHW
    global dir_Results_OutputFile
    global app_ExitCode
    # Variables - Local
    errorCode_DecodeHW=-1
    dir_Results_OutputFile=dir_Results+str(cmd_InputFile.split('.',1)[0])+"_"+cmd_InputCodec+"_out.yuv"
    
    # Command Generation for MFX
    if (cmd_InputApp=="MFX"):
        supported_InputCodecsMFX={'AV1':'','HEVC':':hevc','VP9':'','AVC':':h264','VP8':'','VC1':'','MPEG2':':mpeg2','JPEG':':jpeg','OTHER':''}
        supported_InputPlaybackMFX={'True':'','False':''}
        supported_InputDXMFX={'11':'-d3d11','12':'-d3d12'}
        if  cmd_InputCodec not in supported_InputCodecsMFX:
            #logger.error("\nError!\n",cmd_InputApp,"either doesn't support or doesn't have command-line parameters defined for",cmd_InputCodec,"\nSupported codecs are:",supported_InputCodecsMFX,"\n\n")
            logger.error('\nError!\nCodec not supported.\n{} either doesnot support or doesnot have command-line parameters defined for codec: {}\nSupported codecs are:{}'.format(cmd_InputApp,cmd_InputCodec,list(supported_InputCodecsMFX.keys())))
            errorCode_DecodeHW=192
        else:
            errorCode_DecodeHW=0
        cmd_RunHW = dir_AppSelected+" -i"+supported_InputCodecsMFX.get(cmd_InputCodec)+" "+dir_Source_InputFile+supported_InputPlaybackMFX.get(cmd_InputPlaybackFlag)+" -hw -priority 1"+" "+supported_InputDXMFX.get(cmd_InputDX)+" -o "+dir_Results_OutputFile+" "+cmd_InputAppOptions
        cmd_PlaybackHW = dir_AppSelected+" -i"+supported_InputCodecsMFX.get(cmd_InputCodec)+" "+dir_Source_InputFile+supported_InputPlaybackMFX.get(cmd_InputPlaybackFlag)+" -hw -priority 1"+" "+supported_InputDXMFX.get(cmd_InputDX)+" "+cmd_InputAppOptions
    
    # Command Generation for FFMPEG
    if (cmd_InputApp=="FFMPEG"):
        print("FFMPEG commands yet to be defined.")
    
    # Command Generation for MDA
    if (cmd_InputApp=="MDA"):
        supported_InputCodecsMDA={'AV1':'av1','HEVC':'hevc','VP9':'vp9','AVC':'avc','VP8':'vp8','MPEG2':'mpeg2'}
        if  cmd_InputCodec not in supported_InputCodecsMDA:
            print ("\nError!\n",cmd_InputApp,"either doesn't support or doesn't have command-line parameters defined for",cmd_InputCodec,"\nSupported codecs are:",supported_InputCodecsMDA,"\n\n")
            errorCode_DecodeHW=192
        else:
            errorCode_DecodeHW=0
        cmd_RunHW = dir_AppSelected+" --"+supported_InputCodecsMDA.get(cmd_InputCodec)+" -i "+dir_Source_InputFile+" -o "+dir_Results_OutputFile+" "+cmd_InputAppOptions
    
    # Command Generation for SAMPLE_DECODE
    if (cmd_InputApp=="SAMPLE_DECODE"):
        supported_InputCodecsSampleDecode={'AV1':'av1','HEVC':'h265','VP9':'VP9','AVC':'h264'}
        if  cmd_InputCodec not in supported_InputCodecsSampleDecode:
            print ("\nError!\n",cmd_InputApp,"either doesn't support or doesn't have command-line parameters defined for",cmd_InputCodec,"\nSupported codecs are:",supported_InputCodecsSampleDecode,"\n\n")
            errorCode_DecodeHW=192
        #print("Inside Sample Decode")
        else:
            errorCode_DecodeHW=0
        cmd_RunHW = dir_AppSelected+" "+supported_InputCodecsSampleDecode.get(cmd_InputCodec)+" -i "+dir_Source_InputFile+" -o "+dir_Results_OutputFile+" "+cmd_InputAppOptions
        #print ("Sample Decode Command is:", cmd_RunHW)
    
    # Run cmd_RunHW here
    
    if (errorCode_DecodeHW==0):
        logger.info('HW run command line is:\n{}'.format(cmd_RunHW))
        runTest_Process = subprocess.run(cmd_RunHW,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,shell=True)
        app_ExitCode = runTest_Process.returncode
        runTest_Process_Log = runTest_Process.stdout
        print (runTest_Process_Log)
        logger.info('{}'.format(runTest_Process_Log))
        # Check for output file        
        #logger.info('\nApplication Log\n---------------')
        #logger.info('{}',p1)
        if ((app_ExitCode == 0) and (os.path.isfile(dir_Results_OutputFile))):
            errorCode_DecodeHW=0
            logger.info('\nHW Decode process completed.\n')
            if ((cmd_InputPlaybackFlag == True) and (cmd_InputApp in supported_InputAppsWithPlaybackControl)):
                runTest_Process = subprocess.run(cmd_PlaybackHW,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,shell=True)
                #print(runTest_Process.returncode)
        else:
            errorCode_DecodeHW=11
            logger.error('\nError: HW Decode failed. Please check the applicatiopn log.\n')
    else:
        logger.info('\n\nFatal Error!\nHardware Decode failed.')
    #print ("End of HW Decode")

    return errorCode_DecodeHW
    
# --------------------------------------------------
# <end> decode_hw() function -----------------------
# --------------------------------------------------



# --------------------------------------------------
# <start> decode_sw() function ---------------------
# runs reference decoder ---------------------------
# --------------------------------------------------
def decode_sw():
# Global Variables - new declaration
    global cmd_RunSW
    global dir_Results_OutputFile_SW

    # Global Variables - global mapping
    global dir_Source_InputFile
    global cmd_InputCodec
    global cmd_InputFile
    global errorCode_DecodeSW
    # Variables - Local
    errorCode_DecodeSW=0
    dir_Results_OutputFile_SW=dir_Results+str(cmd_InputFile.split('.',1)[0])+"_"+cmd_InputCodec+"_out_Ref.yuv"

    # Command Generation for Reference Decoders
    if (cmd_InputCodec=="AVC"):
        cmd_RunSW = dir_Apps+"\\Reference\\"+"ldecod.exe -p InputFile="+dir_Source_InputFile+" -p OutputFile="+dir_Results_OutputFile_SW
    elif (cmd_InputCodec=="HEVC"):
        cmd_RunSW = dir_Apps+"\\Reference\\"+"TAppDecoder.exe -b "+dir_Source_InputFile+" -o "+dir_Results_OutputFile_SW
    elif (cmd_InputCodec=="VP9"):
        cmd_RunSW = dir_Apps+"\\Reference\\"+"vpxdec.exe --rawvideo -o "+dir_Results_OutputFile_SW+" "+dir_Source_InputFile
    elif (cmd_InputCodec=="AV1"):
        cmd_RunSW = dir_Apps+"\\Reference\\"+"aomdec --rawvideo -o "+dir_Results_OutputFile_SW+" "+dir_Source_InputFile
    else:
        errorCode_DecodeSW=192
        logger.error('\nError!\nReference Decoder not defined for codec: {}\nSupported codecs are: AVC, HEVC, VP9 & AV1'.format(cmd_InputCodec))
    
    # Run cmd_RunHW here
    logger.info("\n\nDecode - Reference\n------------------")
    if (errorCode_DecodeSW==0):
        logger.info('SW run command line is:\n{}'.format(cmd_RunSW))
        #runTest_Process = subprocess.run(cmd_RunSW,shell=True)
        runTest_Process = subprocess.run(cmd_RunSW,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        runTest_Process_Log = runTest_Process.stdout
        print (runTest_Process_Log)
        logger.info('{}'.format(runTest_Process_Log))
        #print(runTest_Process.returncode)
        #errorCode_DecodeSW
        if os.path.isfile(dir_Results_OutputFile_SW):
            errorCode_DecodeSW=0
            logger.info('\nSW Decode process completed.\n')
        else:
            errorCode_DecodeSW=12
            logger.error('\nError: SW Decode output file did not get created. Please check the applicatiopn log.\n')
    else:
        logger.info('\n\nError!\nSoftware Decode failed.')
    #print ("End of SW Decode")
    return errorCode_DecodeSW
# --------------------------------------------------
# <end> decode_sw() function -----------------------
# --------------------------------------------------



# --------------------------------------------------
# <start> decode_compare() function ----------------
# compares the HW Decoder and SW (Reference) Decoder
# outputs. returned error code should convey if ----
# the compare was successful or not ----------------
# --------------------------------------------------
def decode_compare():
    # Variables - Local
    global errorCode_DecodeCompare
    errorCode_DecodeCompare=0
    byte_position=0
    logger.info("\n\nDecode - Compare\n----------------")
    fp1 = open(dir_Results_OutputFile, "rb")
    fp2 = open(dir_Results_OutputFile_SW, "rb")

    # Checking if Files are opened for reading
    if (fp1 == None or fp2 == None):
        logger.error("Error : Files not open\n")
        errorCode_DecodeCompare=13
    else : 
        logger.info("Files are opened\n")

    # Validating the file size - If any of the file is empty
    head1=fp1.tell()
    fp1.seek(2)
    tail1=fp1.tell()

    head2=fp2.tell()
    fp2.seek(2)
    tail2=fp2.tell()

    if ( (head1 == tail1) or (head2 == tail2) ):
        if ( head1 == tail1 ):
            logger.error("FAIL : HW Decoded file is Empty\n")
            errorCode_DecodeCompare=14
        if ( head2 == tail2 ):
            logger.error("FAIL : Reference Decoded file is Empty\n")
            errorCode_DecodeCompare=15
        
        return errorCode_DecodeCompare

    fp1.seek(0)
    fp2.seek(0)

    # Validating equal file sizes
    fp1.seek(0,2)
    size1=fp1.tell()
    fp2.seek(0,2)
    size2=fp2.tell()

    if ( size1 != size2 ):
        errorCode_DecodeCompare=1
        logger.error(" Reference & HW File size not matching \n")
        #return errorCode_DecodeCompare
        #break

    else : 
        #logger.info("Size of file 1 : ", size1 , ", Size of file 2 : ", size2 , "\n")
        logger.info('Size of file 1 : {} , Size of file 2 : {} \n'.format(size1,size2))
        
        # Comparing byte by byte
        #fp1 = open("file1", "rb")
        #fp2 = open("file2", "rb")
        fp1.seek(0)
        fp2.seek(0)
        byte1=fp1.read(1)
        byte2=fp2.read(1)

        while ( byte1 and byte2 ):
            if ( byte1 != byte2):
                errorCode_DecodeCompare=1 #Miscompare
                logger.error('First Mismatch: {} {}'.format(byte1,byte2))
                logger.error('FAIL : Error at byte position: {} \n'.format(byte_position))
                break

            byte_position+=1
            byte1=fp1.read(1)
            byte2=fp2.read(1)

        if (errorCode_DecodeCompare == 0):
            logger.info("PASS : No mismatch found between the files\n")
            logger.info('End position: {} \n'.format(byte_position))

        fp1.close()
        fp2.close()
        logger.info("\nClosed the files\n")
        #return 0


    #fp1.close()
    #fp2.close()

    
    if (errorCode_DecodeCompare==0):
        print("Compare Successful.")
    else:
        print("Compare Failed.")

    return errorCode_DecodeCompare
    
# --------------------------------------------------
# <end> decode_compare() function ------------------
# --------------------------------------------------


# --------------------------------------------------
# <start> details_result() function ----------------
# prints result summary ----------------------------
# Pass or Fail results to be added -----------------
# --------------------------------------------------
def details_result():
    global exitCode
    global errorCode_DecodeHW
    global errorCode_DecodeSW
    global errorCode_DecodeCompare
    global cmd_InputCompareFlag
    time_Stop=datetime.datetime.now()
    time_Elapsed=time_Stop-time_Start
    logger.info('\n\nResult Summary\n--------------')
    # 0 = Pass, 1 = Fail, -1 = Unknown Error, Error
    errorCodes={0:'Pass',1:'Fail',-1:'Unknown Error'}
    if (exitCode not in errorCodes):
       testResult='Error'
    else: 
        testResult=errorCodes.get(exitCode)
    
    if (errorCode_DecodeHW not in errorCodes):
       testResult_DecodeHW='Error'
    else: 
        testResult_DecodeHW=errorCodes.get(errorCode_DecodeHW)

    if (cmd_InputCompareFlag == True):
        if (errorCode_DecodeSW not in errorCodes):
            testResult_DecodeSW='Error'
        else: 
            testResult_DecodeSW=errorCodes.get(errorCode_DecodeSW)

        if (errorCode_DecodeCompare not in errorCodes):
            testResult_DecodeCompare='Error'
        else: 
            testResult_DecodeCompare=errorCodes.get(errorCode_DecodeCompare)

    logger.info('{}: {}'.format('Test Result'.ljust(tf_Indent01),testResult))
    logger.info('- - - - - - - - - - - - - - - - - - - - - - - - -')
    logger.info('{}: {}'.format('HW Decode'.ljust(tf_Indent01),testResult_DecodeHW))
    if (cmd_InputCompareFlag == True):
        logger.info('{}: {}'.format('SW Decode'.ljust(tf_Indent01),testResult_DecodeSW))
        logger.info('{}: {}'.format('Compare'.ljust(tf_Indent01),testResult_DecodeCompare))
    logger.info('- - - - - - - - - - - - - - - - - - - - - - - - -')
    logger.info('{}: {}'.format('Start Time'.ljust(tf_Indent01),time_Start))
    logger.info('{}: {}'.format('Stop Time'.ljust(tf_Indent01),time_Stop))
    logger.info('{}: {}'.format('Total Run Time'.ljust(tf_Indent01),time_Elapsed))
    logger.info('- - - - - - - - - - - - - - - - - - - - - - - - -')
    logger.info('\n><><><\npixVal')
# --------------------------------------------------
# <end> details_result() function ------------------
# --------------------------------------------------




# --------------------------------------------------
# <start> details_system() function ----------------
# prints details of the target system --------------
# --------------------------------------------------
def details_system():
    logger.info("\n\nSystem Details\n--------------")
    logger.info('{}: {}'.format('System Name'.ljust(tf_Indent01),platform.node()))
    logger.info('{}: {}'.format('Operating System'.ljust(tf_Indent01),platform.platform()))
    #Add GFX Driver Version
# --------------------------------------------------
# <end> details_system() function ------------------
# --------------------------------------------------



# --------------------------------------------------
# <start> fain() function --------------------------
# --------------------------------------------------
if __name__ == "__main__":
    logger.info('pixVal\n><><><')
    logger.info('{}'.format(args))
    global exitCode
    exitCode = -1 #default = unknown issue
    exitCode=check_inputs()
    #print("Input Flag is:",flag_Inputs)
    if (exitCode == 0):
        Path(dir_Results).mkdir(parents=True, exist_ok=True)
        details_system()
        details_test()
        # call the regkey batch file to - getting the driver key path - delete DXVA folder - recreate the DXVA folder
        # variable to capture the return fromm batch file - the DXVA path
        exitCode=decode_hw()
        if (exitCode==0):
            if ((cmd_InputCompareFlag==True)):
                exitCode=decode_sw()
                if((exitCode==0)):
                    exitCode=decode_compare()
                else:#If Reference Decoder Failed.
                    #exitCode=12
                    logger.error('Error: Can not compare the outputs.')
        else:   #if HW Decoder failed.
            logger.error('Error: HW Decoder run unsuccessful.\n')
        # call the regkey batch file to - copy the newly added dwords in DXVA & DXVA Report regkeys to a text file.
    else:
        logger.error('\nError: Please address the user input error(s) above and try again.')
    details_result()
    
    # Copy the log file from Log direcotry to Results direcotry
    # If there is error in input options then Result directory would not have been created.
    if (os.path.isdir(dir_Results) == True):
        copy(log_File,dir_Results)
    print("\n\nExecution done...\n\n")
    sys.exit(exitCode)
# --------------------------------------------------
# <end> main() function ----------------------------
# --------------------------------------------------

"""
End of the Decode Script

"""
