import logging
import undetected_chromedriver.v2 as uc
import re, os, time, concurrent.futures
from pathlib import Path
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.remote_connection import logging
from selenium.webdriver.support.ui import WebDriverWait

#Globals`
THREADS = 4    #Number of threads to create
translationObjList = [None] * THREADS
bannedWordsList = []
choice = None

#Logging
logging.getLogger().setLevel('INFO')

#Regex
pattern1 = re.compile(r'((?:[^\\\"]|\\.)*?)[\"\'<>]') #Match ANY in quotes
pattern2 = re.compile(r'([\u3040-\u309F\u30A0-\u30FF\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A\u2E80-\u2FD5\uFF5F-\uFF9F\u3000-\u303F\u31F0-\u31FF\u3220-\u3243\u3280-\u337F\uFF40-\uFF5E\u2000-\u206F\u2600-\u26FF]+)') #Match ANY JA Text
pattern3 = re.compile(r'[\:\%\=\-\+\/\[\]\"\'\>\<]?[\\\/]+[a-zA-Z0-9_\<\>\"\'\:\;\\\/\[\]\(\)]+|\>\\[a-zA-Z]\<|[^\u3040-\u309F\u30A0-\u30FF\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A\u2E80-\u2FD5\uFF5F-\uFF9F\u31F0-\u31FF\u3220-\u3243\u3280-\u337F\uFF40-\uFF5E\u2600-\u26ff\u2190-\u21FF\u0080-\u00FF\u2150-\u218F\u25A0-\u25FF\u2000-\u206F\u0020\w\\,.!?]+|[\\]+') #Match ANY Symbol or Variable

#Class to hold translation data
class translationObj:
    variableList = []
    text = ''
    lock = 0
    filterVarCalled = 0
    driver = None
    doOnce = 0

    def __init__(self):
        #Selenium
        options = uc.ChromeOptions()
        options.add_argument('log-level=2')
        options.add_argument('--no-first-run --no-service-autorun --password-store=basic')
        driver = uc.Chrome(options=options)
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
    while not(choice == '1' or choice == '2'):
        choice = input('Choose Translation Type:\n[1] Translate Files\n[2] Single Translation\n')

    #Create Directory and Drivers
    Path("translate").mkdir(parents=True, exist_ok=True)
    createDrivers()

    #Single Translation
    if(choice == '2'):
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

        #Filter
        tO = filterVariables(tO)

        #DEEPL
        if(len(text) > 3):
            tO.doOnce = 0
            while("Content message" in tO.text or tO.doOnce == 0):
                #Get Page and Translate
                logging.info('DEEPL: ' + tO.text + ' using driver ' + str(driver))
                url = 'https://www.deepl.com/translator#ja/en/' + tO.text
                driver.get(url)

                #Wait until translation is finished loading
                match = WebDriverWait(driver, 10).until(lambda driver: 
                    re.search(r'^(?!\s*$).+', driver.find_element_by_id('target-dummydiv').get_attribute("innerHTML"))
                )
                tO.doOnce = 1
        
        #GoogleTL
        else:
            tO.doOnce = False
            while("Content message" in tO.text or tO.doOnce == 0):
                #Get Page and Translate
                logging.info('GOOGLE: ' + tO.text + ' using driver ' + str(driver))
                url = 'https://translate.google.com/?sl=ja&tl=en&text=' + tO.text + '&op=translate'
                driver.get(url)

                #Wait until translation is finished loading
                match = WebDriverWait(driver, 10).until(lambda driver: 
                    re.search(r'^(?!\s*$).+', driver.find_element_by_xpath('//*[@jsname="W297wb"]').get_attribute("innerHTML"))
                )
                tO.doOnce = 1

        #Clean
        tO.text = match.group()
        tO = filterVariables(tO)
        tO.filterVarCalled = 0
        tO.release()
        
        #Final QA
        tO.text = tO.text.replace('[ ', '[')
        tO.text = tO.text.replace(' ]', ']')
        tO.text = tO.text.replace('( ', '(')
        tO.text = tO.text.replace(' )', ')')
        tO.text = tO.text.replace('< ', '<')
        tO.text = tO.text.replace(' >', '>')
            
        return tO.text
        
    except TimeoutException:
        driver.save_screenshot('fail/' + str(driver)+ '.png')
        logging.error('Failed to find translation for line: ' + tO.text)
        tO.release()

        return tO.text

#Filter variables from string, then put back
def filterVariables(tO):
    #Quick Strip
    tO.text = tO.text.strip()
    tO.text = tO.text.replace('。', '.')
    tO.text = tO.text.replace('、', ',')
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

        tO.text = tO.text.replace('{', '[')
        tO.text = tO.text.replace('}', ']')
        tO.filterVarCalled = 1
        return tO

    #2. Replace placeholders.
    elif(re.search(r'{[0-9}+]', tO.text)):
        i = 0
        for var in tO.variableList:
            tO.text = tO.text.replace('[' + str(i) + ']', var)
            i += 1

        tO.text = re.sub(r'(?<=[^\.])\.', '', tO.text)
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
            if (re.search(pattern2, match) and re.search(r'^[a-zA-Z0-9_]', match) == None):   #Skip command plugins such as TE: or ParaAdd
                if (choice == '1'):
                    #Scrape off the crust
                    match = re.sub(r'^<?[^\u3040-\u309F\u30A0-\u30FF\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A\u2E80-\u2FD5\uFF5F-\uFF9F\u3000-\u303F\u31F0-\u31FF\u3220-\u3243\u3280-\u337F\uFF40-\uFF5E\u2000-\u206F\u2605-\u2606a-zA-Z0-9]+|[^\u3040-\u309F\u30A0-\u30FF\u3400-\u4DB5\u4E00-\u9FCB\uF900-\uFA6A\u2E80-\u2FD5\uFF5F-\uFF9F\u3000-\u303F\u31F0-\u31FF\u3220-\u3243\u3280-\u337F\uFF40-\uFF5E\u2000-\u206F\u2605-\u2606a-zA-Z0-9]+>?$', '', match)

                    if(match != ''):
                        translatedMatch = translate(match)
                        line = line.replace('\\', '\\\\')
                        line = re.sub(r"\b" + match + r"\b", translatedMatch, line)

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