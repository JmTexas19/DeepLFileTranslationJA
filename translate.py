import re
import os
import requests
from pathlib import Path

#Regex
pattern = r'\[【.*】.*\].*'

#Translate Via DeepL
def translate(text):
    payload = {'auth_key':'506f08ed-1591-da37-fce5-b0e1cedd67b5', 'target_lang':'EN-US', 'text':text}
    r = requests.get('https://api.deepl.com/v2/translate', params=payload)
    return r.json()['translations'][0]['text']

translate('今日はこの窓だけ自由に開閉する。…これで、侵入は容易）')

#Create Directory
Path("translate").mkdir(parents=True, exist_ok=True)

#Open File
for filename in os.listdir("files"):
    with open('translate/' + filename, 'w') as outFile:
        with open ('files/' + filename, 'r', encoding='cp932') as f:

            #Replace Each Line
            for line in f:
                if(re.match(pattern, line) != None):
                    print('Translating ' + line)
                    line = re.sub(pattern, translate(line), line)
                    outFile.write(line)
                else:
                    outFile.write(line)

        print(filename + ' done.')


