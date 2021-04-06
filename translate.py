import re
import os
import requests
import time
import json
import concurrent.futures
from pathlib import Path

token = json.load(open('token.json'))['token']

#Regex
pattern1 = re.compile(r'([一-龠ぁ-ゔァ-ヴーａ-ｚＡ-Ｚ０-９々〆〤～！？、…･・　」「”【】%\(\)\[\]0-9$]+)') #Main Matching Regex
pattern2 = re.compile(r'([一-龠ぁ-ゔァ-ヴー々〆〤～]+)') #Filter Matches with no Japanese Text

#Create Directory
Path("translate").mkdir(parents=True, exist_ok=True)

#Give Options to choose type of translation
choice = 0
while not(choice == '1' or choice == '2'):
    choice = input('Choose Translation Type:\n[1] Translate only matches\n[2] Translate entire line\n')

#Translate Via DeepL
def translate(text):
    payload = {'auth_key': token, 'source_lang':'JA', 'target_lang':'EN-US', 'tag_handling':'xml', 'text':text}
    r = requests.get('https://api.deepl.com/v2/translate', params=payload)
    return r.json()['translations'][0]['text']

def main():
    # Open File
    for filename in os.listdir("files"):
        with open('translate/' + filename, 'w', encoding='UTF-8') as outFile:
            with open('files/' + filename, 'r', encoding='UTF-8') as f:

                # Replace Each Line
                with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:

                    # The following submit all lines
                    fs = [executor.submit(findMatch, line) for line in f]

                    # as_completed return arbitrary future when it is done
                    # Use simple for-loop ensure the future are iterated sequentially
                    for future in fs:
                        # Uncomment to actually write to the output
                        outFile.write(future.result())


def findMatch(line):
    # Check if match in line
    if (re.search(pattern1, line) != None):

        # Translate each match in line. Depends on choice
        for match in re.findall(pattern1, line):

            # Filter out matches with no Japanese
            if (re.search(pattern2, match) != None and '$' not in match):
                if (choice == '1'):
                    match = match.rstrip()
                    print('Translating: ' + match + '\n')
                    translatedMatch = translate(match)
                    line = re.sub(match, translatedMatch, line, 1)

                elif (choice == '2'):
                    match = match.rstrip()
                    line = translate(line)
                    break  # Don't want dupes

                else:
                    print('Bad Coder. Check your if statements')

        return line
    # Skip Line
    else:
        print('Skipping: ' + line)

        return line

start = time.time()
main()
end = time.time()
print(end - start)