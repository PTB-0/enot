words = []
class word : 
    def __init__(self,stringOf,listOfWrongs = []):
        self.listOfWrongs = listOfWrongs
        self.stringOf = stringOf
        words.append(self)
    def addWrong(self,wrong) :
        self.listOfWrongs.append(wrong)
    def giveWord(self) :
        return self.stringOf
def api(yourWord):
    o = ["l","p","ş","ı","0","9"]
    for word in words :
        count = 0
        localWord = word.giveWord()
        wordsLocal = localWord.split("")
        yourLocal = yourWord.split("")
        localWord = localWord.lower()
        yourLocal = yourLocal.lower()
        for i in range(wordsLocal):
            if yourLocal[i] == wordsLocal[i] :
                count += 5 
            else :
                if wordsLocal[i] == "o" :
                    if wordsLocal[i] in o :
                        count += 1
    