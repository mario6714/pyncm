# * Making the wheels again. I forgot that lrc parsers for python already exist while I was coding this lol
import re
from collections import defaultdict
from typing import Iterable
# region Static methods
# Timestamp parsers
def stamp2tag(timestamp):
    mm = int(timestamp / 60)
    ss = int((timestamp - mm * 60))
    xx = int((timestamp - mm * 60 - ss) * 100) # We'd use standard 100th of a second here
    mm,ss,xx = str(mm).rjust(2,'0'),str(ss).rjust(2,'0'),str(xx).rjust(2,'0')
    return f'{mm}:{ss}:{xx}'                    
def tag2stamp(IDTag):
    mm,ss = IDTag.split(':') 
    ss,xx = ss.split('.') # xx is hunderth of a second,but NE didn't think so
    timestamp = int(mm) * 60 + int(ss) + int(xx) * (0.1 ** len(xx)) # <- workaround
    return timestamp
# endregion

def LrcProperty(tagname):
    
    def wrapper(func):
        @property
        def _wrapper(self):
            if not hasattr(self,tagname):return Exception(tagname)
            try:
                return getattr(self,tagname)
            except:
                # So this is how we emurate all the attributes on startup
                # As no values are assigned (not inintalized),they will surely cause errors
                # Making it fallback to another value.Here,we fallback to its raw tagname
                return Exception(tagname)
        @_wrapper.setter
        def _wrapper(self,v):
            setattr(self,tagname,v)
        return _wrapper  
    return wrapper

class LrcRegexes:
    LIDTag_= re.compile(r'(?<=\[)[^\[\]]*(?=\])')
    LIDTag_Type = re.compile(r'[a-z]{2,}(?=:)')
    LIDTag_Content = re.compile(r'(?<=[a-z]{2}:).*')
    LLyrics_ = re.compile(r'(?<=\]).*')
    LBrackets = re.compile(r'(?<=\[).*(?=\])')

class LrcParser:
    '''
    Parses lrc into mutable Python objects
    '''
    # region Properties from Wikipedia [https://en.wikipedia.org/wiki/LRC_(file_format)]
    @LrcProperty('ar')
    def Artist(self):pass
    @LrcProperty('al')
    def Album(self):pass
    @LrcProperty('ti')
    def Title(self):pass
    @LrcProperty('au')
    def Author(self):pass
    @LrcProperty('length')
    def Length(self):pass
    @LrcProperty('by')
    def LRCAuthor(self):pass
    @LrcProperty('offset')
    def Offset(self):pass
    @LrcProperty('re')
    def Program(self):pass
    @LrcProperty('ve')
    def ProgramVersion(self):pass
    # endregion

    def __init__(self,lrc=''):
        '''
        Takes lyrics in `LRC` format,then provides lyrics based on timestamps
        '''
        # Parsing lrc,line by line
        def EmurateAttributes():
            for m in dir(self):
                if any(f in m for f in ['__','Add','Load','Clear','Find','Update','Dump']):continue
                yield (m,str(getattr(self,m)))        
        self.lrcAttributes = list(EmurateAttributes())
        # This function will only work when no attributes are defined
        self.lyrics = defaultdict(list)
        if not lrc:
            # empty input,we are creating lyrics then
            return
        else:self.LoadLrc(lrc)
    
    def LoadLrc(self,lrc):
        '''Loads a LRC formmated lryics file'''
        for line in lrc.split('\n'):
            IDTag           = ''.join(LrcRegexes.LIDTag_.findall(line))
            IDTagType       = ''.join(LrcRegexes.LIDTag_Type.findall(IDTag))
            IDTagContent    = ''.join(LrcRegexes.LIDTag_Content.findall(IDTag))
            Lyrics          = ''.join(LrcRegexes.LLyrics_.findall(line))
            if IDTagType:
                # Tag's type is set,write as class attribute
                setattr(self,IDTagType,IDTagContent)
            elif IDTag:
                # Tag's type is not set but we got the values,treat as lyrics
                # We'll use the timestamp (into seconds) as lyrics' keys,as hashtables can handle that
                timestamp = 0
                try:
                    timestamp = tag2stamp(IDTag)
                    if not isinstance(self.Offset,Exception):timestamp += float(self.Offset)
                except:
                    pass
                if Lyrics:self.lyrics[timestamp].append((IDTag,Lyrics)) # Ignore empty lines

    def AddLyrics(self,timestamp,value):
        # Add 1 or multiple line(s) of lyrics with the same timestamp in seconds 
        if not isinstance(value,list):value = [value]
        for v in value:self.lyrics[timestamp].append((stamp2tag(timestamp),v))

    def ClearLyrics(self):
        # Clears the lyrics buffer
        self.lyrics.clear()

    def UpdateLyrics(self,iterable,timestamp_function,lyrics_function):
        '''This function takes an iterable,a timestamp function,and a lyrics function
        
        And for every item in the iterable,timestamp and lyrics will be fetch via the said functions,then get added to our buffer
        '''
        for line in iterable:
            timestamp = timestamp_function(line)
            lyrics    = lyrics_function(line)
            self.AddLyrics(timestamp,lyrics)

    def DumpLyrics(self,delimiter='\t'):
        '''Format current lyrics buffer then spits out a LRC formatted string'''
        lrc = ''
        # Adding tags
        for prop,attr in self.lrcAttributes:
            value = getattr(self,prop)
            if not isinstance(value,Exception): # If such value do exist
                lrc += f'[{attr}:{value}]' + '\n'        
        # Adding lyrics
        for timestamps,lyrics in self.lyrics.items():
            IDTag,Lyrics = None,[]
            for _IDTag,_Lyrics in lyrics:
                IDTag = _IDTag
                Lyrics.append(_Lyrics)
            lrc += '\n' + f'[{IDTag}]{delimiter.join(Lyrics)}' 
        return lrc # Done

    def Find(self,timestamp):
        '''Finds closest match in our hashable
            
            Returns `(timestamp_seconds,lyrics,indexof)`

            Returns None if the match isn't inside the window
        '''
        # Again,this is very inefficient as its big o notation's linear O(n)
        timestamp,delta_m,bestmatch,index=int(timestamp),None,None,0
        for ts,lr in self.lyrics.items(): # ts:timestamp,lr:lyrics
            index += 1
            delta_m_1 = ts - timestamp
            if delta_m_1 <= 0: # only lyrics that are behind the timestamp
                if delta_m is None or abs(delta_m_1) <= delta_m:
                    # distance's lower,update
                    delta_m = abs(delta_m_1)
                    bestmatch = (ts,lr,index)
            if abs(delta_m_1) > delta_m:break # cutoff at where the distance got bigger
        return bestmatch