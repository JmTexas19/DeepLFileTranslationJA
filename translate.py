import re
import os
import requests
from pathlib import Path

#Regex
pattern = re.compile('([一-龠ぁ-ゔァ-ヴーａ-ｚＡ-Ｚ０-９々〆〤～！、･]+)')

#Translate Via DeepL
def translate(text):
    payload = {'auth_key':'de51ca71-bb2c-cd05-fe93-a1ebe014cd56', 'source_lang':'JA', 'target_lang':'EN-US', 'text':text}
    response = line
    while(re.search(pattern, response) != None):
        r = requests.get('https://api.deepl.com/v2/translate', params=payload)
        response = r.json()['translations'][0]['text']
        print(response)
    return response    

#Create Directory
Path("translate").mkdir(parents=True, exist_ok=True)

#Give Options to choose type of translation
choice = 0
while not(choice == '1' or choice == '2'):
    choice = input('Choose Translation Type:\n[1] Translate only matches\n[2] Translate entire line\n')

#Open File
try:
    for filename in os.listdir("files"):
        with open('translate/' + filename, 'w', encoding='UTF-8') as outFile:
            with open ('files/' + filename, 'r', encoding='UTF-8') as f:
                print('Translating ' + filename + '...')
                count = 0

                #Replace Each Line
                for line in f:
                    count = count + 1   #Keep track of lines for debugging

                    #Check if match in line
                    if(re.search(pattern, line) != None):

                        #Translate each match in line. Depends on choice
                        for match in re.findall(pattern, line):
                            if(choice == '1'):
                                print('Translating: ' + str(count) + ': ' + match)
                                translatedMatch = translate(match)
                                line = re.sub(match, translatedMatch, line)

                            elif(choice == '2'):
                                print('Translating: ' + str(count) + ': ' + match)
                                line = translate(line)
                                break       #Don't want dupes

                            else:
                                print('Bad Coder. Check your if statements')

                        outFile.write(line)
                    #Skip Line
                    else:
                        print('Skipping: ' + str(count))
                        outFile.write(line)

            print(filename + ' done.')
except ValueError:  # includes simplejson.decoder.JSONDecodeError
    print('Decoding JSON has failed')

    


