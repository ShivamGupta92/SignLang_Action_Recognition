#!/usr/bin/env python

"""
create lexicon info.

"""

import sys
from optparse import OptionParser
from lexicon import Lexicon
from string import join

class bimap(dict):
    def __init__(self):
        super(bimap,self).__init__()
        self.val2key={}

    def __setitem__(self, key, val):
        super(bimap,self).__setitem__(key,val)
        self.val2key[val]=key

    def getKey(self, val):
        return self.val2key[val]

    def __str__(self):
        return "key2val="+super(bimap,self).__str__()+" val2key="+self.val2key.__str__()

class Record:
    def __init__(self):
        self.recordid=-1
        self.classid=-1
        self.classname=""
        self.recordname=""
        self.video=""
        self.orth=""
        self.states=""
        self.evaltokens=[]    
    def __str__(self):
        return str(self.classid)+";"+self.classname+";"+self.recordname+";"+self.video+";"+self.orth+";"+str(self.states)+";"+join(self.evaltokens,";")

def main(argv):
    defaultEncoding     = "utf8"   
    usage="usage: %prog [options] <class-info> <record-info> <outfile>\n " + __doc__
    optionParser = OptionParser(usage = usage)
    optionParser.add_option("-E", "--encoding", default=defaultEncoding, dest="encoding",
                            help="encoding ["+defaultEncoding+"]")
    optionParser.add_option("-v", "--verbose", dest="verbose", action="store_true")
    (options, args) = optionParser.parse_args()

    if len(args) != 3 :
        optionParser.error("incorrect number of arguments %d" % len(args))
        sys.exit()

    #set filenames
    classinfoFilename=args[0]
    recordinfoFilename=args[1]
    lexiconinfoFilename=args[2]

    #read calss IDs and structure information: e.g. 1;car1_;1;50;51;52
    classinfoFile = open(classinfoFilename, 'r')
    classTokens=bimap()
    evalTokens={}
    for line in classinfoFile:
        splitlist = unicode(line[:-1], options.encoding).split(';')
        classTokens[splitlist[0]] = splitlist[1]
        evalTokens[splitlist[0]]  = splitlist[2:]

    #print classTokens
    #print evalTokens
    

    #read record IDs and structure information
    recordinfoFile = open(recordinfoFilename, 'r')
    firstLine = recordinfoFile.readline()[:-1]
    fieldList = unicode(firstLine, options.encoding).split(';')
    if options.verbose:
        print "structure:", firstLine, fieldList
    fieldMap={}
    fieldId=0
    for field in fieldList:
        fieldMap[field]=fieldId
        if options.verbose :
            print field, fieldId
        fieldId+=1

    #check required fields
    if not fieldMap.has_key('name') or not fieldMap.has_key('video') or not fieldMap.has_key('orth'):
        print "ERROR: one or more required fields [name,video, and/or orth] are missing."
        keys = fieldMap.keys()
        keys.sort
        for key in keys:
            print key, fieldMap[key]
        sys.exit()

    #create recordings from record info file
    recordings=[]
    currentL1O=0
    for line in recordinfoFile:
        splitlist = unicode(line, options.encoding).split(';')
        if options.verbose:
            for i in range(0,len(splitlist)):
                print i, splitlist[i]
        if len(splitlist) < len(fieldMap):
            if options.verbose:
                print "ERROR: data row '%s' is invalid and will be discarded." % (splitlist)
        else:            
            recordname=splitlist[fieldMap['name']]
            classname=recordname.split('-')[0]
            try:
                classid=classTokens.getKey(classname)
            except KeyError:
                try:
                    if classname[:-1] == "what":
                        classname="what_"
                    elif classname[:-1] == "ixfa":
                        classname="ixfar"
                    elif classname == "ixfal":
                        classname="ixfar"
                    else:
                        sys.exit("ERROR: unknwon classname="+classname)
                    classid=classTokens.getKey(classname)
                except KeyError:
                    print "ERROR: classname="+classname+" has no class key"
                    classid="UNKNOWNID"
            video=splitlist[fieldMap['video']]
            orth=splitlist[fieldMap['orth']]
            states=1
            if(fieldMap.get("states") != None) :
                states=int(splitlist[fieldMap['states']])
            evaltokens=evalTokens[classid]
            
            # update recordings table then iterate again over it
            newRec=Record()
            newRec.recordid=currentL1O
            newRec.classid=classid
            newRec.classname=classname
            newRec.recordname=recordname
            newRec.video=video
            newRec.orth=orth
            newRec.states=states
            newRec.evaltokens=evaltokens
            recordings.append(newRec)
            currentL1O+=1

    currentL1O=0
    currentPartition=0
    for recording in recordings:
        currentPartition=((currentL1O-1)%len(recordings))+1
        print "L1O="+str(currentL1O), "partition="+str(currentPartition), recording

        wordLex = Lexicon(True, False) ##add silence, no coraticalution
        wordLex.verbose = options.verbose
        
        # create lexicon which contains all word phonemes and lemmata except the current L1O word lemmata
        # and get pronunciations for current recording.orth
        pronunciationPhons=[]
        pronunciationStates=[]
        pronunciationRepetitions=[]
        for pronrecording in recordings:
            wordLex.addPhoneme(pronrecording.orth, pronrecording.states) # this is necessary to have an ordered phoneme list
            if pronrecording.classid in recording.evaltokens:            # i.e. we have a similar pronunced class for currentc L1O
                if pronrecording.recordid != recording.recordid:
                    pronunciationPhons.append(pronrecording.orth)
                    pronunciationStates.append(pronrecording.states)
                    pronunciationRepetitions.append(pronrecording.orth.count('+'))
            else:
                wordLex.add(pronrecording.orth, [pronrecording.orth], [pronrecording.states], [pronrecording.orth.count('+')],
                            addCoarticulation=False, checkPhoneme=False, checkLemma=True)                      

        # now also add the current L10 with only similar pronunced phon sequences
        wordLex.add(recording.orth, pronunciationPhons, pronunciationStates, pronunciationRepetitions,
                    addCoarticulation=False, checkPhoneme=False, checkLemma=True)
        wordLex.save(lexiconinfoFilename+"."+str(currentPartition))
        currentL1O+=1

if __name__ == "__main__":
    main(sys.argv)
