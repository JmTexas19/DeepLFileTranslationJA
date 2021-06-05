import re, os, requests, time, json, concurrent.futures
from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from lxml import html

#Regex
pattern1 = re.compile(r'([一-龠ぁ-ゔァ-ヴーａ-ｚＡ-Ｚ０-９々〆〤～！？＋、<>…･・。♥　”゛【】%0-9A-Za-z\\\[\] ]+)') #Main Matching Regex
pattern2 = re.compile(r'([一-龠ぁ-ゔァ-ヴー々〆〤]+)') #Filter Matches with no Japanese Text
pattern3 = re.compile(r'([\\]+[a-zA-Z0-9]+\[[0-9]+\]|[\\]+[a-zA-Z]+<[\\]+[a-zA-Z]+\[[0-9]+\]>|[\\]+[a-zA-Z]+<[-a-zA-Z]+.[\\]+.|[\\]+>)') #Filter for variables (e.g \\n[2])

#Create Directory
Path("translate").mkdir(parents=True, exist_ok=True)

#Give Options to choose type of translation
choice = 0
while not(choice == '1' or choice == '2' or choice == '3'):
    choice = input('Choose Translation Type:\n[1] Translate only matches\n[2] Translate entire line\n')

class textObject:
    variableList = []
    text = ''

#Translate Via DeepL
def translate(text):
    #Selenium
    options = Options()
    options.headless = True
    driver = webdriver.Chrome('chromedriver.exe', options=options)

    #Assign to new object
    tO = textObject()
    tO.text = text

    #Get Page and Translate
    tO = filterVariables(tO)
    url = 'https://www.deepl.com/translator#ja/en/' + tO.text
    driver.get(url)

    #Wait until translation is finished loading
    try:
        match = WebDriverWait(driver, 10).until(lambda driver: 
            re.search(r'^(?!\s*$).+', driver.find_element_by_id('target-dummydiv').get_attribute("innerHTML"))
        )
    except TimeoutException:
        print('Failed to find translation')
        time.sleep(10)
        driver.close()
        filterVariables(tO)

    tO.text = match.group()
    tO.text = tO.text.strip()
    tO = filterVariables(tO)
    driver.close()
    return tO.text

#Filter variables from string, then put back
def filterVariables(tO):
    #1. Replace stars and placeholders and finish
    if('*' in tO.text):
        tO.text = tO.text.replace('*', '\\')
        tO.text = tO.text.replace('.', '')

        if('^' in tO.text):
            i = 0
            for var in tO.variableList:
                tO.text = tO.text.replace(str(i) + '^', var, 1)
                i += 1

        return tO

    #2 No stars, replace placeholders.
    if('var' in tO.text):
        i = 0
        for var in tO.variableList:
            tO.text = tO.text.replace(str(i) + 'var', var, 1)
            i += 1

        return tO

    #3 No stars and placeholders. Replace variables and backslashes and translate. 
    if(re.search(pattern3, tO.text) != None):
        tO.variableList = re.findall(pattern3, tO.text)
        i = 0
        for var in tO.variableList:
            tO.text = tO.text.replace(var, str(i) + 'var', 1)
            i += 1

        if('\\' in tO.text):
            tO.text = tO.text.replace('\\', '')

        return tO
    
    #4 No variables, replace backslashes and translate.
    if('\\' in tO.text):
        tO.text = tO.text.replace('\\', '*')    
        return tO

    #5 Easy translation. Replace Nothing.
    return tO

def main():
    if(choice == '3'):
        translate('実際、この日まで\\n[10]は\"人間の男\"とはセックスどころか、')
        quit()
        

    # Open File
    for filename in os.listdir("files"):
        with open('translate/' + filename, 'w', encoding='UTF-8') as outFile:
            with open('files/' + filename, 'r', encoding='UTF-8') as f:

                # Replace Each Line
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:

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
            if (re.search(pattern2, match)):
                if (choice == '1'):
                    print('Translating: ' + match + '\n')
                    translatedMatch = translate(match)
                    line = line.replace(match, translatedMatch, 1)

                elif (choice == '2'):
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