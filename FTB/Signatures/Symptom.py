'''
Symptom

Represents one symptom which may appear in a crash signature.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

from abc import ABCMeta, abstractmethod
import json
from FTB.Signatures import JSONHelper
from FTB.Signatures.Matchers import StringMatch, NumberMatch

class Symptom():
    '''
    Abstract base class that provides a method to instantiate the right sub class.
    It also supports generating a CrashSignature based on the stored information.
    '''
    __metaclass__ = ABCMeta
    
    def __init__(self, jsonObj):
        # Store the original source so we can return it if someone wants to stringify us
        self.jsonsrc = json.dumps(jsonObj, indent=2)
        self.jsonobj = jsonObj
    
    def __str__(self):
        return self.jsonsrc
    
    @staticmethod
    def fromJSONObject(obj):
        '''
        Create the appropriate Symptom based on the given object (decoded from JSON)
        
        @type obj: map
        @param obj: Object as decoded from JSON
        
        @rtype: Symptom
        @return: Symptom subclass instance matching the given object
        '''
        if not "type" in obj:
            raise RuntimeError("Missing symptom type in object")
        
        stype = obj["type"]
        
        if (stype == "output"):
            return OutputSymptom(obj)
        elif (stype == "stackFrame"):
            return StackFrameSymptom(obj)
        elif (stype == "stackSize"):
            return StackSizeSymptom(obj)
        elif (stype == "crashAddress"):
            return CrashAddressSymptom(obj)
        elif (stype == "instruction"):
            return InstructionSymptom(obj)
        elif (stype == "testcase"):
            return TestcaseSymptom(obj)
        elif (stype == "stackFrames"):
            return StackFramesSymptom(obj)
        else:
            raise RuntimeError("Unknown symptom type: %s" % type)

    @abstractmethod
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return
    
    
class OutputSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.output = StringMatch(JSONHelper.getObjectOrStringChecked(obj, "value", True))
        self.src = JSONHelper.getStringChecked(obj, "src")
        
        if self.src != None:
            self.src = self.src.lower()
            if self.src != "stderr" and self.src != "stdout":
                raise RuntimeError("Invalid source specified: %s" % self.src)
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        checkedOutput = []
        
        if self.src == None:
            checkedOutput.extend(crashInfo.rawStdout)
            checkedOutput.extend(crashInfo.rawStderr)
        elif (self.src == "stdout"):
            checkedOutput = crashInfo.rawStdout
        else:
            checkedOutput = crashInfo.rawStderr
            
        for line in checkedOutput:
            if self.output.matches(line):
                return True
            
        return False
    
class StackFrameSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.functionName = StringMatch(JSONHelper.getNumberOrStringChecked(obj, "functionName", True))        
        self.frameNumber = JSONHelper.getNumberOrStringChecked(obj, "frameNumber")

        if self.frameNumber != None:
            self.frameNumber = NumberMatch(self.frameNumber)
        else:
            # Default to 0
            self.frameNumber = NumberMatch(0)
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        
        for idx in range(len(crashInfo.backtrace)):
            # Not the most efficient way for very long stacks with a small match area
            if self.frameNumber.matches(idx):
                if self.functionName.matches(crashInfo.backtrace[idx]):
                    return True
        
        return False

class StackSizeSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.stackSize = NumberMatch(JSONHelper.getNumberOrStringChecked(obj, "size", True))
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return self.stackSize.matches(len(crashInfo.backtrace))
    
class CrashAddressSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.address = NumberMatch(JSONHelper.getNumberOrStringChecked(obj, "address", True))
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        # In case the crash address is not available,
        # the NumberMatch class will return false to not match.
        return self.address.matches(crashInfo.crashAddress)
    
class InstructionSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.registerNames = JSONHelper.getArrayChecked(obj, "registerNames")
        self.instructionName = JSONHelper.getObjectOrStringChecked(obj, "instructionName")
        
        if self.instructionName != None:
            self.instructionName = StringMatch(self.instructionName)
        elif self.registerNames == None or len(self.registerNames) == 0:
            raise RuntimeError("Must provide at least instruction name or register names")
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        if crashInfo.crashInstruction == None:
            # No crash instruction available, do not match
            return False
        
        if self.registerNames != None:
            for register in self.registerNames:
                if not register in crashInfo.crashInstruction:
                    return False
        
        if self.instructionName != None:
            if not self.instructionName.matches(crashInfo.crashInstruction):
                return False
        
        return True

class TestcaseSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.output = StringMatch(JSONHelper.getObjectOrStringChecked(obj, "value", True))
        
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        
        # No testcase means to fail matching
        if crashInfo.testcase == None:
            return False
        
        testLines = crashInfo.testcase.splitlines()
            
        for line in testLines:
            if self.output.matches(line):
                return True
            
        return False
    
class StackFramesSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.functionNames = []
        
        rawFunctionNames = JSONHelper.getArrayChecked(obj, "functionNames", True)
        
        for fn in rawFunctionNames:
            self.functionNames.append(StringMatch(fn))
        
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
            
        return StackFramesSymptom._match(crashInfo.backtrace, self.functionNames)
    
    def diff(self, crashInfo):
        if self.matches(crashInfo):
            return (0, None)
        
        for depth in range(1,4):
            (bestDepth, bestGuess) = StackFramesSymptom._diff(crashInfo.backtrace, self.functionNames, 0, 1, depth)
            if bestDepth != None:
                guessedFunctionNames = [repr(x) for x in bestGuess]
                
                # Remove trailing wildcards as they are of no use
                while guessedFunctionNames and (guessedFunctionNames[-1] == '?' or guessedFunctionNames[-1] == '???'):
                    guessedFunctionNames.pop()
                    
                if not guessedFunctionNames:
                    # Do not return empty matches. This happens if there's nothing left except wildcards.
                    return (None, None)
                        
                return (bestDepth, StackFramesSymptom({ "type": "stackFrames", 'functionNames' : guessedFunctionNames }))
        
        return (None, None)
    
    @staticmethod
    def _diff(stack, signatureGuess, startIdx, depth, maxDepth):     
        singleWildcardMatch = StringMatch("?")
        
        newSignatureGuess = []
        newSignatureGuess.extend(signatureGuess)
        
        bestDepth = None
        bestGuess = None
        
        for idx in range(startIdx,len(newSignatureGuess)):
            newSignatureGuess.insert(idx, singleWildcardMatch)
            
            # Check if we have a match with our modification
            if StackFramesSymptom._match(stack, newSignatureGuess):
                return (depth, newSignatureGuess)
            
            # If we don't have a match but we're not at our current depth limit,
            # add one more level of depth for our search.
            if depth < maxDepth:
                (newBestDepth, newBestGuess) = StackFramesSymptom._diff(stack, newSignatureGuess, idx, depth+1, maxDepth)
                
                if newBestDepth != None and (bestDepth == None or newBestDepth < bestDepth):
                    bestDepth = newBestDepth
                    bestGuess = newBestGuess
                    
            newSignatureGuess.pop(idx)
            
            # Now repeat the same with replacing instead of adding
            # unless the match at idx is a wildcard itself
            
            if str(newSignatureGuess[idx]) == '?' or str(newSignatureGuess[idx]) == '???':
                continue
            
            origMatch = newSignatureGuess[idx]
            newSignatureGuess[idx] = singleWildcardMatch
            
            # Check if we have a match with our modification
            if StackFramesSymptom._match(stack, newSignatureGuess):
                return (depth, newSignatureGuess)
            
            # If we don't have a match but we're not at our current depth limit,
            # add one more level of depth for our search.
            if depth < maxDepth:
                (newBestDepth, newBestGuess) = StackFramesSymptom._diff(stack, newSignatureGuess, idx, depth+1, maxDepth)
                
                if newBestDepth != None and (bestDepth == None or newBestDepth < bestDepth):
                    bestDepth = newBestDepth
                    bestGuess = newBestGuess
            
            newSignatureGuess[idx] = origMatch
         
        return (bestDepth, bestGuess)
    
    @staticmethod
    def _match(partialStack, partialFunctionNames):    
        # Process as many non-wildcard chars as we can find iteratively for performance reasons
        while partialFunctionNames and partialStack and str(partialFunctionNames[0]) != '?' and str(partialFunctionNames[0]) != '???':
            if not partialFunctionNames[0].matches(partialStack[0]):
                return False
            
            # Change the view on partialStack and partialFunctionNames without actually
            # modifying the underlying arrays. They have to be preserved for the caller.
            partialStack = partialStack[1:]
            partialFunctionNames = partialFunctionNames[1:]
            
        if not partialFunctionNames:
            # End of function names to match, accept
            return True    

        if str(partialFunctionNames[0]) == '?' or str(partialFunctionNames[0]) == '???':
            if StackFramesSymptom._match(partialStack, partialFunctionNames[1:]):
                # We recursively consumed 0 to N stack frames and can now
                # get a match for the remaining stack without the current
                # wildcard element, so we're done and accept the stack.
                return True
            else:
                if not partialStack:
                    # Out of stack to match, reject
                    return False
                
                if str(partialFunctionNames[0]) == '?':
                    # Recurse, consume one stack frame and the question mark
                    return StackFramesSymptom._match(partialStack[1:], partialFunctionNames[1:])
                else:
                    # Recurse, consume one stack frame and keep triple question mark
                    return StackFramesSymptom._match(partialStack[1:], partialFunctionNames)
        elif not partialStack:
            # Out of stack to match, reject
            return False