import logging
import re, os, time, concurrent.futures
from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.remote_connection import logging
from selenium.webdriver.support.ui import WebDriverWait

#Globals`
THREADS = 5    #Number of threads to create
translationObjList = [None] * THREADS
bannedWordsList = []
choice = None

#Logging
logging.getLogger().setLevel('INFO')

#Selenium
options = Options()
options.headless = True
options.add_argument("--disable-web-security")
options.add_argument('log-level=2')

#Regex
pattern1 = re.compile(r'(?<=[\"])[一-龠ぁ-ゔァ-ヴーａ-ｚＡ-Ｚ０-９々〆〤～ｾｸﾊﾗ！？＋（）【】、↑<>…･・。◎◆×♥★=　”゛0-9A-Za-z.?!;&/^%$#@*_+\-\\\[\]\(\)\"\'\ ]+(?=[\"])') #Main Matching Regex
pattern2 = re.compile(r'([一-龠ぁ-ゔァ-ヴー々〆〤～ｾｸﾊﾗ]+)') #Filter Matches with no Japanese Text
pattern3 = re.compile(r'([\\]+[a-zA-Z0-9]+\[[0-9]+\]|[\\]+[a-zA-Z]+<[\\]+[a-zA-Z]+\[[0-9]+\]>|[\\]+[a-zA-Z]+<[-a-zA-Z]+.[\\]+.|[:%A-Za-z\=\-\+\/\\[\]\\\"\>\<]+)') #Filter for variables (e.g \\n[2])

#Class to hold translation data
class translationObj:
    variableList = []
    text = ''
    lock = 0
    filterVarCalled = 0
    driver = None

    def __init__(self):
        driver = webdriver.Chrome('chromedriver.exe', options=options)
        driver.set_page_load_timeout(15)
        driver.implicitly_wait(15) 
        self.driver = driver  

    #Assign driver if not locked
    def getDriver(self):
        if (self.lock == 0):
            self.lock = 1
            return self.driver
        else:
            return None
    
    def release(self):
        self.lock = 0

##--------------MAIN--------------##
def main():
    global choice
    #Give Options to choose type of translation
    while not(choice == '1' or choice == '2' or choice == '3'):
        choice = input('Choose Translation Type:\n[1] Translate only matches\n[2] Translate entire line\n')

    #Create Directory and Drivers
    Path("translate").mkdir(parents=True, exist_ok=True)
    createDrivers()

    #Single Translation
    if(choice == '3'):
        translate('実際、この日まで\\n[10]は\"人間の男\"とはセックスどころか、')
        quit()
        
    # Open File
    for filename in os.listdir("files"):
        with open('translate/' + filename, 'w', encoding='UTF-8') as outFile:
            with open('files/' + filename, 'r', encoding='UTF-8') as f:

                # Replace Each Line
                with concurrent.futures.ThreadPoolExecutor(max_workers=THREADS) as executor:

                    # The following submits all lines
                    fs = [executor.submit(findMatch, line) for line in f]

                    # as_completed return arbitrary future when it is done
                    # Use simple for-loop ensure the future are iterated sequentially
                    for future in fs:
                        outFile.write(future.result())

    #Close Drivers
    for obj in translationObjList:
        obj.driver.close()
        obj.driver.quit()

#Create drivers for translation based on THREADS
def createDrivers():
    for i in range(len(translationObjList)):
        translationObjList[i] = translationObj()

#Translate Via DeepL
def translate(text):
    try:         
        #Assign object to thread
        tO = None
        driver = None
        while(tO == None):
            for obj in translationObjList:
                if(obj.lock == 0):
                    tO = obj
                    tO.text = text
                    driver = tO.getDriver()
                    break   

        doOnce = 0
        while("Content message" in tO.text or doOnce == 0):
            #Get Page and Translate
            logging.info('Translating: ' + tO.text + ' using driver ' + str(driver))
            tO = filterVariables(tO)
            url = 'https://www.deepl.com/translator#ja/en/' + tO.text
            driver.get(url)

            #Wait until translation is finished loading
            match = WebDriverWait(driver, 5).until(lambda driver: 
                re.search(r'^(?!\s*$).+', driver.find_element_by_id('target-dummydiv').get_attribute("innerHTML"))
            )
            doOnce = 1

        #Clean
        tO.text = match.group()
        tO = filterVariables(tO)
        tO.filterVarCalled = 0
        tO.release()
            
        return tO.text
        
    except TimeoutException:
        logging.error('Failed to find translation for line: ' + tO.text)
        tO = filterVariables(tO)
        tO.release()

        return tO.text

#Filter variables from string, then put back
def filterVariables(tO):
    #Quick Strip
    tO.text = tO.text.strip()
    tO.text = tO.text.replace('。', '.')
    tO.text = re.sub(r'(?<=[^\.])\.', '', tO.text)
    tO.text = re.sub(r'[…]+', '...', tO.text)
    tO.text = re.sub(r'(?<!\\)"', '', tO.text)
    tO.text = tO.text.replace('\u3000', ' ')
    tO.text = tO.text.replace('！', '')

    #1. Replace variables and translate. 
    if(re.search(pattern3, tO.text) != None and tO.filterVarCalled == 0):
        tO.variableList = re.findall(pattern3, tO.text)
        i = 0
        for var in tO.variableList:
            tO.text = tO.text.replace(var, '{' + str(i) + '}', 1)
            i += 1

        tO.filterVarCalled = 1
        return tO

    #2. Replace placeholders.
    elif(re.search(r'{[0-9]+}', tO.text)):
        i = 0
        for var in tO.variableList:
            tO.text = tO.text.replace('{' + str(i) + '}', var)
            i += 1

        tO.text = tO.text.replace('\\', '\\\\')
        tO.filterVarCalled = 1
        return tO

    #Easy translation. Replace Nothing.
    tO.filterVarCalled = 1
    tO.text = tO.text.replace('\\', '\\\\')
    return tO

def findMatch(line):
    # Check if match in line
    if (re.search(pattern1, line) != None):

        # Translate each match in line. Depends on choice
        for match in re.findall(pattern1, line):

            # Filter out matches with no Japanese
            if (re.search(pattern2, match) and not any(word in match for word in bannedWordsList) and '' != match):
                if (choice == '1'):
                    translatedMatch = translate(match)
                    line = re.sub(r'(?<!\w)' + re.escape(match) + r'(?!\w)', translatedMatch, line, 1)

                elif (choice == '2'):
                    line = translate(match)
                    break  # Don't want dupes

                else:
                    logging.error('Choice Variable is an invalid value')
                    
        return line
    # Skip Line
    else:
        logging.info('Skipping: ' + line)
        return line

#Call Main and get time
start = time.time()
main()
end = time.time()
logging.info(str(end - start) + ' seconds')