# DeepLFileTranslationJA
Translate Japanese text in files using DeepL without breaking syntax.

## Instructions:
1. Add files you want translated in `files`
2. Replace AUTHKEY with your Microsoft Azure API token inside `tokentemplate.json` and rename file to `token.json`
3. Run the program. Translated files will be placed inside `translate`

## Notes:
* Microsoft Azure translation is strictly for small words (less than 6 characters) because DeepL is not very good at it.
