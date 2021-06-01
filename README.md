# DeepLFileTranslationJA
Used to translate Japanese text in files using DeepL without breaking formatting.

## Instructions:
1. Add files you want translated in `files`
2. Replace AUTHKEY with your DeepL API token inside `tokentemplate.json` and rename file to `token.json`
3. Run the program. Translated files will be placed inside `translate`

## Notes:
* This isn't perfect and might output some stuff you have to fix manually.
* Translation is quick due to implementation of threads. Therefore be aware that translating a mass amount of text will expensive. Make sure you are careful with how much text you translate.
