#########################################
# Project   : ARFF to CSV converter     #
# Created   : 10/01/17 11:08:06         #
# Author    : haloboy777                #
# Licence   : MIT                       #
#########################################


##### 自分で編集しました（ディレクトリ内にarffToCsv.pyを入れなくてもいいようにした）######

# Importing library
import os

# Getting all the arff files from the current directory
files = [arff for arff in os.listdir('./speech_wav') if arff.endswith(".arff")]
files = [arff.replace('.arff', '') for arff in files]

# Function for converting arff list to csv list
def toCsv(content):
    data = False
    header = ""
    newContent = []
    for line in content:
        if not data:
            if "@attribute" in line:
                attri = line.split()
                columnName = attri[attri.index("@attribute")+1]
                header = header + columnName + ","
            elif "@data" in line:
                data = True
                header = header[:-1]
                header += '\n'
                newContent.append(header)
        else:
            newContent.append(line)
    return newContent

# Main loop for reading and writing files
for file in files:
    with open("./speech_wav/{}.arff".format(file) , "r") as inFile:
        content = inFile.readlines()
        #name,ext = os.path.splitext(inFile.name)
        new = toCsv(content)
        with open("./speech_wav/{}.csv".format(file), "w") as outFile:
            outFile.writelines(new)
